from __future__ import annotations

import re
import logging
from datetime import datetime

from core.state_schema import GraphState
from skills.reality_checker import check_expectation_gap
from skills.risk_assessor import assess_major_risk
from tools.sql_tools import QueryScoreArgs, SQLTools

logger = logging.getLogger(__name__)


def _parse_neo4j_result(neo4j_output: str) -> list[dict]:
    """解析Neo4j查询结果为标准格式"""
    results = []
    lines = neo4j_output.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("📊") or line.startswith("【"):
            continue
        
        # 解析格式: "1. 🏆 某大学 (985)"
        if line and line[0].isdigit() and ". " in line:
            try:
                parts = line.split(". ", 1)[1]
                # 提取大学名称和层次
                if "(" in parts and ")" in parts:
                    uni_part = parts.split("(")[0].strip()
                    level_part = parts.split("(")[1].split(")")[0].strip()
                else:
                    uni_part = parts.strip()
                    level_part = "未知"
                
                results.append({
                    "university_name": uni_part,
                    "tier": level_part,
                    "source": "neo4j",
                })
            except (IndexError, ValueError):
                continue
        # 解析格式: "   专业: 某专业"
        elif line.startswith("专业:") or line.startswith("专业："):
            major = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
            if results:
                results[-1]["major_name"] = major
        # 解析格式: "   最低分: 600 | 位次: 10000"
        elif "最低分:" in line or "最低分：" in line:
            try:
                score_part = line.split("最低分:")[1].split("|")[0].strip() if "最低分:" in line else line.split("最低分：")[1].split("|")[0].strip()
                rank_part = line.split("位次:")[1].strip() if "位次:" in line else line.split("位次：")[1].strip()
                if results:
                    results[-1]["min_score"] = int(score_part)
                    results[-1]["lowest_rank"] = int(rank_part)
            except (IndexError, ValueError):
                pass
    
    return results


def build_match_agent(sql_tools: SQLTools):
    async def match_agent(state: GraphState) -> GraphState:
        profile = state.get("user_profile", {})
        missing_fields = [
            key for key in ("province", "subject_type", "major_name") if not profile.get(key)
        ]
        if missing_fields:
            return {
                "error": "画像信息不足，无法查分。请先补充省份、选科和专业。",
                "sql_results": [],
                "next_node": "synthesis_agent",
            }

        query = state.get("user_query", "")
        year_match = re.search(r"(20\d{2})年?", query)
        target_year = int(year_match.group(1)) if year_match else datetime.now().year - 1
        
        # ══════════════════════════════════════════════════════════
        # 双路融合：Neo4j优先，SQLite降级
        # ══════════════════════════════════════════════════════════
        
        # 路径1: 尝试Neo4j图谱查询
        neo4j_results = []
        try:
            from tools.neo4j_tools import query_neo4j_admission_tool
            neo4j_output = query_neo4j_admission_tool.invoke({
                "province": profile["province"],
                "subject_type": profile["subject_type"],
                "score": profile.get("score", 0) or state.get("extracted_score", 0) or 500,
                "target_major": profile["major_name"],
            })
            
            # 检查Neo4j是否返回有效结果
            if "【查询为空】" not in neo4j_output and "【查询失败】" not in neo4j_output and "【系统提示】" not in neo4j_output:
                neo4j_results = _parse_neo4j_result(neo4j_output)
                if neo4j_results:
                    logger.info(f"Neo4j查询成功，返回 {len(neo4j_results)} 条结果")
        except Exception as e:
            logger.warning(f"Neo4j查询失败，降级到SQLite: {e}")
        
        # 路径2: SQLite查询（作为降级或补充）
        args = QueryScoreArgs(
            province=profile["province"],
            subject_type=profile["subject_type"],
            major_name=profile["major_name"],
            year=target_year,
            max_rows=10,
        )
        
        result = await sql_tools.query_scores(args)
        
        # ══════════════════════════════════════════════════════════
        # 结果融合：Neo4j结果优先，SQLite补充
        # ══════════════════════════════════════════════════════════
        
        sql_results = []
        
        # 如果Neo4j有结果，优先使用
        if neo4j_results:
            sql_results = neo4j_results
            # 添加来源标记
            for r in sql_results:
                if "_note" not in r:
                    r["_source"] = "neo4j"
        
        # SQLite结果作为补充
        if result.tier != "error" and result.tier != "empty":
            sqlite_rows = result.data
            # 去重：只添加Neo4j中没有的结果
            existing_unis = {r.get("university_name", "") for r in sql_results if "_note" not in r}
            for row in sqlite_rows:
                if row.get("university_name", "") not in existing_unis:
                    row["_source"] = "sqlite"
                    sql_results.append(row)
            
            if result.is_degraded and result.diagnostics:
                sql_results = [{"_note": d} for d in result.diagnostics] + sql_results
        
        # 如果都没有结果，返回错误
        if not sql_results:
            if result.tier == "error":
                error_msg = result.diagnostics[0] if result.diagnostics else "数据库查询失败"
            elif result.tier == "empty":
                hint = "\n".join(result.suggestions) if result.suggestions else ""
                error_msg = f"未查到相关数据。{hint}" if hint else "未查到相关数据，请检查参数。"
            else:
                error_msg = "图谱和数据库均未找到匹配数据"
            
            return {
                "sql_results": [],
                "error": error_msg,
                "next_node": "synthesis_agent",
            }
        
        # ══════════════════════════════════════════════════════════
        # 风险评估与现实校验
        # ══════════════════════════════════════════════════════════
        
        # 找到第一个有完整数据的行
        valid_row = None
        for row in sql_results:
            if "_note" not in row and "university_name" in row:
                valid_row = row
                break
        
        risk = {}
        reality = {}
        
        if valid_row:
            risk = assess_major_risk(
                profile["major_name"],
                valid_row.get("tier") or valid_row.get("level", "未知"),
                user_profile=profile,
            )
            
            if state.get("extracted_score") is not None:
                try:
                    score = int(state["extracted_score"])
                    reality = check_expectation_gap(score, valid_row.get("min_score", 0))
                except (ValueError, TypeError):
                    pass
        
        return {
            "sql_results": sql_results,
            "risk_assessment": risk,
            "reality_check": reality,
            "next_node": "synthesis_agent",
        }

    return match_agent
