"""Admin CRUD API 路由（自 backend/app/routers 迁移，P1-20）

新增：全部端点强制 X-Admin-Key 鉴权（原实现完全裸奔）。
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from api.crud_services import (
    list_users, get_user_detail, toggle_user_status,
    list_announcements, create_announcement, update_announcement, delete_announcement,
    list_faqs, create_faq, update_faq, delete_faq,
    list_documents, create_document, update_document, delete_document,
    list_feedback, update_feedback_status,
    list_guides, create_guide, update_guide, delete_guide,
    list_keywords, create_keyword, update_keyword, delete_keyword,
    list_universities, update_university,
    list_majors, update_major,
    get_system_config, update_system_config,
)

router = APIRouter(prefix="/api/admin", tags=["admin-crud"])


def _verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """与 api/routers/admin_router.py 保持一致的 Admin Key 校验"""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="管理员 API Key 未配置（ADMIN_API_KEY）")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="无效的管理员 API Key")


# ==================== 用户管理 ====================

@router.get("/users", dependencies=[Depends(_verify_admin_key)])
def api_list_users(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), keyword: str = None):
    return list_users(page, size, keyword)


@router.get("/users/{user_id}", dependencies=[Depends(_verify_admin_key)])
def api_get_user(user_id: int):
    return get_user_detail(user_id)


@router.put("/users/{user_id}/status", dependencies=[Depends(_verify_admin_key)])
def api_toggle_user_status(user_id: int, enabled: bool = True):
    return toggle_user_status(user_id, enabled)


# ==================== 公告管理 ====================

@router.get("/announcements")
def api_list_announcements(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return list_announcements(page, size)


@router.post("/announcements", dependencies=[Depends(_verify_admin_key)])
def api_create_announcement(title: str, content: str, target_role: str = "all", is_pinned: bool = False):
    return create_announcement(title, content, target_role, is_pinned)


@router.put("/announcements/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_announcement(id: int, **kwargs):
    return update_announcement(id, **kwargs)


@router.delete("/announcements/{id}", dependencies=[Depends(_verify_admin_key)])
def api_delete_announcement(id: int):
    return delete_announcement(id)


# ==================== FAQ 管理 ====================

@router.get("/faqs")
def api_list_faqs(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), category: str = None):
    return list_faqs(page, size, category)


@router.post("/faqs", dependencies=[Depends(_verify_admin_key)])
def api_create_faq(question: str, answer: str, category: str = "通用"):
    return create_faq(question, answer, category)


@router.put("/faqs/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_faq(id: int, **kwargs):
    return update_faq(id, **kwargs)


@router.delete("/faqs/{id}", dependencies=[Depends(_verify_admin_key)])
def api_delete_faq(id: int):
    return delete_faq(id)


# ==================== 知识库管理 ====================

@router.get("/knowledge", dependencies=[Depends(_verify_admin_key)])
def api_list_documents(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return list_documents(page, size)


@router.post("/knowledge", dependencies=[Depends(_verify_admin_key)])
def api_create_document(title: str, content: str, category: str = "通用"):
    return create_document(title, content, category)


@router.put("/knowledge/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_document(id: str, content: str):
    return update_document(id, content)


@router.delete("/knowledge/{id}", dependencies=[Depends(_verify_admin_key)])
def api_delete_document(id: str):
    return delete_document(id)


# ==================== 反馈管理 ====================

@router.get("/feedback", dependencies=[Depends(_verify_admin_key)])
def api_list_feedback(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), status: str = None):
    return list_feedback(page, size, status)


@router.put("/feedback/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_feedback(id: int, status: str, admin_reply: str = None):
    return update_feedback_status(id, status, admin_reply)


# ==================== 指南管理 ====================

@router.get("/guides", dependencies=[Depends(_verify_admin_key)])
def api_list_guides(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return list_guides(page, size)


@router.post("/guides", dependencies=[Depends(_verify_admin_key)])
def api_create_guide(title: str, content: str, category: str = "志愿填报"):
    return create_guide(title, content, category)


@router.put("/guides/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_guide(id: int, **kwargs):
    return update_guide(id, **kwargs)


@router.delete("/guides/{id}", dependencies=[Depends(_verify_admin_key)])
def api_delete_guide(id: int):
    return delete_guide(id)


# ==================== 关键词管理 ====================

@router.get("/keywords", dependencies=[Depends(_verify_admin_key)])
def api_list_keywords(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return list_keywords(page, size)


@router.post("/keywords", dependencies=[Depends(_verify_admin_key)])
def api_create_keyword(text: str, group_name: str = "默认"):
    return create_keyword(text, group_name)


@router.put("/keywords/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_keyword(id: int, **kwargs):
    return update_keyword(id, **kwargs)


@router.delete("/keywords/{id}", dependencies=[Depends(_verify_admin_key)])
def api_delete_keyword(id: int):
    return delete_keyword(id)


# ==================== 院校管理 ====================

@router.get("/universities", dependencies=[Depends(_verify_admin_key)])
def api_list_universities(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), keyword: str = None):
    return list_universities(page, size, keyword)


@router.put("/universities/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_university(id: int, **kwargs):
    return update_university(id, **kwargs)


# ==================== 专业管理 ====================

@router.get("/majors", dependencies=[Depends(_verify_admin_key)])
def api_list_majors(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), keyword: str = None):
    return list_majors(page, size, keyword)


@router.put("/majors/{id}", dependencies=[Depends(_verify_admin_key)])
def api_update_major(id: int, **kwargs):
    return update_major(id, **kwargs)


# ==================== 系统配置 ====================

@router.get("/config", dependencies=[Depends(_verify_admin_key)])
def api_get_config():
    return get_system_config()


@router.put("/config", dependencies=[Depends(_verify_admin_key)])
def api_update_config(config: dict):
    return update_system_config(config)
