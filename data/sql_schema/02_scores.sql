CREATE TABLE IF NOT EXISTS admission_scores (
  id SERIAL PRIMARY KEY,
  university_id INTEGER NOT NULL REFERENCES universities(id),
  province VARCHAR(40) NOT NULL,
  subject_type VARCHAR(30) NOT NULL,
  year INTEGER NOT NULL,
  major_name VARCHAR(120) NOT NULL,
  min_score INTEGER NOT NULL,
  lowest_rank INTEGER NOT NULL,
  UNIQUE (university_id, province, subject_type, year, major_name)
);

CREATE INDEX IF NOT EXISTS idx_scores_lookup
  ON admission_scores (province, subject_type, year, major_name);
