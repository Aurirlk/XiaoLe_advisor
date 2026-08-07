from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]

# ── user_profiles 单一 schema 真相源（P0-13）──────────────
# 同时承载：登录认证（username/password_hash/role）+ CRM 画像。
# 任何地方（scripts/init_sqlite.py 等）不得再重复定义本表。
_CRM_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL UNIQUE,
    username TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    role TEXT DEFAULT 'student',
    status TEXT DEFAULT 'active',
    province TEXT DEFAULT '',
    subject_type TEXT DEFAULT '',
    subject_combo TEXT DEFAULT '',
    major_name TEXT DEFAULT '',
    score INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 0,
    budget INTEGER DEFAULT 0,
    budget_range TEXT DEFAULT '',
    target_city TEXT DEFAULT '',
    postgraduate_plan TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    is_repeat INTEGER DEFAULT 0,
    gaokao_city TEXT DEFAULT '',
    risk_tolerance TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    special_notes TEXT DEFAULT '',
    subject_scores_json TEXT DEFAULT '{}',
    extra_tags TEXT DEFAULT '{}',
    session_count INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_seen_at TEXT DEFAULT (datetime('now')),
    last_query TEXT DEFAULT '',
    last_intent TEXT DEFAULT ''
);
"""

# 幂等迁移：为已存在的旧表补齐所有画像/认证列（修复 P0-13 的 no such column 崩库）。
# 以完整 DDL 为真相源：除主键 id 与 phone_number 外的全部列都在此清单。
_MIGRATION_COLUMNS: dict[str, str] = {
    "username": "TEXT DEFAULT ''",
    "password_hash": "TEXT DEFAULT ''",
    "role": "TEXT DEFAULT 'student'",
    "status": "TEXT DEFAULT 'active'",
    "province": "TEXT DEFAULT ''",
    "subject_type": "TEXT DEFAULT ''",
    "subject_combo": "TEXT DEFAULT ''",
    "major_name": "TEXT DEFAULT ''",
    "score": "INTEGER DEFAULT 0",
    "rank": "INTEGER DEFAULT 0",
    "budget": "INTEGER DEFAULT 0",
    "budget_range": "TEXT DEFAULT ''",
    "target_city": "TEXT DEFAULT ''",
    "postgraduate_plan": "TEXT DEFAULT ''",
    "gender": "TEXT DEFAULT ''",
    "is_repeat": "INTEGER DEFAULT 0",
    "gaokao_city": "TEXT DEFAULT ''",
    "risk_tolerance": "TEXT DEFAULT ''",
    "personality": "TEXT DEFAULT ''",
    "special_notes": "TEXT DEFAULT ''",
    "subject_scores_json": "TEXT DEFAULT '{}'",
    "extra_tags": "TEXT DEFAULT '{}'",
    "session_count": "INTEGER NOT NULL DEFAULT 0",
    # 注意：ALTER TABLE ADD COLUMN 要求常量默认值，不能用 datetime('now')；
    # 新表（完整 DDL）仍会用实时时间戳，此处仅用于旧表补列。
    "first_seen_at": "TEXT DEFAULT ''",
    "last_seen_at": "TEXT DEFAULT ''",
    "last_query": "TEXT DEFAULT ''",
    "last_intent": "TEXT DEFAULT ''",
    "strong_subjects": "TEXT DEFAULT '[]'",
    "weak_subjects": "TEXT DEFAULT '[]'",
    "major_preferences": "TEXT DEFAULT '[]'",
    "interests": "TEXT DEFAULT '[]'",
    "target_universities": "TEXT DEFAULT '[]'",
    "target_tiers": "TEXT DEFAULT '[]'",
}

_INDEX_PHONE = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_phone ON user_profiles (phone_number);
"""

_INDEX_LAST_SEEN = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_last_seen ON user_profiles (last_seen_at DESC);
"""

# ── 手机号哈希（PIPL：不落明文，等值查询用确定性哈希）──

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def _phone_hash_salt() -> str:
    salt = os.getenv("PHONE_HASH_SALT", "").strip()
    if not salt:
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise RuntimeError("生产环境必须配置 PHONE_HASH_SALT 环境变量（用于手机号脱敏存储）")
        salt = "zx-crm-dev-salt"
        logger.warning("未配置 PHONE_HASH_SALT，开发环境使用默认盐（仅限本地）")
    return salt


def hash_phone(phone_number: str) -> str:
    """确定性哈希（SHA-256 + 盐）。用于存储与等值查询，禁止回显明文。"""
    if not phone_number:
        return ""
    phone = phone_number.strip()
    return hashlib.sha256((_phone_hash_salt() + phone).encode("utf-8")).hexdigest()


def display_phone(phone_number: str) -> str:
    """对外展示脱敏：仅保留后四位（如 ****1234）。"""
    digits = re.sub(r"\D", "", phone_number or "")
    return f"****{digits[-4:]}" if digits else ""

# ── 意图追踪（已拆分到 intent_tracker.py）──
from core.intent_tracker import (
    IntentTracker,
    INTENT_LOG_TABLE_DDL as _INTENT_LOG_TABLE_DDL,
    INTENT_LOG_INDEX_PHONE as _INTENT_LOG_INDEX_PHONE,
    INTENT_LOG_INDEX_SESSION as _INTENT_LOG_INDEX_SESSION,
    DECISION_JOURNEY_TABLE_DDL as _DECISION_JOURNEY_TABLE_DDL,
    DECISION_JOURNEY_INDEX_PHONE as _DECISION_JOURNEY_INDEX_PHONE,
)

_PROFILE_KEY_MAP = [
    "province", "subject_type", "subject_combo", "major_name", "score", "rank",
    "budget", "budget_range", "target_city", "postgraduate_plan", "gender",
    "is_repeat", "gaokao_city", "risk_tolerance", "personality", "special_notes",
]

_EXTRA_FIELDS = [
    "strong_subjects", "weak_subjects", "major_preferences",
    "interests", "target_universities", "target_tiers",
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

            # 幂等迁移 1：旧表补列（修复 P0-13 的 no such column 崩库）
            cols = {
                row["name"]
                for row in (await conn.execute(text("PRAGMA table_info(user_profiles)"))).mappings()
            }
            for col_name, col_type in _MIGRATION_COLUMNS.items():
                if col_name not in cols:
                    await conn.execute(
                        text(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}")
                    )

            # 幂等迁移 2：存量明文手机号 → 哈希（PIPL 脱敏；仅匹配 11 位手机号，避免重复哈希）
            plain_rows = (
                await conn.execute(text("SELECT id, phone_number FROM user_profiles"))
            ).mappings().all()
            for r in plain_rows:
                raw = r["phone_number"] or ""
                if _PHONE_RE.match(raw.strip()):
                    await conn.execute(
                        text("UPDATE user_profiles SET phone_number = :h WHERE id = :id"),
                        {"h": hash_phone(raw), "id": r["id"]},
                    )

            await conn.execute(text(_INDEX_PHONE))
            await conn.execute(text(_INDEX_LAST_SEEN))
            # V6.0: 意图日志表
            await conn.execute(text(_INTENT_LOG_TABLE_DDL))
            await conn.execute(text(_INTENT_LOG_INDEX_PHONE))
            await conn.execute(text(_INTENT_LOG_INDEX_SESSION))
            # V6.0: 决策旅程表
            await conn.execute(text(_DECISION_JOURNEY_TABLE_DDL))
            await conn.execute(text(_DECISION_JOURNEY_INDEX_PHONE))

    async def load_profile(self, phone_number: str) -> Dict[str, Any]:
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT * FROM user_profiles WHERE phone_number = :pn"),
                    {"pn": hash_phone(phone_number)},
                )
            ).mappings().first()

        if not row:
            return {}

        # 注意：phone_number 已脱敏哈希存储，不回写进 profile（避免污染注入 state 的画像）
        profile: Dict[str, Any] = {}
        for key in _PROFILE_KEY_MAP:
            val = row.get(key)
            if val is not None and val != "":
                profile[key] = val

        # 加载 JSON 字段
        for key in _EXTRA_FIELDS:
            val = row.get(key)
            if val:
                try:
                    parsed = json.loads(val)
                    if parsed:
                        profile[key] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass

        extra_tags = row.get("extra_tags")
        if extra_tags:
            try:
                parsed = json.loads(extra_tags)
                if parsed:
                    profile["extra_tags"] = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        return profile

    async def save_profile(
        self,
        phone_number: str,
        user_profile: Dict[str, Any],
        last_query: str = "",
        last_intent: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        phone_key = hash_phone(phone_number)
        async with self._engine.begin() as conn:
            existing = (
                await conn.execute(
                    text("SELECT id, session_count FROM user_profiles WHERE phone_number = :pn"),
                    {"pn": phone_key},
                )
            ).mappings().first()

            if existing:
                await conn.execute(
                    text("""
                        UPDATE user_profiles SET
                            province = :province,
                            subject_type = :subject_type,
                            subject_combo = :subject_combo,
                            major_name = :major_name,
                            score = :score,
                            rank = :rank,
                            budget = :budget,
                            budget_range = :budget_range,
                            target_city = :target_city,
                            postgraduate_plan = :postgraduate_plan,
                            gender = :gender,
                            is_repeat = :is_repeat,
                            extra_tags = :extra_tags,
                            session_count = :session_count,
                            last_seen_at = :last_seen_at,
                            last_query = :last_query,
                            last_intent = :last_intent
                        WHERE phone_number = :phone_number
                    """),
                    {
                        "province": user_profile.get("province", ""),
                        "subject_type": user_profile.get("subject_type", ""),
                        "subject_combo": user_profile.get("subject_combo", ""),
                        "major_name": user_profile.get("major_name", ""),
                        "score": user_profile.get("score", 0),
                        "rank": user_profile.get("rank", 0),
                        "budget": user_profile.get("budget", 0),
                        "budget_range": user_profile.get("budget_range", ""),
                        "target_city": user_profile.get("target_city", ""),
                        "postgraduate_plan": user_profile.get("postgraduate_plan", ""),
                        "gender": user_profile.get("gender", ""),
                        "is_repeat": 1 if user_profile.get("is_repeat") else 0,
                        "extra_tags": json.dumps(
                            {k: v for k, v in user_profile.items() if k in _EXTRA_FIELDS},
                            ensure_ascii=False
                        ),
                        "session_count": existing["session_count"] + 1,
                        "last_seen_at": now,
                        "last_query": last_query,
                        "last_intent": last_intent,
                        "phone_number": phone_key,
                    },
                )
            else:
                await conn.execute(
                    text("""
                        INSERT INTO user_profiles (
                            phone_number, province, subject_type, subject_combo, major_name,
                            score, rank, budget, budget_range, target_city, postgraduate_plan,
                            gender, is_repeat, extra_tags,
                            session_count, first_seen_at, last_seen_at,
                            last_query, last_intent
                        ) VALUES (
                            :phone_number, :province, :subject_type, :subject_combo, :major_name,
                            :score, :rank, :budget, :budget_range, :target_city, :postgraduate_plan,
                            :gender, :is_repeat, :extra_tags,
                            1, :first_seen_at, :last_seen_at,
                            :last_query, :last_intent
                        )
                    """),
                    {
                        "phone_number": phone_key,
                        "province": user_profile.get("province", ""),
                        "subject_type": user_profile.get("subject_type", ""),
                        "subject_combo": user_profile.get("subject_combo", ""),
                        "major_name": user_profile.get("major_name", ""),
                        "score": user_profile.get("score", 0),
                        "rank": user_profile.get("rank", 0),
                        "budget": user_profile.get("budget", 0),
                        "budget_range": user_profile.get("budget_range", ""),
                        "target_city": user_profile.get("target_city", ""),
                        "postgraduate_plan": user_profile.get("postgraduate_plan", ""),
                        "gender": user_profile.get("gender", ""),
                        "is_repeat": 1 if user_profile.get("is_repeat") else 0,
                        "extra_tags": json.dumps(
                            {k: v for k, v in user_profile.items() if k in _EXTRA_FIELDS},
                            ensure_ascii=False
                        ),
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "last_query": last_query,
                        "last_intent": last_intent,
                    },
                )

    # ── V6.0: 意图追踪（委托给 IntentTracker）──

    def _get_intent_tracker(self) -> "IntentTracker":
        """懒加载 IntentTracker 实例"""
        if not hasattr(self, '_intent_tracker'):
            from core.intent_tracker import IntentTracker
            self._intent_tracker = IntentTracker(self._engine)
        return self._intent_tracker

    async def log_intent(self, phone, session, turn, scene, scene_conf,
                         path=None, path_conf=None, decision=None,
                         signals=None, query="", response="") -> None:
        """记录意图日志"""
        await self._get_intent_tracker().log_intent(
            phone, session, turn, scene, scene_conf,
            path, path_conf, decision, signals, query, response
        )

    async def get_scene_history(self, phone: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户场景历史"""
        return await self._get_intent_tracker().get_scene_history(phone, limit)

    async def detect_hesitation_pattern(self, phone: str) -> Dict[str, Any]:
        """检测用户犹豫模式"""
        return await self._get_intent_tracker().detect_hesitation_pattern(phone)

    async def get_similar_decisions(self, profile: Dict[str, Any], scene: str) -> List[Dict[str, Any]]:
        """获取相似用户的决策"""
        return await self._get_intent_tracker().get_similar_decisions(profile, scene)

    async def log_decision_journey(self, phone, session, stage, milestone, data=None) -> None:
        """记录决策旅程"""
        await self._get_intent_tracker().log_decision_journey(phone, session, stage, milestone, data)

    async def get_user_journey(self, phone: str) -> List[Dict[str, Any]]:
        """获取用户决策旅程"""
        return await self._get_intent_tracker().get_user_journey(phone)

    async def find_similar_profiles(self, profile: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """查找相似画像的用户"""
        async with self._engine.begin() as conn:
            rows = await conn.execute(
                text("""
                    SELECT * FROM user_profiles
                    WHERE province = :province
                      AND subject_type = :subject_type
                      AND ABS(score - :score) < 30
                    ORDER BY last_seen_at DESC
                    LIMIT :limit
                """),
                {
                    "province": profile.get("province", ""),
                    "subject_type": profile.get("subject_type", ""),
                    "score": profile.get("score", 0),
                    "limit": limit,
                },
            )
            return [dict(r) for r in rows.mappings().all()]
