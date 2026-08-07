"""
Neo4j 知识图谱查询工具（增强版 V2）
模板化Function Calling，禁止Text2Cypher

新增查询：
- 城市×行业薪资对比
- 专业→技术→行业链路
- 政策→专业关联
- 院校详情（含城市信息）
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool


def _get_driver():
    """获取Neo4j驱动"""
    try:
        from api.dependencies import get_neo4j_driver
        driver = get_neo4j_driver()
        if not driver:
            return None
        return driver
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 1. 分数查询（保留原有）
# ─────────────────────────────────────────────────────────

class GraphQueryInput(BaseModel):
    province: str = Field(..., description="考生所在省份，例如：广东省")
    subject_type: str = Field(..., description="选科类型：物理类/历史类")
    score: int = Field(..., description="高考分数")
    target_major: Optional[str] = Field(None, description="目标专业关键词，如：计算机")


@tool("query_neo4j_admission_tool", args_schema=GraphQueryInput)
def query_neo4j_admission_tool(
    province: str, subject_type: str, score: int, target_major: Optional[str] = None
) -> str:
    """查询符合分数的大学和专业推荐（基于Neo4j图谱）。
    当用户提供分数并询问能上什么大学/专业时使用。
    """
    if score < 200 or score > 750:
        return "【查询失败】分数输入异常，请提供真实的有效分数（200-750）。"
    if not province or len(province) < 2:
        return "【查询失败】省份信息不完整，请提供完整的省份名称。"

    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接，正在使用本地数据库查询。"

    cypher = """
    MATCH (u:University)-[o:OFFERS]->(m:Major)
    WHERE o.subject_type = $subject_type 
      AND o.min_score <= $max_score 
      AND o.min_score >= $min_score
    """
    params = {
        "subject_type": subject_type,
        "min_score": max(0, score - 10),
        "max_score": score + 30,
    }

    if target_major and len(target_major) >= 2:
        safe_major = ''.join(c for c in target_major if c.isalnum() or '\u4e00' <= c <= '\u9fff')
        if safe_major:
            cypher += " AND m.name CONTAINS $target_major "
            params["target_major"] = safe_major

    cypher += """
    RETURN u.name AS university, u.level AS level, 
           m.name AS major, o.min_score AS score, o.min_rank AS rank
    ORDER BY o.min_score DESC LIMIT 10
    """

    try:
        with driver.session() as session:
            records = [dict(r) for r in session.run(cypher, **params)]
            if not records:
                return f"【查询为空】图谱中未找到 {score}分 ({subject_type}) 的匹配数据。"
            res = f"📊 {score}分 ({province} {subject_type}) 匹配结果：\n\n"
            for i, r in enumerate(records, 1):
                emoji = "🏆" if "985" in (r.get("level") or "") else "🥇" if "211" in (r.get("level") or "") else "📚"
                res += f"{i}. {emoji} {r['university']} ({r.get('level', '未知')})\n   专业: {r['major']} | 最低分: {r['score']} | 位次: {r.get('rank', '未知')}\n\n"
            return res
    except Exception as e:
        return f"【图谱查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 2. 城市×行业薪资查询（新增）
# ─────────────────────────────────────────────────────────

class CitySalaryInput(BaseModel):
    city1: str = Field(..., description="第一个城市名称，例如：深圳")
    city2: str = Field(..., description="第二个城市名称，例如：武汉")
    industry: Optional[str] = Field(None, description="行业名称，例如：互联网/IT。留空则对比全部行业")


@tool("query_city_salary_tool", args_schema=CitySalaryInput)
def query_city_salary_tool(city1: str, city2: str, industry: Optional[str] = None) -> str:
    """对比两个城市的行业薪资水平。
    当用户问"深圳和武汉哪个城市IT薪资高"、"去哪个城市发展好"时使用。
    """
    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接。"

    cypher = """
    MATCH (c:City)-[:HAS_SALARY]->(s:CityIndustrySalary)-[:FOR_INDUSTRY]->(i:Industry)
    WHERE c.name IN [$city1, $city2]
    """
    params = {"city1": city1, "city2": city2}

    if industry:
        cypher += " AND i.name CONTAINS $industry "
        params["industry"] = industry

    cypher += """
    RETURN c.name AS city, i.name AS industry,
           s.avg_salary AS avg, s.median_salary AS median, s.p90_salary AS p90
    ORDER BY c.name, s.avg_salary DESC
    """

    try:
        with driver.session() as session:
            records = [dict(r) for r in session.run(cypher, **params)]
            if not records:
                return f"【查询为空】未找到 {city1} 和 {city2} 的薪资数据。"

            res = f"💰 {city1} vs {city2} 薪资对比：\n\n"
            city1_data = [r for r in records if r["city"] == city1]
            city2_data = [r for r in records if r["city"] == city2]

            for r in city1_data[:5]:
                res += f"【{city1}】{r['industry']}: 平均 {r['avg']}元 | 中位数 {r['median']}元 | 高分位 {r['p90']}元\n"
            for r in city2_data[:5]:
                res += f"【{city2}】{r['industry']}: 平均 {r['avg']}元 | 中位数 {r['median']}元 | 高分位 {r['p90']}元\n"

            # 自动对比
            if city1_data and city2_data:
                c1_avg = sum(r["avg"] for r in city1_data) / len(city1_data)
                c2_avg = sum(r["avg"] for r in city2_data) / len(city2_data)
                winner = city1 if c1_avg > c2_avg else city2
                diff = abs(c1_avg - c2_avg)
                res += f"\n📊 综合对比：{winner} 平均薪资高 {diff:.0f} 元/月"

            return res
    except Exception as e:
        return f"【查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 3. 专业→技术→行业查询（新增）
# ─────────────────────────────────────────────────────────

class MajorTechInput(BaseModel):
    major_name: str = Field(..., description="专业名称，例如：计算机科学与技术")


@tool("query_major_tech_tool", args_schema=MajorTechInput)
def query_major_tech_tool(major_name: str) -> str:
    """查询专业关联的前沿技术和行业方向。
    当用户问"XX专业和AI有什么关系"、"这个专业的前沿方向是什么"时使用。
    """
    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接。"

    cypher = """
    MATCH (m:Major {name: $major})-[:REQUIRES]->(t:Technology)
    OPTIONAL MATCH (t)-[:DRIVES]->(i:Industry)
    RETURN t.name AS tech, t.field AS field, t.maturity AS maturity,
           collect(DISTINCT i.name) AS industries
    """

    try:
        with driver.session() as session:
            records = [dict(r) for r in session.run(cypher, major=major_name)]
            if not records:
                return f"【查询为空】未找到 {major_name} 关联的前沿技术。"

            res = f"🔬 {major_name} 关联的前沿技术：\n\n"
            for r in records:
                maturity_emoji = {"成长": "🟢", "成熟": "🔵", "萌芽": "🟡"}.get(r["maturity"], "⚪")
                res += f"{maturity_emoji} {r['tech']}（{r['field']}，{r['maturity']}期）\n"
                if r["industries"]:
                    res += f"   → 驱动行业：{', '.join(r['industries'])}\n"
            return res
    except Exception as e:
        return f"【查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 4. 政策→专业关联查询（新增）
# ─────────────────────────────────────────────────────────

class PolicyInput(BaseModel):
    province: str = Field(..., description="省份名称，例如：广东省")
    year: Optional[int] = Field(None, description="年份，例如：2026。留空查询最新")


@tool("query_policy_tool", args_schema=PolicyInput)
def query_policy_tool(province: str, year: Optional[int] = None) -> str:
    """查询某省份的招生/就业相关政策。
    当用户问"XX省有什么政策"、"今年有什么新政策"时使用。
    """
    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接。"

    cypher = """
    MATCH (p:Policy)-[:HAS_POLICY]->(c:City)
    WHERE c.province = $province OR p.province = $province
    """
    params = {"province": province}

    if year:
        cypher += " AND p.year = $year "
        params["year"] = year

    cypher += """
    RETURN p.name AS name, p.type AS type, p.description AS desc,
           p.eligibility AS eligibility, p.amount AS amount, p.city AS city
    ORDER BY p.type, p.name
    """

    try:
        with driver.session() as session:
            records = [dict(r) for r in session.run(cypher, **params)]
            if not records:
                return f"【查询为空】未找到 {province} 的相关政策。"

            res = f"📋 {province} 相关政策：\n\n"
            for r in records:
                emoji = {"人才": "👤", "补贴": "💰", "落户": "🏠", "招生": "🎓", "选科": "📚"}.get(r["type"], "📄")
                res += f"{emoji} 【{r['type']}】{r['name']}\n"
                res += f"   {r['desc']}\n"
                if r.get("eligibility"):
                    res += f"   条件：{r['eligibility']}\n"
                if r.get("amount", 0) > 0:
                    res += f"   金额：{r['amount']}元\n"
                res += "\n"
            return res
    except Exception as e:
        return f"【查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 5. 职业路径查询（保留原有）
# ─────────────────────────────────────────────────────────

class CareerPathInput(BaseModel):
    major_name: str = Field(..., description="专业名称，例如：计算机科学与技术")


@tool("query_career_path_tool", args_schema=CareerPathInput)
def query_career_path_tool(major_name: str) -> str:
    """查询专业对应的职业路径和就业前景。
    当用户询问某专业就业方向、前景、对应职业时使用。
    """
    if not major_name or len(major_name) < 2:
        return "【查询失败】专业名称不完整。"

    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接。"

    cypher = """
    MATCH (m:Major {name: $major})-[:LEADS_TO]->(c:Career)
    OPTIONAL MATCH (m)-[:LEADS_TO_INDUSTRY]->(i:Industry)
    RETURN c.name AS career, c.prospect AS prospect,
           collect(DISTINCT i.name) AS industries
    """

    try:
        with driver.session() as session:
            records = [dict(r) for r in session.run(cypher, major=major_name)]
            if not records:
                return f"【查询为空】未找到 {major_name} 的职业路径。"

            res = f"🎓 {major_name} 职业方向：\n\n"
            for r in records:
                prospect = r.get("prospect", "未知")
                emoji = {"绿牌": "🟢", "红牌": "🔴", "黄牌": "🟡"}.get(prospect, "⚪")
                res += f"{emoji} {r['career']}（{prospect}）"
                if r.get("industries"):
                    res += f" → {', '.join(r['industries'])}"
                res += "\n"

            green = sum(1 for r in records if r.get("prospect") == "绿牌")
            red = sum(1 for r in records if r.get("prospect") == "红牌")
            if red > green:
                res += "\n⚠️ 红牌职业较多，建议谨慎选择。"
            elif green > 0:
                res += "\n✅ 有绿牌职业，就业前景较好。"
            return res
    except Exception as e:
        return f"【查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 6. 院校详情查询（保留原有）
# ─────────────────────────────────────────────────────────

class UniversityInfoInput(BaseModel):
    university_name: str = Field(..., description="大学名称，例如：清华大学")


@tool("query_university_info_tool", args_schema=UniversityInfoInput)
def query_university_info_tool(university_name: str) -> str:
    """查询大学详细信息。
    当用户询问某大学的层次、所在城市、开设专业时使用。
    """
    if not university_name or len(university_name) < 2:
        return "【查询失败】大学名称不完整。"

    driver = _get_driver()
    if not driver:
        return "【系统提示】Neo4j图谱未连接。"

    cypher = """
    MATCH (u:University {name: $name})
    OPTIONAL MATCH (u)-[:LOCATED_IN]->(c:City)
    OPTIONAL MATCH (c)-[:BELONGS_TO]->(p:Province)
    OPTIONAL MATCH (u)-[o:OFFERS]->(m:Major)
    RETURN u.name AS name, u.level AS level, u.city AS city, u.tags AS tags,
           c.name AS city_name, c.tier AS city_tier,
           p.name AS province,
           collect(DISTINCT m.name) AS majors,
           count(DISTINCT m) AS major_count
    """

    try:
        with driver.session() as session:
            record = session.run(cypher, name=university_name).single()
            if not record:
                return f"【查询为空】未找到 {university_name} 的信息。"

            level = record.get("level", "未知")
            emoji = "🏆" if "985" in level else "🥇" if "211" in level else "📚"
            res = f"{emoji} {record['name']}\n\n"
            res += f"层次: {level}\n"
            res += f"城市: {record.get('province', '未知')} {record.get('city_name', record.get('city', '未知'))}"
            if record.get("city_tier"):
                res += f"（{record['city_tier']}城市）"
            res += "\n"
            if record.get("tags"):
                res += f"标签: {record['tags']}\n"
            res += f"开设专业数: {record.get('major_count', 0)}\n"

            majors = record.get("majors", [])
            if majors:
                res += f"\n主要专业（前10）:\n"
                for m in majors[:10]:
                    res += f"  - {m}\n"
                if len(majors) > 10:
                    res += f"  ... 等共 {len(majors)} 个专业\n"
            return res
    except Exception as e:
        return f"【查询异常】{e}"


# ─────────────────────────────────────────────────────────
# 工具列表
# ─────────────────────────────────────────────────────────

NEO4J_TOOLS = [
    query_neo4j_admission_tool,
    query_city_salary_tool,
    query_major_tech_tool,
    query_policy_tool,
    query_career_path_tool,
    query_university_info_tool,
]
