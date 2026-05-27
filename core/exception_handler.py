import inspect
from typing import Any, Callable


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
        return {"error": FALLBACK_MESSAGE, "next_node": "synthesis_agent"}
