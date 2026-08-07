"""
问卷字段迁移脚本 — 扩展 user_profiles 表

运行方式：
python scripts/migrate_questionnaire_fields.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sqlite3

# 新增列定义
_NEW_COLUMNS = [
    ("subject_combo", "TEXT DEFAULT ''"),
    ("budget_range", "TEXT DEFAULT ''"),
    ("is_repeat", "INTEGER DEFAULT 0"),
]


def migrate():
    """添加新列到 user_profiles 表"""
    db_path = ROOT / "data" / "zx_advisor.db"
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
        if not cursor.fetchone():
            print("user_profiles 表不存在，跳过迁移")
            conn.close()
            return True
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(user_profiles)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # 添加新列
        added = 0
        for col_name, col_type in _NEW_COLUMNS:
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}")
                print(f"✓ 添加列: {col_name} ({col_type})")
                added += 1
            else:
                print(f"  列已存在: {col_name}")
        
        # target_tiers 存储在 extra_tags JSON 中，无需新增列
        print("✓ target_tiers 存储在 extra_tags JSON 中，无需迁移")
        
        conn.commit()
        conn.close()
        
        print(f"\n迁移完成！新增 {added} 列")
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
