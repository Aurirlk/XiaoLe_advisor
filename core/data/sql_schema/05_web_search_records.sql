-- Web search sessions and cached page content
CREATE TABLE IF NOT EXISTS web_search_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    session_id TEXT DEFAULT '',
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

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

CREATE INDEX IF NOT EXISTS idx_web_sessions_query_hash ON web_search_sessions (query_hash);
CREATE INDEX IF NOT EXISTS idx_web_sessions_created_at ON web_search_sessions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_pages_url_hash ON web_search_pages (url_hash);
CREATE INDEX IF NOT EXISTS idx_web_pages_fetched_at ON web_search_pages (fetched_at DESC);
