"""
意图追踪器 — 从 crm_manager.py 拆分

职责：记录用户意图日志、决策旅程、犹豫模式检测
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


# ── DDL ──
INTENT_LOG_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS user_intent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    scene_type TEXT NOT NULL,
    scene_confidence REAL,
    path_type TEXT,
    path_confidence REAL,
    decision_state TEXT,
    hesitation_signals TEXT DEFAULT '[]',
    query TEXT,
    response TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

INTENT_LOG_INDEX_PHONE = "CREATE INDEX IF NOT EXISTS idx_intent_log_phone ON user_intent_log (phone_number);"
INTENT_LOG_INDEX_SESSION = "CREATE INDEX IF NOT EXISTS idx_intent_log_session ON user_intent_log (session_id);"

DECISION_JOURNEY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS user_decision_journey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    session_id TEXT NOT NULL,
    journey_stage TEXT NOT NULL,
    milestone TEXT NOT NULL,
    milestone_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

DECISION_JOURNEY_INDEX_PHONE = "CREATE INDEX IF NOT EXISTS idx_decision_journey_phone ON user_decision_journey (phone_number);"


class IntentTracker:
    """意图追踪管理器"""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_tables(self) -> None:
        """创建意图追踪相关表"""
        async with self._engine.begin() as conn:
            await conn.execute(text(INTENT_LOG_TABLE_DDL))
            await conn.execute(text(INTENT_LOG_INDEX_PHONE))
            await conn.execute(text(INTENT_LOG_INDEX_SESSION))
            await conn.execute(text(DECISION_JOURNEY_TABLE_DDL))
            await conn.execute(text(DECISION_JOURNEY_INDEX_PHONE))

    async def log_intent(
        self,
        phone: str,
        session: str,
        turn: int,
        scene: str,
        scene_conf: float,
        path: Optional[str] = None,
        path_conf: Optional[float] = None,
        decision: Optional[str] = None,
        signals: Optional[List[str]] = None,
        query: str = "",
        response: str = "",
    ) -> None:
        """记录意图日志"""
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO user_intent_log 
                    (phone_number, session_id, turn_id, scene_type, scene_confidence,
                     path_type, path_confidence, decision_state, hesitation_signals,
                     query, response)
                    VALUES (:phone, :session, :turn, :scene, :scene_conf,
                            :path, :path_conf, :decision, :signals,
                            :query, :response)
                """),
                {
                    "phone": phone, "session": session, "turn": turn,
                    "scene": scene, "scene_conf": scene_conf,
                    "path": path, "path_conf": path_conf,
                    "decision": decision,
                    "signals": json.dumps(signals or [], ensure_ascii=False),
                    "query": query, "response": response,
                },
            )

    async def get_scene_history(self, phone: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户场景历史"""
        async with self._engine.begin() as conn:
            rows = await conn.execute(
                text("""
                    SELECT scene_type, scene_confidence, path_type, decision_state, created_at
                    FROM user_intent_log 
                    WHERE phone_number = :phone 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """),
                {"phone": phone, "limit": limit},
            )
            return [dict(r) for r in rows.mappings().all()]

    async def detect_hesitation_pattern(self, phone: str) -> Dict[str, Any]:
        """检测用户犹豫模式"""
        history = await self.get_scene_history(phone, limit=20)
        
        if len(history) < 3:
            return {"pattern": "new_user", "confidence": 0.0}
        
        scene_changes = sum(
            1 for i in range(1, len(history))
            if history[i]["scene_type"] != history[i - 1]["scene_type"]
        )
        
        hesitation_count = sum(
            1 for h in history if h["decision_state"] in ("hesitant", "lost")
        )
        
        if hesitation_count > len(history) * 0.5:
            return {"pattern": "chronic_hesitator", "confidence": 0.8}
        elif scene_changes > len(history) * 0.3:
            return {"pattern": "topic_switcher", "confidence": 0.7}
        else:
            return {"pattern": "normal", "confidence": 0.6}

    async def get_similar_decisions(
        self, profile: Dict[str, Any], scene: str
    ) -> List[Dict[str, Any]]:
        """获取相似用户的决策"""
        async with self._engine.begin() as conn:
            rows = await conn.execute(
                text("""
                    SELECT uil.scene_type, uil.path_type, uil.decision_state, COUNT(*) as cnt
                    FROM user_intent_log uil
                    JOIN user_profiles up ON uil.phone_number = up.phone_number
                    WHERE up.province = :province 
                      AND ABS(up.score - :score) < 30
                      AND up.subject_type = :subject_type
                      AND uil.scene_type = :scene
                    GROUP BY uil.scene_type, uil.path_type, uil.decision_state
                    ORDER BY cnt DESC
                    LIMIT 10
                """),
                {
                    "province": profile.get("province", ""),
                    "score": profile.get("score", 0),
                    "subject_type": profile.get("subject_type", ""),
                    "scene": scene,
                },
            )
            return [dict(r) for r in rows.mappings().all()]

    async def log_decision_journey(
        self, phone: str, session: str, stage: str,
        milestone: str, data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录决策旅程"""
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO user_decision_journey 
                    (phone_number, session_id, journey_stage, milestone, milestone_data)
                    VALUES (:phone, :session, :stage, :milestone, :data)
                """),
                {
                    "phone": phone, "session": session,
                    "stage": stage, "milestone": milestone,
                    "data": json.dumps(data or {}, ensure_ascii=False),
                },
            )

    async def get_user_journey(self, phone: str) -> List[Dict[str, Any]]:
        """获取用户决策旅程"""
        async with self._engine.begin() as conn:
            rows = await conn.execute(
                text("""
                    SELECT * FROM user_decision_journey 
                    WHERE phone_number = :phone 
                    ORDER BY created_at DESC
                """),
                {"phone": phone},
            )
            return [dict(r) for r in rows.mappings().all()]
