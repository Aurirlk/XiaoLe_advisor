from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from tools.sql_tools import QueryScoreArgs, SQLTools

# ── 工具函数复用 ──

def _neo4j_query(query_type: str, **params) -> List[Dict]:
    """复用 Neo4j 查询的公共封装"""
    from core.kg_client import kg_client
    return kg_client.query(query_type, **params)

async def _neo4j_async(query_type: str, **params) -> List[Dict]:
    import asyncio
    return await asyncio.to_thread(_neo4j_query, query_type, **params)

def _format_list(items: list, title: str, fmt: str, limit: int = 20) -> str:
    """统一格式化列表输出"""
    lines = [title]
    for item in items[:limit]:
        lines.append(fmt.format(**item) if isinstance(item, dict) else f"  - {item}")
    if len(items) > limit:
        lines.append(f"  ... 还有 {len(items) - limit} 项")
    return "\n".join(lines)

async def _web_search(topic: str, prefix: str = "", suffix: str = "最新", top_k: int = 5) -> list:
    """复用联网搜索的公共封装

    P2-11：不再裸吞异常返回 [] —— 服务故障与"无结果"必须可区分，
    由调用方决定文案，避免 LLM 误判为真实无结果。
    """
    from tools.web_search_tools import WebSearchTools
    query = f"{prefix} {topic} {suffix}".strip()
    ws = WebSearchTools(timeout_seconds=8)
    return await ws.search(query, top_k=top_k)


# ── 输入模型 ──

class QueryScoresInput(BaseModel):
    province: str = Field(..., description="省份全称，例如 广东省")
    subject_type: str = Field(..., description="选科类别：物理类 或 历史类")
    major_name: str = Field(..., description="专业全称，例如 计算机科学与技术")
    year: int = Field(..., description="查询年份，如 2025")
    max_rows: int = Field(10, ge=1, le=30, description="最多返回行数")

class SearchExperienceInput(BaseModel):
    query: str = Field(..., description="搜索关键词")
    top_k: int = Field(3, ge=1, le=10, description="返回结果条数")

class WebSearchInput(BaseModel):
    topic: str = Field(..., description="搜索主题")
    scope: str = Field("", description="搜索范围：news(新闻) / policy(政策) / general(通用)")
    region: str = Field("", description="地区筛选，留空=不限")
    max_results: int = Field(5, ge=1, le=10, description="返回结果条数")

class MajorInfoInput(BaseModel):
    major_name: str = Field(..., description="专业全称")

class UniversityInfoInput(BaseModel):
    university_name: str = Field(..., description="院校名称")

class LocationInput(BaseModel):
    location: str = Field(..., description="省份或城市名称")
    location_type: str = Field("province", description="province 或 city")

class CategoryInput(BaseModel):
    category: str = Field(..., description="门类名称，例如 工学、理学")

class CityInfoInput(BaseModel):
    city_name: str = Field(..., description="城市名称")

class GuidanceInput(BaseModel):
    topic: str = Field(..., description="主题：admission/employment/policy/ranking")
    keyword: str = Field("", description="关键词，如院校名或专业名")


# ── 工具函数 ──

@tool(args_schema=QueryScoresInput)
async def query_admission_scores_tool(
    province: str = "",
    subject_type: str = "",
    major_name: str = "",
    year: int = 2025,
    max_rows: int = 10,
) -> str:
    """查询本地 SQLite 数据库中的院校录取分数线。

    当用户询问具体学校/专业的分数线、位次、录取门槛时使用。
    返回包含院校名称、层次、最低分、最低位次的结构化结果。
    """
    from api.dependencies import get_sqlite_engine

    engine: AsyncEngine = get_sqlite_engine()
    sql_tools = SQLTools(engine)

    args = QueryScoreArgs(
        province=province, subject_type=subject_type,
        major_name=major_name, year=year, max_rows=max_rows,
    )
    result = await sql_tools.query_scores(args)

    if result.tier == "error":
        return f"查询失败: {result.diagnostics[0] if result.diagnostics else '未知错误'}"
    if result.tier == "empty":
        suggestions = "\n".join(result.suggestions) if result.suggestions else ""
        return f"未在数据库中找到匹配的录取数据。\n{suggestions}"

    lines = []
    if result.diagnostics:
        lines.append(f"[诊断] {'; '.join(result.diagnostics)}")
    if result.is_degraded:
        lines.append("[注意] 当前结果为降级查询，非精确匹配。")

    for r in result.data:
        if isinstance(r, dict) and "university_name" in r:
            lines.append(
                f"- {r['university_name']}({r.get('tier', '?')}) | "
                f"最低分:{r.get('min_score', '?')} | 最低位次:{r.get('lowest_rank', '?')}"
                f"{' | 年份:' + str(r.get('year', '')) if result.is_degraded else ''}"
            )
        elif not isinstance(r, dict) or "_note" not in r:
            lines.append(f"- {r}")

    return "\n".join(lines)


@tool(args_schema=SearchExperienceInput)
async def search_experience_tool(query: str = "", top_k: int = 3) -> str:
    """从本地向量数据库搜索张雪峰经验库。

    搜索与报考、就业、专业前景相关的经验知识。
    支持多策略降级: ChromaDB 语义检索 + 本地关键词回退。
    """
    import asyncio
    from api.dependencies import get_vector_store

    store = get_vector_store()
    results = await asyncio.to_thread(store.query, query, top_k)
    if results:
        return "\n".join(
            f"[来源：{item.get('source', '未知')}] {item.get('text', '')}"
            for item in results
        )

    try:
        from tools.rag_tools import RAGTools
        text = await asyncio.to_thread(RAGTools().query_zx_experience, query, top_k)
        if text and text.strip():
            return f"[降级模式 - 本地关键词检索]\n{text}"
    except Exception:
        pass

    return "未找到相关经验数据。建议换个关键词重试，或直接询问具体院校/专业。"


@tool(args_schema=WebSearchInput)
async def query_web_search_tool(
    topic: str = "",
    scope: str = "general",
    region: str = "",
    max_results: int = 5,
) -> str:
    """联网搜索工具（合并新闻和政策查询）。

    scope='news' → 查询行业动态/就业新闻/市场趋势
    scope='policy' → 查询高考/招生/加分政策
    scope='general' → 通用搜索
    """
    import asyncio

    try:
        if scope == "news":
            results = await _web_search(topic, prefix=region, suffix="最新新闻", top_k=max_results)
            header = "新闻"
        elif scope == "policy":
            results = await _web_search(topic, prefix=region, suffix="政策 最新", top_k=max_results)
            header = "政策"
        else:
            results = await _web_search(topic, prefix=region, suffix="", top_k=max_results)
            header = "搜索结果"
    except Exception as e:
        # P2-11：搜索服务故障与"无结果"可区分
        return f"[搜索服务暂时不可用] {type(e).__name__}: {e}"

    if not results:
        return f"未找到关于「{topic}」的相关{header}。建议稍后重试或换个关键词。"

    lines = [f"[{header}] {topic}："]
    for i, item in enumerate(results, 1):
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        lines.append(f"{i}. {title}\n   {url}" if url else f"{i}. {title}")
    return "\n".join(lines)


@tool(args_schema=MajorInfoInput)
async def query_major_info_tool(major_name: str = "") -> str:
    """查询专业详细信息（知识图谱）。

    当用户询问某专业的介绍、所属门类、相关技术时使用。
    """
    result = await _neo4j_async("major_info", major_name=major_name)
    if not result or "error" in result[0]:
        return f"未找到专业「{major_name}」的信息。"

    data = result[0]
    major = data.get("major", {})
    category = data.get("category", {})

    lines = [f"[专业] {major_name}"]
    if major.get("code"):
        lines.append(f"  代码: {major['code']}")
    if category:
        lines.append(f"  门类: {category.get('name', '未知')}")

    techs = data.get("related_technologies", [])
    if techs:
        lines.append(f"  相关技术: {', '.join(t.get('name', '') for t in techs[:5])}")
    return "\n".join(lines)


@tool(args_schema=UniversityInfoInput)
async def query_university_info_tool(university_name: str = "") -> str:
    """查询院校详细信息（知识图谱）。"""
    result = await _neo4j_async("university_info", university_name=university_name)
    if not result or "error" in result[0]:
        return f"未找到院校「{university_name}」的信息。"

    uni = result[0].get("university", {})
    lines = [f"[院校] {university_name}"]
    for field, label in [("level", "层次"), ("admin", "主管部门"), ("province", "省份"), ("tags", "特性")]:
        if uni.get(field):
            lines.append(f"  {label}: {uni[field]}")
    if uni.get("satisfaction") and uni["satisfaction"] > 0:
        lines.append(f"  满意度: {uni['satisfaction']}")
    return "\n".join(lines)


@tool(args_schema=LocationInput)
async def query_universities_by_location_tool(
    location: str = "",
    location_type: str = "province",
) -> str:
    """按地区查询院校列表（知识图谱）。"""
    query_type = "universities_by_city" if location_type == "city" else "universities_by_province"
    result = await _neo4j_async(query_type, **{f"{'city' if location_type == 'city' else 'province'}_name": location})
    if not result or "error" in result[0]:
        return f"未找到{location}的院校信息。"

    return _format_list(
        result,
        f"[院校列表] {location}（共{len(result)}所）：",
        "  - {name}（{level}） [{tags}]",
    )


@tool(args_schema=CategoryInput)
async def query_majors_by_category_tool(category: str = "") -> str:
    """按门类查询专业列表（知识图谱）。"""
    result = await _neo4j_async("majors_by_category", category=category)
    if not result or "error" in result[0]:
        return f"未找到门类「{category}」的专业信息。"

    return _format_list(
        result,
        f"[专业列表] {category}（共{len(result)}个）：",
        "  - {name}（{code}）",
        limit=30,
    )


@tool(args_schema=CityInfoInput)
async def query_city_info_tool(city_name: str = "") -> str:
    """查询城市详细信息（知识图谱）。

    返回城市的等级、薪资水平、人才政策、院校列表。
    """
    result = await _neo4j_async("city_info", city_name=city_name)
    if not result or "error" in result[0]:
        return f"未找到城市「{city_name}」的信息。"

    data = result[0]
    city = data.get("city", {})
    lines = [f"[城市] {city_name} — {city.get('tier', '')} | {city.get('province', '')}"]

    salaries = data.get("salary_data", [])
    if salaries:
        lines.append("\n薪资（前5行业）：")
        for s in salaries[:5]:
            lines.append(f"  {s.get('industry', '')}: {s.get('avg', 0)}元/月")

    policies = data.get("policies", [])
    if policies:
        lines.append("\n人才政策：")
        for p in policies[:3]:
            amount = f" 补贴{p['amount']}元" if p.get("amount", 0) > 0 else ""
            lines.append(f"  {p.get('name', '')}{amount}")

    return "\n".join(lines)


@tool(args_schema=GuidanceInput)
async def data_guidance_tool(topic: str = "admission", keyword: str = "") -> str:
    """当系统数据不足时使用。不编造答案，引导用户去官方渠道查询。

    topic可选：admission（录取数据）/ employment（就业数据）/ policy（政策）/ ranking（排名）
    具体URL由系统内置的可靠信息源提供。
    """
    from core.anti_hallucination import DataSufficiencyCheck

    check = DataSufficiencyCheck()
    result = check.evaluate(
        tool_name="data_guidance_tool",
        tool_output="未在数据库中找到匹配数据",
    )

    sources = result["sources"]
    lines = ["[数据引导] 以下信息可能不是最新版本，建议通过官方渠道核实："]
    for i, s in enumerate(sources, 1):
        lines.append(f"  {i}. {s['name']} — {s['url']} — {s['desc']}")
    if keyword:
        lines.append(f"\n建议搜索关键词：{keyword}")
    return "\n".join(lines)


# ── 工具注册表 ──

FUNCTION_TOOLS = [
    query_admission_scores_tool,
    search_experience_tool,
    query_web_search_tool,
    query_major_info_tool,
    query_university_info_tool,
    query_universities_by_location_tool,
    query_majors_by_category_tool,
    query_city_info_tool,
    data_guidance_tool,
]
