"""
多轮对话状态继承、覆盖与回溯测试
验证 Checkpoint + Profile Merge + 变更追踪
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Any, Dict

import pytest

from agents.workers.profile_agent import _extract_from_query, _merge_profile, profile_agent
from core.checkpoint_manager import CheckpointManager
from core.state_schema import ProfileChange

ROOT = Path(__file__).resolve().parents[1]

# ============================================================
# Profile 合并策略单元测试 (无 LLM 依赖)
# ============================================================

class TestProfileMerge:

    def test_merge_new_field_added(self):
        new = {"target_city": "北京"}
        existing = {"province": "广东省"}
        merged, changes = _merge_profile(new, existing, "去北京发展怎么样")
        assert merged["target_city"] == "北京"
        assert merged["province"] == "广东省"
        assert len(changes) == 1
        assert changes[0].get("field") == "target_city"

    def test_merge_override_existing(self):
        """用户反悔：北京 → 成都"""
        new = {"target_city": "成都"}
        existing = {"target_city": "北京", "province": "广东省"}
        merged, changes = _merge_profile(new, existing, "改去成都怎么样")
        assert merged["target_city"] == "成都"
        assert len(changes) == 1
        assert changes[0]["old_value"] == "北京"
        assert changes[0]["new_value"] == "成都"

    def test_merge_same_value_no_change(self):
        new = {"target_city": "北京"}
        existing = {"target_city": "北京"}
        merged, changes = _merge_profile(new, existing, "还是北京")
        assert merged["target_city"] == "北京"
        assert len(changes) == 0

    def test_merge_ignores_underscore_keys(self):
        new = {"_extracted_score": 600, "score": 600}
        existing = {}
        merged, changes = _merge_profile(new, existing, "600分")
        assert merged["score"] == 600
        assert "_extracted_score" not in merged
        assert len(changes) == 1
        assert changes[0]["field"] == "score"

    def test_merge_multiple_overrides(self):
        """一次覆盖多个字段"""
        new = {"target_city": "杭州", "budget": 200000}
        existing = {"target_city": "北京", "budget": 100000, "province": "浙江"}
        merged, changes = _merge_profile(new, existing, "去杭州预算20万")
        assert merged["target_city"] == "杭州"
        assert merged["budget"] == 200000
        assert len(changes) == 2

    def test_change_record_has_all_fields(self):
        new = {"target_city": "上海"}
        existing = {"target_city": "深圳"}
        _, changes = _merge_profile(new, existing, "去上海")
        assert len(changes) == 1
        c = changes[0]
        assert c["field"] == "target_city"
        assert c["old_value"] == "深圳"
        assert c["new_value"] == "上海"
        assert "ts" in c
        assert c["trigger_query"] == "去上海"


# ============================================================
# Query 提取单元测试
# ============================================================

class TestQueryExtraction:

    def test_extract_score(self):
        r = _extract_from_query("我考了600分")
        assert r["score"] == 600

    def test_extract_rank(self):
        r = _extract_from_query("位次: 15000")
        assert r["rank"] == 15000

    def test_extract_city_with_override(self):
        """识别"改去成都"这种反悔表述"""
        r = _extract_from_query("改去成都怎么样")
        assert r["target_city"] == "成都"

    def test_extract_city_with_change(self):
        r = _extract_from_query("换到杭州发展")
        assert r["target_city"] == "杭州"

    def test_extract_city_standard(self):
        r = _extract_from_query("去深圳就业好还是广州")
        assert r.get("target_city") == "深圳"  # 先匹配

    def test_extract_budget_wan(self):
        r = _extract_from_query("预算15万")
        assert r["budget"] == 150000

    def test_extract_budget_qian(self):
        r = _extract_from_query("一年花费5千")
        assert r["budget"] == 5000

    def test_extract_province(self):
        r = _extract_from_query("我是广东的考生")
        assert r["province"] == "广东省"

    def test_extract_subject_physics(self):
        r = _extract_from_query("我选的是物理")
        assert r["subject_type"] == "物理类"

    def test_extract_subject_history(self):
        r = _extract_from_query("历史类考生")
        assert r["subject_type"] == "历史类"

    def test_extract_major(self):
        r = _extract_from_query("想学计算机科学与技术")
        assert r["major_name"] == "计算机科学与技术"

    def test_extract_postgraduate_yes(self):
        r = _extract_from_query("我能接受读研")
        assert r["postgraduate_plan"] == "yes"

    def test_extract_postgraduate_no(self):
        r = _extract_from_query("我不打算考研")
        assert r["postgraduate_plan"] == "no"


# ============================================================
# Profile Agent 多轮对话集成测试
# ============================================================

class TestProfileAgentMultiTurn:

    def test_first_turn_builds_partial_profile(self):
        state: dict = {"user_query": "我广东的，物理类，想学计算机，600分", "user_profile": {}}
        result = profile_agent(state)
        profile = result.get("user_profile", {})
        assert profile["province"] == "广东省"
        assert profile["subject_type"] == "物理类"
        assert profile["major_name"] == "计算机科学与技术"
        assert profile["score"] == 600
        assert result.get("next_node") == "supervisor_agent"

    def test_first_turn_missing_profile(self):
        state: dict = {"user_query": "我就600分", "user_profile": {}}
        result = profile_agent(state)
        assert "province" in result.get("missing_profile_fields", [])
        assert result.get("next_node") == "synthesis_agent"

    def test_second_turn_overrides_city(self):
        """Turn 1: 北京 → Turn 2: 成都"""
        turn1_state: dict = {"user_query": "去北京发展", "user_profile": {}}
        r1 = profile_agent(turn1_state)
        assert r1["user_profile"].get("target_city") == "北京"

        turn2_state: dict = {
            "user_query": "改去成都怎么样",
            "user_profile": r1["user_profile"],
            "profile_history": r1.get("profile_history", []),
        }
        r2 = profile_agent(turn2_state)
        assert r2["user_profile"].get("target_city") == "成都"
        # 应有变更记录
        history = r2.get("profile_history", [])
        assert len(history) == 2  # turn1 新增 + turn2 覆盖

    def test_third_turn_accumulates(self):
        """3 轮累积构建完整画像，验证不丢失之前的信息"""
        history: list = []
        profile: dict = {}

        # Turn 1
        r = profile_agent({"user_query": "我广东的", "user_profile": profile, "profile_history": history})
        profile = r["user_profile"]
        history = r.get("profile_history", [])
        assert profile["province"] == "广东省"

        # Turn 2
        r = profile_agent({"user_query": "物理类", "user_profile": profile, "profile_history": history})
        profile = r["user_profile"]
        history = r.get("profile_history", [])
        assert profile["province"] == "广东省"  # 保留
        assert profile["subject_type"] == "物理类"  # 新增

        # Turn 3
        r = profile_agent({"user_query": "想学计算机，去深圳", "user_profile": profile, "profile_history": history})
        profile = r["user_profile"]
        history = r.get("profile_history", [])
        assert profile["province"] == "广东省"
        assert profile["subject_type"] == "物理类"
        assert profile["major_name"] == "计算机科学与技术"
        assert profile["target_city"] == "深圳"

    def test_override_province(self):
        """用户改省份"""
        state: dict = {"user_query": "不对，我是河南的", "user_profile": {"province": "广东省"}}
        r = profile_agent(state)
        assert r["user_profile"]["province"] == "河南省"
        history = r.get("profile_history", [])
        assert any(h["field"] == "province" for h in history)

    def test_override_major(self):
        """用户改专业"""
        state: dict = {
            "user_query": "算了不学计算机了，换软件工程",
            "user_profile": {
                "province": "广东省", "subject_type": "物理类", "major_name": "计算机科学与技术",
            },
        }
        r = profile_agent(state)
        assert r["user_profile"]["major_name"] == "软件工程"
        history = r.get("profile_history", [])
        assert any(h.get("field") == "major_name" for h in history)

    def test_change_tracking_complete(self):
        """多次更改应完整记录"""
        profile: dict = {}
        history: list = []

        turns = ["去北京发展", "改去上海发展", "还是深圳吧"]
        for q in turns:
            r = profile_agent({"user_query": q, "user_profile": profile, "profile_history": history})
            profile = r["user_profile"]
            history = r.get("profile_history", [])

        assert len(history) == 3
        values = [h["new_value"] for h in history if h["field"] == "target_city"]
        assert values == ["北京", "上海", "深圳"]


# ============================================================
# Checkpoint Manager 单元测试
# ============================================================

class TestCheckpointManager:

    def test_memory_saver_creates(self):
        cm = CheckpointManager(backend="memory")
        saver = cm.get_saver()
        assert saver is not None

    def test_build_config_thread_isolation(self):
        cm = CheckpointManager()
        c1 = cm.build_config("session_A")
        c2 = cm.build_config("session_B")
        assert c1["configurable"]["thread_id"] == "session_A"
        assert c2["configurable"]["thread_id"] == "session_B"
        assert c1["configurable"]["thread_id"] != c2["configurable"]["thread_id"]

    def test_build_init_state(self):
        cm = CheckpointManager()
        state = cm.build_init_state("你好", session_id="s1")
        assert state["user_query"] == "你好"
        assert state["session_id"] == "s1"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"
        assert state["messages"][0]["content"] == "你好"


# ============================================================
# LangGraph Checkpoint 端到端测试 (需要 LLM API)
# ============================================================

LLM_AVAILABLE = bool(os.getenv("DEEPSEEK_API_KEY"))
if not LLM_AVAILABLE:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    LLM_AVAILABLE = bool(os.getenv("DEEPSEEK_API_KEY"))


@pytest.mark.skipif(not LLM_AVAILABLE, reason="DEEPSEEK_API_KEY 未设置")
class TestCheckpointE2E:

    def _load_llm(self):
        import os
        import yaml
        from langchain_openai import ChatOpenAI

        with open(ROOT / "configs" / "llm_config.yaml", "r", encoding="utf-8") as f:
            llm_cfg = yaml.safe_load(f)["llm"]
        return ChatOpenAI(
            model=llm_cfg["model"],
            temperature=0,
            base_url=llm_cfg.get("base_url") or None,
            api_key=os.getenv(llm_cfg["api_key_env"], ""),
            timeout=llm_cfg["timeout_seconds"],
        )

    def test_multi_turn_state_persistence(self):
        """两轮对话验证 state 跨 turn 保持"""
        from api.dependencies import get_db_engine
        from core.graph_builder import build_graph
        from core.checkpoint_manager import CheckpointManager
        from tools.rag_tools import RAGTools

        llm = self._load_llm()
        cm = CheckpointManager(backend="memory")
        graph = build_graph(get_db_engine(), llm, RAGTools(), checkpointer=cm.get_saver())

        session_id = f"test-e2e-{int(time.time())}"

        async def _run():
            # Turn 1: 提供基础画像
            config1 = cm.build_config(session_id)
            state1 = cm.build_init_state("我广东省物理类考生，想学计算机", session_id=session_id)
            result1 = await graph.ainvoke(state1, config=config1)
            p1 = result1.get("user_profile", {})
            assert p1.get("province") == "广东省", f"Turn1 应提取省份, got {p1}"
            assert p1.get("subject_type") == "物理类"

            # Turn 2: 追问，profile 应继承 Turn1
            config2 = cm.build_config(session_id)
            state2 = cm.build_init_state("600分能上什么学校", session_id=session_id)
            result2 = await graph.ainvoke(state2, config=config2)
            p2 = result2.get("user_profile", {})
            assert p2.get("province") == "广东省", "Turn2 应保留 Turn1 的省份"
            assert p2.get("subject_type") == "物理类", "Turn2 应保留 Turn1 的选科"
            assert p2.get("major_name") == "计算机科学与技术", "Turn2 应保留 Turn1 的专业"

        asyncio.run(_run())

    def test_state_rollback_on_override(self):
        """用户反悔城市：北京 → 成都"""
        from api.dependencies import get_db_engine
        from core.graph_builder import build_graph
        from core.checkpoint_manager import CheckpointManager
        from tools.rag_tools import RAGTools

        llm = self._load_llm()
        cm = CheckpointManager(backend="memory")
        graph = build_graph(get_db_engine(), llm, RAGTools(), checkpointer=cm.get_saver())

        session_id = f"test-rollback-{int(time.time())}"

        async def _run():
            # Turn 1
            c1 = cm.build_config(session_id)
            s1 = cm.build_init_state("去北京发展", session_id=session_id)
            r1 = await graph.ainvoke(s1, config=c1)
            assert r1.get("user_profile", {}).get("target_city") == "北京"

            # Turn 2: 反悔
            c2 = cm.build_config(session_id)
            s2 = cm.build_init_state("等一下，改去成都吧", session_id=session_id)
            r2 = await graph.ainvoke(s2, config=c2)
            p2 = r2.get("user_profile", {})
            assert p2.get("target_city") == "成都", f"Turn2 应覆盖为成都, got {p2}"
            history = r2.get("profile_history", [])
            city_changes = [h for h in history if h.get("field") == "target_city"]
            assert len(city_changes) >= 2, f"应有至少2条城市变更, got {len(city_changes)}"

        asyncio.run(_run())

    def test_different_sessions_isolated(self):
        """两个 session 的状态互不干扰"""
        from api.dependencies import get_db_engine
        from core.graph_builder import build_graph
        from core.checkpoint_manager import CheckpointManager
        from tools.rag_tools import RAGTools

        llm = self._load_llm()
        cm = CheckpointManager(backend="memory")
        graph = build_graph(get_db_engine(), llm, RAGTools(), checkpointer=cm.get_saver())

        sid_a = f"test-iso-A-{int(time.time())}"
        sid_b = f"test-iso-B-{int(time.time())}"

        async def _run():
            # Session A: 广东 + 计算机
            r_a = await graph.ainvoke(
                cm.build_init_state("广东物理计算机", session_id=sid_a),
                config=cm.build_config(sid_a),
            )
            # Session B: 河南 + 法学
            r_b = await graph.ainvoke(
                cm.build_init_state("河南历史法学", session_id=sid_b),
                config=cm.build_config(sid_b),
            )
            p_a = r_a.get("user_profile", {})
            p_b = r_b.get("user_profile", {})
            assert p_a.get("province") == "广东省"
            assert p_b.get("province") == "河南省"
            assert p_a.get("province") != p_b.get("province"), "两个 session 应完全隔离"

        asyncio.run(_run())
