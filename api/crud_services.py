"""CRUD 服务层（自 backend/app/services 迁移合并，P1-20）

整合 admin_service / notification_service / feedback_service 的同步 SQLite 逻辑，
统一连接入口，并修复两个 schema 对齐 bug：
- list_users 原 SELECT created_at（user_profiles 无此列）→ first_seen_at
- toggle_user_status 原 UPDATE status（user_profiles 无此列）→ 依赖 crm_manager 迁移新增的 status 列
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "zx_advisor.db"


def get_connection() -> sqlite3.Connection:
    """同步 SQLite 连接（非依赖注入场景用）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ══════════════════ 用户管理 ══════════════════

def list_users(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if keyword:
            where = "WHERE username LIKE ? OR phone_number LIKE ?"
            params = [f"%{keyword}%", f"%{keyword}%"]
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM user_profiles " + where, params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, username, phone_number, role, province, score, rank, first_seen_at "
            f"FROM user_profiles {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [size, offset],
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def get_user_detail(user_id: int) -> dict:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profiles WHERE id=?", (user_id,)).fetchone()
        if not row:
            return {"ok": False, "message": "用户不存在"}
        return {"ok": True, "data": dict(row)}
    finally:
        conn.close()


def toggle_user_status(user_id: int, enabled: bool) -> dict:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE user_profiles SET status=? WHERE id=?",
            ("active" if enabled else "disabled", user_id),
        )
        conn.commit()
        return {"ok": True, "message": "状态已更新"}
    finally:
        conn.close()


# ══════════════════ 公告管理 ══════════════════

def list_announcements(page: int = 1, size: int = 20) -> dict:
    conn = get_connection()
    try:
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM announcements ORDER BY is_pinned DESC, created_at DESC LIMIT ? OFFSET ?",
            (size, offset),
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def create_announcement(title: str, content: str, target_role: str = "all", is_pinned: bool = False) -> dict:
    conn = get_connection()
    try:
        c = conn.execute(
            "INSERT INTO announcements (title, content, target_role, is_pinned) VALUES (?,?,?,?)",
            (title, content, target_role, 1 if is_pinned else 0),
        )
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}, "message": "公告已创建"}
    finally:
        conn.close()


def update_announcement(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields: list[str] = []
        values: list = []
        for k, v in kwargs.items():
            if k in ("title", "content", "target_role", "status"):
                fields.append(f"{k}=?")
                values.append(v)
            if k == "is_pinned":
                fields.append("is_pinned=?")
                values.append(1 if v else 0)
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        fields.append("updated_at=CURRENT_TIMESTAMP")
        values.append(id)
        conn.execute(f"UPDATE announcements SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "公告已更新"}
    finally:
        conn.close()


def delete_announcement(id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM announcements WHERE id=?", (id,))
        conn.commit()
        return {"ok": True, "message": "公告已删除"}
    finally:
        conn.close()


# ══════════════════ FAQ 管理 ══════════════════

def list_faqs(page: int = 1, size: int = 20, category: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if category:
            where = "WHERE category=?"
            params.append(category)
        offset = (page - 1) * size
        total = conn.execute(f"SELECT COUNT(*) FROM faqs {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM faqs {where} ORDER BY is_pinned DESC, sort_order ASC, created_at DESC LIMIT ? OFFSET ?",
            params + [size, offset],
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def create_faq(question: str, answer: str, category: str = "通用") -> dict:
    conn = get_connection()
    try:
        c = conn.execute("INSERT INTO faqs (question, answer, category) VALUES (?,?,?)", (question, answer, category))
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}, "message": "FAQ 已创建"}
    finally:
        conn.close()


def update_faq(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields: list[str] = []
        values: list = []
        for k, v in kwargs.items():
            if k in ("question", "answer", "category", "status", "sort_order", "is_pinned"):
                fields.append(f"{k}=?")
                values.append(v)
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        values.append(id)
        conn.execute(f"UPDATE faqs SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "FAQ 已更新"}
    finally:
        conn.close()


def delete_faq(id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM faqs WHERE id=?", (id,))
        conn.commit()
        return {"ok": True, "message": "FAQ 已删除"}
    finally:
        conn.close()


# ══════════════════ 知识库管理（data/documents 目录） ══════════════════

def _docs_dir() -> Path:
    return ROOT / "data" / "documents"


def list_documents(page: int = 1, size: int = 20) -> dict:
    items = []
    docs_dir = _docs_dir()
    if docs_dir.exists():
        for f in sorted(docs_dir.rglob("*.md")):
            rel = f.relative_to(docs_dir)
            items.append({"id": str(rel), "title": f.stem, "path": str(rel), "updated": f.stat().st_mtime})
    return {"ok": True, "data": {"total": len(items), "items": items}}


def create_document(title: str, content: str, category: str = "通用") -> dict:
    docs_dir = _docs_dir() / category
    docs_dir.mkdir(parents=True, exist_ok=True)
    fpath = docs_dir / f"{title}.md"
    fpath.write_text(content, encoding="utf-8")
    return {"ok": True, "message": "文档已创建"}


def update_document(id: str, content: str) -> dict:
    fpath = _docs_dir() / id
    if not fpath.exists():
        return {"ok": False, "message": "文档不存在"}
    fpath.write_text(content, encoding="utf-8")
    return {"ok": True, "message": "文档已更新"}


def delete_document(id: str) -> dict:
    fpath = _docs_dir() / id
    if fpath.exists():
        fpath.unlink()
    return {"ok": True, "message": "文档已删除"}


# ══════════════════ 反馈管理 ══════════════════

def list_feedback(page: int = 1, size: int = 20, status: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if status:
            where = "WHERE status=?"
            params.append(status)
        offset = (page - 1) * size
        total = conn.execute(f"SELECT COUNT(*) FROM feedback {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM feedback {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [size, offset],
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def update_feedback_status(id: int, status: str, admin_reply: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        if admin_reply:
            conn.execute("UPDATE feedback SET status=?, admin_reply=? WHERE id=?", (status, admin_reply, id))
        else:
            conn.execute("UPDATE feedback SET status=? WHERE id=?", (status, id))
        conn.commit()
        return {"ok": True, "message": "反馈已处理"}
    finally:
        conn.close()


# ══════════════════ 指南管理 ══════════════════

def list_guides(page: int = 1, size: int = 20) -> dict:
    conn = get_connection()
    try:
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM guides").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM guides ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (size, offset),
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def create_guide(title: str, content: str, category: str) -> dict:
    conn = get_connection()
    try:
        c = conn.execute("INSERT INTO guides (title, content, category) VALUES (?,?,?)", (title, content, category))
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}, "message": "指南已创建"}
    finally:
        conn.close()


def update_guide(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields = [f"{k}=?" for k in kwargs if k in ("title", "content", "category", "status")]
        values = [v for k, v in kwargs.items() if k in ("title", "content", "category", "status")]
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        fields.append("updated_at=CURRENT_TIMESTAMP")
        values.append(id)
        conn.execute(f"UPDATE guides SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "指南已更新"}
    finally:
        conn.close()


def delete_guide(id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM guides WHERE id=?", (id,))
        conn.commit()
        return {"ok": True, "message": "指南已删除"}
    finally:
        conn.close()


# ══════════════════ 关键词管理 ══════════════════

def list_keywords(page: int = 1, size: int = 20) -> dict:
    conn = get_connection()
    try:
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM quick_keywords").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM quick_keywords ORDER BY group_name, sort_order ASC LIMIT ? OFFSET ?",
            (size, offset),
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def create_keyword(text: str, group_name: str = "默认") -> dict:
    conn = get_connection()
    try:
        c = conn.execute("INSERT INTO quick_keywords (text, group_name) VALUES (?,?)", (text, group_name))
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}, "message": "关键词已创建"}
    finally:
        conn.close()


def update_keyword(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields = [f"{k}=?" for k in kwargs if k in ("text", "group_name", "sort_order", "status")]
        values = [v for k, v in kwargs.items() if k in ("text", "group_name", "sort_order", "status")]
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        values.append(id)
        conn.execute(f"UPDATE quick_keywords SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "关键词已更新"}
    finally:
        conn.close()


def delete_keyword(id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM quick_keywords WHERE id=?", (id,))
        conn.commit()
        return {"ok": True, "message": "关键词已删除"}
    finally:
        conn.close()


# ══════════════════ 院校 / 专业管理 ══════════════════

def list_universities(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if keyword:
            where = "WHERE name LIKE ? OR province LIKE ?"
            params = [f"%{keyword}%", f"%{keyword}%"]
        offset = (page - 1) * size
        total = conn.execute(f"SELECT COUNT(*) FROM universities {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, name, province, level, admin, tags FROM universities {where} ORDER BY name LIMIT ? OFFSET ?",
            params + [size, offset],
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def update_university(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields = [f"{k}=?" for k in kwargs if k in ("name", "province", "level", "admin", "tags")]
        values = [v for k, v in kwargs.items() if k in ("name", "province", "level", "admin", "tags")]
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        values.append(id)
        conn.execute(f"UPDATE universities SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "院校已更新"}
    finally:
        conn.close()


def list_majors(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if keyword:
            where = "WHERE name LIKE ? OR category LIKE ?"
            params = [f"%{keyword}%", f"%{keyword}%"]
        offset = (page - 1) * size
        total = conn.execute(f"SELECT COUNT(*) FROM majors {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM majors {where} ORDER BY name LIMIT ? OFFSET ?",
            params + [size, offset],
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def update_major(id: int, **kwargs) -> dict:
    conn = get_connection()
    try:
        fields = [f"{k}=?" for k in kwargs if k in ("name", "code", "category", "subcategory")]
        values = [v for k, v in kwargs.items() if k in ("name", "code", "category", "subcategory")]
        if not fields:
            return {"ok": False, "message": "无更新字段"}
        values.append(id)
        conn.execute(f"UPDATE majors SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        return {"ok": True, "message": "专业已更新"}
    finally:
        conn.close()


# ══════════════════ 系统配置 ══════════════════

def get_system_config() -> dict:
    try:
        import yaml
        config_path = ROOT / "configs" / ".config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return {"ok": True, "data": cfg}
        return {"ok": True, "data": {}}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def update_system_config(config: dict) -> dict:
    try:
        import yaml
        config_path = ROOT / "configs" / ".config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, indent=2)
        return {"ok": True, "message": "配置已更新"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ══════════════════ 通知服务 ══════════════════

def send_notification(user_id: int, title: str, content: Optional[str] = None,
                      type: str = "system", related_id: Optional[int] = None) -> dict:
    conn = get_connection()
    try:
        c = conn.execute(
            "INSERT INTO notifications (user_id, title, content, type, related_id) VALUES (?,?,?,?,?)",
            (user_id, title, content, type, related_id),
        )
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}}
    finally:
        conn.close()


def send_announcement_notification(announcement_id: int, target_role: str = "all") -> int:
    """发送公告通知给指定角色的所有用户，返回发送数量"""
    conn = get_connection()
    try:
        ann = conn.execute("SELECT title, content FROM announcements WHERE id=?", (announcement_id,)).fetchone()
        if not ann:
            return 0
        if target_role == "all":
            users = conn.execute("SELECT id FROM user_profiles").fetchall()
        else:
            users = conn.execute("SELECT id FROM user_profiles WHERE role=?", (target_role,)).fetchall()
        for u in users:
            conn.execute(
                "INSERT INTO notifications (user_id, title, content, type, related_id) VALUES (?,?,?,'announcement',?)",
                (u["id"], ann["title"], ann["content"], announcement_id),
            )
        conn.commit()
        return len(users)
    finally:
        conn.close()


def list_notifications(user_id: int, page: int = 1, size: int = 20) -> dict:
    conn = get_connection()
    try:
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=?", (user_id,)).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, size, offset),
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()


def mark_as_read(notification_id: int, user_id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notification_id, user_id))
        conn.commit()
        return {"ok": True, "message": "已标记为已读"}
    finally:
        conn.close()


def mark_all_as_read(user_id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0", (user_id,))
        conn.commit()
        return {"ok": True, "message": "全部标记为已读"}
    finally:
        conn.close()


def get_unread_count(user_id: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,)).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ══════════════════ 反馈服务（用户端） ══════════════════

def submit_feedback(user_id: int, conversation_id: str = None, rating: int = 0, comment: str = None) -> dict:
    conn = get_connection()
    try:
        c = conn.execute(
            "INSERT INTO feedback (user_id, conversation_id, rating, comment) VALUES (?,?,?,?)",
            (user_id, conversation_id, rating, comment),
        )
        conn.commit()
        return {"ok": True, "data": {"id": c.lastrowid}, "message": "反馈已提交"}
    finally:
        conn.close()


def list_user_feedback(user_id: int, page: int = 1, size: int = 20) -> dict:
    conn = get_connection()
    try:
        offset = (page - 1) * size
        total = conn.execute("SELECT COUNT(*) FROM feedback WHERE user_id=?", (user_id,)).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM feedback WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, size, offset),
        ).fetchall()
        return {"ok": True, "data": {"total": total, "items": [dict(r) for r in rows], "page": page, "size": size}}
    finally:
        conn.close()
