"""
Token 成本追踪器：记录 LLM API 调用量，支持日/月限额
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
CST = timezone(timedelta(hours=8))

# 内置定价表：元/百万 token
PRICING: Dict[str, Dict[str, float]] = {
    "deepseek-chat":        {"input": 1.0, "output": 2.0},
    "deepseek-reasoner":    {"input": 4.0, "output": 16.0},
    "qwen-plus":            {"input": 0.8, "output": 2.0},
    "qwen-max":             {"input": 2.4, "output": 9.6},
    "qwen-turbo":           {"input": 0.3, "output": 0.6},
    "qwen-flash":           {"input": 0.0, "output": 0.0},
    "glm-4-plus":           {"input": 5.0, "output": 5.0},
    "glm-4-flash":          {"input": 0.0, "output": 0.0},
    "doubao-1-5-pro-32k-250115": {"input": 0.8, "output": 2.0},
    "MiniMax-Text-01":      {"input": 1.0, "output": 8.0},
    "gemini-2.0-flash":     {"input": 0.1, "output": 0.4},
}

DEFAULT_DAILY_LIMIT = 10.0    # 元
DEFAULT_MONTHLY_LIMIT = 200.0  # 元


class CostTracker:
    """Token 成本追踪器"""

    def __init__(self, db_path: str | Path | None = None, config: dict | None = None) -> None:
        self._db_path = str(db_path or ROOT / "data" / "zx_advisor.db")
        self._config = config or {}
        self._daily_limit = self._config.get("daily_limit", DEFAULT_DAILY_LIMIT)
        self._monthly_limit = self._config.get("monthly_limit", DEFAULT_MONTHLY_LIMIT)
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_table(self) -> None:
        ddl_path = ROOT / "data" / "sql_schema" / "08_cost_tracking.sql"
        if ddl_path.exists():
            sql = ddl_path.read_text(encoding="utf-8")
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now', '+8 hours')),
                model_name TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost_yuan REAL DEFAULT 0.0,
                session_id TEXT,
                turn_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON token_usage(timestamp);
            CREATE INDEX IF NOT EXISTS idx_usage_model ON token_usage(model_name);
            """
        conn = self._connect()
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        pricing = PRICING.get(model_name, {"input": 1.0, "output": 2.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    def record_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        session_id: str = "",
        turn_id: str = "",
    ) -> float:
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO token_usage (model_name, input_tokens, output_tokens, cost_yuan, session_id, turn_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (model_name, input_tokens, output_tokens, cost, session_id, turn_id),
            )
            conn.commit()
        finally:
            conn.close()
        return cost

    def get_daily_usage(self, date: str | None = None) -> dict:
        if not date:
            date = datetime.now(CST).strftime("%Y-%m-%d")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), COALESCE(SUM(cost_yuan),0), COUNT(*) "
                "FROM token_usage WHERE date(timestamp) = ?",
                (date,),
            ).fetchone()
            by_model = conn.execute(
                "SELECT model_name, SUM(input_tokens), SUM(output_tokens), SUM(cost_yuan), COUNT(*) "
                "FROM token_usage WHERE date(timestamp) = ? GROUP BY model_name ORDER BY SUM(cost_yuan) DESC",
                (date,),
            ).fetchall()
            return {
                "date": date,
                "total_input_tokens": row[0],
                "total_output_tokens": row[1],
                "total_cost_yuan": round(row[2], 4),
                "request_count": row[3],
                "by_model": [
                    {"model": r[0], "input_tokens": r[1], "output_tokens": r[2],
                     "cost_yuan": round(r[3], 4), "count": r[4]}
                    for r in by_model
                ],
            }
        finally:
            conn.close()

    def get_monthly_usage(self, month: str | None = None) -> dict:
        if not month:
            month = datetime.now(CST).strftime("%Y-%m")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), COALESCE(SUM(cost_yuan),0), COUNT(*) "
                "FROM token_usage WHERE strftime('%%Y-%%m', timestamp) = ?",
                (month,),
            ).fetchone()
            return {
                "month": month,
                "total_input_tokens": row[0],
                "total_output_tokens": row[1],
                "total_cost_yuan": round(row[2], 4),
                "request_count": row[3],
                "daily_limit": self._daily_limit,
                "monthly_limit": self._monthly_limit,
            }
        finally:
            conn.close()

    def check_limit(self) -> tuple[bool, str]:
        daily = self.get_daily_usage()
        monthly = self.get_monthly_usage()
        if daily["total_cost_yuan"] >= self._daily_limit:
            return False, f"日限额已达 {daily['total_cost_yuan']:.2f}/{self._daily_limit:.2f} 元"
        if monthly["total_cost_yuan"] >= self._monthly_limit:
            return False, f"月限额已达 {monthly['total_cost_yuan']:.2f}/{self._monthly_limit:.2f} 元"
        return True, ""
