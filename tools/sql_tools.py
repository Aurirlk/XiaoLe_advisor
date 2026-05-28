"""
SQL 查询工具 — 含多级降级/模糊搜索/省名标准化/专业别名/诊断建议
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.tool_retry import (
    ToolResult, normalize_province, normalize_subject,
)


class QueryScoreArgs(BaseModel):
    province: str = Field(..., description="省份全称，例如 河北省。")
    subject_type: str = Field(..., description="选科类别：物理类 或 历史类。")
    major_name: str = Field(..., description="专业全称，例如 计算机科学与技术。")
    year: int = Field(..., description="查询年份，建议使用近3年。")
    max_rows: int = Field(10, ge=1, le=30, description="最多返回记录条数。")


_EXACT_SQL = text("""
    SELECT u.name AS university_name, u.tier, s.province, s.subject_type, s.year,
           s.major_name, s.min_score, s.lowest_rank
    FROM admission_scores s
    JOIN universities u ON u.id = s.university_id
    WHERE s.province = :province
      AND s.subject_type = :subject_type
      AND s.major_name = :major_name
      AND s.year = :year
    ORDER BY s.min_score DESC
    LIMIT :max_rows
""")

_FUZZY_MAJOR_SQL = text("""
    SELECT u.name AS university_name, u.tier, s.province, s.subject_type, s.year,
           s.major_name, s.min_score, s.lowest_rank
    FROM admission_scores s
    JOIN universities u ON u.id = s.university_id
    WHERE s.province = :province
      AND s.subject_type = :subject_type
      AND s.major_name LIKE :major_pattern
      AND s.year = :year
    ORDER BY s.min_score DESC
    LIMIT :max_rows
""")

_WIDEN_YEAR_SQL = text("""
    SELECT u.name AS university_name, u.tier, s.province, s.subject_type, s.year,
           s.major_name, s.min_score, s.lowest_rank
    FROM admission_scores s
    JOIN universities u ON u.id = s.university_id
    WHERE s.province = :province
      AND s.subject_type = :subject_type
      AND s.major_name = :major_name
    ORDER BY s.year DESC, s.min_score DESC
    LIMIT :max_rows
""")

_PROBE_SQL = text("""
    SELECT DISTINCT s.province, s.subject_type, s.year, s.major_name
    FROM admission_scores s
    WHERE s.province LIKE :probe_province
       OR s.major_name LIKE :probe_major
    LIMIT 10
""")


class SQLTools:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def _execute(self, stmt, params: dict) -> List[Dict[str, Any]]:
        async with self.engine.begin() as conn:
            rows = (await conn.execute(stmt, params)).mappings().all()
        return [dict(r) for r in rows]

    async def query_scores(self, args: QueryScoreArgs) -> ToolResult:
        """
        多级降级查询:
        L1: 精确匹配（省名标准化后）
        L2: 专业名 LIKE 模糊匹配
        L3: 放宽年份限制
        L4: 探测数据库中有哪些省份/专业，生成建议
        """
        diags: List[str] = []
        suggestions: List[str] = []
        norm_province = normalize_province(args.province)
        norm_subject = normalize_subject(args.subject_type)

        if norm_province != args.province:
            diags.append(f"省名标准化: \"{args.province}\" → \"{norm_province}\"")
        if norm_subject != args.subject_type:
            diags.append(f"选科标准化: \"{args.subject_type}\" → \"{norm_subject}\"")

        base_params = {
            "province": norm_province,
            "subject_type": norm_subject,
            "major_name": args.major_name,
            "year": args.year,
            "max_rows": args.max_rows,
        }

        # ---- L1: 精确匹配 ----
        try:
            rows = await self._execute(_EXACT_SQL, base_params)
        except Exception as exc:
            return ToolResult.error(f"数据库查询异常: {exc}")

        if rows:
            result = ToolResult.exact(rows)
            if diags:
                result.diagnostics = diags
            return result

        # ---- L2: 专业名 LIKE 模糊匹配 ----
        fuzzy_params = {
            "province": norm_province,
            "subject_type": norm_subject,
            "major_pattern": f"%{args.major_name}%",
            "year": args.year,
            "max_rows": args.max_rows,
        }
        try:
            rows = await self._execute(_FUZZY_MAJOR_SQL, fuzzy_params)
        except Exception:
            rows = []

        if rows:
            diags.append(f"精确匹配无结果，已使用专业名模糊匹配 (LIKE '%{args.major_name}%')")
            matched_majors = {r["major_name"] for r in rows}
            if len(matched_majors) > 1:
                diags.append(f"模糊匹配到 {len(matched_majors)} 个专业: {', '.join(sorted(matched_majors))}")
            result = ToolResult.fuzzy(rows, diag=diags[0] if diags else "")
            result.diagnostics = diags
            return result

        # ---- L3: 放宽年份 ----
        widen_params = {
            "province": norm_province,
            "subject_type": norm_subject,
            "major_name": args.major_name,
            "max_rows": args.max_rows,
        }
        try:
            rows = await self._execute(_WIDEN_YEAR_SQL, widen_params)
        except Exception:
            rows = []

        if rows:
            diags.append(f"{args.year} 年无数据，已放宽年份限制展示所有年份结果")
            suggestions.append(f"提示: {args.year} 年暂无收录，上表为历史年份数据")
            result = ToolResult.degraded(rows, diag=diags[-1], suggestions=suggestions)
            result.diagnostics = diags
            return result

        # ---- L4: 探测 + 生成建议 ----
        probe_params = {
            "probe_province": f"%{norm_province.replace('省', '')}%",
            "probe_major": f"%{args.major_name[:4]}%",
        }
        try:
            probe_rows = await self._execute(_PROBE_SQL, probe_params)
        except Exception:
            probe_rows = []

        if probe_rows:
            available = set()
            for r in probe_rows:
                available.add(f"{r['province']}|{r['subject_type']}|{r['major_name']}")
            diags.append(f"数据库中未找到 {norm_province}/{norm_subject}/{args.major_name}/{args.year} 的精确数据")
            suggestions.append("当前数据库可查的组合示例:")
            for item in sorted(available)[:5]:
                suggestions.append(f"  → {item}")
            if len(available) > 5:
                suggestions.append(f"  ...共 {len(available)} 种组合")
        else:
            diags.append(f"数据库查询无结果: {norm_province} / {norm_subject} / {args.major_name} / {args.year}")
            suggestions.append("请检查省份/选科/专业名称是否正确")
            suggestions.append("可用省份简称或全称，例如: '广东' 或 '广东省'")
            suggestions.append(f"当前种子数据仅覆盖广东省物理类，可联系管理员扩充")

        result = ToolResult.empty(diag=diags[-1], suggestions=suggestions)
        result.diagnostics = diags
        return result
