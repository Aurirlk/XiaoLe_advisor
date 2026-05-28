from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import get_web_search_service, get_web_search_store
from core.web_search_service import WebSearchService
from core.web_search_store import WebSearchStore, make_hash

router = APIRouter(prefix="/web", tags=["web"])


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="搜索关键词")
    session_id: str = Field("", description="对话会话 ID（可选）")
    force_refresh: bool = Field(False, description="忽略缓存强制重新联网")


class WebSearchResponse(BaseModel):
    ok: bool
    query: str
    db_session_id: int
    result_count: int
    from_cache: bool
    query_hash: str
    formatted_preview: str


class SessionListItem(BaseModel):
    id: int
    query_text: str
    query_hash: str
    session_id: str
    result_count: int
    created_at: str


class SessionDetailResponse(BaseModel):
    ok: bool
    session: dict


class CacheCheckResponse(BaseModel):
    ok: bool
    cached: bool
    query_hash: str
    db_session_id: Optional[int] = None


@router.post("/search", response_model=WebSearchResponse)
async def web_search(
    payload: WebSearchRequest,
    service: WebSearchService = Depends(get_web_search_service),
):
    bundle = await service.search_fetch_and_persist(
        payload.query,
        chat_session_id=payload.session_id,
        force_refresh=payload.force_refresh,
    )
    preview = bundle.formatted_text[:500] + (
        "..." if len(bundle.formatted_text) > 500 else ""
    )
    return WebSearchResponse(
        ok=True,
        query=payload.query,
        db_session_id=bundle.db_session_id,
        result_count=len(bundle.pages),
        from_cache=bundle.from_cache,
        query_hash=bundle.query_hash,
        formatted_preview=preview,
    )


@router.get("/sessions", response_model=List[SessionListItem])
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: WebSearchStore = Depends(get_web_search_store),
):
    rows = await store.list_sessions(limit=limit, offset=offset)
    return [SessionListItem(**row) for row in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    store: WebSearchStore = Depends(get_web_search_store),
):
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session 不存在")
    return SessionDetailResponse(ok=True, session=session)


@router.get("/cache/check", response_model=CacheCheckResponse)
async def cache_check(
    q: str = Query(..., min_length=1, description="查询词"),
    store: WebSearchStore = Depends(get_web_search_store),
    service: WebSearchService = Depends(get_web_search_service),
):
    cached = await store.find_cached_session(q, service.config.cache_ttl_hours)
    query_hash = make_hash(q)
    if cached:
        return CacheCheckResponse(
            ok=True,
            cached=True,
            query_hash=query_hash,
            db_session_id=cached.db_session_id,
        )
    return CacheCheckResponse(ok=True, cached=False, query_hash=query_hash)
