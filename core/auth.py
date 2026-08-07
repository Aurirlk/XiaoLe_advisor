"""JWT认证与密码哈希模块"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


def _resolve_jwt_secret() -> str:
    """解析 JWT 密钥：生产环境必须显式配置，禁止弱默认值。

    - 生产环境（APP_ENV=production）未配置 JWT_SECRET → 直接启动失败（fail-fast）。
    - 开发环境未配置 → 生成进程级随机密钥并告警（重启后旧 token 失效，属预期行为）。
    """
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret:
        if len(secret) < 32:
            logger.warning("JWT_SECRET 长度不足 32 字符，建议使用更强的密钥")
        return secret
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("生产环境必须配置 JWT_SECRET 环境变量（不允许默认值）")
    logger.warning("未配置 JWT_SECRET，开发环境使用进程级随机密钥（重启后所有 token 失效）")
    return secrets.token_urlsafe(48)


# JWT配置
JWT_SECRET = _resolve_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "168"))  # 7天

# HTTP Bearer认证方案
security = HTTPBearer()


def hash_password(password: str) -> str:
    """对密码进行bcrypt哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码与哈希是否匹配"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """从请求中获取当前用户（FastAPI依赖项）"""
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """要求管理员权限的依赖项"""
    user = await get_current_user(credentials)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
