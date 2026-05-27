from datetime import datetime, timezone
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from api.dependencies import get_redis_client

router = APIRouter(prefix="/chat", tags=["chat"])
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., min_length=1, description="用户消息")


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
    key = f"chat:session:{session_id}"
    raw_messages = await redis.lrange(key, 0, -1)
    if not raw_messages:
        raise HTTPException(status_code=404, detail="session_id 不存在")
    messages = [json.loads(item) for item in raw_messages]
    return SessionResponse(session_id=session_id, messages=messages)


@router.delete("/history/{session_id}")
async def clear_history(session_id: str, redis: Redis = Depends(get_redis_client)):
    key = f"chat:session:{session_id}"
    deleted = await redis.delete(key)
    return {"ok": True, "session_id": session_id, "deleted": bool(deleted)}
