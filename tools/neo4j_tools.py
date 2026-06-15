"""
Neo4j 知识图谱查询工具
模板化Function Calling，禁止Text2Cypher

架构铁律：
- 大模型做参数提取，纯Python做安全兜底与图谱查询
- 所有Cypher必须是预定义的模板，禁止动态生成
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class GraphQueryInput(BaseModel):
    province: str = Field(..., description="考生所在省份，例如：广东省")
    subject_type: str = Field(..., description="选科类型：物理类/历史类")
    score: int = Field(..., description="高考分数")
    target_major: Optional[str] = Field(None, description="目标专业关键词，如：计算机")


@tool("query_neo4j_admission_tool", args_schema=GraphQueryInput)
def query_neo4j_admission_tool(
    province: str, 
    subject_type: str, 
    score: int, 
    target_major: Optional[str] = None
) -> str:
    """
    通过Neo4j知识图谱查询符合分数的大学和专业推荐。
    当用户提供分数并询问能上什么大学/专业时使用此工具。
    返回该分数段内的院校、专业和录取分数线。
    
    查询逻辑：
    - 向下浮动10分（冲刺）
    - 向上浮动30分（保底）
    - 可选专业过滤
    """
    # 分数校验
    if score < 200 or score > 750:
        return "【查询失败】分数输入异常，请提供真实的有效分数（200-750）。"
    
    # 省份校验
    if not province or len(province) < 2:
        return "【查询失败】省份信息不完整，请提供完整的省份名称（如：广东省）。"
    
    # 获取Neo4j驱动
    try:
        from api.dependencies import get_neo4j_driver
        driver = get_neo4j_driver()
        if not driver:
            return "【系统提示】Neo4j图谱未连接，正在使用本地数据库查询。"
    except Exception:
        return "【系统提示】Neo4j模块未加载，正在使用本地数据库查询。"
    
    # 构建Cypher模板（固定模式，安全兜底）
    cypher = """
    MATCH (u:University)-[o:OFFERS]->(m:Major)
    WHERE o.subject_type = $subject_type 
      AND o.min_score <= $max_score 
      AND o.min_score >= $min_score
    """
    
    params = {
        "subject_type": subject_type,
        "min_score": max(0, score - 10),  # 冲刺线
        "max_score": score + 30,          # 保底线
    }
    
    # 可选专业过滤（防止注入）
    if target_major and len(target_major) >= 2:
        # 只允许中文和英文字符
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
            result = session.run(cypher, **params)
            records = [dict(record) for record in result]
            
            if not records:
                return f"【查询为空】图谱中未找到 {score}分 ({subject_type}) 的匹配数据，请尝试放宽条件。"
            
            # 格式化输出
            res_str = f"📊 Neo4j图谱查询结果 - {score}分 ({province} {subject_type})：\n\n"
            for i, r in enumerate(records, 1):
                level_emoji = "🏆" if "985" in (r.get("level") or "") else "🥇" if "211" in (r.get("level") or "") else "📚"
                res_str += f"{i}. {level_emoji} {r['university']} ({r.get('level', '未知')})\n"
                res_str += f"   专业: {r['major']}\n"
                res_str += f"   最低分: {r['score']} | 位次: {r.get('rank', '未知')}\n\n"
            return res_str
            
    except Exception as e:
        return f"【图谱查询异常】{str(e)}"


class CareerPathInput(BaseModel):
    major_name: str = Field(..., description="专业名称，例如：计算机科学与技术")


@tool("query_career_path_tool", args_schema=CareerPathInput)
def query_career_path_tool(major_name: str) -> str:
    """
    查询专业对应的职业路径和就业前景（基于Neo4j图谱）。
    当用户询问某专业就业方向、前景、对应职业时使用。
    
    返回该专业对应的职业列表，包含就业前景标识（绿牌/红牌）。
    """
    if not major_name or len(major_name) < 2:
        return "【查询失败】专业名称不完整。"
    
    # 获取Neo4j驱动
    try:
        from api.dependencies import get_neo4j_driver
        driver = get_neo4j_driver()
        if not driver:
            return "【系统提示】Neo4j图谱未连接，正在使用本地知识库查询。"
    except Exception:
        return "【系统提示】Neo4j模块未加载，正在使用本地知识库查询。"
    
    # Cypher模板
    cypher = """
    MATCH (m:Major {name: $major_name})-[:LEADS_TO]->(c:Career)
    RETURN c.name AS career, c.prospect AS prospect
    ORDER BY c.prospect
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher, major_name=major_name)
            records = [dict(record) for record in result]
            
            if not records:
                return f"【查询为空】未找到 {major_name} 的职业路径数据。图谱中可能尚未导入该数据。"
            
            # 格式化输出
            res_str = f"🎓 {major_name} 主要职业方向：\n\n"
            for r in records:
                prospect = r.get("prospect", "未知")
                if prospect == "绿牌":
                    emoji = "🟢"
                elif prospect == "红牌":
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                res_str += f"- {emoji} {r['career']}（{prospect}就业前景）\n"
            
            # 添加提示
            green_count = sum(1 for r in records if r.get("prospect") == "绿牌")
            red_count = sum(1 for r in records if r.get("prospect") == "红牌")
            if red_count > green_count:
                res_str += "\n⚠️ 该专业红牌职业较多，建议谨慎选择。"
            elif green_count > 0:
                res_str += "\n✅ 该专业有绿牌职业，就业前景较好。"
            
            return res_str
            
    except Exception as e:
        return f"【查询异常】{str(e)}"


class UniversityInfoInput(BaseModel):
    university_name: str = Field(..., description="大学名称，例如：清华大学")


@tool("query_university_info_tool", args_schema=UniversityInfoInput)
def query_university_info_tool(university_name: str) -> str:
    """
    查询大学详细信息（基于Neo4j图谱）。
    当用户询问某大学的层次、所在城市、开设专业时使用。
    """
    if not university_name or len(university_name) < 2:
        return "【查询失败】大学名称不完整。"
    
    try:
        from api.dependencies import get_neo4j_driver
        driver = get_neo4j_driver()
        if not driver:
            return "【系统提示】Neo4j图谱未连接。"
    except Exception:
        return "【系统提示】Neo4j模块未加载。"
    
    # 查询大学信息
    cypher = """
    MATCH (u:University {name: $uni_name})
    OPTIONAL MATCH (u)-[:LOCATED_IN]->(p:Province)
    OPTIONAL MATCH (u)-[o:OFFERS]->(m:Major)
    RETURN u.name AS name, u.level AS level, u.city AS city, u.tags AS tags,
           p.name AS province,
           collect(DISTINCT m.name) AS majors,
           count(DISTINCT m) AS major_count
    """
    
    try:
        with driver.session() as session:
            result = session.run(cypher, uni_name=university_name)
            record = result.single()
            
            if not record:
                return f"【查询为空】未找到 {university_name} 的信息。"
            
            name = record["name"]
            level = record.get("level", "未知")
            city = record.get("city", "未知")
            tags = record.get("tags", "")
            province = record.get("province", "未知")
            majors = record.get("majors", [])
            major_count = record.get("major_count", 0)
            
            # 格式化输出
            level_emoji = "🏆" if "985" in level else "🥇" if "211" in level else "📚"
            res_str = f"{level_emoji} {name}\n\n"
            res_str += f"层次: {level}\n"
            res_str += f"城市: {province} {city}\n"
            if tags:
                res_str += f"标签: {tags}\n"
            res_str += f"开设专业数: {major_count}\n"
            
            if majors and len(majors) > 0:
                res_str += f"\n主要专业（前10）:\n"
                for m in majors[:10]:
                    res_str += f"  - {m}\n"
                if len(majors) > 10:
                    res_str += f"  ... 等共 {len(majors)} 个专业\n"
            
            return res_str
            
    except Exception as e:
        return f"【查询异常】{str(e)}"


# 工具列表，供外部注册
NEO4J_TOOLS = [query_neo4j_admission_tool, query_career_path_tool, query_university_info_tool]
