import logging
from core.state_schema import GraphState
from skills.ai_exposure_checker import assess_ai_exposure, get_major_exposure_summary
from tools.rag_tools import RAGTools

logger = logging.getLogger(__name__)


def _query_career_path_from_neo4j(major_name: str) -> str:
    """从Neo4j查询职业路径"""
    try:
        from tools.neo4j_tools import query_career_path_tool
        result = query_career_path_tool.invoke({"major_name": major_name})
        if "【查询为空】" not in result and "【系统提示】" not in result:
            return result
    except Exception as e:
        logger.warning(f"Neo4j职业路径查询失败: {e}")
    return ""


def _query_major_stats(major_name: str) -> str:
    """从SQLite查询投研级专业数据"""
    try:
        import sqlite3
        from pathlib import Path
        
        db_path = Path(__file__).resolve().parents[2] / "data" / "zx_advisor.db"
        if not db_path.exists():
            return ""
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        stats_parts = []
        
        # 查询就业去向
        dest = conn.execute(
            "SELECT * FROM major_destination_stats WHERE major_name = ? ORDER BY year DESC LIMIT 1",
            (major_name,)
        ).fetchone()
        
        if dest:
            stats_parts.append(f"📊 就业去向（{dest['year']}年）:")
            if dest['employed_rate']:
                stats_parts.append(f"  - 实际就业率: {dest['employed_rate']*100:.1f}%")
            if dest['postgraduate_rate']:
                stats_parts.append(f"  - 升学率: {dest['postgraduate_rate']*100:.1f}%")
            if dest['civil_servant_rate']:
                stats_parts.append(f"  - 考公上岸率: {dest['civil_servant_rate']*100:.1f}%")
            if dest['avg_start_salary']:
                stats_parts.append(f"  - 起薪中位数: {dest['avg_start_salary']}元")
        
        # 查询薪资分布
        salary = conn.execute(
            "SELECT * FROM major_salary_stats WHERE major_name = ? ORDER BY year DESC LIMIT 1",
            (major_name,)
        ).fetchone()
        
        if salary:
            stats_parts.append(f"\n💰 薪资分布（{salary['year']}年）:")
            if salary['salary_p25']:
                stats_parts.append(f"  - 25分位: {salary['salary_p25']}元")
            if salary['salary_p50']:
                stats_parts.append(f"  - 中位数: {salary['salary_p50']}元")
            if salary['salary_p75']:
                stats_parts.append(f"  - 75分位: {salary['salary_p75']}元")
        
        # 查询稳定性
        stability = conn.execute(
            "SELECT * FROM major_stability_stats WHERE major_name = ? ORDER BY year DESC LIMIT 1",
            (major_name,)
        ).fetchone()
        
        if stability:
            stats_parts.append(f"\n📈 稳定性（{stability['year']}年）:")
            if stability['turnover_rate_1y']:
                stats_parts.append(f"  - 一年离职率: {stability['turnover_rate_1y']*100:.1f}%")
            if stability['exam_dependency']:
                stats_parts.append(f"  - 考公依赖度: {stability['exam_dependency']}")
            if stability['required_certs'] and stability['required_certs'] != '[]':
                import json
                certs = json.loads(stability['required_certs'])
                if certs:
                    stats_parts.append(f"  - 必需证书: {', '.join(certs)}")
        
        conn.close()
        
        return "\n".join(stats_parts) if stats_parts else ""
        
    except Exception as e:
        logger.warning(f"查询投研级数据失败: {e}")
        return ""


def build_career_agent(rag_tools: RAGTools):
    def career_agent(state: GraphState) -> GraphState:
        profile = state.get("user_profile", {})
        major_name = profile.get("major_name", "")
        query = state.get("user_query", "")
        
        # ══════════════════════════════════════════════════════════
        # 多源数据融合
        # ══════════════════════════════════════════════════════════
        
        career_parts = []
        
        # 1. RAG经验库检索（现有功能）
        rag_context = rag_tools.query_zx_experience(query=query, top_k=3)
        if rag_context:
            career_parts.append("【经验库语录】")
            career_parts.append(rag_context)
        
        # 2. Neo4j职业路径查询
        if major_name:
            neo4j_career = _query_career_path_from_neo4j(major_name)
            if neo4j_career:
                career_parts.append("\n" + neo4j_career)
        
        # 3. 投研级专业数据
        if major_name:
            major_stats = _query_major_stats(major_name)
            if major_stats:
                career_parts.append("\n" + major_stats)
        
        # 4. AI暴露度评估
        if major_name:
            ai_exposure = assess_ai_exposure(major_name)
            if ai_exposure:
                exposure_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                emoji = exposure_emoji.get(ai_exposure["risk_level"], "⚪")
                
                career_parts.append(f"\n{emoji} AI暴露度评估:")
                career_parts.append(f"  - 风险分: {ai_exposure['ai_exposure_risk']:.0%} ({ai_exposure['risk_level']})")
                
                if ai_exposure["high_risk_tasks"]:
                    career_parts.append(f"  - 高风险任务: {', '.join(ai_exposure['high_risk_tasks'][:2])}")
                if ai_exposure["high_barrier_tasks"]:
                    career_parts.append(f"  - 高壁垒任务: {', '.join(ai_exposure['high_barrier_tasks'][:2])}")
                if ai_exposure["enhancement_suggestions"]:
                    career_parts.append(f"  - 建议增强: {', '.join(ai_exposure['enhancement_suggestions'][:2])}")
        
        career_context = "\n".join(career_parts) if career_parts else "暂无相关就业数据"
        
        return {"career_context": career_context, "next_node": "synthesis_agent"}

    return career_agent
