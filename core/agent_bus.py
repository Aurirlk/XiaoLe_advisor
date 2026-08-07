"""
Agent 通信总线（蓝图 Phase 3.1，2026-08-06 重建）

职责：多 Agent 之间的协作通道——消息订阅/发布、请求-响应、广播。

背景：本文件曾因"零引用"被误删（前几轮死代码清理），但它是蓝图
「多智能体协作体系」的核心组件（docs/技术文档.md / .omo/plans/）。
本次按蓝图重建并接入 graph_builder，恢复"中枢-员工"协作叙事。

设计原则：
1. 进程内事件总线（asyncio 友好），不引入消息中间件——作品集规模足够
2. 三种模式：publish/subscribe（广播）、request/reply（请求-响应）、broadcast（群发）
3. 与 LangGraph 正交：总线是节点间的"旁路通道"，不干扰图的条件路由；
   节点可通过总线协作（如 career_agent 向 match_agent 要院校数据）
4. 全部方法可异步调用，线程安全（asyncio.Lock 保护订阅表）
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# 消息类型常量（蓝图：消息订阅/发布 + 请求-响应 + 广播）
MSG_TYPE_EVENT = "event"            # 单向事件（广播给订阅者）
MSG_TYPE_REQUEST = "request"        # 请求-响应（等待 reply）
MSG_TYPE_REPLY = "reply"            # 请求的应答
MSG_TYPE_BROADCAST = "broadcast"    # 群发（所有订阅该 topic 的 agent）


@dataclass
class BusMessage:
    """总线消息载体"""
    topic: str                          # 主题（如 "profile.updated" / "sql.query"）
    msg_type: str = MSG_TYPE_EVENT
    payload: Dict[str, Any] = field(default_factory=dict)   # 业务数据
    sender: str = ""                    # 发送方 agent 名
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reply_topic: str = ""               # request 模式：应答发到哪个 topic


class AgentCommunicationBus:
    """Agent 通信总线

    用法：
        bus = AgentCommunicationBus()
        # 订阅
        bus.subscribe("profile.updated", my_handler)   # handler: async (BusMessage) -> None
        # 发布（广播给所有订阅者）
        await bus.publish("profile.updated", {"province": "广东省"})
        # 请求-响应（等第一个 handler 回复）
        reply = await bus.request("sql.query", {"table": "admission_scores"}, timeout=3.0)
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[BusMessage], Awaitable[Optional[Dict]]]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._stats: Dict[str, int] = {"published": 0, "requests": 0, "replies": 0}

    # ── 订阅 ────────────────────────────────────────────────

    def subscribe(
        self,
        topic: str,
        handler: Callable[[BusMessage], Awaitable[Optional[Dict]]],
    ) -> None:
        """订阅主题。handler 接收 BusMessage，返回 dict（request 模式用作应答）或 None。"""
        # 注意：同步注册（在 agent 构建阶段调用），无需 await
        self._subscribers[topic].append(handler)
        logger.debug("[Bus] %s 订阅 topic=%s（现有 %d 个订阅者）",
                     getattr(handler, "__name__", "?"), topic, len(self._subscribers[topic]))

    def unsubscribe(self, topic: str, handler) -> None:
        try:
            self._subscribers[topic].remove(handler)
        except ValueError:
            pass

    # ── 发布/广播 ──────────────────────────────────────────

    async def publish(self, topic: str, payload: Dict[str, Any] | None = None, sender: str = "") -> int:
        """发布事件给所有订阅者（fire-and-forget，等待各自完成但结果丢弃）。返回订阅者数量。"""
        msg = BusMessage(topic=topic, msg_type=MSG_TYPE_EVENT, payload=payload or {}, sender=sender)
        handlers = list(self._subscribers.get(topic, []))
        async with self._lock:
            self._stats["published"] += 1
        for h in handlers:
            try:
                await h(msg)
            except Exception:
                logger.warning("[Bus] 发布 topic=%s 时 handler 异常", topic, exc_info=True)
        return len(handlers)

    async def broadcast(self, topics: List[str], payload: Dict[str, Any] | None = None, sender: str = "") -> int:
        """向多个主题群发（蓝图 broadcast 模式）。返回总订阅者数。"""
        total = 0
        for topic in topics:
            total += await self.publish(topic, payload, sender)
        return total

    # ── 请求-响应 ──────────────────────────────────────────

    async def request(
        self,
        topic: str,
        payload: Dict[str, Any] | None = None,
        sender: str = "",
        timeout: float = 3.0,
    ) -> Optional[Dict[str, Any]]:
        """请求-响应：向订阅者发请求，取第一个返回 dict 的 handler 作为应答。

        无订阅者 / 全部超时返回 None（调用方应优雅降级，不抛异常）。
        """
        reply_topic = f"{topic}.reply.{uuid.uuid4().hex[:8]}"
        msg = BusMessage(
            topic=topic, msg_type=MSG_TYPE_REQUEST,
            payload=payload or {}, sender=sender, reply_topic=reply_topic,
        )
        handlers = list(self._subscribers.get(topic, []))
        async with self._lock:
            self._stats["requests"] += 1
        if not handlers:
            return None

        async def _call(h) -> Optional[Dict[str, Any]]:
            try:
                result = await asyncio.wait_for(h(msg), timeout=timeout)
                return result if isinstance(result, dict) else None
            except asyncio.TimeoutError:
                logger.debug("[Bus] request topic=%s 超时", topic)
                return None
            except Exception:
                logger.warning("[Bus] request topic=%s handler 异常", topic, exc_info=True)
                return None

        results = await asyncio.gather(*[_call(h) for h in handlers])
        for r in results:
            if r:
                async with self._lock:
                    self._stats["replies"] += 1
                return r
        return None

    # ── 工具 ───────────────────────────────────────────────

    def subscriber_count(self, topic: str) -> int:
        return len(self._subscribers.get(topic, []))

    def topics(self) -> List[str]:
        return list(self._subscribers.keys())

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
