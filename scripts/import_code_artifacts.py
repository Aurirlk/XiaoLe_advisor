from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "zx_advisor.db"
EXPERIENCE_PATH = ROOT / "data" / "vector_store" / "zx_experience.json"
ARTIFACT_JSON = ROOT / "data" / "seeds" / "experience_artifact.json"

MAJOR_ROWS = [
    ("080901", "计算机科学与技术", "工学", 0, 1, 5,
     "万金油专业，就业面广，互联网/国企/考公均可，起薪高但内卷严重，存在35岁中年危机。"),
    ("080902", "软件工程", "工学", 0, 0, 5,
     "与计算机高度重合，更偏向工程实践和代码落地，学费通常较贵，是拿高薪的最短路径。"),
    ("030101k", "法学", "法学", 0, 1, 3,
     "考公之王，但也是红牌专业。如果不考公、不过法考、进不了红圈所，底层法务薪资极低，典型方差极大的专业。"),
    ("070301", "化学", "理学", 1, 0, 2,
     "四大天坑之一。本科学历极难找高薪对口工作，进厂或做实验员有毒有害危险性高，必须读研读博。"),
    ("083001", "生物工程", "工学", 1, 0, 2,
     "四大天坑之一。投资周期长，国内产业环境不成熟，普通本科毕业大概率转行或做低薪销售。"),
    ("100201k", "临床医学", "医学", 0, 0, 4,
     "先苦后甜的精英专业。必须5+3起步，普通家庭慎报，规培期间收入极低，但35岁以后是越老越吃香的铁饭碗。"),
    ("050301", "新闻学", "文学", 0, 1, 2,
     "传统媒体式微，自媒体不需要新闻学本科学历。考公有一定岗位，但竞争极其惨烈，性价比很低。"),
    ("020101", "经济学", "经济学", 0, 1, 3,
     "看似高大上，实则极看重第一学历（清北复交）和家庭人脉。普通二本学经济学大概率去做柜员或卖保险。"),
]

SCORE_ROWS_2024 = [
    ("深圳大学", "广东省", 2024, "物理类", "计算机科学与技术", 628, 12000, "guangdong_2024"),
    ("深圳大学", "广东省", 2024, "物理类", "软件工程", 618, 16000, "guangdong_2024"),
    ("深圳大学", "广东省", 2024, "物理类", "人工智能", 613, 19000, "guangdong_2024"),
    ("深圳大学", "广东省", 2024, "物理类", "电子信息工程", 610, 21000, "guangdong_2024"),
    ("深圳大学", "广东省", 2024, "物理类", "土木工程", 591, 35000, "guangdong_2024"),
    ("华南师范大学", "广东省", 2024, "物理类", "物理学(师范)", 591, 35000, "guangdong_2024"),
    ("华南师范大学", "广东省", 2024, "物理类", "数学与应用数学(师范)", 587, 38000, "guangdong_2024"),
    ("华南师范大学", "广东省", 2024, "物理类", "计算机科学与技术", 580, 45000, "guangdong_2024"),
    ("华南师范大学", "广东省", 2024, "物理类", "光电信息科学与工程", 574, 52000, "guangdong_2024"),
    ("广东工业大学", "广东省", 2024, "物理类", "计算机科学与技术", 575, 51000, "guangdong_2024"),
    ("广东工业大学", "广东省", 2024, "物理类", "自动化", 568, 58000, "guangdong_2024"),
    ("广东工业大学", "广东省", 2024, "物理类", "机械设计制造及其自动化", 560, 65000, "guangdong_2024"),
]


def _ensure_db() -> sqlite3.Connection:
    from scripts.init_sqlite import init_sqlite

    init_sqlite(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def import_majors_legacy(conn: sqlite3.Connection) -> int:
    from core.data_importer.pipeline import import_majors

    rows = [
        {
            "major_code": r[0],
            "major_name": r[1],
            "category": r[2],
            "is_pitfall": r[3],
            "civil_service_friendly": r[4],
            "base_salary_tier": r[5],
            "description": r[6],
        }
        for r in MAJOR_ROWS
    ]
    imported, _ = import_majors(conn, rows)
    conn.commit()
    return imported


def import_scores_2024(conn: sqlite3.Connection) -> int:
    from core.data_importer.pipeline import import_scores

    rows = [
        {
            "university_name": r[0],
            "province": r[1],
            "year": r[2],
            "subject_type": r[3],
            "major_name": r[4],
            "min_score": r[5],
            "lowest_rank": r[6],
            "data_source": r[7],
        }
        for r in SCORE_ROWS_2024
    ]
    from core.data_importer.pipeline import create_batch, file_checksum

    batch_id = create_batch(
        conn,
        source_file="import_code_artifacts.py",
        source_type="builtin",
        checksum="legacy",
        record_count=len(rows),
    )
    imported, _ = import_scores(conn, rows, batch_id, "guangdong_2024")
    conn.commit()
    return imported


def import_experience_json(path: Path | None = None) -> int:
    src = path or ARTIFACT_JSON
    if not src.exists():
        return 0
    raw = json.loads(src.read_text(encoding="utf-8"))
    existing: list[dict] = []
    if EXPERIENCE_PATH.exists():
        existing = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
    known_sources = {d.get("source", "") for d in existing}
    added = 0
    for item in raw:
        doc_id = item.get("id", "")
        category = item.get("category", "")
        text = item.get("text", "").strip()
        if not text:
            continue
        source = f"code_artifact/{doc_id}" if doc_id else f"code_artifact/{category}"
        if source in known_sources:
            continue
        existing.append({"source": source, "text": text})
        known_sources.add(source)
        added += 1
    EXPERIENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPERIENCE_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return added


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Import code_artifact data")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--sql-only", action="store_true")
    parser.add_argument("--json-path", type=Path, default=ARTIFACT_JSON)
    args = parser.parse_args()

    if not args.json_only:
        conn = _ensure_db()
        majors_n = import_majors_legacy(conn)
        scores_n = import_scores_2024(conn)
        conn.close()
        print(f"SQLite majors upserted: {majors_n} rows touched")
        print(f"SQLite 2024 scores upserted: {scores_n} rows touched")
        print(f"Database: {DB_PATH}")

    if not args.sql_only:
        added = import_experience_json(args.json_path)
        print(f"RAG index appended: {added} documents -> {EXPERIENCE_PATH}")


if __name__ == "__main__":
    main()
