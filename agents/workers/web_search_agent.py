from __future__ import annotations

from core.state_schema import GraphState
from tools.web_search_tools import WebSearchTools


def build_web_search_agent(web_search: WebSearchTools | None = None):
    web_search = web_search or WebSearchTools()

    def web_search_agent(state: GraphState) -> GraphState:
        query = state.get("user_query", "")
        results = web_search.search(query=query, top_k=5)
        formatted = web_search.format_results(results)
        if not formatted:
            formatted = "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），请基于本地数据与经验回答】"
        return {"web_search_results": formatted, "next_node": "synthesis_agent"}

    return web_search_agent

