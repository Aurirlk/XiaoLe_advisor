"""创建 admin CRUD 模块所需的数据表"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "zx_advisor.db"

SQL_STATEMENTS = [
    # 公告表
    """CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target_role TEXT DEFAULT 'all',
        is_pinned INTEGER DEFAULT 0,
        status TEXT DEFAULT 'draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # FAQ 表
    """CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        category TEXT DEFAULT '通用',
        sort_order INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # 报考指南表
    """CREATE TABLE IF NOT EXISTS guides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT '志愿填报',
        status TEXT DEFAULT 'draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # 快捷提问词表
    """CREATE TABLE IF NOT EXISTS quick_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        group_name TEXT DEFAULT '默认',
        sort_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # 用户反馈表
    """CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        conversation_id TEXT,
        rating INTEGER DEFAULT 0,
        comment TEXT,
        status TEXT DEFAULT 'pending',
        admin_reply TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    # 通知表
    """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        type TEXT DEFAULT 'system',
        is_read INTEGER DEFAULT 0,
        related_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
]


def run():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    for sql in SQL_STATEMENTS:
        cursor.execute(sql)
    conn.commit()
    conn.close()
    print(f"✓ 6 张表创建/确认成功 ({DB_PATH})")


if __name__ == "__main__":
    run()
