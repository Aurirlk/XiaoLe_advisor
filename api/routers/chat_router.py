from datetime import datetime, timezone
import json
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis

from api.dependencies import get_redis_client

router = APIRouter(prefix="/chat", tags=["chat"])
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7

_SAFE_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, description="用户消息")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not _SAFE_SESSION_ID_RE.match(v):
            raise ValueError("session_id 只允许字母数字下划线和短横线，最长 128 字符")
        return v


class SessionResponse(BaseModel):
    session_id: str
    messages: List[dict]


@router.post("/message")
async def save_message(payload: ChatRequest, redis: Redis = Depends(get_redis_client)):
    key = f"chat:session:{payload.session_id}"
    record = {"role": "user", "content": payload.message, "ts": datetime.now(timezone.utc).isoformat()}
    await redis.rpush(key, json.dumps(record, ensure_ascii=False))
    await redis.expire(key, SESSION_TTL_SECONDS)
    message_count = await redis.llen(key)
    return {"ok": True, "session_id": payload.session_id, "message_count": message_count}


@router.get("/history/{session_id}", response_model=SessionResponse)
async def get_history(session_id: str, redis: Redis = Depends(get_redis_client)):
    if not _SAFE_SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="session_id 格式非法")
    key = f"chat:session:{session_id}"
    raw_messages = await redis.lrange(key, 0, -1)
    if not raw_messages:
        raise HTTPException(status_code=404, detail="session_id 不存在")
    messages = []
    for item in raw_messages:
        try:
            messages.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            continue
    return SessionResponse(session_id=session_id, messages=messages)


@router.delete("/history/{session_id}")
async def clear_history(session_id: str, redis: Redis = Depends(get_redis_client)):
    if not _SAFE_SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="session_id 格式非法")
    key = f"chat:session:{session_id}"
    deleted = await redis.delete(key)
    return {"ok": True, "session_id": session_id, "deleted": bool(deleted)}
