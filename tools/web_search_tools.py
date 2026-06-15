"""
联网搜索工具 — 支持多搜索源

- DuckDuckGo: 免费，无需 Key（默认）
- Metaso（秘塔）: 国内可用，结果质量高，需 API Key
- Tavily: 海外搜索，需 API Key
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _load_search_config() -> dict:
    cfg_path = ROOT / "configs" / "web_search_config.yaml"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("web_search", {})
    return {}


def _resolve_api_key(raw: str) -> str:
    if raw.startswith("${") and raw.endswith("}"):
        import os
        return os.getenv(raw[2:-1], "")
    return raw


class WebSearchTools:
    """联网搜索工具，支持 DuckDuckGo / Metaso / Tavily"""

    def __init__(
        self,
        user_agent: str | None = None,
        timeout_seconds: float = 4.0,
        provider: str = "",
        config: dict | None = None,
    ) -> None:
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; ZXAIAdvisor/1.0)"
        self.timeout_seconds = timeout_seconds

        if config is None:
            try:
                import yaml
                config = _load_search_config()
            except Exception:
                config = {}

        self.provider = provider or config.get("provider", "duckduckgo")
        self._config = config

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        """搜索入口，根据 provider 分发"""
        q = (query or "").strip()
        if not q:
            return []

        if self.provider == "metaso":
            return await self._search_metaso(q, top_k)
        elif self.provider == "tavily":
            return await self._search_tavily(q, top_k)
        else:
            return await asyncio.to_thread(self._sync_search_ddg, q, top_k)

    # ── DuckDuckGo（免费）─────────────────────────────────
    def _sync_search_ddg(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        request = Request(url=url, headers={"User-Agent": self.user_agent}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except (URLError, TimeoutError, ValueError):
            return []

        matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body)
        items: List[Dict[str, str]] = []
        for href, title_html in matches[:max(top_k, 1)]:
            title = re.sub(r"<.*?>", "", title_html)
            title = html.unescape(title).strip()
            href = html.unescape(href).strip()
            if not title or not href:
                continue
            items.append({"title": title, "url": href})
        return items[:top_k]

    # ── 秘塔搜索 ─────────────────────────────────────────
    async def _search_metaso(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        import httpx
        api_key = _resolve_api_key(self._config.get("metaso", {}).get("api_key", ""))
        base_url = self._config.get("metaso", {}).get("base_url", "https://api.metaso.cn/api/open/search")
        if not api_key:
            logger.warning("Metaso API Key 未配置，回退到 DuckDuckGo")
            return await asyncio.to_thread(self._sync_search_ddg, query, top_k)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "size": top_k},
                )
                resp.raise_for_status()
                data = resp.json()

            items = []
            for result in data.get("results", [])[:top_k]:
                items.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                })
            return items
        except Exception as e:
            logger.warning("Metaso 搜索失败: %s，回退到 DuckDuckGo", e)
            return await asyncio.to_thread(self._sync_search_ddg, query, top_k)

    # ── Tavily ────────────────────────────────────────────
    async def _search_tavily(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        import httpx
        api_key = _resolve_api_key(self._config.get("tavily", {}).get("api_key", ""))
        base_url = self._config.get("tavily", {}).get("base_url", "https://api.tavily.com/search")
        if not api_key:
            logger.warning("Tavily API Key 未配置，回退到 DuckDuckGo")
            return await asyncio.to_thread(self._sync_search_ddg, query, top_k)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    base_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": top_k,
                        "include_answer": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            items = []
            for result in data.get("results", [])[:top_k]:
                items.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                })
            return items
        except Exception as e:
            logger.warning("Tavily 搜索失败: %s，回退到 DuckDuckGo", e)
            return await asyncio.to_thread(self._sync_search_ddg, query, top_k)

    @staticmethod
    def format_results(results: List[Dict[str, str]]) -> str:
        if not results:
            return ""
        lines = []
        for i, item in enumerate(results, start=1):
            lines.append(f"{i}. {item.get('title', '').strip()} | {item.get('url', '').strip()}")
        return "\n".join(lines).strip()

    @staticmethod
    def to_json(results: List[Dict[str, str]]) -> str:
        return json.dumps(results, ensure_ascii=False, indent=2)
