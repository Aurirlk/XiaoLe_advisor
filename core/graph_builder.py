from __future__ import annotations

from typing import Callable, Awaitable

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine

from agents.supervisor_agent import build_supervisor_agent
from agents.synthesis_agent import build_synthesis_agent
from agents.workers.career_agent import build_career_agent
from agents.workers.match_agent import build_match_agent
from agents.workers.profile_agent import profile_agent
from agents.workers.parent_agent import parent_agent
from agents.workers.family_agent import family_agent
from agents.workers.sql_agent import build_sql_agent
from agents.workers.web_search_agent import build_web_search_agent
from core.exception_handler import safe_node_call
from core.state_schema import GraphState
from skills.red_team_auditor import RedTeamAuditor
from skills.conflict_detector import detect_family_conflict
from tools.rag_tools import RAGTools
from tools.sql_tools import SQLTools
from tools.web_search_tools import WebSearchTools


def _route_next(state: GraphState) -> str:
    return state.get("next_node", "synthesis_agent")


def build_graph(
    engine: AsyncEngine,
    llm: ChatOpenAI,
    rag_tools: RAGTools | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    on_conversation_end: Callable[[GraphState], Awaitable[None]] | None = None,
    web_search_service=None,
    feedback_store=None,
):
    graph = StateGraph(GraphState)
    sql_tools = SQLTools(engine)
    rag_tools = rag_tools or RAGTools()
    web_search_tools = WebSearchTools()
    supervisor_agent = build_supervisor_agent(llm)
    synthesis_agent = build_synthesis_agent(llm, feedback_store=feedback_store)
    match_agent = build_match_agent(sql_tools)
    career_agent = build_career_agent(rag_tools)
    web_search_agent = build_web_search_agent(
        web_search_service=web_search_service,
        web_search=web_search_tools,
    )
    sql_fc_agent = build_sql_agent(llm)
    red_team_auditor = RedTeamAuditor()

    async def _supervisor_node(state: GraphState) -> dict:
        return await safe_node_call(supervisor_agent, state)

    async def _profile_node(state: GraphState) -> dict:
        return await safe_node_call(profile_agent, state)

    async def _parent_node(state: GraphState) -> dict:
        return await safe_node_call(parent_agent, state)

    async def _family_node(state: GraphState) -> dict:
        return await safe_node_call(family_agent, state)

    async def _match_node(state: GraphState) -> dict:
        return await safe_node_call(match_agent, state)

    async def _career_node(state: GraphState) -> dict:
        return await safe_node_call(career_agent, state)

    async def _web_search_node(state: GraphState) -> dict:
        return await safe_node_call(web_search_agent, state)

    async def _synthesis_node(state: GraphState) -> dict:
        result = await safe_node_call(synthesis_agent, state)
        if on_conversation_end:
            try:
                await on_conversation_end(state)
            except Exception:
                import logging
                logging.getLogger(__name__).warning("on_conversation_end 回调失败", exc_info=True)
        return result

    async def _sql_agent_node(state: GraphState) -> dict:
        return await safe_node_call(sql_fc_agent, state)

    async def _red_team_auditor_node(state: GraphState) -> dict:
        """反方审计节点 - 对推荐列表进行致命性审查"""
        sql_results = state.get("sql_results", [])
        profile = state.get("user_profile", {})
        
        # 过滤掉_note类型的记录，只保留真实推荐
        recommendations = [r for r in sql_results if isinstance(r, dict) and "_note" not in r]
        
        if not recommendations:
            return {"audit_result": {"passed": True, "audit_summary": "无推荐数据，跳过审计"}, "next_node": "synthesis_agent"}
        
        audit_result = red_team_auditor.audit_recommendations(profile, recommendations)
        return {"audit_result": audit_result, "next_node": "synthesis_agent"}

    async def _conflict_detector_node(state: GraphState) -> dict:
        """家庭冲突检测节点"""
        parent_c = state.get("parent_constraints", {})
        student_p = state.get("student_preferences", {})
        score = state.get("extracted_score", 0) or state.get("user_profile", {}).get("score", 0)
        rank = state.get("extracted_rank", 0) or state.get("user_profile", {}).get("rank", 0)
        
        conflict_result = detect_family_conflict(parent_c, student_p, score, rank)
        return {"family_conflict": conflict_result}

    # 注册所有节点
    graph.add_node("supervisor_agent", _supervisor_node)
    graph.add_node("profile_agent", _profile_node)
    graph.add_node("parent_agent", _parent_node)
    graph.add_node("family_agent", _family_node)
    graph.add_node("match_agent", _match_node)
    graph.add_node("career_agent", _career_node)
    graph.add_node("web_search_agent", _web_search_node)
    graph.add_node("synthesis_agent", _synthesis_node)
    graph.add_node("sql_agent", _sql_agent_node)
    graph.add_node("red_team_auditor", _red_team_auditor_node)
    graph.add_node("conflict_detector", _conflict_detector_node)

    # 入口 → supervisor
    graph.add_edge(START, "supervisor_agent")

    # supervisor 路由（支持 parent_agent 和 family_agent）
    graph.add_conditional_edges(
        "supervisor_agent",
        _route_next,
        {
            "profile_agent": "profile_agent",
            "parent_agent": "parent_agent",
            "family_agent": "family_agent",
            "match_agent": "match_agent",
            "career_agent": "career_agent",
            "web_search_agent": "web_search_agent",
            "sql_agent": "sql_agent",
            "synthesis_agent": "synthesis_agent",
            "red_team_auditor": "red_team_auditor",
            "conflict_detector": "conflict_detector",
        },
    )

    # profile_agent 路由
    graph.add_conditional_edges(
        "profile_agent",
        _route_next,
        {
            "supervisor_agent": "supervisor_agent",
            "synthesis_agent": "synthesis_agent",
        },
    )

    # parent_agent → family_agent（家长提取后自动融合）
    graph.add_conditional_edges(
        "parent_agent",
        _route_next,
        {
            "family_agent": "family_agent",
            "synthesis_agent": "synthesis_agent",
        },
    )

    # family_agent → synthesis
    graph.add_edge("family_agent", "synthesis_agent")

    # match_agent → red_team_auditor → synthesis（反方审计链路）
    graph.add_edge("match_agent", "red_team_auditor")
    graph.add_edge("red_team_auditor", "synthesis_agent")

    # conflict_detector → synthesis（冲突检测后直接到合成）
    graph.add_edge("conflict_detector", "synthesis_agent")

    # 其他 agent → synthesis
    graph.add_edge("career_agent", "synthesis_agent")
    graph.add_edge("web_search_agent", "synthesis_agent")
    graph.add_edge("sql_agent", "synthesis_agent")
    graph.add_edge("synthesis_agent", END)

    return graph.compile(checkpointer=checkpointer)
