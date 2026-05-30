"""
综合防幻觉穿透测试
覆盖: 全局异常处理器 / 状态污染 / 越权注入 / 系统兜底
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from core.exception_handler import FALLBACK_MESSAGE, safe_node_call

ROOT = Path(__file__).resolve().parents[1]
EDGE_PATH = ROOT / "data" / "eval" / "skills_edge_cases.json"


# ============================================================
# safe_node_call 防穿透测试
# ============================================================

class TestSafeNodeCall:

    def test_sync_function_ok(self):
        def ok_node(state):
            return {"result": state.get("x", 0)}
        result = asyncio.run(safe_node_call(ok_node, {"x": 42}))
        assert result == {"result": 42}

    def test_sync_function_crash(self):
        def crash_node(_state):
            raise RuntimeError("测试异常")
        result = asyncio.run(safe_node_call(crash_node, {}))
        assert result["error"] == FALLBACK_MESSAGE
        assert result["next_node"] == "synthesis_agent"

    def test_async_function_ok(self):
        async def ok_node(state):
            return {"ok": True, "value": state.get("v")}
        result = asyncio.run(safe_node_call(ok_node, {"v": "hello"}))
        assert result == {"ok": True, "value": "hello"}

    def test_async_function_crash(self):
        async def crash_node(_state):
            raise ValueError("async boom")
        result = asyncio.run(safe_node_call(crash_node, {}))
        assert result["error"] == FALLBACK_MESSAGE
        assert result["next_node"] == "synthesis_agent"

    def test_sync_function_returns_none(self):
        def none_node(_state):
            return None
        result = asyncio.run(safe_node_call(none_node, {}))
        assert result is None

    def test_sync_function_returns_non_dict(self):
        def int_node(_state):
            return 42
        result = asyncio.run(safe_node_call(int_node, {}))
        assert result == 42

    def test_function_with_zero_division(self):
        def div_node(_state):
            return {"value": 1 / 0}
        result = asyncio.run(safe_node_call(div_node, {}))
        assert result["error"] == FALLBACK_MESSAGE
        assert result["next_node"] == "synthesis_agent"

    def test_function_with_recursion(self):
        def recurse_node(_state):
            def inner():
                return inner()
            return inner()
        result = asyncio.run(safe_node_call(recurse_node, {}))
        assert result["error"] == FALLBACK_MESSAGE
        assert result["next_node"] == "synthesis_agent"

    def test_all_errors_route_to_synthesis(self):
        """任何异常都必须将 next_node 设为 synthesis_agent，避免流程死锁"""
        error_types = [
            (lambda _: 1 / 0, "ZeroDivisionError"),
            (lambda _: {}["missing"], "KeyError"),
            (lambda _: int("abc"), "ValueError"),
            (lambda _: [][0], "IndexError"),
        ]
        for node, label in error_types:
            result = asyncio.run(safe_node_call(node, {}))
            assert result["next_node"] == "synthesis_agent", f"{label}: next_node 应兜底"
            assert result["error"] == FALLBACK_MESSAGE, f"{label}: error 应为兜底消息"

    def test_fallback_message_not_empty(self):
        assert len(FALLBACK_MESSAGE) > 10, "兜底消息不应为空"


# ============================================================
# 状态污染防穿透测试
# ============================================================

class TestStatePollution:

    def test_state_with_injection_in_query(self):
        """user_query 含注入不应污染其他状态字段"""
        async def node(state):
            return {"safe_field": state.get("user_query", "")[:10]}

        state = {
            "user_query": "DROP TABLE users; -- malicious",
            "user_profile": {"province": "test"},
        }
        result = asyncio.run(safe_node_call(node, state))
        assert "error" not in result
        assert result.get("safe_field") == "DROP TABLE"

    def test_state_with_null_bytes(self):
        async def node(state):
            return {"clean": state.get("user_query", "").replace("\x00", "")}

        state = {"user_query": "query\x00with\x00nulls"}
        result = asyncio.run(safe_node_call(node, state))
        assert "\x00" not in result["clean"]

    def test_state_with_unicode_overflow(self):
        async def node(state):
            return {"length": len(state.get("user_query", ""))}
        huge = "🎓" * 10000
        state = {"user_query": huge}
        result = asyncio.run(safe_node_call(node, state))
        assert result["length"] == 10000

    def test_state_with_malformed_unicode(self):
        async def node(state):
            return {"len": len(state.get("user_query", ""))}
        state = {"user_query": b"\x80\x81\x82".decode("utf-8", errors="replace")}
        result = asyncio.run(safe_node_call(node, state))
        assert "error" not in result


# ============================================================
# Skills 跨模块防穿透集成测试
# ============================================================

class TestSkillIntegrationAntiHallucination:

    def test_risk_assessor_never_crashes_on_garbage(self):
        """无论什么垃圾输入，risk_assessor 不能崩溃"""
        garbage_inputs = [
            {"major": "", "tier": ""},
            {"major": None, "tier": None},
            {"major": "x" * 10000, "tier": "y" * 10000},
            {"major": "\x00\x00", "tier": "\x00"},
        ]
        from skills.risk_assessor import assess_major_risk
        for inp in garbage_inputs:
            r = assess_major_risk(inp["major"], inp["tier"])
            assert isinstance(r, dict), f"输入 {inp} 应返回 dict"
            assert "is_risk" in r
            assert "risk_level" in r

    def test_reality_checker_never_crashes_on_garbage(self):
        """边界值输入不崩溃"""
        from skills.reality_checker import check_expectation_gap
        garbage = [
            (10**10, 10**10),
            (-10**10, -10**10),
            (0, 0),
            (10**100, 1),
        ]
        for us, ts in garbage:
            r = check_expectation_gap(us, ts)
            assert "is_realistic" in r

    def test_roi_calculator_never_crashes_on_garbage(self):
        from skills.roi_calculator import calculate_roi
        garbage = [
            (-1, -1, -1),
            (0, 0, 0),
            (10**10, 10**10, 10**10),
        ]
        for args in garbage:
            r = calculate_roi(*args)
            assert "total_cost" in r
            assert "roi_ratio" in r

    def test_decision_heuristics_never_crashes_on_none(self):
        from skills.decision_heuristics import (
            build_soul_questions,
            city_priority_hint,
            ten_year_pressure_test,
            summarize_decision_hints,
        )
        build_soul_questions(None)  # type: ignore
        city_priority_hint(None)    # type: ignore
        ten_year_pressure_test(None)  # type: ignore
        r = summarize_decision_hints(None)  # type: ignore
        assert isinstance(r, dict)

    def test_decision_heuristics_never_crashes_on_garbage_keys(self):
        """profile 含随机字段不应崩溃"""
        from skills.decision_heuristics import summarize_decision_hints
        profile = {
            "INJECTION": "DROP ALL",
            "\x00key": "\x00value",
            "nested": {"deep": {"very_deep": "value"}},
            "score": "not_a_number",
            "budget": None,
        }
        r = summarize_decision_hints(profile)
        assert isinstance(r, dict)
        assert "soul_questions" in r
        assert "hints" in r


# ============================================================
# GraphState 状态安全测试
# ============================================================

class TestGraphStateSafety:

    def test_state_next_node_only_allowed_values(self):
        """确保 next_node 只能是预定义路由值"""
        from core.state_schema import AllowedNode
        allowed = set(AllowedNode.__args__)  # type: ignore[attr-defined]
        assert "supervisor_agent" in allowed
        assert "synthesis_agent" in allowed
        assert "END" in allowed
        assert len(allowed) >= 7, f"至少 7 个节点, got {len(allowed)}"

    def test_state_schema_fields_exist(self):
        """核心 state 字段完整"""
        from core.state_schema import GraphState
        annotations = GraphState.__annotations__
        required = [
            "messages", "user_query", "user_profile",
            "extracted_score", "extracted_rank", "sql_results",
            "career_context", "web_search_results",
            "risk_assessment", "reality_check", "decision_hints",
            "missing_profile_fields", "next_node", "error",
        ]
        for field in required:
            assert field in annotations, f"GraphState 缺少字段: {field}"
