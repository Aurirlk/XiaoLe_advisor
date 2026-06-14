from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from core.web_search_service import WebSearchConfig, WebSearchService
from core.web_search_store import WebSearchStore


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def service_bundle(tmp_path):
    db = tmp_path / "svc.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db.as_posix()}")

    async def _setup():
        store = WebSearchStore(engine)
        await store.ensure_tables()
        return store

    store = _run(_setup())

    mock_search = MagicMock()
    mock_search.search.return_value = [
        {"title": "结果A", "url": "https://example.com/a"},
    ]

    mock_fetcher = MagicMock()
    mock_fetch = AsyncMock(
        return_value=MagicMock(status="ok", text="抓取到的正文", chars=6, error="")
    )
    mock_fetcher.fetch_page = mock_fetch

    mock_vector = MagicMock()
    mock_vector.upsert_documents.return_value = 1

    cfg = WebSearchConfig(
        top_k=3,
        enable_page_fetch=True,
        cache_ttl_hours=24,
        fetch_concurrency=1,
    )
    svc = WebSearchService(
        store=store,
        web_search=mock_search,
        page_fetcher=mock_fetcher,
        vector_store=mock_vector,
        config=cfg,
    )
    yield svc, store, mock_search, mock_fetcher, mock_vector
    _run(engine.dispose())


def test_search_fetch_and_persist(service_bundle):
    svc, store, mock_search, mock_fetcher, mock_vector = service_bundle

    async def _test():
        bundle = await svc.search_fetch_and_persist("测试查询", chat_session_id="s1")
        assert bundle.from_cache is False
        assert bundle.db_session_id > 0
        assert len(bundle.pages) == 1
        assert "抓取到的正文" in bundle.formatted_text
        session = await store.get_session(bundle.db_session_id)
        assert session["pages"][0]["fetch_status"] == "ok"

    _run(_test())
    mock_search.search.assert_called_once()
    mock_fetcher.fetch_page.assert_called_once()
    mock_vector.upsert_documents.assert_called_once()


def test_cache_hit_skips_search(service_bundle):
    svc, store, mock_search, _mock_fetcher, _mock_vector = service_bundle

    async def _test():
        first = await svc.search_fetch_and_persist("缓存命中测试")
        assert first.from_cache is False
        mock_search.reset_mock()
        second = await svc.search_fetch_and_persist("缓存命中测试")
        assert second.from_cache is True

    _run(_test())
    mock_search.search.assert_not_called()


def test_empty_search_results(service_bundle):
    svc, _store, mock_search, _mock_fetcher, mock_vector = service_bundle
    mock_search.search.return_value = []

    async def _test():
        bundle = await svc.search_fetch_and_persist("无结果")
        assert "系统提示" in bundle.formatted_text

    _run(_test())
    mock_vector.upsert_documents.assert_not_called()
