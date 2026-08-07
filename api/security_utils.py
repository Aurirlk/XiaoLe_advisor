"""API 安全工具：上传限制 / MIME 校验 / WebSocket 鉴权与连接配额

背景（交接手册 P0-10 / P0-11）：
- 上传端点曾无鉴权、无大小限制、先全量 read() 再判断大小（形同虚设）
- WebSocket 端点曾裸 accept()，任何人可白嫖 LLM/TTS 配额
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, UploadFile, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth import decode_access_token

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def auth_required() -> bool:
    """多模态/高成本端点是否强制鉴权。

    生产环境恒为 True；开发环境默认放行，可用 API_AUTH_REQUIRED=1 打开。
    """
    if _is_production():
        return True
    return os.getenv("API_AUTH_REQUIRED", "").lower() in ("1", "true", "yes")


_bearer = HTTPBearer(auto_error=False)


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """高成本端点的鉴权依赖。

    - 带上有效 Bearer token → 返回 payload
    - 未带 token 且生产环境 / API_AUTH_REQUIRED=1 → 401
    - 未带 token 且开发环境 → 返回匿名身份（便于本地联调）
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="无效的令牌")
        return payload
    if auth_required():
        raise HTTPException(
            status_code=401,
            detail="该接口需要登录后使用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"sub": "anonymous", "role": "guest"}

# ── 上传限制 ─────────────────────────────────────────────

MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_UPLOAD_MB", "10")) * 1024 * 1024
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "10")) * 1024 * 1024
MAX_DOC_BYTES = int(os.getenv("MAX_DOC_UPLOAD_MB", "20")) * 1024 * 1024

ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3", "audio/ogg", "audio/mp4", "audio/aac",
    "video/webm",  # 部分浏览器 MediaRecorder 会给 video/webm 容器
}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
ALLOWED_DOC_TYPES = ALLOWED_IMAGE_TYPES | {
    "application/pdf", "text/csv", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def read_limited(f: UploadFile, limit: int) -> bytes:
    """流式读取上传文件，超限立即 413（避免先整体读进内存再检查）"""
    buf = bytearray()
    total = 0
    while True:
        chunk = await f.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail=f"文件过大（上限 {limit // (1024 * 1024)}MB）")
        buf.extend(chunk)
    return bytes(buf)


def check_content_type(f: UploadFile, allowed: set[str], label: str = "文件") -> None:
    ct = (f.content_type or "").lower().split(";")[0].strip()
    if ct not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的{label}格式: {ct or '未知'}")


def validate_image_bytes(data: bytes) -> None:
    """用 Pillow 校验真实图像头（content_type 可被客户端伪造）"""
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except ImportError:
        logger.warning("Pillow 未安装，跳过图像头校验")
    except Exception:
        raise HTTPException(status_code=400, detail="文件不是有效的图像")


# ── 轻量限流（进程内滑动窗口）─────────────────────────────
# 多实例部署请换成 Redis；这里的目标是挡住单机刷 LLM/TTS 配额的行为。

_RATE_BUCKETS: dict[str, deque] = defaultdict(deque)
_RATE_LOCK = asyncio.Lock()


class RateLimiter:
    """按 (端点, 调用方) 维度的滑动窗口限流依赖工厂。

    用法: `_limit = RateLimiter("asr", limit=20, window=60)` → `Depends(_limit)`
    """

    def __init__(self, name: str, limit: int, window: int = 60):
        self.name = name
        self.limit = int(os.getenv(f"RATE_LIMIT_{name.upper()}", str(limit)))
        self.window = window

    async def __call__(self, request: Request) -> None:
        if self.limit <= 0:  # 显式配置为 0 表示关闭限流
            return
        auth = request.headers.get("authorization", "")
        caller = auth[-24:] if auth else (request.client.host if request.client else "unknown")
        key = f"{self.name}:{caller}"
        now = time.monotonic()
        async with _RATE_LOCK:
            bucket = _RATE_BUCKETS[key]
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = int(self.window - (now - bucket[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请 {retry_after} 秒后重试",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)


# ── WebSocket 鉴权与配额 ─────────────────────────────────

_WS_SEMAPHORE = asyncio.Semaphore(int(os.getenv("WS_MAX_CONN", "200")))
WS_IDLE_TIMEOUT = int(os.getenv("WS_IDLE_TIMEOUT_SECONDS", "120"))


def ws_auth_enabled() -> bool:
    """WS 鉴权开关：生产环境恒开启（WS_AUTH_DISABLED 无效）；开发环境默认关闭，
    可用 API_AUTH_REQUIRED=1 打开，便于本地联调不必每次拿 token。
    """
    if _is_production():
        if os.getenv("WS_AUTH_DISABLED", "").lower() in ("1", "true", "yes"):
            logger.error("生产环境不允许 WS_AUTH_DISABLED，已忽略该配置")
        return True
    return auth_required()


async def authenticate_ws(websocket: WebSocket) -> dict | None:
    """校验 WS 连接的 token（?token=xxx 查询参数）。

    返回 user payload；校验失败时关闭连接并返回 None（调用方应直接 return）。
    """
    if not ws_auth_enabled():
        return {"sub": "dev", "role": "student"}
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4401, reason="缺少 token")
        return None
    try:
        return decode_access_token(token)
    except Exception:
        await websocket.close(code=4401, reason="token 无效或已过期")
        return None


def ws_semaphore() -> asyncio.Semaphore:
    return _WS_SEMAPHORE
