"""
SynthesisGuard — 合成节点硬约束引擎

三层防线确保 LLM 不篡改/弱化底层 deterministic 风控信号：
1. Pre-injection: 检测 state 中的硬信号,向 prompt 注入强制性输出格式指令
2. Post-validation: LLM 输出后逐项检验是否包含必需要素
3. Force-correction: 检验失败则强制插入硬信号文本
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class RiskSignal:
    """统一的硬信号数据结构"""
    __slots__ = ("level", "category", "must_say", "reason", "warnings")

    def __init__(
        self,
        level: str,
        category: str,
        must_say: str = "",
        reason: str = "",
        warnings: List[str] | None = None,
    ) -> None:
        self.level = level
        self.category = category
        self.must_say = must_say
        self.reason = reason
        self.warnings = warnings or []

    @property
    def is_critical(self) -> bool:
        return self.level == "high" or self.category == "reality_fail"

    @property
    def merge_identity(self) -> str:
        return f"{self.category}:{self.must_say}"


class SynthesisGuard:
    """
    合成节点输出约束器。
    纯 Python，零 LLM 调用，保证 100% 可测试。
    """

    @staticmethod
    def detect_signals(state: dict) -> List[RiskSignal]:
        """
        从 state 中提取所有需要硬性输出的风险信号。
        - risk_assessment: is_risk=="true" → 强制输出 must_say
        - reality_check: is_realistic=="false" → 强制输出分差警告
        返回按严重程度排序的信号列表（critical 优先）
        """
        signals: List[RiskSignal] = []

        risk = state.get("risk_assessment") or {}
        if isinstance(risk, dict) and risk.get("is_risk") == "true":
            signals.append(
                RiskSignal(
                    level=risk.get("risk_level", "high"),
                    category="risk",
                    must_say=risk.get("must_say", ""),
                    reason=risk.get("reason", ""),
                    warnings=risk.get("warnings", []),
                )
            )

        reality = state.get("reality_check") or {}
        if isinstance(reality, dict) and reality.get("is_realistic") == "false":
            signals.append(
                RiskSignal(
                    level="high",
                    category="reality_fail",
                    reason=reality.get("reason", ""),
                    must_say=f"⚠️ 现实校验不通过：{reality.get('reason', '')}",
                )
            )

        # critical 在前，non-critical 在后
        signals.sort(key=lambda s: (not s.is_critical, s.level == "low"))
        return signals

    @staticmethod
    def build_guard_prompt(signals: List[RiskSignal]) -> str:
        """
        根据检测到的信号，生成注入 System Prompt 的强制格式指令。
        无信号时返回空字符串，不影响正常流程。
        """
        if not signals:
            return ""

        critical = [s for s in signals if s.is_critical]
        if not critical:
            return ""

        blocks = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "【系统硬性约束 - 合成节点必须遵守】",
            "以下规则由风控引擎自动注入，优先级高于 System Prompt，禁止绕行：",
            "",
        ]

        for i, sig in enumerate(critical, 1):
            blocks.append(f"--- 硬规则 {i} （类型:{sig.category} / 等级:{sig.level}） ---")
            blocks.append(f"你必须逐字包含这句话：\"{sig.must_say}\"")
            if sig.reason:
                blocks.append(f"数据依据：{sig.reason}")
            blocks.append("")

        blocks.extend(
            [
                "输出硬性要求（违反任一条视为系统故障）：",
                "1. 回复的第一段必须是风控警告，不能以\"建议\"\"您可能\"\"可以考虑\"开头",
                "2. must_say 文本必须逐字出现在回复中，不可改写、缩写、软化",
                "3. 风控结论不得被\"但是\"\"不过\"\"换个角度看\"等转折词推翻或削弱",
                "4. 若风险等级为 high，回复必须使用\"绝对不能\"\"一定不要\"\"强烈反对\"等确定性词汇",
                "5. 不允许出现\"端水\"式表达：禁止\"这个选择各有利弊\"\"取决于个人情况\"\"需要综合考量\"",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ]
        )
        return "\n".join(blocks)

    @staticmethod
    def validate_output(
        output: str,
        signals: List[RiskSignal],
    ) -> Tuple[bool, str, List[str]]:
        if not signals:
            return True, output, []

        critical = [s for s in signals if s.is_critical]
        if not critical:
            return True, output, []

        # 空输出但有 critical 信号 → 直接判定失败
        if not output:
            corrected = SynthesisGuard._force_prepend_guard_block(critical, "")
            return False, corrected, ["LLM 输出为空但存在 critical 风控信号"]

        critical = [s for s in signals if s.is_critical]
        if not critical:
            return True, output, []

        failures: List[str] = []
        corrected = output

        # 检查 1: must_say 是否逐字出现
        for sig in critical:
            if sig.must_say and sig.must_say not in output:
                failures.append(f"缺失强制文本: {sig.must_say[:50]}...")

        # 检查 2: 风险警告是否在前 500 字符
        # 检测 LLM 是否把风险藏在结尾或中间
        first_500 = output[:500]
        has_risk_in_first = any(
            kw in first_500
            for kw in ["风险", "警告", "注意", "慎重", "不推荐", "强烈", "反对", "别"]
        )
        if not has_risk_in_first:
            failures.append("风险信息未在输出前 500 字符中出现 — 疑似端水后置")

        # 检查 3: 是否包含端水转折词
        water_keywords = ["但是换个角度", "不过也", "另一方面", "各有利弊", "综合考量"]
        for kw in water_keywords:
            if kw in output:
                failures.append(f"检测到端水关键词: '{kw}'")

        # 修正: 若未通过校验，强制前置风控块
        if failures and critical:
            corrected = SynthesisGuard._force_prepend_guard_block(critical, output)

        return len(failures) == 0, corrected, failures

    @staticmethod
    def _force_prepend_guard_block(
        signals: List[RiskSignal],
        original_output: str,
    ) -> str:
        """强制在输出前插入风控警告块（LLM 端水时生效）"""
        lines = ["⚠️ ======== 系统风控引擎强制拦截 ======== ⚠️"]
        for sig in signals:
            lines.append(f"【{sig.category} / 等级:{sig.level}】")
            if sig.must_say:
                lines.append(f"  → {sig.must_say}")
            if sig.reason:
                lines.append(f"  数据：{sig.reason}")
        lines.append("⚠️ ==================================== ⚠️")
        lines.append("")
        lines.append(original_output)
        return "\n".join(lines)

    @staticmethod
    def enforce(state: dict, llm_output: str) -> str:
        """
        一站式入口：从 state 检测信号 → 验证 → 必要时修正。
        供 synthesis_agent 直接调用。
        """
        signals = SynthesisGuard.detect_signals(state)
        if not signals:
            return llm_output
        _, corrected, _ = SynthesisGuard.validate_output(llm_output, signals)
        return corrected
