-- 家长画像表
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
CREATE INDEX IF NOT EXISTS idx_parent_student ON parent_profiles (student_phone);

-- 家庭背景表
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
CREATE INDEX IF NOT EXISTS idx_family_student ON family_contexts (student_phone);
