-- Token 成本追踪表
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
