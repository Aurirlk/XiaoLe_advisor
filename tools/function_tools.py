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


class NewsQueryInput(BaseModel):
    topic: str = Field(..., description="查询主题，例如：计算机就业、人工智能行业、医学前景")
    region: str = Field("", description="地区筛选，例如：广东、全国。留空=不限")
    category: str = Field("", description="新闻类别：教育/科技/经济/社会。留空=不限")
    max_results: int = Field(5, ge=1, le=10, description="返回结果条数")


class PolicyQueryInput(BaseModel):
    topic: str = Field(..., description="政策主题，例如：强基计划、平行志愿、新高考改革、加分政策")
    province: str = Field("", description="省份筛选，例如：广东省。留空=全国政策")
    year: int = Field(0, description="年份筛选，0=最新")
    max_results: int = Field(5, ge=1, le=10, description="返回结果条数")


class MajorAdmissionInput(BaseModel):
    major_name: str = Field(..., description="专业全称，例如 计算机科学与技术")
    province: str = Field(..., description="省份全称，例如 广东省")
    year: int = Field(2025, description="查询年份")
    subject_type: str = Field("物理类", description="选科类别：物理类 或 历史类")


class AdmissionChanceInput(BaseModel):
    score: int = Field(..., description="高考分数")
    province: str = Field(..., description="省份全称，例如 广东省")
    subject_type: str = Field("物理类", description="选科类别：物理类 或 历史类")
    college_name: str = Field("", description="目标院校名称，留空则预测所有院校")
    major_name: str = Field("", description="目标专业名称，留空则预测所有专业")


class ProvinceCutoffInput(BaseModel):
    province: str = Field(..., description="省份全称，例如 广东省")
    year: int = Field(2025, description="查询年份")
    subject_type: str = Field("物理类", description="选科类别：物理类 或 历史类")


class CollegeInfoInput(BaseModel):
    college_name: str = Field(..., description="院校名称，例如 清华大学")


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
async def search_experience_tool(query: str = "", top_k: int = 3) -> str:
    """从本地向量数据库搜索张雪峰经验库。

    搜索与报考、就业、专业前景相关的经验知识。
    当用户询问就业前景、考研建议、专业选择策略等问题时使用。
    支持多策略降级: ChromaDB 语义检索 + 本地关键词回退。
    """
    import asyncio
    from api.dependencies import get_vector_store

    # L1: ChromaDB 语义检索（to_thread 避免阻塞事件循环）
    store = get_vector_store()
    results = await asyncio.to_thread(store.query, query, top_k)

    if results:
        lines = []
        for item in results:
            lines.append(f"[来源：{item.get('source', '未知')}] {item.get('text', '')}")
        return "\n".join(lines)

    # L2: 本地 RAGTools 关键词检索作为降级
    try:
        from tools.rag_tools import RAGTools
        rag = RAGTools()
        text = await asyncio.to_thread(rag.query_zx_experience, query, top_k)
        if text and text.strip():
            return "[降级模式 - 本地关键词检索]\n" + text
    except Exception:
        pass

    return "未找到相关经验数据。建议换个关键词重试，或直接询问具体院校/专业。"


@tool(args_schema=NewsQueryInput)
async def query_news_tool(
    topic: str = "",
    region: str = "",
    category: str = "",
    max_results: int = 5,
) -> str:
    """查询实时专业领域相关新闻。

    当用户询问某专业/行业的最新动态、就业新闻、行业趋势、市场变化时使用。
    支持按地区和类别筛选。
    """
    import asyncio
    from tools.web_search_tools import WebSearchTools

    query_parts = [topic]
    if region:
        query_parts.append(region)
    if category:
        query_parts.append(category)
    query_parts.append("最新新闻")
    query = " ".join(query_parts)

    ws = WebSearchTools(timeout_seconds=8)
    try:
        results = await ws.search(query, top_k=max_results)
    except Exception:
        results = []

    if not results:
        return f"未找到关于「{topic}」的最新新闻。建议稍后重试或换个关键词。"

    lines = [f"📰 关于「{topic}」的最新新闻："]
    for i, item in enumerate(results, 1):
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        lines.append(f"{i}. {title}")
        if url:
            lines.append(f"   链接：{url}")
    return "\n".join(lines)


@tool(args_schema=PolicyQueryInput)
async def query_policy_tool(
    topic: str = "",
    province: str = "",
    year: int = 0,
    max_results: int = 5,
) -> str:
    """查询高考/招生相关政策。

    当用户询问录取政策、加分政策、志愿填报规则、招生计划变化、强基计划、
    平行志愿、新高考改革等政策类问题时使用。
    """
    import asyncio
    from tools.web_search_tools import WebSearchTools

    query_parts = []
    if province:
        query_parts.append(province)
    query_parts.append(topic)
    query_parts.append("政策")
    if year > 0:
        query_parts.append(str(year))
    else:
        query_parts.append("最新")
    query = " ".join(query_parts)

    ws = WebSearchTools(timeout_seconds=8)
    try:
        results = await ws.search(query, top_k=max_results)
    except Exception:
        results = []

    if not results:
        return f"未找到关于「{topic}」的相关政策。建议稍后重试或访问教育部官网查询。"

    scope = f"{province}省" if province else "全国"
    year_str = f"{year}年" if year > 0 else "最新"
    lines = [f"📋 {scope}{year_str}「{topic}」相关政策："]
    for i, item in enumerate(results, 1):
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        lines.append(f"{i}. {title}")
        if url:
            lines.append(f"   链接：{url}")
    return "\n".join(lines)


@tool(args_schema=MajorAdmissionInput)
async def query_major_admission_tool(
    major_name: str = "",
    province: str = "",
    year: int = 2025,
    subject_type: str = "物理类",
) -> str:
    """查询专业录取分数线（咕咕数据API）。

    当用户询问某专业在特定省份的录取分数线时使用此工具。
    返回该专业在各院校的录取分数和位次信息。
    """
    from core.providers.gugu_api_client import gugu_client

    try:
        result = await gugu_client.query_major_line(major_name, province, year, subject_type)
        if not result or "data" not in result:
            return f"未找到{major_name}专业在{province}{year}年的录取数据。"

        data = result["data"]
        lines = [f"📊 {major_name}专业 {province} {year}年录取分数线："]
        for item in data[:10]:
            college = item.get("collegeName", "未知院校")
            min_score = item.get("minScore", "未知")
            min_rank = item.get("minRank", "未知")
            lines.append(f"- {college}: 最低分 {min_score}, 最低位次 {min_rank}")
        return "\n".join(lines)
    except Exception as e:
        return f"查询专业录取分数线失败: {str(e)}"


@tool(args_schema=AdmissionChanceInput)
async def query_admission_chance_tool(
    score: int = 0,
    province: str = "",
    subject_type: str = "物理类",
    college_name: str = "",
    major_name: str = "",
) -> str:
    """预测录取概率（咕咕数据API）。

    根据考生分数、省份和选科，预测被目标院校/专业录取的概率。
    返回冲/稳/保三个梯度的院校推荐。
    """
    from core.providers.gugu_api_client import gugu_client

    try:
        result = await gugu_client.predict_admission(
            score, province, subject_type, college_name or None, major_name or None
        )
        if not result or "data" not in result:
            return "录取概率预测失败，请稍后重试。"

        data = result["data"]
        lines = [f"🎯 {score}分 {province} {subject_type} 录取概率预测："]

        if "reach" in data and data["reach"]:
            lines.append("\n📈 冲一冲（概率<40%）：")
            for item in data["reach"][:5]:
                name = item.get("collegeName", "未知")
                prob = item.get("probability", "未知")
                lines.append(f"- {name}: {prob}%")

        if "match" in data and data["match"]:
            lines.append("\n📊 稳一稳（概率40%-70%）：")
            for item in data["match"][:5]:
                name = item.get("collegeName", "未知")
                prob = item.get("probability", "未知")
                lines.append(f"- {name}: {prob}%")

        if "safety" in data and data["safety"]:
            lines.append("\n🛡️ 保一保（概率>70%）：")
            for item in data["safety"][:5]:
                name = item.get("collegeName", "未知")
                prob = item.get("probability", "未知")
                lines.append(f"- {name}: {prob}%")

        return "\n".join(lines)
    except Exception as e:
        return f"录取概率预测失败: {str(e)}"


@tool(args_schema=ProvinceCutoffInput)
async def query_province_cutoff_tool(
    province: str = "",
    year: int = 2025,
    subject_type: str = "物理类",
) -> str:
    """查询各省批次线（咕咕数据API）。

    当用户询问某省份的本科一批/二批/专科分数线时使用此工具。
    """
    from core.providers.gugu_api_client import gugu_client

    try:
        result = await gugu_client.query_province_cutoff(province, year, subject_type)
        if not result or "data" not in result:
            return f"未找到{province}{year}年的批次线数据。"

        data = result["data"]
        lines = [f"📋 {province} {year}年 {subject_type} 批次线："]
        for item in data:
            batch = item.get("batchName", "未知批次")
            score = item.get("score", "未知")
            lines.append(f"- {batch}: {score}分")
        return "\n".join(lines)
    except Exception as e:
        return f"查询批次线失败: {str(e)}"


@tool(args_schema=CollegeInfoInput)
async def query_college_info_tool(college_name: str = "") -> str:
    """查询院校基础信息（咕咕数据API）。

    当用户询问某院校是否是985/211/双一流、院校层次、所在城市等信息时使用。
    """
    from core.providers.gugu_api_client import gugu_client

    try:
        result = await gugu_client.query_college_info(college_name)
        if not result or "data" not in result:
            return f"未找到{college_name}的信息。"

        data = result["data"]
        lines = [f"🏫 {college_name} 基础信息："]
        lines.append(f"- 层次: {data.get('level', '未知')}")
        lines.append(f"- 城市: {data.get('city', '未知')}")
        lines.append(f"- 类型: {data.get('type', '未知')}")
        if data.get("is985"):
            lines.append("- 985工程: ✓")
        if data.get("is211"):
            lines.append("- 211工程: ✓")
        if data.get("isDoubleFirstClass"):
            lines.append("- 双一流: ✓")
        return "\n".join(lines)
    except Exception as e:
        return f"查询院校信息失败: {str(e)}"


FUNCTION_TOOLS = [
    query_admission_scores_tool,
    search_experience_tool,
    query_news_tool,
    query_policy_tool,
    query_major_admission_tool,
    query_admission_chance_tool,
    query_province_cutoff_tool,
    query_college_info_tool,
]
