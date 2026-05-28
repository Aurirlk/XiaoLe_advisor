from __future__ import annotations

import asyncio

from core.exception_handler import FALLBACK_MESSAGE, safe_node_call
from skills.decision_heuristics import (
    build_soul_questions,
    city_priority_hint,
    summarize_decision_hints,
)
from skills.reality_checker import check_expectation_gap
from skills.risk_assessor import assess_major_risk
from skills.roi_calculator import calculate_roi


def test_calculate_roi_basic():
    data = calculate_roi(10000, 4, 50000)
    assert data["total_cost"] == 40000.0
    assert data["roi_ratio"] == 0.8


def test_check_expectation_gap_low_score():
    result = check_expectation_gap(user_score=540, target_min_score=560, tolerance=8)
    assert result["is_realistic"] == "false"


def test_assess_major_risk_high_risk_combo():
    result = assess_major_risk("生物工程", "双非")
    assert result["is_risk"] == "true"
    assert result["risk_level"] == "high"


def test_build_soul_questions_missing_profile_fields():
    questions = build_soul_questions({})
    assert len(questions) >= 5


def test_city_priority_hint_with_city():
    text = city_priority_hint({"target_city": "深圳"})
    assert "深圳" in text


def test_summarize_decision_hints_structure():
    result = summarize_decision_hints({"target_city": "广州"})
    assert "soul_questions" in result
    assert "hints" in result
    assert isinstance(result["hints"], list)


def test_safe_node_call_with_exception():
    def broken_node(_state):
        raise RuntimeError("boom")

    result = asyncio.run(safe_node_call(broken_node, {}))
    assert result["error"] == FALLBACK_MESSAGE
    assert result["next_node"] == "synthesis_agent"


def test_safe_node_call_async():
    async def ok_node(state):
        return {"ok": state.get("x")}

    result = asyncio.run(safe_node_call(ok_node, {"x": 1}))
    assert result == {"ok": 1}
