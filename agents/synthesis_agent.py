from pathlib import Path
import json
import logging
from datetime import datetime, timezone, timedelta
from functools import lru_cache

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from core.state_schema import GraphState
from core.synthesis_guard import SynthesisGuard
from skills.decision_heuristics import summarize_decision_hints, generate_progressive_questions
from skills.reason_generator import ReasonGenerator

ROOT = Path(__file__).resolve().parents[1]
ZX_PROMPT_PATH = ROOT / "configs" / "prompts" / "zx_system_prompt.md"
FALLBACK_PROMPT_PATH = ROOT / "configs" / "prompts" / "synthesis_system_prompt.txt"
PATCHES_PATH = ROOT / "configs" / "synthesis_patches.yaml"

logger = logging.getLogger(__name__)


def _load_synthesis_prompt() -> str:
    if ZX_PROMPT_PATH.exists():
        return ZX_PROMPT_PATH.read_text(encoding="utf-8")
    return FALLBACK_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_feedback_patches() -> list[dict]:
    """读取反馈补丁（P0-7：进程内缓存，避免每请求读盘；改动后调用 clear_feedback_patches_cache）"""
    if not PATCHES_PATH.exists():
        return []
    data = yaml.safe_load(PATCHES_PATH.read_text(encoding="utf-8")) or {}
    return data.get("patches", []) or []


def clear_feedback_patches_cache() -> None:
    _load_feedback_patches.cache_clear()


def _build_patch_inject(tags: list[str]) -> str:
    if not tags:
        return ""
    patches = _load_feedback_patches()
    injects: list[str] = []
    tag_set = set(tags)
    for patch in patches:
        trigger_tags = set(patch.get("trigger_tags") or [])
        if trigger_tags & tag_set:
            injects.append(str(patch.get("inject", "")).strip())
    return "\n".join(item for item in injects if item)


def build_synthesis_agent(llm: ChatOpenAI, feedback_store=None, xuefeng_store=None):
    async def synthesis_agent(state: GraphState) -> GraphState:
        sql_results = state.get("sql_results", [])
        risk = state.get("risk_assessment", {})
        reality = state.get("reality_check", {})
        career_context = state.get("career_context", "")
        web_search_results = state.get("web_search_results", "")
        missing_profile_fields = state.get("missing_profile_fields", [])
        error = state.get("error", "")
        field_alias = {"province": "省份", "subject_type": "选科类别", "major_name": "目标专业"}
        if missing_profile_fields:
            missing_text = "、".join(field_alias.get(item, item) for item in missing_profile_fields)
            content = f"信息还不够，我没法给你精准方案。请补充：{missing_text}。"
            return {"messages": [{"role": "assistant", "content": content}], "next_node": "END"}

        if error:
            return {"messages": [{"role": "assistant", "content": error}], "next_node": "END"}

        query = state.get("user_query", "")
        profile = state.get("user_profile") or {}

        # ── 张雪峰对话语料风格锚点（2026-08-06）──────────────
        # synthesis 是雪峰风格的最终出口：检索雪峰原话作为风格参考注入 prompt。
        # 检索失败/无语料时静默跳过（不影响主链路）。
        xuefeng_hits = ""
        if xuefeng_store is not None:
            try:
                import asyncio as _asyncio
                hits = await _asyncio.to_thread(xuefeng_store.search, query, 2)
                if hits:
                    xuefeng_hits = "\n".join(
                        f"[雪峰原话：{h.get('source','')}] {h.get('text','')}" for h in hits
                    )
            except Exception:
                logger.warning("雪峰语料检索失败（跳过风格锚点）", exc_info=True)
        decision_hints = state.get("decision_hints") or summarize_decision_hints(profile)
        # 蓝图 Phase 3.3：结果融合节点输出的综合上下文（开启融合时才有值）
        fusion_context = state.get("fusion_context", "")
        payload = {
            "user_query": query,
            "user_profile": profile,
            "subject_scores": state.get("subject_scores", {}),
            "parent_profile": state.get("parent_profile", {}),
            "family_context": state.get("family_context", {}),
            "sql_results": sql_results[:5],
            "risk_assessment": risk,
            "reality_check": reality,
            "career_context": career_context,
            "web_search_results": web_search_results,
            "fusion_context": fusion_context,
            "xuefeng_style_refs": xuefeng_hits,   # 雪峰原话风格参考（2026-08-06）
            "decision_hints": decision_hints,
            "user_emotion": {
                "label": state.get("emotion_label", "neutral"),
                "intensity": state.get("emotion_intensity", 0.0),
            },
        }
        system_prompt = _load_synthesis_prompt()

        # --- 时间感知注入 ---
        current_dt_str = state.get("current_datetime", "")
        if current_dt_str:
            try:
                dt = datetime.fromisoformat(current_dt_str)
                gaokao_date = datetime(dt.year, 6, 7)
                if dt > gaokao_date:
                    gaokao_date = datetime(dt.year + 1, 6, 7)
                days_to_gaokao = (gaokao_date.date() - dt.date()).days
                month = dt.month
                if 6 <= month <= 8:
                    period = "志愿填报进行中"
                elif 9 <= month <= 12:
                    period = "新学期备考阶段"
                else:
                    period = "高考冲刺阶段"
                time_context = (
                    f"## 当前时间（回复中必须参考）\n"
                    f"- 当前日期：{dt.strftime('%Y年%m月%d日 %A')}\n"
                    f"- 当前时间：{dt.strftime('%H:%M')}\n"
                    f"- 今年高考：{dt.year}年6月7-8日\n"
                    f"- 距离高考：{days_to_gaokao} 天\n"
                    f"- 当前阶段：{period}\n"
                )
                system_prompt = time_context + "\n\n" + system_prompt
            except (ValueError, TypeError):
                pass

        session_id = state.get("session_id", "")
        if feedback_store and session_id:
            try:
                negative_tags = await feedback_store.get_session_negative_tags(session_id)
                patch_text = _build_patch_inject(negative_tags)
                if patch_text:
                    system_prompt = patch_text + "\n\n" + system_prompt
            except Exception:
                logging.getLogger(__name__).warning("获取 session 负反馈标签失败", exc_info=True)

        # --- Guard: 检测硬信号，注入强制格式指令 ---
        guard_signals = SynthesisGuard.detect_signals(state)
        guard_prompt = SynthesisGuard.build_guard_prompt(guard_signals)
        if guard_prompt:
            system_prompt = guard_prompt + "\n\n" + system_prompt

        # --- Anti-Hallucination: 检测数据充分性，注入反幻觉约束 ---
        from core.anti_hallucination import AntiHallucinationSkill, ANTI_HALLUCINATION_PROMPT

        anti_hallucination = AntiHallucinationSkill()
        tool_results_for_check = []
        for r in sql_results:
            if isinstance(r, dict):
                entry = {
                    "name": r.get("_tool_name", "unknown"),
                    "output": str(r.get("_tool_output", "") or ""),
                    "query": query,
                }
                # 过滤掉非工具返回的内部状态 （如 _note 类记录）
                if "_note" not in r:
                    tool_results_for_check.append(entry)

        if tool_results_for_check:
            ah_result = anti_hallucination.check(tool_results_for_check, query)
            if ah_result["should_warn"]:
                system_prompt = ANTI_HALLUCINATION_PROMPT + "\n\n" + system_prompt
                # 如果数据严重缺失，注入引导话术
                if ah_result["should_block"]:
                    guidance = ah_result["guidance"]
                    system_prompt = f"[当前数据充分性: 严重不足]\n{guidance}\n\n{system_prompt}"

        # --- V6.0 增强模块注入 ---
        scene_type = state.get("scene_type", "gaokao")
        path_type = state.get("path_type")
        decision_state = state.get("decision_state", "firm")
        
        # 1. 信息差弥合
        info_gap_content = state.get("info_gap_content", "")
        if info_gap_content:
            system_prompt = f"[信息差弥合]\n{info_gap_content}\n\n{system_prompt}"
        
        # 2. 决策框架
        decision_framework = state.get("decision_framework", "")
        if decision_framework:
            system_prompt = f"[决策框架]\n{decision_framework}\n\n{system_prompt}"
        
        # 3. 现实映射
        reality_mapping = state.get("reality_mapping", "")
        if reality_mapping:
            system_prompt = f"[现实映射]\n{reality_mapping}\n\n{system_prompt}"
        
        # 4. 家庭调解
        family_mediation = state.get("family_mediation", "")
        if family_mediation:
            system_prompt = f"[家庭调解]\n{family_mediation}\n\n{system_prompt}"
        
        # 5. 情感支持
        emotional_support = state.get("emotional_support", "")
        if emotional_support:
            system_prompt = f"[情感支持]\n{emotional_support}\n\n{system_prompt}"
        
        # 6. 回退响应
        fallback_response = state.get("fallback_response", "")
        if fallback_response:
            system_prompt = f"[用户可能需要引导]\n{fallback_response}\n\n{system_prompt}"
        
        # 7. 渐进询问
        progressive_questions = state.get("progressive_questions", [])
        if progressive_questions:
            questions_text = "\n".join([f"- {q.get('question', '')}" for q in progressive_questions[:5]])
            system_prompt = f"[渐进询问建议]\n{questions_text}\n\n{system_prompt}"
        
        # 将增强信息注入 payload
        payload["scene_type"] = scene_type
        payload["path_type"] = path_type
        payload["decision_state"] = decision_state
        if info_gap_content:
            payload["info_gap_content"] = info_gap_content
        if decision_framework:
            payload["decision_framework"] = decision_framework
        if reality_mapping:
            payload["reality_mapping"] = reality_mapping
        if family_mediation:
            payload["family_mediation"] = family_mediation
        if emotional_support:
            payload["emotional_support"] = emotional_support
        
        # V6.0: 生成推荐理由
        recommendation_reasons = []
        if sql_results and profile:
            reason_generator = ReasonGenerator()
            for result in sql_results[:5]:
                if isinstance(result, dict) and "_note" not in result:
                    try:
                        reason = reason_generator.generate_reason(
                            university=result.get("university_name", result.get("school_name", "")),
                            major=result.get("major_name", ""),
                            user_profile=profile,
                            admission_data=result,
                            employment_data=result.get("employment_data"),
                        )
                        recommendation_reasons.append({
                            "university": reason.university,
                            "major": reason.major,
                            "reasons": reason.reasons,
                            "data_support": reason.data_support,
                            "risk_notes": reason.risk_notes,
                            "confidence": reason.confidence,
                        })
                    except Exception as e:
                        logger.warning(f"生成推荐理由失败: {e}")
        
        if recommendation_reasons:
            payload["recommendation_reasons"] = recommendation_reasons

        # ── P1-1 真流式：改用 astream 聚合（而非 ainvoke）──
        # 原因：ChatOpenAI.ainvoke 走 _agenerate 一次性生成，不触发 on_llm_new_token
        # 回调 → LangGraph stream_mode="messages" 捕获不到逐 token。
        # llm.astream 则逐 chunk 发出并触发回调，这里聚合后仍返回完整消息
        # （内容与 ainvoke 完全一致，仅底层传输路径不同），
        # 同时流式路由能实时推送 token。
        llm_chunks: list[str] = []
        async for chunk in llm.astream(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        "请基于以下结构化数据生成最终报考建议，严格禁止编造数据。\n"
                        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                    )
                ),
            ]
        ):
            c = getattr(chunk, "content", "")
            if c:
                llm_chunks.append(str(c))
        llm_reply_text = "".join(llm_chunks)

        # --- Guard: 输出后校验与强制修正 ---
        final_content = SynthesisGuard.enforce(state, llm_reply_text)

        return {"messages": [{"role": "assistant", "content": final_content}], "next_node": "END"}

    return synthesis_agent
