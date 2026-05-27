from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

ROOT = Path(__file__).resolve().parents[1]

_CRM_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL UNIQUE,
    province TEXT DEFAULT '',
    subject_type TEXT DEFAULT '',
    major_name TEXT DEFAULT '',
    score INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 0,
    budget INTEGER DEFAULT 0,
    target_city TEXT DEFAULT '',
    postgraduate_plan TEXT DEFAULT '',
    extra_tags TEXT DEFAULT '{}',
    session_count INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_seen_at TEXT DEFAULT (datetime('now')),
    last_query TEXT DEFAULT '',
    last_intent TEXT DEFAULT ''
);
"""

_INDEX_PHONE = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_phone ON user_profiles (phone_number);
"""

_INDEX_LAST_SEEN = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_last_seen ON user_profiles (last_seen_at DESC);
"""

_PROFILE_KEY_MAP = [
    "province", "subject_type", "major_name", "score", "rank",
    "budget", "target_city", "postgraduate_plan",
]


class CRMProfileManager:
    """
    CRM 用户画像持久化管理器。

    将 state_schema.py 中收集的 user_profile 结构体以 phone_number 为
    主键存入 CRM 表，支持断点续传——下次用户来访时直接从 CRM 加载历史画像
    作为 LangGraph 的 initial state，无需重放全量聊天历史。
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_table(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text(_CRM_TABLE_DDL))
            await conn.execute(text(_INDEX_PHONE))
            await conn.execute(text(_INDEX_LAST_SEEN))

    async def load_profile(self, phone_number: str) -> Dict[str, Any]:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT * FROM user_profiles WHERE phone_number = :pn"),
                    {"pn": phone_number},
                )
            ).mappings().first()

        if not row:
            return {}

        profile: Dict[str, Any] = {
            "phone_number": row["phone_number"],
        }
        for key in _PROFILE_KEY_MAP:
            val = row.get(key)
            if val is not None and val != "" and val != 0:
                profile[key] = val
        return profile

    async def save_profile(
        self,
        phone_number: str,
        user_profile: Dict[str, Any],
        last_query: str = "",
        last_intent: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with self._engine.begin() as conn:
            existing = (
                await conn.execute(
                    text("SELECT id, session_count FROM user_profiles WHERE phone_number = :pn"),
                    {"pn": phone_number},
                )
            ).mappings().first()

            if existing:
                await conn.execute(
                    text("""
                        UPDATE user_profiles SET
                            province = :province,
                            subject_type = :subject_type,
                            major_name = :major_name,
                            score = :score,
                            rank = :rank,
                            budget = :budget,
                            target_city = :target_city,
                            postgraduate_plan = :postgraduate_plan,
                            session_count = :session_count,
                            last_seen_at = :last_seen_at,
                            last_query = :last_query,
                            last_intent = :last_intent
                        WHERE phone_number = :phone_number
                    """),
                    {
                        "province": user_profile.get("province", ""),
                        "subject_type": user_profile.get("subject_type", ""),
                        "major_name": user_profile.get("major_name", ""),
                        "score": user_profile.get("score", 0),
                        "rank": user_profile.get("rank", 0),
                        "budget": user_profile.get("budget", 0),
                        "target_city": user_profile.get("target_city", ""),
                        "postgraduate_plan": user_profile.get("postgraduate_plan", ""),
                        "session_count": existing["session_count"] + 1,
                        "last_seen_at": now,
                        "last_query": last_query,
                        "last_intent": last_intent,
                        "phone_number": phone_number,
                    },
                )
            else:
                await conn.execute(
                    text("""
                        INSERT INTO user_profiles (
                            phone_number, province, subject_type, major_name,
                            score, rank, budget, target_city, postgraduate_plan,
                            session_count, first_seen_at, last_seen_at,
                            last_query, last_intent
                        ) VALUES (
                            :phone_number, :province, :subject_type, :major_name,
                            :score, :rank, :budget, :target_city, :postgraduate_plan,
                            1, :first_seen_at, :last_seen_at,
                            :last_query, :last_intent
                        )
                    """),
                    {
                        "phone_number": phone_number,
                        "province": user_profile.get("province", ""),
                        "subject_type": user_profile.get("subject_type", ""),
                        "major_name": user_profile.get("major_name", ""),
                        "score": user_profile.get("score", 0),
                        "rank": user_profile.get("rank", 0),
                        "budget": user_profile.get("budget", 0),
                        "target_city": user_profile.get("target_city", ""),
                        "postgraduate_plan": user_profile.get("postgraduate_plan", ""),
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "last_query": last_query,
                        "last_intent": last_intent,
                    },
                )
