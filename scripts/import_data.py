"""
批量导入院校/分数线/专业数据。

用法:
  python -m scripts.import_data data/templates/admission_scores.csv --dry-run
  python -m scripts.import_data data/batches/2025_zhejiang.csv --source zhejiang_2025
  python -m scripts.import_data --rollback-batch 12
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data_importer.pipeline import import_file, rollback_batch
from scripts.init_sqlite import init_sqlite

DB_PATH = ROOT / "data" / "zx_advisor.db"


def _connect() -> sqlite3.Connection:
    init_sqlite(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def main() -> None:
    parser = argparse.ArgumentParser(description="Import university data from CSV/JSON")
    parser.add_argument("path", nargs="?", type=Path, help="CSV/JSON 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅校验不写入")
    parser.add_argument("--source", default="", help="默认 data_source 标识")
    parser.add_argument("--rollback-batch", type=int, help="回滚指定批次")
    args = parser.parse_args()

    conn = _connect()
    try:
        if args.rollback_batch is not None:
            deleted = rollback_batch(conn, args.rollback_batch)
            conn.commit()
            print(f"Rolled back batch {args.rollback_batch}, deleted {deleted} score rows")
            return

        if not args.path:
            parser.error("请提供文件路径，或使用 --rollback-batch")

        report = import_file(
            args.path,
            conn,
            dry_run=args.dry_run,
            default_source=args.source,
        )
        if report.ok:
            print(report.message)
            print(
                f"kind={report.kind} imported={report.records_imported} "
                f"updated={report.records_updated} batch_id={report.batch_id}"
            )
        else:
            print("Import failed:", report.message)
            for err in report.errors:
                print(" -", err)
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
