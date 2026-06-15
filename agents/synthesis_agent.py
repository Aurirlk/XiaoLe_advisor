from pathlib import Path
import json
import logging
from datetime import datetime, timezone, timedelta

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from core.state_schema import GraphState
from core.synthesis_guard import SynthesisGuard
from skills.decision_heuristics import summarize_decision_hints

ROOT = Path(__file__).resolve().parents[1]
ZX_PROMPT_PATH = ROOT / "configs" / "prompts" / "zx_system_prompt.md"
FALLBACK_PROMPT_PATH = ROOT / "configs" / "prompts" / "synthesis_system_prompt.txt"
PATCHES_PATH = ROOT / "configs" / "synthesis_patches.yaml"


def _load_synthesis_prompt() -> str:
    if ZX_PROMPT_PATH.exists():
        return ZX_PROMPT_PATH.read_text(encoding="utf-8")
    return FALLBACK_PROMPT_PATH.read_text(encoding="utf-8")


def _load_feedback_patches() -> list[dict]:
    if not PATCHES_PATH.exists():
        return []
    data = yaml.safe_load(PATCHES_PATH.read_text(encoding="utf-8")) or {}
    return data.get("patches", []) or []


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


def build_synthesis_agent(llm: ChatOpenAI, feedback_store=None):
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
        decision_hints = state.get("decision_hints") or summarize_decision_hints(state.get("user_profile", {}))
        payload = {
            "user_query": query,
            "user_profile": state.get("user_profile", {}),
            "subject_scores": state.get("subject_scores", {}),
            "parent_profile": state.get("parent_profile", {}),
            "family_context": state.get("family_context", {}),
            "sql_results": sql_results[:5],
            "risk_assessment": risk,
            "reality_check": reality,
            "career_context": career_context,
            "web_search_results": web_search_results,
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

        llm_reply = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        "请基于以下结构化数据生成最终报考建议，严格禁止编造数据。\n"
                        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                    )
                ),
            ]
        )

        # --- Guard: 输出后校验与强制修正 ---
        final_content = SynthesisGuard.enforce(state, str(llm_reply.content))

        return {"messages": [{"role": "assistant", "content": final_content}], "next_node": "END"}

    return synthesis_agent
