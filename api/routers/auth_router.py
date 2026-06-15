"""认证API路由"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import sqlite3

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

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
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _user_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "phone_number": row["phone_number"],
        "username": row["username"],
        "role": row["role"],
        "province": row["province"],
        "score": row["score"],
        "rank": row["rank"],
    }


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, conn: sqlite3.Connection = Depends(_get_db)):
    if req.role not in ("student", "parent", "admin"):
        raise HTTPException(status_code=400, detail="角色必须是 student, parent 或 admin")

    existing = conn.execute(
        "SELECT id FROM user_profiles WHERE phone_number = ?", (req.phone_number,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="手机号已注册")

    username = req.username or req.phone_number
    password_hash = hash_password(req.password)

    conn.execute(
        "INSERT INTO user_profiles (phone_number, username, password_hash, role) VALUES (?, ?, ?, ?)",
        (req.phone_number, username, password_hash, req.role),
    )
    conn.commit()

    user = conn.execute(
        "SELECT * FROM user_profiles WHERE phone_number = ?", (req.phone_number,)
    ).fetchone()

    token = create_access_token({"sub": str(user["id"]), "phone": req.phone_number, "role": req.role})

    return AuthResponse(ok=True, token=token, user=_user_to_dict(user), message="注册成功")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, conn: sqlite3.Connection = Depends(_get_db)):
    user = conn.execute(
        "SELECT * FROM user_profiles WHERE phone_number = ?", (req.phone_number,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    if not user["password_hash"]:
        raise HTTPException(status_code=401, detail="该账号未设置密码，请使用手机号验证码登录或重新注册")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    token = create_access_token({"sub": str(user["id"]), "phone": req.phone_number, "role": user["role"]})

    return AuthResponse(ok=True, token=token, user=_user_to_dict(user), message="登录成功")


@router.get("/me", response_model=AuthResponse)
async def get_me(current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(_get_db)):
    user_id = current_user.get("sub")
    user = conn.execute("SELECT * FROM user_profiles WHERE id = ?", (user_id,)).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return AuthResponse(ok=True, user=_user_to_dict(user), message="获取成功")
