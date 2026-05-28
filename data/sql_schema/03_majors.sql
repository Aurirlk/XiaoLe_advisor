CREATE TABLE IF NOT EXISTS majors (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(80) NOT NULL,
  civil_service_friendly BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS major_career_stats (
  id SERIAL PRIMARY KEY,
  major_id INTEGER NOT NULL REFERENCES majors(id),
  city VARCHAR(60) NOT NULL,
  avg_start_salary INTEGER NOT NULL,
  tuition_per_year INTEGER NOT NULL,
  years_to_graduate INTEGER NOT NULL DEFAULT 4,
  UNIQUE (major_id, city)
);
