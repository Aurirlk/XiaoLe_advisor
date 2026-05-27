from __future__ import annotations

import re
from datetime import datetime

from core.state_schema import GraphState
from skills.reality_checker import check_expectation_gap
from skills.risk_assessor import assess_major_risk
from tools.sql_tools import QueryScoreArgs, SQLTools


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
        args = QueryScoreArgs(
            province=profile["province"],
            subject_type=profile["subject_type"],
            major_name=profile["major_name"],
            year=target_year,
            max_rows=10,
        )

        result = await sql_tools.query_scores(args)

        if result.tier == "error":
            return {
                "sql_results": [],
                "error": result.diagnostics[0] if result.diagnostics else "数据库查询失败",
                "next_node": "synthesis_agent",
            }

        if result.tier == "empty":
            hint = "\n".join(result.suggestions) if result.suggestions else ""
            return {
                "sql_results": [],
                "error": f"未查到相关数据。{hint}" if hint else "未查到相关数据，请检查参数。",
                "next_node": "synthesis_agent",
            }

        rows = result.data
        risk = assess_major_risk(
            profile["major_name"],
            rows[0]["tier"] if rows else "未知",
            user_profile=profile,
        )
        reality = {}
        if rows and state.get("extracted_score"):
            reality = check_expectation_gap(state["extracted_score"], rows[0]["min_score"])

        sql_results = rows
        if result.is_degraded and result.diagnostics:
            sql_results = [{"_note": d} for d in result.diagnostics] + rows

        return {
            "sql_results": sql_results,
            "risk_assessment": risk,
            "reality_check": reality,
            "next_node": "synthesis_agent",
        }

    return match_agent
