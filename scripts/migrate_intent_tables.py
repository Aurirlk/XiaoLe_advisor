"""
数据库迁移脚本 — 创建意图日志表和决策旅程表

运行方式：
python scripts/migrate_intent_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sqlite3

# 意图日志表
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

INTENT_LOG_INDEX_PHONE = """
CREATE INDEX IF NOT EXISTS idx_intent_log_phone ON user_intent_log (phone_number);
"""

INTENT_LOG_INDEX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_intent_log_session ON user_intent_log (session_id);
"""

# 决策旅程表
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

DECISION_JOURNEY_INDEX_PHONE = """
CREATE INDEX IF NOT EXISTS idx_decision_journey_phone ON user_decision_journey (phone_number);
"""


def migrate():
    """执行迁移（同步方式）"""
    # 数据库路径
    db_path = ROOT / "data" / "zx_advisor.db"
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        print("请先运行 init_sqlite.py 初始化数据库")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("开始迁移...")
        
        # 创建意图日志表
        print("创建 user_intent_log 表...")
        cursor.execute(INTENT_LOG_TABLE_DDL)
        cursor.execute(INTENT_LOG_INDEX_PHONE)
        cursor.execute(INTENT_LOG_INDEX_SESSION)
        print("✓ user_intent_log 表创建完成")
        
        # 创建决策旅程表
        print("创建 user_decision_journey 表...")
        cursor.execute(DECISION_JOURNEY_TABLE_DDL)
        cursor.execute(DECISION_JOURNEY_INDEX_PHONE)
        print("✓ user_decision_journey 表创建完成")
        
        conn.commit()
        conn.close()
        
        print("\n迁移完成！")
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
