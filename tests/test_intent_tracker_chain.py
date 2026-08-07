"""
intent_tracker 写入链路测试（P1-9 修复回归）

背景：log_intent/log_decision_journey 此前零调用方（写入链路断裂）。
本测试覆盖：表创建 → 意图落库 → 场景历史 → 犹豫模式 → 决策旅程 全链路，
防止断链回归。
"""
from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sqlite_engine(tmp_path):
    """临时 SQLite 引擎（每个测试独立库）"""
    from sqlalchemy.ext.asyncio import create_async_engine

    db_path = tmp_path / "intent_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
def tracker(sqlite_engine):
    from core.intent_tracker import IntentTracker

    return IntentTracker(sqlite_engine)


async def test_ensure_tables_creates_intent_schema(tracker):
    """建表后存在 user_intent_log 与 user_decision_journey"""
    from sqlalchemy import text

    await tracker.ensure_tables()
    engine = tracker._engine
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        names = {r[0] for r in rows.fetchall()}
    assert "user_intent_log" in names
    assert "user_decision_journey" in names


async def test_log_intent_write_chain(tracker):
    """log_intent 写入后可被 get_scene_history 读回（断链回归测试）"""
    await tracker.ensure_tables()
    await tracker.log_intent(
        phone="13800000001",
        session="sess-intent-1",
        turn=2,
        scene="gaokao",
        scene_conf=0.9,
        path="employment",
        path_conf=0.8,
        decision="hesitant",
        signals=["纠结", "迷茫"],
        query="我到底该不该学医",
        response="先看家庭预算再决定",
    )
    history = await tracker.get_scene_history("13800000001")
    assert len(history) == 1
    row = history[0]
    assert row["scene_type"] == "gaokao"
    assert row["path_type"] == "employment"
    assert row["decision_state"] == "hesitant"


async def test_log_intent_anonymous_phone(tracker):
    """匿名用户（空 phone 兜底为 anonymous）也应可落库"""
    await tracker.ensure_tables()
    await tracker.log_intent(
        phone="anonymous",
        session="sess-anon",
        turn=0,
        scene="career",
        scene_conf=0.7,
    )
    history = await tracker.get_scene_history("anonymous")
    assert len(history) == 1
    assert history[0]["scene_type"] == "career"


async def test_detect_hesitation_pattern(tracker):
    """犹豫模式检测：chronic_hesitator 需要在多轮数据下命中"""
    await tracker.ensure_tables()
    # 写入 4 轮，超过半数（>50%）decision_state=hesitant → chronic_hesitator
    for i in range(4):
        await tracker.log_intent(
            phone="13800000002",
            session=f"sess-{i}",
            turn=i,
            scene="gaokao",
            scene_conf=0.8,
            decision="hesitant" if i < 3 else "firm",
        )
    pattern = await tracker.detect_hesitation_pattern("13800000002")
    assert pattern["pattern"] == "chronic_hesitator"
    assert pattern["confidence"] > 0.5


async def test_detect_hesitation_new_user(tracker):
    """新用户（不足 3 条）→ new_user"""
    await tracker.ensure_tables()
    await tracker.log_intent(phone="13800000003", session="s", turn=0,
                             scene="gaokao", scene_conf=0.5)
    pattern = await tracker.detect_hesitation_pattern("13800000003")
    assert pattern["pattern"] == "new_user"


async def test_decision_journey_write_read(tracker):
    """决策旅程写入与读取"""
    await tracker.ensure_tables()
    await tracker.log_decision_journey(
        phone="13800000004",
        session="sess-journey",
        stage="gaokao",
        milestone="decision_detector",
        data={"route": "decision_detector", "decision_state": "hesitant"},
    )
    journey = await tracker.get_user_journey("13800000004")
    assert len(journey) == 1
    assert journey[0]["milestone"] == "decision_detector"
    assert journey[0]["journey_stage"] == "gaokao"


async def test_similar_decisions_grouping(tracker):
    """get_similar_decisions 关联 user_profiles 聚合"""
    from sqlalchemy import text

    await tracker.ensure_tables()
    # 直接建 user_profiles（DDL 来自 crm_manager，复用测试最小化）
    engine = tracker._engine
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                phone_number TEXT PRIMARY KEY,
                province TEXT, score INTEGER, subject_type TEXT
            )
        """))
        await conn.execute(text(
            "INSERT INTO user_profiles VALUES ('13800000005', '广东省', 600, '物理类')"
        ))
    await tracker.log_intent(
        phone="13800000005", session="s", turn=0,
        scene="gaokao", scene_conf=0.9,
        path="postgrad", decision="firm",
    )
    similar = await tracker.get_similar_decisions(
        {"province": "广东省", "score": 610, "subject_type": "物理类"},
        scene="gaokao",
    )
    assert len(similar) >= 1
    assert similar[0]["path_type"] == "postgrad"
