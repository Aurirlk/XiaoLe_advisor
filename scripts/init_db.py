from pathlib import Path
import os

import psycopg2
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with open(ROOT / "configs" / "db_config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["postgres"]
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["database"],
        user=cfg["user"],
        password=os.getenv(cfg["password_env"], ""),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        for file in [
            "01_universities.sql",
            "02_scores.sql",
            "03_majors.sql",
            "04_user_profiles.sql",
            "05_web_search_records.sql",
        ]:
            sql = (ROOT / "data" / "sql_schema" / file).read_text(encoding="utf-8")
            cur.execute(sql)
    conn.close()
    print("Database initialized.")


if __name__ == "__main__":
    main()
