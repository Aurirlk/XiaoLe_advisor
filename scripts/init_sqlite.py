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
    username TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    role TEXT DEFAULT 'student',
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

CRM_INDEX_USERNAME = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_username ON user_profiles (username);
"""

CRM_INDEX_ROLE = """
CREATE INDEX IF NOT EXISTS idx_crm_profiles_role ON user_profiles (role);
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

DATA_IMPORT_BATCHES_SQL = """
CREATE TABLE IF NOT EXISTS data_import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'csv',
    record_count INTEGER NOT NULL DEFAULT 0,
    checksum TEXT DEFAULT '',
    imported_at TEXT DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'completed',
    error_log TEXT DEFAULT ''
);
"""

CONVERSATION_TURNS_SQL = """
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

FEEDBACK_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL UNIQUE REFERENCES conversation_turns(turn_id),
    session_id TEXT NOT NULL,
    rating INTEGER NOT NULL,
    tags TEXT DEFAULT '[]',
    comment TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

FEEDBACK_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_turns_created ON conversation_turns (created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_records (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback_records (rating);",
    "CREATE INDEX IF NOT EXISTS idx_scores_batch ON admission_scores (import_batch_id);",
    "CREATE INDEX IF NOT EXISTS idx_batches_imported_at ON data_import_batches (imported_at DESC);",
]

RAG_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
    source, text, tokenize='unicode61'
);
"""

COST_TRACKING_SQL = """
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
"""

COST_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON token_usage (timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_usage_model ON token_usage (model_name);",
]

FAMILY_PROFILES_SQL = """
CREATE TABLE IF NOT EXISTS parent_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_phone TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    name TEXT DEFAULT '',
    occupation TEXT DEFAULT '',
    industry TEXT DEFAULT '',
    education TEXT DEFAULT '',
    expectation TEXT DEFAULT '',
    concerns TEXT DEFAULT '[]',
    decision_weight TEXT DEFAULT 'consultative',
    phone TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', '+8 hours')),
    updated_at TEXT DEFAULT (datetime('now', '+8 hours'))
);
"""

FAMILY_CONTEXTS_SQL = """
CREATE TABLE IF NOT EXISTS family_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_phone TEXT NOT NULL UNIQUE,
    income_level TEXT DEFAULT '',
    annual_budget INTEGER DEFAULT 0,
    total_budget INTEGER DEFAULT 0,
    is_only_child INTEGER DEFAULT -1,
    sibling_count INTEGER DEFAULT 0,
    family_resources TEXT DEFAULT '[]',
    decision_maker TEXT DEFAULT '',
    location_preference TEXT DEFAULT '',
    financial_urgency TEXT DEFAULT '',
    parent_consensus TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now', '+8 hours')),
    updated_at TEXT DEFAULT (datetime('now', '+8 hours'))
);
"""

FAMILY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_parent_student ON parent_profiles (student_phone);",
    "CREATE INDEX IF NOT EXISTS idx_family_student ON family_contexts (student_phone);",
]


def _migrate_admission_scores_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(admission_scores)").fetchall()}
    if "data_source" not in cols:
        conn.execute("ALTER TABLE admission_scores ADD COLUMN data_source TEXT DEFAULT 'seed'")
    if "import_batch_id" not in cols:
        conn.execute("ALTER TABLE admission_scores ADD COLUMN import_batch_id INTEGER")


def _migrate_user_profiles_columns(conn: sqlite3.Connection) -> None:
    """为 user_profiles 表添加新画像字段和认证字段"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(user_profiles)").fetchall()}
    new_cols = {
        "username": "TEXT DEFAULT ''",
        "password_hash": "TEXT DEFAULT ''",
        "role": "TEXT DEFAULT 'student'",
        "gender": "TEXT DEFAULT ''",
        "gaokao_city": "TEXT DEFAULT ''",
        "strong_subjects": "TEXT DEFAULT '[]'",
        "weak_subjects": "TEXT DEFAULT '[]'",
        "major_preferences": "TEXT DEFAULT '[]'",
        "interests": "TEXT DEFAULT '[]'",
        "personality": "TEXT DEFAULT ''",
        "target_universities": "TEXT DEFAULT '[]'",
        "risk_tolerance": "TEXT DEFAULT ''",
        "special_notes": "TEXT DEFAULT ''",
        "subject_scores_json": "TEXT DEFAULT '{}'",
    }
    for col_name, col_type in new_cols.items():
        if col_name not in cols:
            conn.execute(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}")

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
    # 注意：CRM_INDEX_USERNAME和CRM_INDEX_ROLE需要在迁移后执行
    # 因为旧表可能没有username和role字段
    conn.execute(WEB_SEARCH_SESSIONS_SQL)
    conn.execute(WEB_SEARCH_PAGES_SQL)
    conn.execute(WEB_SEARCH_INDEX_QUERY)
    conn.execute(WEB_SEARCH_INDEX_CREATED)
    conn.execute(WEB_SEARCH_INDEX_URL)
    conn.execute(WEB_SEARCH_INDEX_FETCHED)
    conn.execute(MAJORS_SQL)
    conn.execute(DATA_IMPORT_BATCHES_SQL)
    conn.execute(CONVERSATION_TURNS_SQL)
    conn.execute(FEEDBACK_RECORDS_SQL)
    _migrate_admission_scores_columns(conn)
    for stmt in FEEDBACK_INDEXES:
        conn.execute(stmt)

    conn.execute(RAG_FTS_SQL)
    conn.execute(COST_TRACKING_SQL)
    for stmt in COST_INDEXES:
        conn.execute(stmt)

    conn.execute(FAMILY_PROFILES_SQL)
    conn.execute(FAMILY_CONTEXTS_SQL)
    for stmt in FAMILY_INDEXES:
        conn.execute(stmt)

    _migrate_user_profiles_columns(conn)
    
    # 在迁移后创建索引（确保字段存在）
    conn.execute(CRM_INDEX_USERNAME)
    conn.execute(CRM_INDEX_ROLE)
    conn.execute(CRM_INDEX_LAST_SEEN)

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
