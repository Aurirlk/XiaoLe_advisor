from __future__ import annotations

from typing import TYPE_CHECKING

from core.state_schema import GraphState

if TYPE_CHECKING:
    from core.web_search_service import WebSearchService
    from tools.web_search_tools import WebSearchTools


def build_web_search_agent(
    web_search_service: "WebSearchService | None" = None,
    web_search: "WebSearchTools | None" = None,
):
    async def web_search_agent(state: GraphState) -> GraphState:
        query = state.get("user_query", "")
        session_id = state.get("session_id", "") or ""

        if web_search_service is not None:
            bundle = await web_search_service.search_fetch_and_persist(
                query,
                chat_session_id=session_id,
            )
            formatted = bundle.formatted_text
            if not formatted:
                formatted = (
                    "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），"
                    "请基于本地数据与经验回答】"
                )
            return {
                "web_search_results": formatted,
                "web_search_pages": bundle.pages,
                "next_node": "synthesis_agent",
            }

        from tools.web_search_tools import WebSearchTools

        tools = web_search or WebSearchTools()
        results = tools.search(query=query, top_k=5)
        formatted = tools.format_results(results)
        if not formatted:
            formatted = (
                "【系统提示：外部搜索无结果/失败（可能网络不可用或超时），"
                "请基于本地数据与经验回答】"
            )
        return {"web_search_results": formatted, "next_node": "synthesis_agent"}

    return web_search_agent
