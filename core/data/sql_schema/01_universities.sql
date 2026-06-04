CREATE TABLE IF NOT EXISTS universities (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  tier VARCHAR(30) NOT NULL,
  city VARCHAR(60) NOT NULL,
  tags TEXT[] DEFAULT '{}',
  graduate_recommendation_rate NUMERIC(5,2) DEFAULT 0
);
