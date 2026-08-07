import asyncio
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


def build_career_agent(rag_tools: RAGTools, bus=None, reflexion=None):
    async def career_agent(state: GraphState) -> GraphState:
        profile = state.get("user_profile", {})
        major_name = profile.get("major_name", "")
        query = state.get("user_query", "")

        # ══════════════════════════════════════════════════════════
        # 多源数据融合（P0-7：async + 并行，避免串行阻塞事件循环）
        # ══════════════════════════════════════════════════════════

        async def _fetch_rag() -> str:
            try:
                # 知识库分权（2026-08-06）：career_agent 只查就业/专业/政策/指南域，
                # 不查院校库（那是 match_agent 的地盘）；跨域兜底由检索层处理并打标记。
                return await rag_tools.query_zx_experience_async(
                    query=query,
                    top_k=3,
                    kb_scope=["user:employment/", "user:majors/", "user:policies/", "user:guides/"],
                )
            except Exception:
                logger.warning("RAG 经验库检索失败", exc_info=True)
                return ""

        async def _fetch_neo4j() -> str:
            if not major_name:
                return ""
            try:
                return await asyncio.to_thread(_query_career_path_from_neo4j, major_name)
            except Exception:
                logger.warning("Neo4j 职业路径查询失败", exc_info=True)
                return ""

        async def _fetch_stats() -> str:
            if not major_name:
                return ""
            try:
                return await asyncio.to_thread(_query_major_stats, major_name)
            except Exception:
                logger.warning("投研级数据查询失败", exc_info=True)
                return ""

        async def _fetch_ai_exposure() -> dict | None:
            if not major_name:
                return None
            try:
                return await asyncio.to_thread(assess_ai_exposure, major_name)
            except Exception:
                logger.warning("AI 暴露度评估失败", exc_info=True)
                return None

        rag_context, neo4j_career, major_stats, ai_exposure = await asyncio.gather(
            _fetch_rag(), _fetch_neo4j(), _fetch_stats(), _fetch_ai_exposure()
        )

        # ══════════════════════════════════════════════════════════
        # 蓝图 Phase 3.1：Agent 通信总线请求-响应（可选增强）
        # career 向 match 订阅者请求录取数据（"以我的分数能上哪些学校"），
        # 拿到后并入就业上下文——Agent 间真正协作，不依赖 state 顺序。
        # ══════════════════════════════════════════════════════════
        bus_admission = None
        if bus is not None:
            try:
                bus_admission = await bus.request(
                    "match.admission",
                    {"province": profile.get("province", ""),
                     "subject_type": profile.get("subject_type", ""),
                     "major_name": major_name,
                     "score": profile.get("score") or state.get("extracted_score") or 0},
                    sender="career_agent",
                    timeout=2.0,
                )
            except Exception:
                logger.warning("career_agent 总线请求失败（跳过）", exc_info=True)

        career_parts = []

        # 1. RAG经验库检索（现有功能）
        if rag_context:
            career_parts.append("【经验库语录】")
            career_parts.append(rag_context)

        # 2. Neo4j职业路径查询
        if neo4j_career:
            career_parts.append("\n" + neo4j_career)

        # 3. 投研级专业数据
        if major_stats:
            career_parts.append("\n" + major_stats)

        # 3.5 总线协作录取数据（match 订阅者应答）
        if bus_admission:
            unis = bus_admission.get("universities") or []
            if unis:
                career_parts.append("\n【可冲院校参考（Agent 总线协作）】")
                career_parts.append("、".join(str(u) for u in unis[:5]))

        # 4. AI暴露度评估
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

        # ══════════════════════════════════════════════════════════
        # 蓝图 Phase 3.2：自我反思质量门（可选增强）
        # 输出为空/缺关键要素时，用 regenerate 放宽 kb_scope 重查 RAG 一次。
        # ══════════════════════════════════════════════════════════
        reflexion_report = None
        if reflexion is not None:
            try:
                async def _regenerate_career(q: str, hint: str, ctx: dict) -> str:
                    """反思重试：放宽知识域范围再查一次（防分权漏检）"""
                    try:
                        return await rag_tools.query_zx_experience_async(
                            query=q,
                            top_k=4,
                            kb_scope=None,  # 全库兜底
                        )
                    except Exception:
                        return ""

                reflection = await reflexion.reflect(
                    query=query,
                    output=career_context,
                    context={"scene": "career", "sql_results": state.get("sql_results") or []},
                    topic="career",
                    regenerate=_regenerate_career,
                )
                reflexion_report = {
                    "node": "career_agent",
                    "satisfied": reflection.satisfied,
                    "issues": reflection.issues,
                    "suggestions": reflection.suggestions,
                    "reflections": reflection.reflections,
                }
                # 反思重试过且拿到补充内容 → 追加到上下文（不覆盖 bus 协作等已有数据）
                if reflection.reflections > 0 and reflection.output:
                    if reflection.output not in career_context:
                        career_context = career_context + "\n【反思补充】\n" + reflection.output
            except Exception:
                logger.warning("career_agent 反思评估失败（跳过）", exc_info=True)

        payload = {"career_context": career_context, "next_node": "synthesis_agent"}
        if reflexion_report is not None:
            payload["reflexion_report"] = reflexion_report
        return payload

    return career_agent
