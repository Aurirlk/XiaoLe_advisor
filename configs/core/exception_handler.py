import inspect
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "数据接口暂时繁忙，但听张老师一句劝，先看分数段位次，再谈专业梦想。"


async def safe_node_call(node: Callable[..., Any], state: dict) -> dict:
    try:
        if inspect.iscoroutinefunction(node):
            return await node(state)
        result = node(state)
        # Some libraries / wrappers may return an awaitable even when the
        # callable itself is not an `async def`.
        if inspect.isawaitable(result):
            return await result
        return result
    except Exception:
        logger.warning("safe_node_call 异常 [%s]", getattr(node, "__name__", node), exc_info=True)
        return {"error": FALLBACK_MESSAGE, "next_node": "synthesis_agent"}
