from __future__ import annotations

import json
import uuid
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_compiled_graph, get_checkpoint_manager
from core.web_search_status import drain_status

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

router = APIRouter(prefix="/stream", tags=["stream"])


class StreamRequest(BaseModel):
    query: str
    session_id: str = ""


_AGENT_NODES = frozenset({
    "profile_agent", "match_agent", "career_agent",
    "web_search_agent", "sql_agent", "synthesis_agent", "supervisor_agent",
})


async def _event_generator(
    graph,
    query: str,
    session_id: str = "",
) -> AsyncGenerator[dict, None]:
    sid = session_id or str(uuid.uuid4())
    cm = get_checkpoint_manager()

    init_state = cm.build_init_state(query, session_id=sid)
    config = cm.build_config(sid, recursion_limit=50)

    logger.info(f"[{sid}] 开始处理查询: {query[:80]}...")

    last_node = ""
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
                last_node = node_name
    except Exception as e:
        logger.warning(f"[{sid}] graph.astream 异常: {type(e).__name__}: {e}")

    try:
        final_state = graph.get_state(config)
        if final_state and final_state.values:
            messages = final_state.values.get("messages", [])
            logger.info(f"[{sid}] 最终状态消息数: {len(messages)}, 消息类型: {[getattr(m, 'type', type(m).__name__) for m in messages]}")
            assistant_msgs = [
                msg for msg in messages
                if getattr(msg, "type", "") == "ai"
            ]
            for msg in assistant_msgs[-1:]:
                content = getattr(msg, "content", None)
                logger.warning(f"[{sid}] AI回复内容长度: {len(str(content)) if content else 0}")
                if content:
                    yield {"event": "message", "data": json.dumps({"type": "token", "msg": str(content)}, ensure_ascii=False)}
            if not assistant_msgs:
                logger.warning(f"[{sid}] 未找到AI消息，yield 错误提示")
                yield {"event": "message", "data": json.dumps({"type": "token", "msg": "服务暂时繁忙（AI 未生成回复），请稍后重试。"}, ensure_ascii=False)}
        else:
            logger.warning(f"[{sid}] get_state 返回空或无效状态")
            yield {"event": "message", "data": json.dumps({"type": "token", "msg": "服务暂时不可用（状态丢失），请稍后重试。"}, ensure_ascii=False)}
    except Exception as e:
        logger.warning(f"[{sid}] get_state 异常: {type(e).__name__}: {e}")

    yield {
        "event": "message",
        "data": json.dumps({"type": "meta", "session_id": sid}, ensure_ascii=False),
    }


@router.post("/advice")
async def stream_advice(
    payload: StreamRequest,
    graph=Depends(get_compiled_graph),
):
    return EventSourceResponse(_event_generator(graph, payload.query, payload.session_id))


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
