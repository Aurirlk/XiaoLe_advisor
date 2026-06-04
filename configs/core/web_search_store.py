from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def make_hash(value: str) -> str:
    normalized = (value or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


_WEB_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS web_search_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    session_id TEXT DEFAULT '',
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

_WEB_PAGES_DDL = """
CREATE TABLE IF NOT EXISTS web_search_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES web_search_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    title TEXT DEFAULT '',
    snippet TEXT DEFAULT '',
    content_text TEXT DEFAULT '',
    content_chars INTEGER NOT NULL DEFAULT 0,
    fetch_status TEXT NOT NULL DEFAULT 'pending',
    fetch_error TEXT DEFAULT '',
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE (session_id, url_hash)
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_web_sessions_query_hash ON web_search_sessions (query_hash);",
    "CREATE INDEX IF NOT EXISTS idx_web_sessions_created_at ON web_search_sessions (created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_web_pages_url_hash ON web_search_pages (url_hash);",
    "CREATE INDEX IF NOT EXISTS idx_web_pages_fetched_at ON web_search_pages (fetched_at DESC);",
]


@dataclass
class CachedSession:
    db_session_id: int
    query_text: str
    query_hash: str
    chat_session_id: str
    result_count: int
    created_at: str
    pages: List[Dict[str, Any]]


class WebSearchStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text(_WEB_SESSIONS_DDL))
            await conn.execute(text(_WEB_PAGES_DDL))
            for stmt in _INDEXES:
                await conn.execute(text(stmt))

    async def create_session(
        self,
        query_text: str,
        chat_session_id: str = "",
    ) -> tuple[int, str]:
        query_hash = make_hash(query_text)
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    INSERT INTO web_search_sessions (query_text, query_hash, session_id, result_count)
                    VALUES (:query_text, :query_hash, :session_id, 0)
                    """
                ),
                {
                    "query_text": query_text,
                    "query_hash": query_hash,
                    "session_id": chat_session_id or "",
                },
            )
            row_id = result.lastrowid
        return int(row_id), query_hash

    async def update_session_count(self, db_session_id: int, count: int) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE web_search_sessions SET result_count = :count WHERE id = :id"
                ),
                {"count": count, "id": db_session_id},
            )

    async def save_page(
        self,
        db_session_id: int,
        *,
        url: str,
        title: str = "",
        snippet: str = "",
        content_text: str = "",
        fetch_status: str = "pending",
        fetch_error: str = "",
    ) -> None:
        url_hash = make_hash(url)
        content_chars = len(content_text or "")
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO web_search_pages (
                        session_id, url, url_hash, title, snippet,
                        content_text, content_chars, fetch_status, fetch_error
                    )
                    VALUES (
                        :session_id, :url, :url_hash, :title, :snippet,
                        :content_text, :content_chars, :fetch_status, :fetch_error
                    )
                    ON CONFLICT(session_id, url_hash) DO UPDATE SET
                        title = excluded.title,
                        snippet = excluded.snippet,
                        content_text = excluded.content_text,
                        content_chars = excluded.content_chars,
                        fetch_status = excluded.fetch_status,
                        fetch_error = excluded.fetch_error,
                        fetched_at = datetime('now')
                    """
                ),
                {
                    "session_id": db_session_id,
                    "url": url,
                    "url_hash": url_hash,
                    "title": title,
                    "snippet": snippet,
                    "content_text": content_text,
                    "content_chars": content_chars,
                    "fetch_status": fetch_status,
                    "fetch_error": fetch_error or "",
                },
            )

    async def find_cached_session(
        self,
        query_text: str,
        ttl_hours: int = 24,
    ) -> Optional[CachedSession]:
        query_hash = make_hash(query_text)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, query_text, query_hash, session_id, result_count, created_at
                        FROM web_search_sessions
                        WHERE query_hash = :query_hash AND created_at >= :cutoff
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {"query_hash": query_hash, "cutoff": cutoff},
                )
            ).mappings().first()
            if not row:
                return None
            pages = await self.get_session_pages(int(row["id"]), conn=conn)
        return CachedSession(
            db_session_id=int(row["id"]),
            query_text=str(row["query_text"]),
            query_hash=str(row["query_hash"]),
            chat_session_id=str(row["session_id"] or ""),
            result_count=int(row["result_count"] or 0),
            created_at=str(row["created_at"] or ""),
            pages=pages,
        )

    async def get_session_pages(
        self,
        db_session_id: int,
        conn=None,
    ) -> List[Dict[str, Any]]:
        query = text(
            """
            SELECT url, title, snippet, content_text, content_chars,
                   fetch_status, fetch_error, fetched_at
            FROM web_search_pages
            WHERE session_id = :session_id
            ORDER BY id ASC
            """
        )
        params = {"session_id": db_session_id}
        if conn is not None:
            rows = (await conn.execute(query, params)).mappings().all()
        else:
            async with self._engine.connect() as c:
                rows = (await c.execute(query, params)).mappings().all()
        return [dict(r) for r in rows]

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, query_text, query_hash, session_id,
                               result_count, created_at
                        FROM web_search_sessions
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    {"limit": limit, "offset": offset},
                )
            ).mappings().all()
        return [dict(r) for r in rows]

    async def get_session(self, db_session_id: int) -> Optional[Dict[str, Any]]:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, query_text, query_hash, session_id,
                               result_count, created_at
                        FROM web_search_sessions
                        WHERE id = :id
                        """
                    ),
                    {"id": db_session_id},
                )
            ).mappings().first()
            if not row:
                return None
            pages = await self.get_session_pages(db_session_id, conn=conn)
        return {**dict(row), "pages": pages}
