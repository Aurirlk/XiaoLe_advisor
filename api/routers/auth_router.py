"""认证API路由"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import sqlite3

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
)
from core.crm_manager import display_phone, hash_phone

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "zx_advisor.db"


class RegisterRequest(BaseModel):
    phone_number: str
    password: str
    role: str = "student"
    username: Optional[str] = None


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class AuthResponse(BaseModel):
    ok: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    message: str = ""


def _get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _user_to_dict(row: sqlite3.Row, phone_display: str | None = None) -> dict:
    """返回给客户端的用户信息。

    phone_number 字段不读库（库里是脱敏哈希），优先使用调用方传入的明文/脱敏值，
    否则统一脱敏为 ****xxxx。
    """
    return {
        "id": row["id"],
        "phone_number": phone_display or display_phone(""),
        "username": row["username"],
        "role": row["role"],
        "province": row["province"],
        "score": row["score"],
        "rank": row["rank"],
    }


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, conn: sqlite3.Connection = Depends(_get_db)):
    # 安全：公开注册接口禁止自注册 admin（管理员由后台/脚本创建）
    if req.role not in ("student", "parent"):
        raise HTTPException(status_code=400, detail="角色必须是 student 或 parent")
    if not req.password or len(req.password) < 8:
        raise HTTPException(status_code=400, detail="密码长度不能少于 8 位")

    phone_key = hash_phone(req.phone_number)
    existing = conn.execute(
        "SELECT id FROM user_profiles WHERE phone_number = ?", (phone_key,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="手机号已注册")

    username = req.username or req.phone_number
    password_hash = hash_password(req.password)

    conn.execute(
        "INSERT INTO user_profiles (phone_number, username, password_hash, role) VALUES (?, ?, ?, ?)",
        (phone_key, username, password_hash, req.role),
    )
    conn.commit()

    user = conn.execute(
        "SELECT * FROM user_profiles WHERE phone_number = ?", (phone_key,)
    ).fetchone()

    token = create_access_token({"sub": str(user["id"]), "phone": req.phone_number, "role": req.role})

    return AuthResponse(ok=True, token=token, user=_user_to_dict(user, req.phone_number), message="注册成功")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, conn: sqlite3.Connection = Depends(_get_db)):
    """登录：校验手机号 + 密码，颁发 JWT"""
    user = conn.execute(
        "SELECT * FROM user_profiles WHERE phone_number = ?", (hash_phone(req.phone_number),)
    ).fetchone()

    # 统一错误信息，防止用户枚举（OWASP API2:2023）
    _AUTH_FAIL = HTTPException(status_code=401, detail="手机号或密码错误")

    if not user:
        raise _AUTH_FAIL
    password_hash = user["password_hash"] if "password_hash" in user.keys() else None
    if not password_hash or not verify_password(req.password, password_hash):
        raise _AUTH_FAIL

    token = create_access_token({"sub": str(user["id"]), "phone": req.phone_number, "role": user["role"]})
    return AuthResponse(ok=True, token=token, user=_user_to_dict(user, req.phone_number), message="登录成功")


@router.get("/me", response_model=AuthResponse)
async def get_me(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    conn: sqlite3.Connection = Depends(_get_db),
):
    """获取当前登录用户信息（必须携带有效 token）"""
    if not credentials:
        raise HTTPException(
            status_code=401, detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # decode_access_token 失败会抛 401，不做 except 兜底
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    user = conn.execute("SELECT * FROM user_profiles WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return AuthResponse(ok=True, user=_user_to_dict(user, payload.get("phone")), message="获取成功")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """刷新Token - 用当前有效Token换取新Token"""
    new_token = create_access_token({
        "sub": current_user.get("sub"),
        "phone": current_user.get("phone"),
        "role": current_user.get("role"),
    })
    return AuthResponse(ok=True, token=new_token, message="Token已刷新")
