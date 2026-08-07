"""通知 + 反馈用户端 API 路由（自 backend/app/routers 迁移，P1-20）

修复：原实现 `get_current_user`（async）未 await 即使用，鉴权恒失效。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from api.crud_services import (
    list_faqs, list_keywords,
    list_notifications, get_unread_count, mark_as_read, mark_all_as_read,
    submit_feedback,
)
from core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["user-notification"])
security = HTTPBearer(auto_error=False)


class FeedbackSubmit(BaseModel):
    rating: int
    comment: Optional[str] = None
    conversation_id: Optional[str] = None


# ==================== 通知 ====================

@router.get("/notifications")
async def api_list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    return list_notifications(user["id"], page, size)


@router.get("/notifications/unread-count")
async def api_unread_count(user: dict = Depends(get_current_user)):
    return {"ok": True, "data": {"count": get_unread_count(user["id"])}}


@router.put("/notifications/{id}/read")
async def api_mark_read(id: int, user: dict = Depends(get_current_user)):
    return mark_as_read(id, user["id"])


@router.put("/notifications/read-all")
async def api_mark_all_read(user: dict = Depends(get_current_user)):
    return mark_all_as_read(user["id"])


# ==================== 反馈 ====================

@router.post("/feedback")
async def api_submit_feedback(
    payload: FeedbackSubmit,
    user: dict = Depends(get_current_user),
):
    return submit_feedback(user["id"], payload.conversation_id, payload.rating, payload.comment)


# ==================== 用户端 FAQ / 快捷提问词 ====================

@router.get("/faqs")
def api_user_list_faqs(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50)):
    return list_faqs(page, size)


@router.get("/quick-keywords")
def api_get_keywords():
    result = list_keywords(page=1, size=100)
    if result.get("ok"):
        return {"ok": True, "data": {"items": result["data"]["items"]}}
    return result
