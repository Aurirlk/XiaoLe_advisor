from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.dependencies import (
    get_checkpoint_manager,
    get_compiled_graph,
    get_conversation_turn_store,
)
from core.web_search_status import drain_status

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

router = APIRouter(prefix="/stream", tags=["stream"])


class StreamRequest(BaseModel):
    query: str
    session_id: str = ""
    conversation_role: str = "student"


_AGENT_NODES = frozenset({
    "profile_agent", "parent_agent", "family_agent", "match_agent", "career_agent",
    "web_search_agent", "sql_agent", "synthesis_agent", "supervisor_agent",
})


async def _event_generator(
    graph,
    query: str,
    session_id: str = "",
    turn_store=None,
    conversation_role: str = "student",
) -> AsyncGenerator[dict, None]:
    sid = session_id or str(uuid.uuid4())
    turn_id = str(uuid.uuid4())
    cm = get_checkpoint_manager()

    init_state = cm.build_init_state(query, session_id=sid)
    init_state["current_datetime"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    init_state["conversation_role"] = conversation_role

    # 情感分析（关键词模式，零成本）
    from core.emotion_analyzer import get_emotion_analyzer
    emotion_analyzer = get_emotion_analyzer(method="keyword")
    emotion_result = await emotion_analyzer.analyze(query)
    init_state["emotion_label"] = emotion_result.label
    init_state["emotion_intensity"] = emotion_result.intensity
    init_state["emotion_valence"] = emotion_result.valence

    config = cm.build_config(sid, recursion_limit=50)

    logger.info(f"[{sid}] turn={turn_id} 开始处理查询: {query[:80]}...")

    route_path: list[str] = []
    assistant_response = ""
    final_profile: dict = {}
    sql_hit_count = 0
    risk_level = ""

    try:
        async for chunk in graph.astream(init_state, config=config):
            for status_msg in drain_status(sid):
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "status", "msg": status_msg},
                        ensure_ascii=False,
                    ),
                }
            for node_name in chunk:
                if node_name in _AGENT_NODES and (
                    not route_path or route_path[-1] != node_name
                ):
                    route_path.append(node_name)
                logger.info(f"[{sid}] 节点完成: {node_name}")
                if node_name == "web_search_agent":
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {"type": "status", "msg": "联网查询与落库已完成"},
                            ensure_ascii=False,
                        ),
                    }
                elif node_name == "synthesis_agent":
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "status", "msg": "正在生成最终建议..."}, ensure_ascii=False),
                    }
    except Exception as e:
        logger.warning(f"[{sid}] graph.astream 异常: {type(e).__name__}: {e}")

    try:
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            values = final_state.values
            final_profile = values.get("user_profile") or {}
            sql_results = values.get("sql_results") or []
            sql_hit_count = len([r for r in sql_results if "_note" not in r])
            risk = values.get("risk_assessment") or {}
            risk_level = str(risk.get("level", risk.get("risk_level", "")))

            # 发送 profile_update 事件，让前端侧边栏实时刷新画像
            if final_profile:
                profile_event = {"type": "profile_update", "profile": final_profile}
                parent_profile = values.get("parent_profile")
                if parent_profile:
                    profile_event["parent_profile"] = parent_profile
                family_context = values.get("family_context")
                if family_context:
                    profile_event["family_context"] = family_context
                subject_scores = values.get("subject_scores")
                if subject_scores:
                    profile_event["subject_scores"] = subject_scores
                # 情绪数据（供前端 TTS 使用）
                el = values.get("emotion_label")
                if el:
                    profile_event["emotion"] = {
                        "label": el,
                        "intensity": values.get("emotion_intensity", 0.5),
                        "valence": values.get("emotion_valence", 0.0),
                    }
                yield {
                    "event": "message",
                    "data": json.dumps(profile_event, ensure_ascii=False),
                }

            messages = values.get("messages", [])
            logger.info(f"[{sid}] 最终状态消息数: {len(messages)}")
            assistant_msgs = [
                msg for msg in messages
                if getattr(msg, "type", "") == "ai"
            ]
            for msg in assistant_msgs[-1:]:
                content = getattr(msg, "content", None)
                if content:
                    assistant_response = str(content)
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {"type": "token", "msg": assistant_response},
                            ensure_ascii=False,
                        ),
                    }
            if not assistant_msgs:
                assistant_response = "服务暂时繁忙（AI 未生成回复），请稍后重试。"
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "token", "msg": assistant_response}, ensure_ascii=False),
                }
        else:
            assistant_response = "服务暂时不可用（状态丢失），请稍后重试。"
            yield {
                "event": "message",
                "data": json.dumps({"type": "token", "msg": assistant_response}, ensure_ascii=False),
            }
    except Exception as e:
        logger.warning(f"[{sid}] get_state 异常: {type(e).__name__}: {e}")
        assistant_response = "服务暂时不可用，请稍后重试。"

    if turn_store is not None:
        try:
            await turn_store.save_turn(
                turn_id=turn_id,
                session_id=sid,
                user_query=query,
                assistant_response=assistant_response,
                route_path=route_path,
                user_profile_snapshot=final_profile,
                sql_hit_count=sql_hit_count,
                risk_level=risk_level,
            )
        except Exception as e:
            logger.warning(f"[{sid}] save_turn 失败: {e}")

    # 写入 Redis 对话历史（与 chat_router 共享）
    try:
        from api.dependencies import get_redis_client
        redis = get_redis_client()
        if redis:
            import json as _json
            user_record = {"role": "user", "content": query, "ts": datetime.now(timezone.utc).isoformat()}
            ai_record = {"role": "assistant", "content": assistant_response, "ts": datetime.now(timezone.utc).isoformat()}
            key = f"chat:session:{sid}"
            await redis.rpush(key, _json.dumps(user_record, ensure_ascii=False))
            await redis.rpush(key, _json.dumps(ai_record, ensure_ascii=False))
            await redis.expire(key, 60 * 60 * 24 * 7)  # 7 天 TTL
    except Exception as e:
        logger.debug(f"[{sid}] Redis 对话历史写入失败（非致命）: {e}")

    yield {
        "event": "message",
        "data": json.dumps(
            {"type": "meta", "session_id": sid, "turn_id": turn_id},
            ensure_ascii=False,
        ),
    }


@router.post("/advice")
async def stream_advice(
    payload: StreamRequest,
    graph=Depends(get_compiled_graph),
    turn_store=Depends(get_conversation_turn_store),
):
    return EventSourceResponse(
        _event_generator(
            graph, payload.query, payload.session_id, turn_store,
            conversation_role=payload.conversation_role,
        )
    )


@router.get("/state/{session_id}")
async def get_state(session_id: str, graph=Depends(get_compiled_graph)):
    """获取指定 session 的当前画像状态（用于前端展示/调试）"""
    cm = get_checkpoint_manager()
    config = cm.build_config(session_id)
    try:
        state = graph.get_state(config)
        if state and state.values:
            profile = state.values.get("user_profile", {})
            history = state.values.get("profile_history", [])
            return {
                "ok": True,
                "session_id": session_id,
                "profile": profile,
                "profile_history": history[-10:],
            }
        return {"ok": True, "session_id": session_id, "profile": {}, "profile_history": []}
    except Exception:
        return {"ok": True, "session_id": session_id, "profile": {}, "profile_history": []}


@router.get("/history/{session_id}")
async def get_profile_history(session_id: str, graph=Depends(get_compiled_graph)):
    """获取 session 的画像变更历史"""
    cm = get_checkpoint_manager()
    config = cm.build_config(session_id)
    try:
        state = graph.get_state(config)
        if state and state.values:
            history = state.values.get("profile_history", [])
            return {"ok": True, "session_id": session_id, "changes": len(history), "history": history}
        return {"ok": True, "session_id": session_id, "changes": 0, "history": []}
    except Exception:
        return {"ok": True, "session_id": session_id, "changes": 0, "history": []}
