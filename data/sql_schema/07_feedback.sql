-- 对话轮次与满意度反馈
CREATE TABLE IF NOT EXISTS conversation_turns (
  turn_id VARCHAR(64) PRIMARY KEY,
  session_id VARCHAR(120) NOT NULL,
  user_query TEXT NOT NULL,
  assistant_response TEXT DEFAULT '',
  route_path TEXT DEFAULT '[]',
  user_profile_snapshot TEXT DEFAULT '{}',
  sql_hit_count INTEGER NOT NULL DEFAULT 0,
  risk_level VARCHAR(30) DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback_records (
  id SERIAL PRIMARY KEY,
  turn_id VARCHAR(64) NOT NULL UNIQUE REFERENCES conversation_turns(turn_id),
  session_id VARCHAR(120) NOT NULL,
  rating INTEGER NOT NULL,
  tags TEXT DEFAULT '[]',
  comment TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON conversation_turns (session_id);
CREATE INDEX IF NOT EXISTS idx_turns_created ON conversation_turns (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_records (session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback_records (rating);
