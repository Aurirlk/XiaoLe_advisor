-- 数据导入批次追溯
CREATE TABLE IF NOT EXISTS data_import_batches (
  id SERIAL PRIMARY KEY,
  source_file VARCHAR(255) NOT NULL,
  source_type VARCHAR(20) NOT NULL DEFAULT 'csv',
  record_count INTEGER NOT NULL DEFAULT 0,
  checksum VARCHAR(64) DEFAULT '',
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  status VARCHAR(20) NOT NULL DEFAULT 'completed',
  error_log TEXT DEFAULT ''
);

-- admission_scores 来源字段（PostgreSQL 新库由 02_scores 含列；旧库需手动迁移）
ALTER TABLE admission_scores ADD COLUMN IF NOT EXISTS data_source VARCHAR(120) DEFAULT 'seed';
ALTER TABLE admission_scores ADD COLUMN IF NOT EXISTS import_batch_id INTEGER REFERENCES data_import_batches(id);

CREATE INDEX IF NOT EXISTS idx_scores_batch ON admission_scores (import_batch_id);
CREATE INDEX IF NOT EXISTS idx_batches_imported_at ON data_import_batches (imported_at DESC);
