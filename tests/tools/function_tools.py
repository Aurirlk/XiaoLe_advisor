from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from tools.sql_tools import QueryScoreArgs, SQLTools


class QueryScoresInput(BaseModel):
    province: str = Field(..., description="省份全称，例如 河北省、广东省")
    subject_type: str = Field(..., description="选科类别：物理类 或 历史类")
    major_name: str = Field(..., description="专业全称，例如 计算机科学与技术")
    year: int = Field(..., description="查询年份，如 2025")
    max_rows: int = Field(10, ge=1, le=30, description="最多返回行数")


class SearchExperienceInput(BaseModel):
    query: str = Field(..., description="搜索关键词，例如 计算机就业前景")
    top_k: int = Field(3, ge=1, le=10, description="返回结果条数")


@tool(args_schema=QueryScoresInput)
async def query_admission_scores_tool(
    province: str = "",
    subject_type: str = "",
    major_name: str = "",
    year: int = 2025,
    max_rows: int = 10,
) -> str:
    """查询本地 SQLite 数据库中的院校录取分数线。

    当用户询问具体学校/专业的分数线、位次、录取门槛时使用此工具。
    必须提供省份、选科类别、专业名称和年份。
    支持省名简称（如"广东"→"广东省"）和专业名模糊匹配。
    返回包含院校名称、层次、最低分、最低位次的结构化结果。
    """
    from api.dependencies import get_sqlite_engine

    engine: AsyncEngine = get_sqlite_engine()
    sql_tools = SQLTools(engine)

    args = QueryScoreArgs(
        province=province,
        subject_type=subject_type,
        major_name=major_name,
        year=year,
        max_rows=max_rows,
    )
    result = await sql_tools.query_scores(args)

    lines: List[str] = []

    if result.diagnostics:
        lines.append(f"[诊断] {'; '.join(result.diagnostics)}")

    if result.tier == "error":
        lines.append(f"查询失败: {result.diagnostics[0] if result.diagnostics else '未知错误'}")
        return "\n".join(lines)

    if result.tier == "empty":
        lines.append("未在数据库中找到匹配的录取数据。")
        if result.suggestions:
            for s in result.suggestions:
                lines.append(s)
        return "\n".join(lines)

    if result.is_degraded:
        lines.append(f"[注意] 当前结果为降级查询，非精确匹配。")

    for r in result.data:
        if isinstance(r, dict) and "university_name" in r:
            lines.append(
                f"- {r['university_name']}({r.get('tier', '?')}) | "
                f"{r.get('subject_type', '')} | {r.get('major_name', '')} | "
                f"最低分:{r.get('min_score', '?')} | 最低位次:{r.get('lowest_rank', '?')}"
                f"{' | 年份:' + str(r.get('year', '')) if result.is_degraded else ''}"
            )
        elif isinstance(r, dict) and "_note" in r:
            pass
        else:
            lines.append(f"- {r}")

    return "\n".join(lines)


@tool(args_schema=SearchExperienceInput)
def search_experience_tool(query: str = "", top_k: int = 3) -> str:
    """从本地向量数据库搜索张雪峰经验库。

    搜索与报考、就业、专业前景相关的经验知识。
    当用户询问就业前景、考研建议、专业选择策略等问题时使用。
    支持多策略降级: ChromaDB 语义检索 + 本地关键词回退。
    """
    from api.dependencies import get_vector_store

    # L1: ChromaDB 语义检索
    store = get_vector_store()
    results = store.query(query, top_k=top_k)

    if results:
        lines = []
        for item in results:
            lines.append(f"[来源：{item.get('source', '未知')}] {item.get('text', '')}")
        return "\n".join(lines)

    # L2: 本地 RAGTools 关键词检索作为降级
    try:
        from tools.rag_tools import RAGTools
        rag = RAGTools()
        text = rag.query_zx_experience(query, top_k=top_k)
        if text and text.strip():
            return "[降级模式 - 本地关键词检索]\n" + text
    except Exception:
        pass

    return "未找到相关经验数据。建议换个关键词重试，或直接询问具体院校/专业。"


FUNCTION_TOOLS = [query_admission_scores_tool, search_experience_tool]
