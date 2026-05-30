from __future__ import annotations

import asyncio
import json

import importlib.util
from fastapi.testclient import TestClient

REDIS_INSTALLED = importlib.util.find_spec("redis") is not None

if REDIS_INSTALLED:
    from api.main import app
    from api.routers.stream_router import _event_generator


def test_healthz_route():
    if not REDIS_INSTALLED:
        return
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_root_route():
    if not REDIS_INSTALLED:
        return
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "ZX AI Advisor"
    assert "endpoints" in body


def test_status_route():
    if not REDIS_INSTALLED:
        return
    app.state.started_at = 0.0
    app.state.notes = []
    app.state.graph_ready = False
    app.state.db_ready = False
    app.state.redis_ready = False

    client = TestClient(app)
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "uptime_seconds" in body


class DummyGraph:
    async def astream_events(self, *_args, **_kwargs):
        yield {"event": "on_tool_start", "name": "tool", "data": {}}
        yield {"event": "on_chat_model_stream", "name": "model", "data": {"chunk": type("C", (), {"content": "你好"})()}}


def test_web_cache_check_route(monkeypatch):
    if not REDIS_INSTALLED:
        return
    from api.dependencies import get_web_search_store, get_web_search_service

    async def _fake_find(*_a, **_k):
        return None

    store = get_web_search_store()
    monkeypatch.setattr(store, "find_cached_session", _fake_find)

    client = TestClient(app)
    resp = client.get("/web/cache/check", params={"q": "测试政策"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["cached"] is False
    assert "query_hash" in body


def test_web_search_route_mocked(monkeypatch):
    if not REDIS_INSTALLED:
        return
    from api.dependencies import get_web_search_service
    from core.web_search_service import WebSearchBundle

    async def _fake_search(*_a, **_k):
        return WebSearchBundle(
            formatted_text="[来源1] 测试 | https://example.com\n正文\n---",
            pages=[{"url": "https://example.com", "title": "测试"}],
            db_session_id=1,
            from_cache=False,
            query_hash="abc",
        )

    svc = get_web_search_service()
    monkeypatch.setattr(svc, "search_fetch_and_persist", _fake_search)

    client = TestClient(app)
    resp = client.post(
        "/web/search",
        json={"query": "2026政策", "session_id": "", "force_refresh": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["result_count"] == 1


def test_event_generator_output():
    if not REDIS_INSTALLED:
        return
    out = []
    async def _collect():
        async for event in _event_generator(DummyGraph(), "test query", session_id="test-session"):
            out.append(event)
    asyncio.run(_collect())
    assert len(out) >= 3  # tool_start + chat_model_stream + meta(session_id)
    assert out[0]["event"] == "message"
    # 最后一条是 meta 事件，倒数第二条是 token
    payload = json.loads(out[-2]["data"])
    assert payload["type"] == "token"
