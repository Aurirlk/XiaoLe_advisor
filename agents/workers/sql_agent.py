from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from core.state_schema import GraphState
from tools.function_tools import FUNCTION_TOOLS


SQL_AGENT_SYSTEM_PROMPT = """
你是报考系统的 SQL 数据查询代理。你有权使用工具查询本地数据库中的院校录取数据。
规则：
1. 用户询问分数线/位次/录取门槛时，调用 query_admission_scores_tool 获取数据
2. 用户询问经验/建议时，可以调用 search_experience_tool 搜索经验库
3. 用简洁清晰的方式呈现查询结果，禁止编造任何数据
4. 如果工具返回空或失败，如实告知用户
5. 如果用户未提供完整参数（省份、选科、专业），先提醒补充
""".strip()


def build_sql_agent(llm: ChatOpenAI):
    react_graph = create_react_agent(llm, FUNCTION_TOOLS)

    async def sql_agent(state: GraphState) -> GraphState:
        query = state.get("user_query", "")
        profile = state.get("user_profile", {})

        augmented_query = query
        if profile:
            parts = []
            if profile.get("province"):
                parts.append(f"省份：{profile['province']}")
            if profile.get("subject_type"):
                parts.append(f"选科：{profile['subject_type']}")
            if profile.get("major_name"):
                parts.append(f"专业：{profile['major_name']}")
            if parts:
                augmented_query = f"{query}\n已知用户信息：{'；'.join(parts)}"

        result = await react_graph.ainvoke(
            {
                "messages": [
                    SystemMessage(content=SQL_AGENT_SYSTEM_PROMPT),
                    HumanMessage(content=augmented_query),
                ],
            }
        )

        final_messages = result.get("messages", [])
        answer = ""
        for msg in reversed(final_messages):
            if hasattr(msg, "content") and msg.content and msg.type == "ai":
                answer = str(msg.content)
                break

        return {
            "sql_results": [{"llm_answer": answer}] if answer else [],
            "next_node": "synthesis_agent",
        }

    return sql_agent
