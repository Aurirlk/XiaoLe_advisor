from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from core.data_importer.pipeline import import_file, rollback_batch
from scripts.init_sqlite import init_sqlite


def _temp_db() -> tuple[Path, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    init_sqlite(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    return db_path, conn


def test_import_scores_and_rollback():
    db_path, conn = _temp_db()
    csv_path = Path(__file__).resolve().parents[1] / "data" / "templates" / "admission_scores.csv"

    dry = import_file(csv_path, conn, dry_run=True)
    assert dry.ok

    report = import_file(csv_path, conn, dry_run=False, default_source="template")
    assert report.ok
    assert report.batch_id is not None

    count = conn.execute("SELECT COUNT(*) FROM admission_scores WHERE import_batch_id = ?", (report.batch_id,)).fetchone()[0]
    assert count >= 1

    deleted = rollback_batch(conn, report.batch_id)
    conn.commit()
    assert deleted >= 1

    remaining = conn.execute(
        "SELECT COUNT(*) FROM admission_scores WHERE import_batch_id = ?",
        (report.batch_id,),
    ).fetchone()[0]
    assert remaining == 0

    conn.close()
    db_path.unlink(missing_ok=True)


def test_import_zhejiang_sample():
    db_path, conn = _temp_db()
    sample = db_path.parent / "zhejiang_sample.csv"
    sample.write_text(
        "university_name,province,subject_type,year,major_name,min_score,lowest_rank,data_source\n"
        "浙江大学,浙江省,物理类,2024,计算机科学与技术,685,3500,zhejiang_2024\n",
        encoding="utf-8",
    )
    report = import_file(sample, conn, dry_run=False)
    assert report.ok
    row = conn.execute(
        "SELECT s.province FROM admission_scores s "
        "JOIN universities u ON u.id = s.university_id "
        "WHERE u.name = '浙江大学' AND s.province = '浙江省'"
    ).fetchone()
    assert row[0] == "浙江省"
    conn.close()
    sample.unlink(missing_ok=True)
    db_path.unlink(missing_ok=True)
