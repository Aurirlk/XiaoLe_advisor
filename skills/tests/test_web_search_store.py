from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from core.web_search_store import WebSearchStore, make_hash


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def store(tmp_path):
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db.as_posix()}")

    async def _setup():
        s = WebSearchStore(engine)
        await s.ensure_tables()
        return s, engine

    s, engine = _run(_setup())
    yield s
    _run(engine.dispose())


def test_create_session_and_save_page(store: WebSearchStore):
    async def _test():
        sid, qh = await store.create_session("2026 广东新高考政策", "chat-1")
        assert qh == make_hash("2026 广东新高考政策")
        await store.save_page(
            sid,
            url="https://example.com/a",
            title="政策解读",
            content_text="正文内容",
            fetch_status="ok",
        )
        await store.update_session_count(sid, 1)
        session = await store.get_session(sid)
        assert session is not None
        assert session["result_count"] == 1
        assert len(session["pages"]) == 1
        assert session["pages"][0]["content_text"] == "正文内容"

    _run(_test())


def test_find_cached_session(store: WebSearchStore):
    async def _test():
        sid, _ = await store.create_session("缓存测试查询", "")
        await store.save_page(
            sid,
            url="https://example.com/b",
            title="t",
            content_text="body",
            fetch_status="ok",
        )
        await store.update_session_count(sid, 1)
        cached = await store.find_cached_session("缓存测试查询", ttl_hours=24)
        assert cached is not None
        assert cached.db_session_id == sid
        assert len(cached.pages) == 1

    _run(_test())


def test_page_upsert_on_conflict(store: WebSearchStore):
    async def _test():
        sid, _ = await store.create_session("dup test", "")
        await store.save_page(
            sid,
            url="https://example.com/c",
            title="v1",
            content_text="old",
            fetch_status="ok",
        )
        await store.save_page(
            sid,
            url="https://example.com/c",
            title="v2",
            content_text="new",
            fetch_status="ok",
        )
        pages = await store.get_session_pages(sid)
        assert len(pages) == 1
        assert pages[0]["title"] == "v2"

    _run(_test())
