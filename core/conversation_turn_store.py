from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


_TURNS_DDL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    assistant_response TEXT DEFAULT '',
    route_path TEXT DEFAULT '[]',
    user_profile_snapshot TEXT DEFAULT '{}',
    sql_hit_count INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_turns_created ON conversation_turns (created_at DESC);",
]


@dataclass
class TurnRecord:
    turn_id: str
    session_id: str
    user_query: str
    assistant_response: str
    route_path: List[str]
    user_profile_snapshot: Dict[str, Any]
    sql_hit_count: int
    risk_level: str


class ConversationTurnStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_tables(self) -> None:
        from scripts.init_sqlite import init_sqlite

        init_sqlite()

    async def save_turn(
        self,
        turn_id: str,
        session_id: str,
        user_query: str,
        assistant_response: str,
        route_path: List[str],
        user_profile_snapshot: Dict[str, Any] | None = None,
        sql_hit_count: int = 0,
        risk_level: str = "",
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO conversation_turns (
                        turn_id, session_id, user_query, assistant_response,
                        route_path, user_profile_snapshot, sql_hit_count, risk_level
                    )
                    VALUES (
                        :turn_id, :session_id, :user_query, :assistant_response,
                        :route_path, :user_profile_snapshot, :sql_hit_count, :risk_level
                    )
                    ON CONFLICT(turn_id) DO UPDATE SET
                        assistant_response = excluded.assistant_response,
                        route_path = excluded.route_path,
                        user_profile_snapshot = excluded.user_profile_snapshot,
                        sql_hit_count = excluded.sql_hit_count,
                        risk_level = excluded.risk_level
                    """
                ),
                {
                    "turn_id": turn_id,
                    "session_id": session_id,
                    "user_query": user_query,
                    "assistant_response": assistant_response,
                    "route_path": json.dumps(route_path, ensure_ascii=False),
                    "user_profile_snapshot": json.dumps(
                        user_profile_snapshot or {}, ensure_ascii=False
                    ),
                    "sql_hit_count": sql_hit_count,
                    "risk_level": risk_level,
                },
            )

    async def get_turn(self, turn_id: str) -> Optional[Dict[str, Any]]:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT * FROM conversation_turns WHERE turn_id = :tid"),
                    {"tid": turn_id},
                )
            ).mappings().first()
        if not row:
            return None
        data = dict(row)
        data["route_path"] = json.loads(data.get("route_path") or "[]")
        data["user_profile_snapshot"] = json.loads(
            data.get("user_profile_snapshot") or "{}"
        )
        return data

    async def list_turns(
        self,
        session_id: str | None = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if session_id:
            sql = """
                SELECT * FROM conversation_turns
                WHERE session_id = :sid
                ORDER BY created_at DESC LIMIT :lim
            """
            params = {"sid": session_id, "lim": limit}
        else:
            sql = """
                SELECT * FROM conversation_turns
                ORDER BY created_at DESC LIMIT :lim
            """
            params = {"lim": limit}
        async with self._engine.begin() as conn:
            rows = (await conn.execute(text(sql), params)).mappings().all()
        result = []
        for row in rows:
            data = dict(row)
            data["route_path"] = json.loads(data.get("route_path") or "[]")
            data["user_profile_snapshot"] = json.loads(
                data.get("user_profile_snapshot") or "{}"
            )
            result.append(data)
        return result

    async def count_turns_since(self, days: int) -> int:
        if not isinstance(days, int) or days < 1:
            raise ValueError(f"days 必须是正整数，收到: {days}")
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) AS cnt FROM conversation_turns
                        WHERE created_at >= datetime('now', :offset)
                        """
                    ),
                    {"offset": f"-{days} days"},
                )
            ).mappings().first()
        return int(row["cnt"]) if row else 0
