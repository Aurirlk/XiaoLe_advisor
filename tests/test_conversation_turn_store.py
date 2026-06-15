from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from core.conversation_turn_store import ConversationTurnStore
from scripts.init_sqlite import init_sqlite
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def turn_store():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    init_sqlite(db_path)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    store = ConversationTurnStore(engine)
    yield store, engine, db_path

    async def _dispose():
        await engine.dispose()

    asyncio.run(_dispose())
    db_path.unlink(missing_ok=True)


def test_save_and_get_turn(turn_store):
    store, _, _ = turn_store

    async def _run():
        await store.ensure_tables()
        await store.save_turn(
            turn_id="turn-1",
            session_id="sess-1",
            user_query="测试问题",
            assistant_response="测试回答",
            route_path=["supervisor_agent", "match_agent"],
            user_profile_snapshot={"province": "广东省"},
            sql_hit_count=3,
            risk_level="medium",
        )
        turn = await store.get_turn("turn-1")
        assert turn is not None
        assert turn["user_query"] == "测试问题"
        assert turn["route_path"] == ["supervisor_agent", "match_agent"]

    asyncio.run(_run())
