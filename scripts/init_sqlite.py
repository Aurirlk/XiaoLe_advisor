from __future__ import annotations

from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "zx_advisor.db"


UNIVERSITIES_SQL = """
CREATE TABLE IF NOT EXISTS universities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL,
    city TEXT NOT NULL,
    tags TEXT DEFAULT '',
    graduate_recommendation_rate REAL DEFAULT 0
);
"""

ADMISSION_SCORES_SQL = """
CREATE TABLE IF NOT EXISTS admission_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university_id INTEGER NOT NULL REFERENCES universities(id),
    province TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    major_name TEXT NOT NULL,
    min_score INTEGER NOT NULL,
    lowest_rank INTEGER NOT NULL,
    UNIQUE (university_id, province, subject_type, year, major_name)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_scores_lookup
    ON admission_scores (province, subject_type, year, major_name);
"""

USER_PROFILES_SQL = """
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

CRM_INDEX_PHONE = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_phone ON user_profiles (phone_number);
"""

CRM_INDEX_LAST_SEEN = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_last_seen ON user_profiles (last_seen_at DESC);
"""

WEB_SEARCH_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS web_search_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    session_id TEXT DEFAULT '',
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

WEB_SEARCH_PAGES_SQL = """
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

WEB_SEARCH_INDEX_QUERY = """
CREATE INDEX IF NOT EXISTS idx_web_sessions_query_hash ON web_search_sessions (query_hash);
"""

WEB_SEARCH_INDEX_CREATED = """
CREATE INDEX IF NOT EXISTS idx_web_sessions_created_at ON web_search_sessions (created_at DESC);
"""

WEB_SEARCH_INDEX_URL = """
CREATE INDEX IF NOT EXISTS idx_web_pages_url_hash ON web_search_pages (url_hash);
"""

WEB_SEARCH_INDEX_FETCHED = """
CREATE INDEX IF NOT EXISTS idx_web_pages_fetched_at ON web_search_pages (fetched_at DESC);
"""

MAJORS_SQL = """
CREATE TABLE IF NOT EXISTS majors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_code TEXT UNIQUE,
    major_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    is_pitfall INTEGER NOT NULL DEFAULT 0,
    civil_service_friendly INTEGER NOT NULL DEFAULT 0,
    base_salary_tier INTEGER NOT NULL DEFAULT 3,
    description TEXT DEFAULT ''
);
"""

SEED_UNIVERSITIES = [
    ("清华大学", "顶尖985", "北京", "211,985,双一流", 65.0),
    ("北京大学", "顶尖985", "北京", "211,985,双一流", 60.0),
    ("浙江大学", "顶尖985", "杭州", "211,985,双一流", 45.0),
    ("上海交通大学", "顶尖985", "上海", "211,985,双一流", 40.0),
    ("复旦大学", "顶尖985", "上海", "211,985,双一流", 42.0),
    ("南京大学", "顶尖985", "南京", "211,985,双一流", 38.0),
    ("华中科技大学", "985", "武汉", "211,985,双一流", 35.0),
    ("武汉大学", "985", "武汉", "211,985,双一流", 33.0),
    ("中山大学", "985", "广州", "211,985,双一流", 30.0),
    ("华南理工大学", "985", "广州", "211,985,双一流", 28.0),
    ("深圳大学", "双非一本", "深圳", "双非", 5.0),
    ("广东工业大学", "双非一本", "广州", "双非", 3.0),
    ("广州大学", "双非一本", "广州", "双非", 2.0),
    ("暨南大学", "211", "广州", "211,双一流", 15.0),
    ("华南师范大学", "211", "广州", "211,双一流", 12.0),
]

SEED_SCORES = [
    (1, "广东省", "物理类", 2025, "计算机科学与技术", 695, 85),
    (2, "广东省", "物理类", 2025, "计算机科学与技术", 692, 110),
    (3, "广东省", "物理类", 2025, "计算机科学与技术", 680, 520),
    (4, "广东省", "物理类", 2025, "计算机科学与技术", 678, 600),
    (5, "广东省", "物理类", 2025, "计算机科学与技术", 675, 780),
    (1, "广东省", "物理类", 2025, "软件工程", 693, 95),
    (2, "广东省", "物理类", 2025, "软件工程", 690, 130),
    (6, "广东省", "物理类", 2025, "计算机科学与技术", 670, 1200),
    (7, "广东省", "物理类", 2025, "计算机科学与技术", 648, 4500),
    (8, "广东省", "物理类", 2025, "计算机科学与技术", 635, 8500),
    (9, "广东省", "物理类", 2025, "计算机科学与技术", 630, 10500),
    (10, "广东省", "物理类", 2025, "计算机科学与技术", 620, 14500),
    (11, "广东省", "物理类", 2025, "计算机科学与技术", 585, 32000),
    (12, "广东省", "物理类", 2025, "计算机科学与技术", 560, 48000),
    (13, "广东省", "物理类", 2025, "计算机科学与技术", 545, 62000),
    (14, "广东省", "物理类", 2025, "计算机科学与技术", 600, 22000),
    (15, "广东省", "物理类", 2025, "计算机科学与技术", 595, 24500),
    (1, "广东省", "物理类", 2025, "临床医学", 698, 60),
    (2, "广东省", "物理类", 2025, "临床医学", 694, 80),
    (8, "广东省", "物理类", 2025, "临床医学", 640, 7200),
    (9, "广东省", "物理类", 2025, "临床医学", 625, 12000),
    (1, "广东省", "物理类", 2025, "法学", 690, 150),
    (2, "广东省", "物理类", 2025, "法学", 686, 200),
    (9, "广东省", "物理类", 2025, "法学", 622, 13500),
]


def init_sqlite(db_path: str | Path | None = None) -> str:
    target = Path(db_path or DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute(UNIVERSITIES_SQL)
    conn.execute(ADMISSION_SCORES_SQL)
    conn.execute(INDEX_SQL)
    conn.execute(USER_PROFILES_SQL)
    conn.execute(CRM_INDEX_PHONE)
    conn.execute(CRM_INDEX_LAST_SEEN)
    conn.execute(WEB_SEARCH_SESSIONS_SQL)
    conn.execute(WEB_SEARCH_PAGES_SQL)
    conn.execute(WEB_SEARCH_INDEX_QUERY)
    conn.execute(WEB_SEARCH_INDEX_CREATED)
    conn.execute(WEB_SEARCH_INDEX_URL)
    conn.execute(WEB_SEARCH_INDEX_FETCHED)
    conn.execute(MAJORS_SQL)

    cur = conn.execute("SELECT COUNT(*) FROM universities")
    if cur.fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO universities (name, tier, city, tags, graduate_recommendation_rate) "
            "VALUES (?, ?, ?, ?, ?)",
            SEED_UNIVERSITIES,
        )

    cur = conn.execute("SELECT COUNT(*) FROM admission_scores")
    if cur.fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO admission_scores (university_id, province, subject_type, year, "
            "major_name, min_score, lowest_rank) VALUES (?, ?, ?, ?, ?, ?, ?)",
            SEED_SCORES,
        )

    conn.commit()
    conn.close()
    return str(target)


if __name__ == "__main__":
    path = init_sqlite()
    print(f"SQLite database initialized: {path}")
