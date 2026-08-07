from __future__ import annotations

from typing import Callable, Awaitable

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine

from agents.supervisor_agent import build_supervisor_agent
from agents.synthesis_agent import build_synthesis_agent
from agents.chat_agent import build_chat_agent
from agents.decision_detector import build_decision_detector
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
    enable_result_fusion: bool = False,
    enable_write_agent: bool = False,
    xuefeng_store=None,
    enable_agent_bus: bool = False,
    enable_reflexion: bool = False,
):
    graph = StateGraph(GraphState)
    sql_tools = SQLTools(engine)
    rag_tools = rag_tools or RAGTools()
    web_search_tools = WebSearchTools()
    supervisor_agent = build_supervisor_agent(llm)
    synthesis_agent = build_synthesis_agent(
        llm, feedback_store=feedback_store, xuefeng_store=xuefeng_store
    )

    # 蓝图 Phase 3.1：Agent 通信总线（可选增强）
    # 总线是节点间的"旁路通道"：match 完成后 publish 事件，career 通过
    # request 向 match 订阅者请求录取数据（请求-响应），实现跨 worker 协作，
    # 不干扰 LangGraph 的条件路由。
    bus = None
    if enable_agent_bus:
        from core.agent_bus import AgentCommunicationBus
        bus = AgentCommunicationBus()

    # 蓝图 Phase 3.2：自我反思质量门（可选增强）
    # match/career 输出后做规则评估；career 不满意时放宽 kb_scope 重查。
    reflexion = None
    if enable_reflexion:
        from core.reflexion_agent import ReflexionAgent
        reflexion = ReflexionAgent(max_reflections=1, llm=llm)

    match_agent = build_match_agent(sql_tools, bus=bus, reflexion=reflexion)
    career_agent = build_career_agent(rag_tools, bus=bus, reflexion=reflexion)

    # 蓝图 Phase 3.1：match 订阅者 —— 应答 career 的 "match.admission" 请求
    if bus is not None:
        from datetime import datetime
        from tools.sql_tools import QueryScoreArgs

        async def _match_admission_handler(msg):
            """请求-响应 handler：用 SQL 查"该分数能上的院校"，返回给 career。"""
            payload = msg.payload or {}
            major = payload.get("major_name") or ""
            if not major:
                return None
            try:
                args = QueryScoreArgs(
                    province=payload.get("province", "广东省"),
                    subject_type=payload.get("subject_type", "物理类"),
                    major_name=major,
                    year=int(datetime.now().year - 1),
                    max_rows=5,
                )
                result = await sql_tools.query_scores(args)
                if result.tier in ("error", "empty"):
                    return None
                return {"universities": [r.get("university_name") for r in result.data][:5]}
            except Exception:
                logger = __import__("logging").getLogger(__name__)
                logger.warning("match.admission handler 查询失败", exc_info=True)
                return None

        bus.subscribe("match.admission", _match_admission_handler)

    web_search_agent = build_web_search_agent(
        web_search_service=web_search_service,
        web_search=web_search_tools,
        llm=llm,
    )
    sql_fc_agent = build_sql_agent(llm)
    red_team_auditor = RedTeamAuditor()
    chat_agent = build_chat_agent(llm)
    decision_detector = build_decision_detector(llm, rag_tools)
    # 蓝图 Phase 3.3：结果融合器（synthesis 前融合节点，可选增强）
    fusion = None
    if enable_result_fusion:
        from core.result_fusion import AgentResult, ResultFusion
        fusion = ResultFusion(llm=llm)

    # 蓝图 write_Agent（2026-08-06）：唯一写权限 worker（可选增强）
    write_agent = None
    if enable_write_agent:
        from agents.workers.write_agent import WriteAgent
        write_agent = WriteAgent(vector_store=getattr(rag_tools, "_vector_store", None))

    async def _supervisor_node(state: GraphState) -> dict:
        result = await safe_node_call(supervisor_agent, state)
        # 蓝图 Phase 3.1：把总线协作统计写入 state（供 review / 面试展示）
        if bus is not None:
            result["bus_stats"] = bus.get_stats()
        return result

    async def _chat_node(state: GraphState) -> dict:
        return await safe_node_call(chat_agent, state)

    async def _decision_detector_node(state: GraphState) -> dict:
        return await safe_node_call(decision_detector, state)

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
                # 把 synthesis 的返回值合并进 state 再交给回调：
                # 回调需要读到最终 assistant 回复（messages）用于意图落库；
                # 直接传旧 state 会让 log_intent 的 response 永远为空。
                merged_state: dict = dict(state)
                if isinstance(result, dict):
                    for k, v in result.items():
                        if k == "messages":
                            prev = list(merged_state.get("messages") or [])
                            merged_state["messages"] = prev + list(v or [])
                        else:
                            merged_state[k] = v
                await on_conversation_end(merged_state)
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

    async def _fusion_node(state: GraphState) -> dict:
        """蓝图 Phase 3.3：结果融合节点（synthesis 前）。

        收集各 worker 的中间输出，用 ResultFusion 融合成综合上下文，
        写入 fusion_context 供 synthesis 使用。不满足条件时直接透传
        （next_node 交给 supervisor 已设的目标），不改变路由。
        """
        query = state.get("user_query", "")
        results: list = []
        # 各 worker 输出 → AgentResult（有内容才参与融合）
        sql_results = [r for r in (state.get("sql_results") or []) if isinstance(r, dict) and "_note" not in r]
        if sql_results:
            results.append(AgentResult(
                agent_name="match_agent", confidence=0.8,
                content="\n".join(str(r) for r in sql_results[:3]),
                metadata={"type": "sql"},
            ))
        career = (state.get("career_context") or "").strip()
        if career:
            results.append(AgentResult(
                agent_name="career_agent", confidence=0.8,
                content=career[:800], metadata={"type": "career"},
            ))
        web = (state.get("web_search_results") or "").strip()
        if web:
            results.append(AgentResult(
                agent_name="web_search_agent", confidence=0.7,
                content=web[:800], metadata={"type": "web"},
            ))
        if not results:
            return {"fusion_context": "", "next_node": "synthesis_agent"}

        try:
            fused = await fusion.fuse(results, query, strategy="merge")
            return {"fusion_context": fused, "next_node": "synthesis_agent"}
        except Exception:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("结果融合失败，透传原始输出", exc_info=True)
            return {"fusion_context": "", "next_node": "synthesis_agent"}

    async def _write_agent_node(state: GraphState) -> dict:
        """蓝图 write_Agent：把 web 搜索结果写入知识库（唯一写权限，可选增强）。

        从 state 读取 web_search_pages（增量累积的搜索页面），交给 WriteAgent
        去重写入；写入结果记录到 state.write_result（不影响主链路，失败静默）。
        """
        pages = state.get("web_search_pages") or []
        if not pages or write_agent is None:
            return {"write_result": {"ok": True, "written": 0, "skipped": 0, "reason": "无待写入页面"},
                    "next_node": "synthesis_agent"}
        write_summary = {"ok": True, "written": 0, "skipped": 0}
        for page in pages[:5]:  # 单轮最多写 5 个页面，防膨胀
            try:
                result = await write_agent.write_web_result_async(
                    url=page.get("url", ""),
                    title=page.get("title", ""),
                    content=page.get("content", page.get("text", "")),
                )
                write_summary["written"] += result.get("written", 0)
                write_summary["skipped"] += result.get("skipped", 0)
            except Exception:
                logger = __import__("logging").getLogger(__name__)
                logger.warning("write_agent 写入失败（跳过）", exc_info=True)
        return {"write_result": write_summary, "next_node": "synthesis_agent"}

    # 注册所有节点
    graph.add_node("supervisor_agent", _supervisor_node)
    graph.add_node("chat_agent", _chat_node)
    graph.add_node("decision_detector", _decision_detector_node)
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
    if fusion is not None:
        graph.add_node("result_fusion", _fusion_node)
    if write_agent is not None:
        graph.add_node("write_agent", _write_agent_node)

    # 入口 → supervisor
    graph.add_edge(START, "supervisor_agent")

    # supervisor 路由（支持 parent_agent 和 family_agent）
    supervisor_routes: dict = {
        "chat_agent": "chat_agent",
        "decision_detector": "decision_detector",
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
    }
    if fusion is not None:
        supervisor_routes["result_fusion"] = "result_fusion"
    if write_agent is not None:
        supervisor_routes["write_agent"] = "write_agent"
    graph.add_conditional_edges("supervisor_agent", _route_next, supervisor_routes)

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

    # match_agent → red_team_auditor → (fusion) → synthesis（反方审计链路）
    graph.add_edge("match_agent", "red_team_auditor")
    if fusion is not None:
        graph.add_edge("red_team_auditor", "result_fusion")
        graph.add_edge("result_fusion", "synthesis_agent")
    else:
        graph.add_edge("red_team_auditor", "synthesis_agent")

    # conflict_detector → synthesis（冲突检测后直接到合成）
    graph.add_edge("conflict_detector", "synthesis_agent")

    # 其他 agent → (fusion) → synthesis
    if fusion is not None:
        graph.add_edge("career_agent", "result_fusion")
        graph.add_edge("sql_agent", "result_fusion")
    else:
        graph.add_edge("career_agent", "synthesis_agent")
        graph.add_edge("sql_agent", "synthesis_agent")

    # web_search_agent → (write_agent) → (fusion) → synthesis
    # write_agent 开启时：搜索结果先落库再合成（蓝图单一写权限链路）
    if write_agent is not None:
        graph.add_edge("web_search_agent", "write_agent")
        if fusion is not None:
            graph.add_edge("write_agent", "result_fusion")
        else:
            graph.add_edge("write_agent", "synthesis_agent")
    elif fusion is not None:
        graph.add_edge("web_search_agent", "result_fusion")
    else:
        graph.add_edge("web_search_agent", "synthesis_agent")

    graph.add_edge("chat_agent", END)
    graph.add_edge("decision_detector", "synthesis_agent")
    graph.add_edge("synthesis_agent", END)

    return graph.compile(checkpointer=checkpointer)
