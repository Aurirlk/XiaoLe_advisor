from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import (
    get_conversation_turn_store,
    get_feedback_analyzer_callback,
    get_feedback_store,
)
from core.conversation_turn_store import ConversationTurnStore
from core.feedback_store import FeedbackRecord, FeedbackStore

router = APIRouter(prefix="/feedback", tags=["feedback"])

FEEDBACK_TAGS = ["数据不准", "建议没用", "太端水", "没回答我的问题", "路由错了"]


class FeedbackRequest(BaseModel):
    turn_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=-1, le=1)
    tags: List[str] = Field(default_factory=list)
    comment: str = ""


class FeedbackResponse(BaseModel):
    ok: bool
    feedback_id: int
    turn_id: str


class FeedbackStatsResponse(BaseModel):
    ok: bool
    stats: dict


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    store: FeedbackStore = Depends(get_feedback_store),
    turn_store: ConversationTurnStore = Depends(get_conversation_turn_store),
    on_negative=Depends(get_feedback_analyzer_callback),
):
    turn = await turn_store.get_turn(payload.turn_id)
    if not turn:
        raise HTTPException(status_code=404, detail="turn_id 不存在")

    record = FeedbackRecord(
        turn_id=payload.turn_id,
        session_id=turn["session_id"],
        rating=payload.rating,
        tags=payload.tags,
        comment=payload.comment,
    )
    feedback_id = await store.save_feedback(record)

    if payload.rating == -1:
        await on_negative(
            turn_id=payload.turn_id,
            query=turn.get("user_query", ""),
            bad_answer=turn.get("assistant_response", ""),
            tags=payload.tags,
        )

    return FeedbackResponse(ok=True, feedback_id=feedback_id, turn_id=payload.turn_id)


@router.get("/stats", response_model=FeedbackStatsResponse)
async def feedback_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    store: FeedbackStore = Depends(get_feedback_store),
):
    stats = await store.get_stats(days=days)
    return FeedbackStatsResponse(ok=True, stats=stats)


@router.get("/turns/{turn_id}")
async def get_turn_with_feedback(
    turn_id: str,
    turn_store: ConversationTurnStore = Depends(get_conversation_turn_store),
    store: FeedbackStore = Depends(get_feedback_store),
):
    turn = await turn_store.get_turn(turn_id)
    if not turn:
        raise HTTPException(status_code=404, detail="turn_id 不存在")
    feedback = await store.get_feedback(turn_id)
    return {"ok": True, "turn": turn, "feedback": feedback}


@router.get("/tags")
async def list_feedback_tags():
    return {"ok": True, "tags": FEEDBACK_TAGS}
