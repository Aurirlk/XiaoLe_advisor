"""全网搜索 API 代理路由（自 backend/app/routers 迁移，P1-20）"""
from __future__ import annotations

from fastapi import APIRouter, Query

from api.response import fail, ok

router = APIRouter(prefix="/api/web", tags=["web-search"])


@router.get("/search")
async def web_search(
    query: str = Query(..., min_length=1, max_length=200),
    count: int = Query(8, ge=1, le=20),
):
    """站内搜索代理 — 复用现有 WebSearchService"""
    try:
        from tools.web_search_tools import WebSearchService
        searcher = WebSearchService()
        results = await searcher.search(query, top_k=count)
        items = []
        for r in results:
            items.append({
                "title": r.get("title", "")[:100],
                "url": r.get("url", ""),
                "author": r.get("author") or r.get("source") or "",
                "summary": r.get("content") or r.get("snippet") or r.get("summary", "")[:300],
            })
        return ok(data={"items": items, "total": len(items)})
    except Exception as e:
        return fail(message=f"搜索失败: {str(e)}")
