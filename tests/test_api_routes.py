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
    async def astream(self, *_args, **_kwargs):
        yield {"supervisor_agent": {"next_node": "synthesis_agent"}}
        yield {"synthesis_agent": {"messages": []}}

    def get_state(self, _config):
        class State:
            values = {
                "messages": [type("M", (), {"type": "ai", "content": "你好"})()],
                "user_profile": {},
                "sql_results": [],
                "risk_assessment": {},
            }
        return State()


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


def test_feedback_route():
    if not REDIS_INSTALLED:
        return
    from api.dependencies import get_conversation_turn_store

    async def _setup():
        turn_store = get_conversation_turn_store()
        await turn_store.ensure_tables()
        await turn_store.save_turn(
            turn_id="api-turn-1",
            session_id="api-sess",
            user_query="test",
            assistant_response="answer",
            route_path=["synthesis_agent"],
        )

    asyncio.run(_setup())

    client = TestClient(app)
    resp = client.post(
        "/feedback",
        json={"turn_id": "api-turn-1", "rating": 1, "tags": [], "comment": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_event_generator_output():
    if not REDIS_INSTALLED:
        return
    from api.dependencies import get_conversation_turn_store

    out = []

    async def _collect():
        turn_store = get_conversation_turn_store()
        await turn_store.ensure_tables()
        async for event in _event_generator(
            DummyGraph(), "test query", session_id="test-session", turn_store=turn_store
        ):
            out.append(event)

    asyncio.run(_collect())
    assert len(out) >= 2
    assert out[0]["event"] == "message"
    meta = json.loads(out[-1]["data"])
    assert meta["type"] == "meta"
    assert "turn_id" in meta
    token = json.loads(out[-2]["data"])
    assert token["type"] == "token"
