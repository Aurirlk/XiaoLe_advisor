import inspect
import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "数据接口暂时繁忙，但听张老师一句劝，先看分数段位次，再谈专业梦想。"

# 这些异常几乎必然是代码缺陷（而非外部服务抖动），不允许被兜底吞掉：
# 吞掉的结果是核心功能坏了却伪装成"服务繁忙"，长期无人发现（见交接手册 P0-4）。
_CODE_DEFECT_EXCEPTIONS = (NameError, AttributeError, TypeError, KeyError, ImportError, SyntaxError)


async def safe_node_call(node: Callable[..., Any], state: dict) -> dict:
    node_name = getattr(node, "__name__", str(node))
    try:
        if inspect.iscoroutinefunction(node):
            return await node(state)
        result = node(state)
        # Some libraries / wrappers may return an awaitable even when the
        # callable itself is not an `async def`.
        if inspect.isawaitable(result):
            return await result
        return result
    except _CODE_DEFECT_EXCEPTIONS:
        # 代码缺陷：ERROR 级日志 + 开发/测试环境直接抛出让其可见；
        # 生产环境仍兜底返回但日志级别为 ERROR，便于告警系统捕获。
        logger.error("节点 [%s] 存在代码缺陷（非业务异常）", node_name, exc_info=True)
        if os.getenv("APP_ENV", "development").lower() != "production":
            raise
        return {"error": FALLBACK_MESSAGE, "next_node": "synthesis_agent"}
    except Exception:
        logger.warning("safe_node_call 业务异常 [%s]", node_name, exc_info=True)
        return {"error": FALLBACK_MESSAGE, "next_node": "synthesis_agent"}
