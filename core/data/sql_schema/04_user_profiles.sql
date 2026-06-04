CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    province VARCHAR(40) DEFAULT '',
    subject_type VARCHAR(30) DEFAULT '',
    major_name VARCHAR(120) DEFAULT '',
    score INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 0,
    budget INTEGER DEFAULT 0,
    target_city VARCHAR(60) DEFAULT '',
    postgraduate_plan VARCHAR(10) DEFAULT '',
    extra_tags TEXT[] DEFAULT '{}',
    session_count INTEGER NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_query TEXT DEFAULT '',
    last_intent VARCHAR(40) DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_phone ON user_profiles (phone_number);
CREATE INDEX IF NOT EXISTS idx_user_profiles_last_seen ON user_profiles (last_seen_at DESC);
