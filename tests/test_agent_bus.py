"""
Agent 通信总线测试（蓝图 Phase 3.1 重建回归）

覆盖：发布/订阅、请求-响应、广播、无订阅者优雅降级、异常隔离。
"""
from __future__ import annotations

import asyncio

import pytest

from core.agent_bus import AgentCommunicationBus, BusMessage, MSG_TYPE_BROADCAST, MSG_TYPE_REQUEST

pytestmark = pytest.mark.asyncio


async def test_publish_reaches_subscribers():
    """发布事件 → 所有订阅者收到"""
    bus = AgentCommunicationBus()
    received = []

    async def handler(msg: BusMessage):
        received.append((msg.topic, msg.payload))

    bus.subscribe("profile.updated", handler)
    n = await bus.publish("profile.updated", {"province": "广东省"})
    assert n == 1
    assert received == [("profile.updated", {"province": "广东省"})]


async def test_publish_multiple_subscribers():
    """多订阅者全部收到（广播语义）"""
    bus = AgentCommunicationBus()
    got = []

    async def h1(msg): got.append("h1")

    async def h2(msg): got.append("h2")

    bus.subscribe("t", h1)
    bus.subscribe("t", h2)
    await bus.publish("t")
    assert sorted(got) == ["h1", "h2"]


async def test_request_reply():
    """请求-响应：第一个返回 dict 的 handler 成为应答"""
    bus = AgentCommunicationBus()

    async def provider(msg: BusMessage):
        return {"rows": [1, 2, 3]}

    bus.subscribe("sql.query", provider)
    reply = await bus.request("sql.query", {"table": "admission_scores"})
    assert reply == {"rows": [1, 2, 3]}


async def test_request_no_subscribers_returns_none():
    """无订阅者 → 返回 None（不抛异常，调用方优雅降级）"""
    bus = AgentCommunicationBus()
    reply = await bus.request("nobody.listens", {})
    assert reply is None


async def test_request_timeout_returns_none():
    """订阅者超时 → 返回 None"""
    bus = AgentCommunicationBus()

    async def slow_handler(msg):
        await asyncio.sleep(5)

    bus.subscribe("slow.topic", slow_handler)
    reply = await bus.request("slow.topic", {}, timeout=0.1)
    assert reply is None


async def test_handler_exception_isolated():
    """单个 handler 异常不影响其他订阅者"""
    bus = AgentCommunicationBus()
    got = []

    async def bad(msg):
        raise RuntimeError("boom")

    async def good(msg):
        got.append("ok")

    bus.subscribe("t", bad)
    bus.subscribe("t", good)
    await bus.publish("t")  # 不应抛异常
    assert got == ["ok"]


async def test_broadcast_multiple_topics():
    """群发：向多个主题广播"""
    bus = AgentCommunicationBus()
    got = []

    async def h(msg):
        got.append(msg.topic)

    bus.subscribe("a", h)
    bus.subscribe("b", h)
    n = await bus.broadcast(["a", "b"])
    assert n == 2
    assert sorted(got) == ["a", "b"]


async def test_stats_tracking():
    """统计计数"""
    bus = AgentCommunicationBus()

    async def h(msg): return {"x": 1}

    bus.subscribe("t", h)
    await bus.publish("t")
    await bus.request("t")
    stats = bus.get_stats()
    assert stats["published"] == 1
    assert stats["requests"] == 1
    assert stats["replies"] == 1
    assert bus.subscriber_count("t") == 1
    assert "t" in bus.topics()
