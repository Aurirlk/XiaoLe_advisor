from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import yaml

from core.web_search_status import push_status
from core.web_search_store import WebSearchStore, make_hash
from tools.page_fetcher import PageFetcher
from tools.web_search_tools import WebSearchTools

if TYPE_CHECKING:
    from tools.vector_store import ChromaVectorStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "web_search_config.yaml"


@dataclass
class WebSearchConfig:
    top_k: int = 5
    search_timeout_seconds: float = 4.0
    fetch_timeout_seconds: float = 8.0
    max_content_bytes: int = 512_000
    cache_ttl_hours: int = 24
    user_agent: str = "Mozilla/5.0 (compatible; ZXAIAdvisor/1.0)"
    enable_page_fetch: bool = True
    vector_collection: str = "zx_web_cache"
    max_chroma_text_chars: int = 2000
    synthesis_excerpt_chars: int = 800
    fetch_concurrency: int = 3

    @classmethod
    def load(cls, path: Path | None = None) -> "WebSearchConfig":
        cfg_path = path or DEFAULT_CONFIG_PATH
        data: Dict[str, Any] = {}
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f).get("web_search", {}) or {}
        ttl = int(os.getenv("WEB_SEARCH_CACHE_TTL_HOURS", data.get("cache_ttl_hours", 24)))
        enable_fetch = os.getenv("WEB_SEARCH_ENABLE_FETCH", "").strip()
        if enable_fetch == "0":
            fetch_enabled = False
        elif enable_fetch == "1":
            fetch_enabled = True
        else:
            fetch_enabled = bool(data.get("enable_page_fetch", True))
        return cls(
            top_k=int(data.get("top_k", 5)),
            search_timeout_seconds=float(data.get("search_timeout_seconds", 4)),
            fetch_timeout_seconds=float(data.get("fetch_timeout_seconds", 8)),
            max_content_bytes=int(data.get("max_content_bytes", 512_000)),
            cache_ttl_hours=ttl,
            user_agent=str(data.get("user_agent", "Mozilla/5.0 (compatible; ZXAIAdvisor/1.0)")),
            enable_page_fetch=fetch_enabled,
            vector_collection=str(data.get("vector_collection", "zx_web_cache")),
            max_chroma_text_chars=int(data.get("max_chroma_text_chars", 2000)),
            synthesis_excerpt_chars=int(data.get("synthesis_excerpt_chars", 800)),
            fetch_concurrency=int(data.get("fetch_concurrency", 3)),
        )


@dataclass
class WebSearchBundle:
    formatted_text: str
    pages: List[Dict[str, Any]] = field(default_factory=list)
    db_session_id: int = 0
    from_cache: bool = False
    query_hash: str = ""


StatusCallback = Callable[[str], None]


class WebSearchService:
    def __init__(
        self,
        store: WebSearchStore,
        web_search: WebSearchTools | None = None,
        page_fetcher: PageFetcher | None = None,
        vector_store: "ChromaVectorStore | None" = None,
        config: WebSearchConfig | None = None,
    ) -> None:
        self.config = config or WebSearchConfig.load()
        self.store = store
        self.web_search = web_search or WebSearchTools(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.search_timeout_seconds,
        )
        self.page_fetcher = page_fetcher or PageFetcher(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.fetch_timeout_seconds,
            max_content_bytes=self.config.max_content_bytes,
        )
        self.vector_store = vector_store

    async def search_fetch_and_persist(
        self,
        query: str,
        chat_session_id: str = "",
        *,
        force_refresh: bool = False,
        on_status: Optional[StatusCallback] = None,
    ) -> WebSearchBundle:
        q = (query or "").strip()
        if not q:
            return WebSearchBundle(
                formatted_text="【系统提示：查询内容为空】",
                query_hash=make_hash(""),
            )

        def _status(msg: str) -> None:
            if chat_session_id:
                push_status(chat_session_id, msg)
            if on_status:
                on_status(msg)

        if not force_refresh:
            cached = await self.store.find_cached_session(q, self.config.cache_ttl_hours)
            if cached and cached.pages:
                _status("命中本地联网查询缓存")
                formatted = self._format_pages(cached.pages)
                return WebSearchBundle(
                    formatted_text=formatted,
                    pages=cached.pages,
                    db_session_id=cached.db_session_id,
                    from_cache=True,
                    query_hash=cached.query_hash,
                )

        _status("正在联网搜索...")
        results = self.web_search.search(q, top_k=self.config.top_k)
        if not results:
            return WebSearchBundle(
                formatted_text=(
                    "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），"
                    "请基于本地数据与经验回答】"
                ),
                query_hash=make_hash(q),
            )

        db_session_id, query_hash = await self.store.create_session(q, chat_session_id)

        if self.config.enable_page_fetch:
            sem = asyncio.Semaphore(self.config.fetch_concurrency)
            pages: List[Dict[str, Any]] = []

            async def _fetch_one(idx: int, item: Dict[str, str]) -> Dict[str, Any]:
                url = item.get("url", "")
                title = item.get("title", "")
                _status(f"正在抓取网页 {idx + 1}/{len(results)}...")
                async with sem:
                    if not url:
                        return {
                            "url": url,
                            "title": title,
                            "content_text": "",
                            "fetch_status": "error",
                            "fetch_error": "empty url",
                        }
                    fetch = await self.page_fetcher.fetch_page(url)
                return {
                    "url": url,
                    "title": title,
                    "content_text": fetch.text if fetch.status == "ok" else "",
                    "fetch_status": fetch.status,
                    "fetch_error": fetch.error,
                    "content_chars": fetch.chars,
                }

            fetched = await asyncio.gather(
                *[_fetch_one(i, r) for i, r in enumerate(results)]
            )
            pages = list(fetched)
        else:
            pages = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content_text": "",
                    "fetch_status": "skipped",
                    "fetch_error": "",
                    "content_chars": 0,
                }
                for r in results
            ]

        for page in pages:
            await self.store.save_page(
                db_session_id,
                url=page.get("url", ""),
                title=page.get("title", ""),
                content_text=page.get("content_text", ""),
                fetch_status=page.get("fetch_status", "pending"),
                fetch_error=page.get("fetch_error", ""),
            )

        await self.store.update_session_count(db_session_id, len(pages))

        if self.vector_store:
            _status("正在写入向量缓存...")
            self._upsert_to_vector(q, pages)

        formatted = self._format_pages(pages)
        return WebSearchBundle(
            formatted_text=formatted,
            pages=pages,
            db_session_id=db_session_id,
            from_cache=False,
            query_hash=query_hash,
        )

    def _upsert_to_vector(self, query: str, pages: List[Dict[str, Any]]) -> None:
        if not self.vector_store:
            return
        docs: List[Dict[str, str]] = []
        for page in pages:
            url = page.get("url", "")
            if not url or page.get("fetch_status") not in ("ok", "skipped"):
                continue
            title = page.get("title", "")
            body = (page.get("content_text") or "")[: self.config.max_chroma_text_chars]
            if not body and page.get("fetch_status") == "skipped":
                body = title
            if not body:
                continue
            url_hash = make_hash(url)
            docs.append(
                {
                    "id": url_hash,
                    "source": url,
                    "text": f"{title}\n\n{body}".strip(),
                    "meta_type": "web_search",
                    "meta_query_hash": make_hash(query),
                }
            )
        if docs:
            self.vector_store.upsert_documents(docs, id_key="id")

    def _format_pages(self, pages: List[Dict[str, Any]]) -> str:
        if not pages:
            return ""
        excerpt = self.config.synthesis_excerpt_chars
        blocks: List[str] = []
        for i, page in enumerate(pages, start=1):
            title = page.get("title", "").strip()
            url = page.get("url", "").strip()
            status = page.get("fetch_status", "")
            body = (page.get("content_text") or "").strip()
            if body:
                body = body[:excerpt] + ("..." if len(body) > excerpt else "")
            elif status not in ("ok", "skipped"):
                body = f"[抓取失败: {page.get('fetch_error', status)}]"
            header = f"[来源{i}] {title} | {url}"
            blocks.append(f"{header}\n{body}\n---")
        return "\n".join(blocks).strip()
