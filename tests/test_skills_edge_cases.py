"""
技能边缘案例与防穿透评测测试
覆盖: risk_assessor / reality_checker / decision_heuristics / roi_calculator
80+ 边缘案例 × 对抗注入 × 边界值 × 异常输入
"""
from __future__ import annotations

import json
from pathlib import Path

from skills.risk_assessor import assess_major_risk
from skills.reality_checker import check_expectation_gap
from skills.decision_heuristics import (
    build_soul_questions,
    city_priority_hint,
    summarize_decision_hints,
    ten_year_pressure_test,
)
from skills.roi_calculator import calculate_roi

ROOT = Path(__file__).resolve().parents[1]
EDGE_PATH = ROOT / "data" / "eval" / "skills_edge_cases.json"


def load_edge_cases():
    return json.loads(EDGE_PATH.read_text(encoding="utf-8"))


# ============================================================
# risk_assessor 边缘与穿透测试
# ============================================================

class TestRiskAssessorEdgeCases:

    def test_all_golden_cases(self):
        cases = load_edge_cases()["risk_assessor_cases"]
        failures = []
        for c in cases:
            profile = c.get("profile") if c.get("profile") is not None else None
            result = assess_major_risk(c["major"], c["tier"], user_profile=profile)
            if result["is_risk"] != ("true" if c["expect_risk"] else "false"):
                failures.append(
                    f"[{c['id']}] {c['label']}: "
                    f"expected is_risk={'true' if c['expect_risk'] else 'false'}, "
                    f"got {result['is_risk']}"
                )
            if result["risk_level"] != c["expect_risk_level"]:
                failures.append(
                    f"[{c['id']}] {c['label']}: "
                    f"expected risk_level={c['expect_risk_level']}, "
                    f"got {result['risk_level']}"
                )
        assert not failures, f"risk_assessor 失败 {len(failures)} 条:\n" + "\n".join(failures)

    def test_no_false_negative_on_high_risk(self):
        """确保所有高风险组合均被检测（零漏报）"""
        for major in ["生物工程", "化学工程", "环境工程", "材料科学与工程"]:
            for tier in ["双非一本", "211", "二本", "专科", "未知", ""]:
                r = assess_major_risk(major, tier)
                if tier not in ("985", "顶尖211"):
                    assert r["is_risk"] == "true", f"{major}+{tier} 应触发风控"
                    assert r["risk_level"] == "high"

    def test_no_false_positive_on_safe_combos(self):
        """确保安全组合不误报（零误报）"""
        safe_combos = [
            ("计算机科学与技术", "双非一本"),
            ("软件工程", "211"),
            ("法学", "二本"),
            ("金融学", "985"),
            ("临床医学", "985", {"budget": 100000}),
            ("口腔医学", "顶尖211", {"budget": 200000}),
        ]
        for combo in safe_combos:
            if len(combo) == 3:
                major, tier, profile = combo
            else:
                major, tier = combo
                profile = {}
            r = assess_major_risk(major, tier, user_profile=profile)
            assert r["is_risk"] == "false", f"{major}+{tier} 不应触发风控, got {r}"

    def test_medical_risk_budget_boundaries(self):
        """医学风控预算边界精密测试"""
        # 刚好触发 (79999)
        r = assess_major_risk("临床医学", "985", user_profile={"budget": 79999})
        assert r["is_risk"] == "true"
        # 刚好不触发 (80000)
        r = assess_major_risk("临床医学", "985", user_profile={"budget": 80000})
        assert r["is_risk"] == "false"

    def test_profile_is_none(self):
        """profile=None 不应崩溃"""
        r = assess_major_risk("生物工程", "双非一本", user_profile=None)
        assert r["is_risk"] == "true"
        assert r["risk_level"] == "high"

    def test_empty_strings_safe(self):
        """空字符串专业/层次不应崩溃"""
        r = assess_major_risk("", "")
        assert r["is_risk"] == "false"

    def test_output_structure_complete(self):
        """输出结构始终包含所有必要字段"""
        r = assess_major_risk("计算机", "985")
        for key in ["is_risk", "reason", "risk_level", "warnings", "must_say"]:
            assert key in r, f"缺少字段: {key}"

    def test_high_risk_output_has_must_say(self):
        """高风险输出必须包含劝退信息"""
        r = assess_major_risk("生物工程", "双非一本")
        assert len(r["must_say"]) > 0, "高风险必须提供 must_say"


# ============================================================
# reality_checker 边缘测试
# ============================================================

class TestRealityCheckerEdgeCases:

    def test_all_golden_cases(self):
        cases = load_edge_cases()["reality_checker_cases"]
        failures = []
        for c in cases:
            tol = c.get("tolerance", 8)
            result = check_expectation_gap(c["user_score"], c["target_min"], tol)
            if result["is_realistic"] != c["expect"]["is_realistic"]:
                failures.append(
                    f"[{c['id']}] {c['label']}: "
                    f"expected {c['expect']['is_realistic']}, got {result['is_realistic']}"
                )
        assert not failures, f"reality_checker 失败 {len(failures)} 条:\n" + "\n".join(failures)

    def test_boundary_exact_tolerance(self):
        """边界值：-9 失败，-8 通过（gap < -tolerance）"""
        assert check_expectation_gap(591, 600, 8)["is_realistic"] == "false"  # gap=-9 < -8
        assert check_expectation_gap(592, 600, 8)["is_realistic"] == "true"   # gap=-8 >= -8

    def test_boundary_exact_high_warning(self):
        """边界值：35 不警告，36 警告"""
        assert check_expectation_gap(635, 600, 8)["is_realistic"] == "true"
        assert check_expectation_gap(636, 600, 8)["is_realistic"] == "warning"

    def test_default_tolerance(self):
        """默认 tolerance=8"""
        r = check_expectation_gap(590, 600)
        assert r["is_realistic"] == "false"
        r = check_expectation_gap(593, 600)
        assert r["is_realistic"] == "true"

    def test_zero_tolerance(self):
        """tolerance=0 时精确比较"""
        assert check_expectation_gap(599, 600, 0)["is_realistic"] == "false"
        assert check_expectation_gap(600, 600, 0)["is_realistic"] == "true"
        assert check_expectation_gap(601, 600, 0)["is_realistic"] == "true"

    def test_negative_inputs_no_crash(self):
        """负数输入不崩溃"""
        r = check_expectation_gap(-100, 500, 8)
        assert r["is_realistic"] == "false"
        r = check_expectation_gap(500, -100, 8)
        assert r["is_realistic"] == "warning"


# ============================================================
# decision_heuristics 边缘测试
# ============================================================

class TestDecisionHeuristicsEdgeCases:

    def test_all_golden_cases(self):
        cases = load_edge_cases()["decision_heuristics_cases"]
        failures = []
        for c in cases:
            profile = c["profile"]

            if "expect_min_questions" in c:
                qs = build_soul_questions(profile)
                if len(qs) < c["expect_min_questions"]:
                    failures.append(f"[{c['id']}] {c['label']}: questions={len(qs)} < {c['expect_min_questions']}")

            if "expect_questions" in c:
                qs = build_soul_questions(profile)
                if len(qs) != c["expect_questions"]:
                    failures.append(f"[{c['id']}] {c['label']}: expected {c['expect_questions']} questions, got {len(qs)}")

            if "expect_questions_below" in c:
                qs = build_soul_questions(profile)
                if len(qs) >= c["expect_questions_below"]:
                    failures.append(f"[{c['id']}] {c['label']}: expected <{c['expect_questions_below']}, got {len(qs)}")

            if "expect_contains" in c:
                qs = build_soul_questions(profile)
                found = any(c["expect_contains"] in q for q in qs)
                if not found:
                    failures.append(f"[{c['id']}] {c['label']}: question not found: '{c['expect_contains']}'")

            if "expect_not_contains" in c:
                qs = build_soul_questions(profile)
                found = any(c["expect_not_contains"] in q for q in qs)
                if found:
                    failures.append(f"[{c['id']}] {c['label']}: question should NOT contain: '{c['expect_not_contains']}'")

            if "expect_city_hint_contains" in c:
                hint = city_priority_hint(profile)
                if c["expect_city_hint_contains"] not in hint:
                    failures.append(f"[{c['id']}] {c['label']}: city_hint missing '{c['expect_city_hint_contains']}'")

            if "expect_ten_year_contains" in c:
                text = ten_year_pressure_test(profile)
                if c["expect_ten_year_contains"] not in text:
                    failures.append(f"[{c['id']}] {c['label']}: ten_year missing '{c['expect_ten_year_contains']}'")

            if "expect_keys" in c:
                result = summarize_decision_hints(profile)
                for key in c["expect_keys"]:
                    if key not in result:
                        failures.append(f"[{c['id']}] {c['label']}: summarize missing key '{key}'")

        assert not failures, f"decision_heuristics 失败 {len(failures)} 条:\n" + "\n".join(failures)

    def test_empty_profile_generates_at_least_5_questions(self):
        qs = build_soul_questions({})
        assert len(qs) >= 5

    def test_fully_populated_profile_generates_no_questions(self):
        qs = build_soul_questions({
            "province": "广东", "subject_type": "物理类",
            "major_name": "计算机", "score": 600, "rank": 5000,
            "target_city": "深圳", "budget": 100000, "postgraduate_plan": "yes",
        })
        assert len(qs) == 0

    def test_summarize_always_returns_valid_structure(self):
        for profile in [{}, {"province": "A"}, {"target_city": "B"}]:
            r = summarize_decision_hints(profile)
            assert isinstance(r.get("soul_questions"), list)
            assert isinstance(r.get("hints"), list)
            assert len(r["hints"]) == 2
            for h in r["hints"]:
                assert "type" in h
                assert "text" in h

    def test_city_hint_with_none_value(self):
        """city 为 None 时的降级输出"""
        hint = city_priority_hint({"target_city": None})
        assert "能去更强的城市就别自我感动" in hint

    def test_ten_year_with_empty_profile(self):
        text = ten_year_pressure_test({})
        assert "你想去的城市" in text


# ============================================================
# roi_calculator 边缘测试
# ============================================================

class TestROICalculatorEdgeCases:

    def test_all_golden_cases(self):
        cases = load_edge_cases()["roi_calculator_cases"]
        failures = []
        for c in cases:
            r = calculate_roi(c["tuition"], c["years"], c["salary"])
            if abs(r["total_cost"] - c["expect_total"]) > 0.01:
                failures.append(f"[{c['id']}] {c['label']}: total_cost {r['total_cost']} != {c['expect_total']}")
            if abs(r["roi_ratio"] - c["expect_ratio"]) > 0.01:
                failures.append(f"[{c['id']}] {c['label']}: roi_ratio {r['roi_ratio']} != {c['expect_ratio']}")
        assert not failures, f"roi_calculator 失败 {len(failures)} 条:\n" + "\n".join(failures)

    def test_zero_salary_returns_negative_one(self):
        r = calculate_roi(10000, 4, 0)
        assert r["roi_ratio"] == -1.0

    def test_negative_salary_returns_negative_one(self):
        r = calculate_roi(10000, 4, -5000)
        assert r["roi_ratio"] == -1.0

    def test_zero_tuition_zero_years(self):
        r = calculate_roi(0, 0, 10000)
        assert r["total_cost"] == 0.0
        assert r["roi_ratio"] == 0.0

    def test_output_is_always_dict_with_required_keys(self):
        for args in [(0, 0, 0), (-1, -1, -1), (99999, 99, 99999)]:
            r = calculate_roi(*args)
            assert "total_cost" in r
            assert "roi_ratio" in r
