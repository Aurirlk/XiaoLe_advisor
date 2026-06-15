from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from core.conversation_turn_store import ConversationTurnStore
from core.feedback_store import FeedbackRecord, FeedbackStore
from scripts.init_sqlite import init_sqlite
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def stores():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    init_sqlite(db_path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    yield ConversationTurnStore(engine), FeedbackStore(engine), engine, db_path

    async def _dispose():
        await engine.dispose()

    asyncio.run(_dispose())
    db_path.unlink(missing_ok=True)


def test_feedback_save_and_stats(stores):
    turn_store, feedback_store, _, _ = stores

    async def _run():
        await turn_store.ensure_tables()
        await feedback_store.ensure_tables()
        await turn_store.save_turn(
            turn_id="t1",
            session_id="s1",
            user_query="q",
            assistant_response="a",
            route_path=["match_agent"],
        )
        fid = await feedback_store.save_feedback(
            FeedbackRecord(turn_id="t1", session_id="s1", rating=1, tags=[])
        )
        assert fid > 0
        stats = await feedback_store.get_stats(days=30)
        assert stats["feedback_count"] == 1
        assert stats["positive_count"] == 1

    asyncio.run(_run())


def test_negative_feedback_tags(stores):
    turn_store, feedback_store, _, _ = stores

    async def _run():
        await turn_store.ensure_tables()
        await feedback_store.ensure_tables()
        await turn_store.save_turn(
            turn_id="t2",
            session_id="s2",
            user_query="q2",
            assistant_response="a2",
            route_path=["synthesis_agent"],
        )
        await feedback_store.save_feedback(
            FeedbackRecord(
                turn_id="t2",
                session_id="s2",
                rating=-1,
                tags=["太端水"],
            )
        )
        tags = await feedback_store.get_session_negative_tags("s2")
        assert "太端水" in tags

    asyncio.run(_run())
