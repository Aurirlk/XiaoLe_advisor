from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


AllowedNode = Literal[
    "supervisor_agent",
    "profile_agent",
    "match_agent",
    "career_agent",
    "sql_agent",
    "synthesis_agent",
    "END",
]


class ProfileChange(TypedDict, total=False):
    """单次画像字段变更记录"""
    field: str
    old_value: Optional[str]
    new_value: str
    ts: str
    trigger_query: str


class GraphState(TypedDict, total=False):
    messages: Annotated[List[dict], add_messages]
    user_query: str
    session_id: str
    phone_number: str
    user_profile: Dict[str, Any]
    profile_history: List[ProfileChange]
    extracted_score: int
    extracted_rank: int
    sql_results: List[Dict[str, str]]
    career_context: str
    web_search_results: str
    web_search_pages: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    reality_check: Dict[str, Any]
    decision_hints: Dict[str, Any]
    missing_profile_fields: List[str]
    next_node: AllowedNode
    error: str
