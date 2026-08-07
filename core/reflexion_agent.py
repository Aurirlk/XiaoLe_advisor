"""
自我反思 Agent（蓝图 Phase 3.2，2026-08-06 重建）

职责：输出质量评估 → 问题识别 → 改进建议 → 迭代优化（循环推理）。
蓝图要求集成到 match_agent 和 career_agent，并具备反思记忆。

背景：本文件曾因"零引用"被误删（前几轮死代码清理），实为蓝图
「多智能体协作体系」核心组件，本次按蓝图重建。

设计：
1. ReflexionAgent 接收"查询 + 初版输出"，判断质量（确定性规则 + 可选 LLM 复核）
2. 不满意时生成改进提示（reflection），允许重试（max_reflections 次）
3. 反思记忆（ReflectionMemory）：按主题存"问题-改进"对，后续同类查询直接复用
4. 零 LLM 依赖路径：纯规则评估（数据完整性/关键要素/冲突标记）保证可离线测试；
   LLM 复核为可选增强（use_llm=True 时调用）

用法：
    agent = ReflexionAgent(max_reflections=2)
    final, meta = await agent.reflect(
        query="临床医学就业前景", output="医学就业不错",
        context={"sql_results": [...], "scene": "career"},
    )
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 反思记忆保留上限（防无限增长；按主题 LRU 裁剪）
_MEMORY_LIMIT_PER_TOPIC = 20


@dataclass
class ReflectionMemory:
    """反思记忆：按主题记录「问题-改进」对，后续同类查询直接复用改进建议"""
    _store: Dict[str, Deque[Dict[str, Any]]] = field(default_factory=lambda: defaultdict(deque))

    def add(self, topic: str, issue: str, suggestion: str) -> None:
        entry = {"issue": issue, "suggestion": suggestion, "ts": time.time()}
        q = self._store[topic]
        q.append(entry)
        while len(q) > _MEMORY_LIMIT_PER_TOPIC:  # LRU 裁剪最旧
            q.popleft()

    def get_suggestions(self, topic: str) -> List[str]:
        return [e["suggestion"] for e in self._store.get(topic, [])]

    def has_prior_failures(self, topic: str) -> bool:
        return len(self._store.get(topic, [])) > 0

    def size(self) -> int:
        return sum(len(q) for q in self._store.values())


@dataclass
class ReflectionResult:
    output: str                        # 最终输出（可能是重试后的）
    reflections: int                   # 实际反思次数
    satisfied: bool                    # 是否达到质量要求
    issues: List[str] = field(default_factory=list)   # 识别到的问题
    suggestions: List[str] = field(default_factory=list)  # 改进建议


class ReflexionAgent:
    """自我反思循环：评估 → 改进 → 重试（上限内）→ 记忆沉淀"""

    # 必含要素（按领域判断输出是否覆盖关键信息）
    _REQUIRED_ELEMENTS = {
        "career": ["就业", "前景"],
        "match": ["分数", "位次"],
        "gaokao": ["分数", "位次", "院校"],
        "default": [],
    }

    def __init__(
        self,
        max_reflections: int = 2,
        llm=None,
        use_llm: bool = False,
        memory: ReflectionMemory | None = None,
    ) -> None:
        self.max_reflections = max(0, max_reflections)
        self.llm = llm
        self.use_llm = bool(use_llm) and llm is not None
        self.memory = memory or ReflectionMemory()

    # ── 评估（确定性规则，可离线）────────────────────────────

    def _evaluate(self, query: str, output: str, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """返回 (是否满意, 问题列表)。

        规则（零 LLM 依赖）：
        1. 输出为空/过短 → 不满意
        2. 有工具结果但输出未引用任何数据 → 不满意（"有料没用"）
        3. 领域必含要素缺失 → 不满意
        4. 上下文有 risk 标记（风控冲突）→ 提示但不算硬失败
        """
        issues: List[str] = []
        text = (output or "").strip()
        if not text:
            issues.append("输出为空")
        elif len(text) < 20:
            issues.append("输出过短，信息量不足")

        scene = context.get("scene") or context.get("scene_type") or "default"
        required = self._REQUIRED_ELEMENTS.get(scene, self._REQUIRED_ELEMENTS["default"])
        for elem in required:
            if elem and elem not in text:
                issues.append(f"缺少关键要素「{elem}」")

        # 有工具结果但输出没引用
        tool_results = context.get("sql_results") or context.get("tool_results") or []
        if tool_results and not any(
            str(getattr(r, "get", lambda k, d=None: d)("university_name", "") or r.get("text", "") if isinstance(r, dict) else r)
            for r in tool_results[:3]
        ):
            # 简化判断：只要有工具结果且输出不含"分/位次/院校"任一，标记"未引用数据"
            if not any(k in text for k in ("分", "位次", "院校", "薪资", "就业")):
                issues.append("有工具结果但输出未引用数据")

        risk = context.get("risk_assessment") or {}
        if risk and risk.get("level") in ("high", "critical"):
            issues.append("存在高风险风控标记，建议复核")

        return len(issues) == 0, issues

    def _suggest(self, query: str, output: str, issues: List[str], topic: str) -> List[str]:
        """根据问题生成改进建议（规则化）。"""
        suggestions: List[str] = []
        for issue in issues:
            if "为空" in issue or "过短" in issue:
                suggestions.append("请补充具体数据支撑（分数/位次/院校/就业数据），避免空泛。")
            elif "关键要素" in issue:
                elem = issue.split("「")[1].split("」")[0]
                suggestions.append(f"请在回答中明确覆盖「{elem}」相关内容。")
            elif "未引用数据" in issue:
                suggestions.append("请基于检索到的工具结果给出结论，并标注数据来源。")
            elif "风控" in issue:
                suggestions.append("请降低风险表述，明确标注不确定性。")
        # 复用历史记忆中的改进建议
        suggestions.extend(self.memory.get_suggestions(topic))
        return suggestions[:4]

    # ── 核心：反思循环 ──────────────────────────────────────

    async def reflect(
        self,
        query: str,
        output: str,
        context: Dict[str, Any] | None = None,
        topic: str = "default",
        regenerate=None,
    ) -> ReflectionResult:
        """执行反思循环。

        regenerate: 可选 async 回调 (query, reflection_hint, context) -> str，
            用于重试时让上层重新生成输出；None 时只评估不改写（纯质量门）。

        topic: 反思记忆的主题键。缺省时自动从 context 的场景推导
        （scene/scene_type/career/match），保证同类查询共享记忆。
        """
        context = context or {}
        if topic == "default":
            topic = (
                context.get("scene")
                or context.get("scene_type")
                or "default"
            )
        current = output or ""
        reflections = 0
        issues: List[str] = []

        for attempt in range(self.max_reflections + 1):
            satisfied, issues = self._evaluate(query, current, context)
            if satisfied:
                break
            reflections = attempt + 1
            if regenerate is None or attempt >= self.max_reflections:
                break
            suggestions = self._suggest(query, current, issues, topic)
            reflection_hint = "；".join(suggestions) if suggestions else "提升回答质量与数据支撑"
            logger.info("[Reflexion] %s 第 %d 次反思，问题=%s", topic, attempt + 1, issues)
            try:
                current = await regenerate(query, reflection_hint, context)
            except Exception:
                logger.warning("[Reflexion] 重新生成失败，保留上一版输出", exc_info=True)
                break

        # 记忆沉淀：仍有问题则记录（供未来同类查询）
        if issues:
            for issue in issues:
                sug = self._suggest(query, current, [issue], topic)
                if sug:
                    self.memory.add(topic, issue, sug[0])

        return ReflectionResult(
            output=current,
            reflections=reflections,
            satisfied=not issues,
            issues=issues,
            suggestions=self._suggest(query, current, issues, topic),
        )
