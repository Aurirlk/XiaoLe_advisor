from __future__ import annotations

import asyncio

from tools.page_fetcher import PageFetcher, is_safe_url


class TestIsSafeUrl:
    def test_http_ok(self):
        assert is_safe_url("https://example.com/page")

    def test_file_blocked(self):
        assert not is_safe_url("file:///etc/passwd")

    def test_localhost_blocked(self):
        assert not is_safe_url("http://127.0.0.1/test")

    def test_private_ip_blocked(self):
        assert not is_safe_url("http://192.168.1.1/internal")


def test_fetch_page_timeout(monkeypatch):
    fetcher = PageFetcher(timeout_seconds=0.001)

    async def _raise(*_args, **_kwargs):
        import httpx

        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("tools.page_fetcher.httpx.AsyncClient", lambda **kw: _FakeClient(_raise))

    async def _run():
        return await fetcher.fetch_page("https://example.com")

    result = asyncio.run(_run())
    assert result.status in ("timeout", "error")


class _FakeClient:
    def __init__(self, get_coro):
        self._get = get_coro

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, headers=None):
        return await self._get(url, headers=headers)
