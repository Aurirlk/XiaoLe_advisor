from __future__ import annotations

from core.data_importer.validators import validate_rows


def test_validate_score_row_ok():
    rows = [{
        "university_name": "深圳大学",
        "province": "广东",
        "subject_type": "物理",
        "year": 2024,
        "major_name": "计算机科学与技术",
        "min_score": 600,
        "lowest_rank": 10000,
        "data_source": "test",
    }]
    report = validate_rows(rows, "admission_scores")
    assert report.ok
    assert report.row_count == 1


def test_validate_score_row_missing_source():
    rows = [{
        "university_name": "深圳大学",
        "province": "广东省",
        "subject_type": "物理类",
        "year": 2024,
        "major_name": "计算机科学与技术",
        "min_score": 600,
        "lowest_rank": 10000,
        "data_source": "",
    }]
    report = validate_rows(rows, "admission_scores")
    assert not report.ok
    assert any(e.field == "data_source" for e in report.errors)


def test_validate_university_row():
    rows = [{"name": "", "tier": "985", "city": "北京"}]
    report = validate_rows(rows, "universities")
    assert not report.ok
