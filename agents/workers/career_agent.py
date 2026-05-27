from core.state_schema import GraphState
from tools.rag_tools import RAGTools


def build_career_agent(rag_tools: RAGTools):
    def career_agent(state: GraphState) -> GraphState:
        query = state.get("user_query", "")
        context = rag_tools.query_zx_experience(query=query, top_k=3)
        return {"career_context": context, "next_node": "synthesis_agent"}

    return career_agent
