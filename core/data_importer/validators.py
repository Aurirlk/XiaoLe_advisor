from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.tool_retry import normalize_province, normalize_subject

VALID_SUBJECTS = {"物理类", "历史类"}
SCORE_MIN, SCORE_MAX = 100, 750
RANK_MIN, RANK_MAX = 1, 2_000_000


@dataclass
class ValidationError:
    row: int
    field: str
    message: str


@dataclass
class ValidationReport:
    ok: bool
    errors: List[ValidationError] = field(default_factory=list)
    row_count: int = 0


def validate_university_row(row: Dict[str, Any], row_num: int) -> List[ValidationError]:
    errors: List[ValidationError] = []
    if not str(row.get("name", "")).strip():
        errors.append(ValidationError(row_num, "name", "院校名称不能为空"))
    if not str(row.get("tier", "")).strip():
        errors.append(ValidationError(row_num, "tier", "院校层次不能为空"))
    if not str(row.get("city", "")).strip():
        errors.append(ValidationError(row_num, "city", "城市不能为空"))
    return errors


def validate_score_row(row: Dict[str, Any], row_num: int) -> List[ValidationError]:
    errors: List[ValidationError] = []
    if not str(row.get("university_name", "")).strip():
        errors.append(ValidationError(row_num, "university_name", "院校名称不能为空"))
    province = normalize_province(str(row.get("province", "")))
    if not province:
        errors.append(ValidationError(row_num, "province", "省份不能为空"))
    subject = normalize_subject(str(row.get("subject_type", "")))
    if subject not in VALID_SUBJECTS:
        errors.append(ValidationError(row_num, "subject_type", f"选科无效: {row.get('subject_type')}"))
    try:
        year = int(row.get("year", 0))
        if year < 2015 or year > 2035:
            errors.append(ValidationError(row_num, "year", f"年份超出范围: {year}"))
    except (TypeError, ValueError):
        errors.append(ValidationError(row_num, "year", "年份必须为整数"))
    if not str(row.get("major_name", "")).strip():
        errors.append(ValidationError(row_num, "major_name", "专业名称不能为空"))
    try:
        score = int(row.get("min_score", -1))
        if not SCORE_MIN <= score <= SCORE_MAX:
            errors.append(ValidationError(row_num, "min_score", f"分数超出范围: {score}"))
    except (TypeError, ValueError):
        errors.append(ValidationError(row_num, "min_score", "分数必须为整数"))
    try:
        rank = int(row.get("lowest_rank", -1))
        if not RANK_MIN <= rank <= RANK_MAX:
            errors.append(ValidationError(row_num, "lowest_rank", f"位次超出范围: {rank}"))
    except (TypeError, ValueError):
        errors.append(ValidationError(row_num, "lowest_rank", "位次必须为整数"))
    if not str(row.get("data_source", "")).strip():
        errors.append(ValidationError(row_num, "data_source", "data_source 来源标识不能为空"))
    return errors


def validate_major_row(row: Dict[str, Any], row_num: int) -> List[ValidationError]:
    errors: List[ValidationError] = []
    if not str(row.get("major_name", "")).strip():
        errors.append(ValidationError(row_num, "major_name", "专业名称不能为空"))
    if not str(row.get("category", "")).strip():
        errors.append(ValidationError(row_num, "category", "学科门类不能为空"))
    return errors


def validate_rows(
    rows: List[Dict[str, Any]],
    kind: str,
) -> ValidationReport:
    errors: List[ValidationError] = []
    for i, row in enumerate(rows, start=2):
        if kind == "universities":
            errors.extend(validate_university_row(row, i))
        elif kind == "admission_scores":
            errors.extend(validate_score_row(row, i))
        elif kind == "majors":
            errors.extend(validate_major_row(row, i))
    return ValidationReport(ok=len(errors) == 0, errors=errors, row_count=len(rows))
