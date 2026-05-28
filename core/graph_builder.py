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
from agents.workers.sql_agent import build_sql_agent
from agents.workers.web_search_agent import build_web_search_agent
from core.exception_handler import safe_node_call
from core.state_schema import GraphState
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
):
    graph = StateGraph(GraphState)
    sql_tools = SQLTools(engine)
    rag_tools = rag_tools or RAGTools()
    web_search_tools = WebSearchTools()
    supervisor_agent = build_supervisor_agent(llm)
    synthesis_agent = build_synthesis_agent(llm)
    match_agent = build_match_agent(sql_tools)
    career_agent = build_career_agent(rag_tools)
    web_search_agent = build_web_search_agent(
        web_search_service=web_search_service,
        web_search=web_search_tools,
    )
    sql_fc_agent = build_sql_agent(llm)

    # `safe_node_call` is async; nodes must be async functions too, otherwise
    # langgraph will receive the coroutine object instead of a dict result.
    async def _supervisor_node(state: GraphState) -> dict:
        return await safe_node_call(supervisor_agent, state)

    async def _profile_node(state: GraphState) -> dict:
        return await safe_node_call(profile_agent, state)

    async def _match_node(state: GraphState) -> dict:
        return await safe_node_call(match_agent, state)

    async def _career_node(state: GraphState) -> dict:
        return await safe_node_call(career_agent, state)

    async def _web_search_node(state: GraphState) -> dict:
        return await safe_node_call(web_search_agent, state)

    async def _synthesis_node(state: GraphState) -> dict:
        result = await safe_node_call(synthesis_agent, state)
        if on_conversation_end:
            await on_conversation_end(state)
        return result

    async def _sql_agent_node(state: GraphState) -> dict:
        return await safe_node_call(sql_fc_agent, state)

    graph.add_node("supervisor_agent", _supervisor_node)
    graph.add_node("profile_agent", _profile_node)
    graph.add_node("match_agent", _match_node)
    graph.add_node("career_agent", _career_node)
    graph.add_node("web_search_agent", _web_search_node)
    graph.add_node("synthesis_agent", _synthesis_node)
    graph.add_node("sql_agent", _sql_agent_node)
    graph.add_edge(START, "supervisor_agent")
    graph.add_conditional_edges(
        "supervisor_agent",
        _route_next,
        {
            "profile_agent": "profile_agent",
            "match_agent": "match_agent",
            "career_agent": "career_agent",
            "web_search_agent": "web_search_agent",
            "sql_agent": "sql_agent",
            "synthesis_agent": "synthesis_agent",
        },
    )
    graph.add_conditional_edges(
        "profile_agent",
        _route_next,
        {
            "supervisor_agent": "supervisor_agent",
            "synthesis_agent": "synthesis_agent",
        },
    )
    graph.add_edge("match_agent", "synthesis_agent")
    graph.add_edge("career_agent", "synthesis_agent")
    graph.add_edge("web_search_agent", "synthesis_agent")
    graph.add_edge("sql_agent", "synthesis_agent")
    graph.add_edge("synthesis_agent", END)
    return graph.compile(checkpointer=checkpointer)
