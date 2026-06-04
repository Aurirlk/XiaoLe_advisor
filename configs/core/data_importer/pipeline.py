from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from core.data_importer.validators import validate_rows
from core.tool_retry import normalize_province, normalize_subject

ImportKind = Literal["universities", "admission_scores", "majors", "unknown"]


@dataclass
class ImportReport:
    ok: bool
    kind: ImportKind
    source_file: str
    batch_id: Optional[int] = None
    records_imported: int = 0
    records_updated: int = 0
    dry_run: bool = False
    errors: List[str] = field(default_factory=list)
    message: str = ""


def detect_kind(path: Path, rows: List[Dict[str, Any]]) -> ImportKind:
    if not rows:
        return "unknown"
    keys = set(rows[0].keys())
    if "university_name" in keys and "min_score" in keys:
        return "admission_scores"
    if "name" in keys and "tier" in keys:
        return "universities"
    if "major_name" in keys and "category" in keys:
        return "majors"
    name = path.name.lower()
    if "score" in name or "admission" in name:
        return "admission_scores"
    if "universit" in name:
        return "universities"
    if "major" in name:
        return "majors"
    return "unknown"


def load_rows(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "rows" in data:
            return data["rows"]
        raise ValueError("JSON 须为数组或含 rows 字段的对象")
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError(f"不支持的文件类型: {suffix}")


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_university_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM universities WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row[0])
    conn.execute(
        "INSERT INTO universities (name, tier, city, tags, graduate_recommendation_rate) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, "待补充", "待补充", "", 0.0),
    )
    return int(conn.execute("SELECT id FROM universities WHERE name = ?", (name,)).fetchone()[0])


def import_universities(
    conn: sqlite3.Connection,
    rows: List[Dict[str, Any]],
    batch_id: Optional[int],
) -> tuple[int, int]:
    imported = updated = 0
    for row in rows:
        tags = str(row.get("tags", ""))
        rate = float(row.get("graduate_recommendation_rate", 0) or 0)
        cur = conn.execute(
            """
            INSERT INTO universities (name, tier, city, tags, graduate_recommendation_rate)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                tier = excluded.tier,
                city = excluded.city,
                tags = excluded.tags,
                graduate_recommendation_rate = excluded.graduate_recommendation_rate
            """,
            (
                str(row["name"]).strip(),
                str(row.get("tier", "待补充")).strip(),
                str(row.get("city", "待补充")).strip(),
                tags,
                rate,
            ),
        )
        if cur.rowcount:
            imported += 1
        else:
            updated += 1
    return imported, updated


def import_scores(
    conn: sqlite3.Connection,
    rows: List[Dict[str, Any]],
    batch_id: Optional[int],
    default_source: str = "",
) -> tuple[int, int]:
    imported = updated = 0
    for row in rows:
        uni_name = str(row["university_name"]).strip()
        uid = ensure_university_id(conn, uni_name)
        province = normalize_province(str(row["province"]))
        subject = normalize_subject(str(row["subject_type"]))
        data_source = str(row.get("data_source") or default_source or "import").strip()
        cur = conn.execute(
            """
            INSERT INTO admission_scores (
                university_id, province, subject_type, year, major_name,
                min_score, lowest_rank, data_source, import_batch_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(university_id, province, subject_type, year, major_name) DO UPDATE SET
                min_score = excluded.min_score,
                lowest_rank = excluded.lowest_rank,
                data_source = excluded.data_source,
                import_batch_id = excluded.import_batch_id
            """,
            (
                uid,
                province,
                subject,
                int(row["year"]),
                str(row["major_name"]).strip(),
                int(row["min_score"]),
                int(row["lowest_rank"]),
                data_source,
                batch_id,
            ),
        )
        if cur.rowcount:
            imported += 1
        else:
            updated += 1
    return imported, updated


def import_majors(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> tuple[int, int]:
    imported = updated = 0
    for row in rows:
        cur = conn.execute(
            """
            INSERT INTO majors (
                major_code, major_name, category, is_pitfall,
                civil_service_friendly, base_salary_tier, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(major_name) DO UPDATE SET
                major_code = excluded.major_code,
                category = excluded.category,
                is_pitfall = excluded.is_pitfall,
                civil_service_friendly = excluded.civil_service_friendly,
                base_salary_tier = excluded.base_salary_tier,
                description = excluded.description
            """,
            (
                str(row.get("major_code", "")).strip() or None,
                str(row["major_name"]).strip(),
                str(row["category"]).strip(),
                int(row.get("is_pitfall", 0) or 0),
                int(row.get("civil_service_friendly", 0) or 0),
                int(row.get("base_salary_tier", 3) or 3),
                str(row.get("description", "")).strip(),
            ),
        )
        if cur.rowcount:
            imported += 1
        else:
            updated += 1
    return imported, updated


def create_batch(
    conn: sqlite3.Connection,
    source_file: str,
    source_type: str,
    checksum: str,
    record_count: int,
    status: str = "completed",
    error_log: str = "",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO data_import_batches (
            source_file, source_type, record_count, checksum, status, error_log
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_file, source_type, record_count, checksum, status, error_log),
    )
    return int(cur.lastrowid)


def rollback_batch(conn: sqlite3.Connection, batch_id: int) -> int:
    cur = conn.execute(
        "DELETE FROM admission_scores WHERE import_batch_id = ?",
        (batch_id,),
    )
    deleted = cur.rowcount
    conn.execute(
        "UPDATE data_import_batches SET status = 'rolled_back' WHERE id = ?",
        (batch_id,),
    )
    return deleted


def import_file(
    path: Path,
    conn: sqlite3.Connection,
    *,
    dry_run: bool = False,
    default_source: str = "",
) -> ImportReport:
    path = Path(path)
    try:
        rows = load_rows(path)
    except Exception as exc:
        return ImportReport(
            ok=False,
            kind="unknown",
            source_file=str(path),
            dry_run=dry_run,
            errors=[str(exc)],
            message="文件读取失败",
        )

    kind = detect_kind(path, rows)
    if kind == "unknown":
        return ImportReport(
            ok=False,
            kind=kind,
            source_file=str(path),
            dry_run=dry_run,
            errors=["无法识别文件类型，请使用标准模板列名"],
        )

    report = validate_rows(rows, kind)
    if not report.ok:
        return ImportReport(
            ok=False,
            kind=kind,
            source_file=str(path),
            dry_run=dry_run,
            errors=[f"行{e.row} {e.field}: {e.message}" for e in report.errors],
            message="校验失败",
        )

    if dry_run:
        return ImportReport(
            ok=True,
            kind=kind,
            source_file=str(path),
            dry_run=True,
            records_imported=len(rows),
            message=f"dry-run 通过，共 {len(rows)} 行",
        )

    checksum = file_checksum(path)
    batch_id = create_batch(
        conn,
        source_file=path.name,
        source_type=path.suffix.lstrip(".").lower(),
        checksum=checksum,
        record_count=len(rows),
    )

    if kind == "universities":
        imported, updated = import_universities(conn, rows, batch_id)
    elif kind == "admission_scores":
        imported, updated = import_scores(conn, rows, batch_id, default_source)
    else:
        imported, updated = import_majors(conn, rows)

    conn.commit()
    return ImportReport(
        ok=True,
        kind=kind,
        source_file=str(path),
        batch_id=batch_id,
        records_imported=imported,
        records_updated=updated,
        message=f"导入完成 batch_id={batch_id}",
    )


def get_data_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    provinces = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT province FROM admission_scores ORDER BY province"
        ).fetchall()
    ]
    years = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT year FROM admission_scores ORDER BY year DESC"
        ).fetchall()
    ]
    score_count = conn.execute("SELECT COUNT(*) FROM admission_scores").fetchone()[0]
    uni_count = conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    major_count = conn.execute("SELECT COUNT(*) FROM majors").fetchone()[0]
    by_province = conn.execute(
        """
        SELECT province, COUNT(*) AS cnt
        FROM admission_scores
        GROUP BY province
        ORDER BY cnt DESC
        """
    ).fetchall()
    batches = conn.execute(
        """
        SELECT id, source_file, source_type, record_count, status, imported_at
        FROM data_import_batches
        ORDER BY imported_at DESC
        LIMIT 50
        """
    ).fetchall()
    return {
        "university_count": uni_count,
        "score_count": score_count,
        "major_count": major_count,
        "provinces": provinces,
        "years": years,
        "by_province": [{"province": r[0], "count": r[1]} for r in by_province],
        "recent_batches": [
            {
                "id": r[0],
                "source_file": r[1],
                "source_type": r[2],
                "record_count": r[3],
                "status": r[4],
                "imported_at": r[5],
            }
            for r in batches
        ],
    }
