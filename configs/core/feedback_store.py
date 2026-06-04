from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


_FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    rating INTEGER NOT NULL,
    tags TEXT DEFAULT '[]',
    comment TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_records (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback_records (rating);",
]


@dataclass
class FeedbackRecord:
    turn_id: str
    session_id: str
    rating: int
    tags: List[str]
    comment: str = ""


class FeedbackStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_tables(self) -> None:
        from scripts.init_sqlite import init_sqlite

        init_sqlite()

    async def save_feedback(self, record: FeedbackRecord) -> int:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    INSERT INTO feedback_records (turn_id, session_id, rating, tags, comment)
                    VALUES (:turn_id, :session_id, :rating, :tags, :comment)
                    ON CONFLICT(turn_id) DO UPDATE SET
                        rating = excluded.rating,
                        tags = excluded.tags,
                        comment = excluded.comment
                    """
                ),
                {
                    "turn_id": record.turn_id,
                    "session_id": record.session_id,
                    "rating": record.rating,
                    "tags": json.dumps(record.tags, ensure_ascii=False),
                    "comment": record.comment,
                },
            )
            if result.lastrowid:
                return int(result.lastrowid)
            row = (
                await conn.execute(
                    text("SELECT id FROM feedback_records WHERE turn_id = :tid"),
                    {"tid": record.turn_id},
                )
            ).first()
            return int(row[0]) if row else 0

    async def get_feedback(self, turn_id: str) -> Optional[Dict[str, Any]]:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT * FROM feedback_records WHERE turn_id = :tid"),
                    {"tid": turn_id},
                )
            ).mappings().first()
        if not row:
            return None
        data = dict(row)
        data["tags"] = json.loads(data.get("tags") or "[]")
        return data

    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        async with self._engine.begin() as conn:
            summary = (
                await conn.execute(
                    text(
                        """
                        SELECT
                            COUNT(*) AS total,
                            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS positive,
                            SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS negative
                        FROM feedback_records
                        WHERE created_at >= datetime('now', :offset)
                        """
                    ),
                    {"offset": f"-{days} days"},
                )
            ).mappings().first()

            tag_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT tags FROM feedback_records
                        WHERE rating = -1 AND created_at >= datetime('now', :offset)
                        """
                    ),
                    {"offset": f"-{days} days"},
                )
            ).fetchall()

            joined = (
                await conn.execute(
                    text(
                        """
                        SELECT f.rating, t.route_path
                        FROM feedback_records f
                        JOIN conversation_turns t ON t.turn_id = f.turn_id
                        WHERE f.created_at >= datetime('now', :offset)
                        """
                    ),
                    {"offset": f"-{days} days"},
                )
            ).fetchall()

        tag_counts: Dict[str, int] = {}
        for (tags_json,) in tag_rows:
            for tag in json.loads(tags_json or "[]"):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        route_stats: Dict[str, Dict[str, int]] = {}
        for rating, route_path_json in joined:
            paths = json.loads(route_path_json or "[]")
            key = "->".join(paths) if paths else "unknown"
            bucket = route_stats.setdefault(key, {"positive": 0, "negative": 0, "total": 0})
            bucket["total"] += 1
            if rating == 1:
                bucket["positive"] += 1
            elif rating == -1:
                bucket["negative"] += 1

        total = int(summary["total"] or 0) if summary else 0
        positive = int(summary["positive"] or 0) if summary else 0
        negative = int(summary["negative"] or 0) if summary else 0
        return {
            "days": days,
            "feedback_count": total,
            "positive_count": positive,
            "negative_count": negative,
            "satisfaction_rate": round(positive / total, 3) if total else 0.0,
            "tag_distribution": tag_counts,
            "by_route_path": route_stats,
        }

    async def list_negative_feedback(self, days: int = 30) -> List[Dict[str, Any]]:
        async with self._engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT f.*, t.user_query, t.assistant_response, t.route_path
                        FROM feedback_records f
                        JOIN conversation_turns t ON t.turn_id = f.turn_id
                        WHERE f.rating = -1
                          AND f.created_at >= datetime('now', :offset)
                        ORDER BY f.created_at DESC
                        """
                    ),
                    {"offset": f"-{days} days"},
                )
            ).mappings().all()
        result = []
        for row in rows:
            data = dict(row)
            data["tags"] = json.loads(data.get("tags") or "[]")
            data["route_path"] = json.loads(data.get("route_path") or "[]")
            result.append(data)
        return result

    async def get_session_negative_tags(self, session_id: str) -> List[str]:
        async with self._engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT tags FROM feedback_records
                        WHERE session_id = :sid AND rating = -1
                        ORDER BY created_at DESC LIMIT 5
                        """
                    ),
                    {"sid": session_id},
                )
            ).fetchall()
        tags: List[str] = []
        for (tags_json,) in rows:
            tags.extend(json.loads(tags_json or "[]"))
        return list(dict.fromkeys(tags))
