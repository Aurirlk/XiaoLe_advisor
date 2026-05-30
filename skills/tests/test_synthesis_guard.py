"""
SynthesisGuard 防端水约束引擎测试
覆盖: 信号检测 / prompt 注入 / 输出校验 / 强制修正 / 无信号不干扰
"""
from __future__ import annotations

from core.synthesis_guard import RiskSignal, SynthesisGuard


# ============================================================
# RiskSignal 数据结构测试
# ============================================================

class TestRiskSignal:

    def test_high_risk_is_critical(self):
        s = RiskSignal(level="high", category="risk", must_say="test")
        assert s.is_critical is True

    def test_low_risk_not_critical(self):
        s = RiskSignal(level="low", category="risk", must_say="")
        assert s.is_critical is False

    def test_reality_fail_is_critical(self):
        s = RiskSignal(level="low", category="reality_fail", must_say="test")
        assert s.is_critical is True

    def test_merge_identity_unique(self):
        a = RiskSignal(level="high", category="risk", must_say="A")
        b = RiskSignal(level="high", category="risk", must_say="B")
        assert a.merge_identity != b.merge_identity


# ============================================================
# 信号检测测试
# ============================================================

class TestDetectSignals:

    def test_empty_state_returns_empty(self):
        r = SynthesisGuard.detect_signals({})
        assert r == []

    def test_risk_false_not_detected(self):
        state = {"risk_assessment": {"is_risk": "false", "risk_level": "low"}}
        r = SynthesisGuard.detect_signals(state)
        assert r == []

    def test_risk_true_detected(self):
        state = {
            "risk_assessment": {
                "is_risk": "true",
                "risk_level": "high",
                "must_say": "别上头",
                "reason": "生化环材",
                "warnings": ["警告1"],
            }
        }
        r = SynthesisGuard.detect_signals(state)
        assert len(r) == 1
        assert r[0].category == "risk"
        assert r[0].level == "high"
        assert r[0].must_say == "别上头"
        assert r[0].is_critical is True

    def test_reality_fail_detected(self):
        state = {"reality_check": {"is_realistic": "false", "reason": "分数差距过大"}}
        r = SynthesisGuard.detect_signals(state)
        assert len(r) == 1
        assert r[0].category == "reality_fail"
        assert r[0].is_critical is True
        assert "分数差距过大" in r[0].must_say

    def test_reality_warning_not_filtered_as_critical(self):
        """is_realistic='warning' 不应被当作 critical 信号"""
        state = {"reality_check": {"is_realistic": "warning", "reason": "高分低报"}}
        r = SynthesisGuard.detect_signals(state)
        assert len(r) == 0

    def test_reality_true_not_detected(self):
        state = {"reality_check": {"is_realistic": "true", "reason": "匹配"}}
        r = SynthesisGuard.detect_signals(state)
        assert r == []

    def test_both_risk_and_reality_detected(self):
        state = {
            "risk_assessment": {"is_risk": "true", "risk_level": "high", "must_say": "劝退"},
            "reality_check": {"is_realistic": "false", "reason": "分太低"},
        }
        r = SynthesisGuard.detect_signals(state)
        assert len(r) == 2

    def test_critical_signals_sorted_first(self):
        state = {
            "risk_assessment": {"is_risk": "true", "risk_level": "low", "must_say": "低风险"},
            "reality_check": {"is_realistic": "false", "reason": "分差"},
        }
        r = SynthesisGuard.detect_signals(state)
        assert r[0].is_critical is True

    def test_risk_assessment_missing_key(self):
        state = {"risk_assessment": {}}
        r = SynthesisGuard.detect_signals(state)
        assert r == []

    def test_risk_assessment_none(self):
        state = {"risk_assessment": None}
        r = SynthesisGuard.detect_signals(state)
        assert r == []

    def test_reality_check_not_dict(self):
        state = {"reality_check": "not a dict"}
        r = SynthesisGuard.detect_signals(state)
        assert r == []


# ============================================================
# Prompt 注入测试
# ============================================================

class TestBuildGuardPrompt:

    def test_no_signals_returns_empty(self):
        r = SynthesisGuard.build_guard_prompt([])
        assert r == ""

    def test_critical_signal_generates_prompt(self):
        sig = RiskSignal(level="high", category="risk", must_say="绝对不能报", reason="生化环材")
        r = SynthesisGuard.build_guard_prompt([sig])
        assert "绝对不能报" in r
        assert "生化环材" in r
        assert "硬性约束" in r
        assert "端水" in r

    def test_prompt_contains_five_mandatory_rules(self):
        sig = RiskSignal(level="high", category="risk", must_say="test")
        r = SynthesisGuard.build_guard_prompt([sig])
        assert "1." in r and "5." in r, "必须包含 5 条输出硬性要求"

    def test_prompt_forbids_water_keywords(self):
        sig = RiskSignal(level="high", category="risk", must_say="test")
        r = SynthesisGuard.build_guard_prompt([sig])
        assert "各有利弊" in r
        assert "综合考量" in r

    def test_prompt_requires_deterministic_words(self):
        sig = RiskSignal(level="high", category="risk", must_say="test")
        r = SynthesisGuard.build_guard_prompt([sig])
        assert "绝对不能" in r

    def test_non_critical_signals_no_prompt(self):
        sig = RiskSignal(level="low", category="risk", must_say="")
        r = SynthesisGuard.build_guard_prompt([sig])
        assert r == ""


# ============================================================
# 输出校验测试
# ============================================================

class TestValidateOutput:

    def test_passes_when_must_say_present(self):
        sig = RiskSignal(level="high", category="risk", must_say="绝对不能报")
        output = "⚠️ 风控警告：绝对不能报。你的分数远低于目标线。"
        ok, _, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is True
        assert failures == []

    def test_fails_when_must_say_missing(self):
        sig = RiskSignal(level="high", category="risk", must_say="绝对不能报")
        output = "我建议你再慎重考虑一下这个选择。"
        ok, _, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is False
        assert any("缺失" in f for f in failures)

    def test_corrects_output_when_validation_fails(self):
        sig = RiskSignal(level="high", category="risk", must_say="强制劝退文本")
        output = "你可以考虑其他专业。"
        ok, corrected, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is False
        assert "强制劝退文本" in corrected
        assert "系统风控引擎强制拦截" in corrected
        assert "你可以考虑其他专业" in corrected

    def test_detects_water_keywords(self):
        sig = RiskSignal(level="high", category="risk", must_say="务必谨慎")
        output = "务必谨慎。但是换个角度，各有利弊。"
        ok, _, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is False
        assert any("端水" in f or "各有利弊" in f for f in failures)

    def test_detects_risk_buried_deep_in_output(self):
        """风险藏在 500 字符之后 → 失败"""
        sig = RiskSignal(level="high", category="risk", must_say="风险极高")
        # 前 500 字符全是无关内容
        padding = "这是一段无关的文本。" * 60  # ~600 chars
        output = padding + "风险极高，不建议报考。"
        ok, _, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is False
        assert any("前 500" in f for f in failures)

    def test_passes_when_risk_in_first(self):
        sig = RiskSignal(level="high", category="risk", must_say="风险极高")
        output = "风险极高，这是系统风控的硬结论。" + ("补充信息。" * 50)
        ok, _, failures = SynthesisGuard.validate_output(output, [sig])
        assert ok is True

    def test_empty_output_handled(self):
        sig = RiskSignal(level="high", category="risk", must_say="test")
        ok, corrected, _ = SynthesisGuard.validate_output("", [sig])
        assert ok is False
        assert "test" in corrected

    def test_no_signals_always_passes(self):
        ok, output, failures = SynthesisGuard.validate_output("hello world", [])
        assert ok is True
        assert output == "hello world"

    def test_non_critical_only_passes(self):
        sig = RiskSignal(level="low", category="risk", must_say="")
        ok, _, _ = SynthesisGuard.validate_output("output without must_say", [sig])
        assert ok is True

    def test_force_prepend_contains_all_signals(self):
        sigs = [
            RiskSignal(level="high", category="risk", must_say="劝退A", reason="数据A"),
            RiskSignal(level="high", category="reality_fail", must_say="劝退B", reason="数据B"),
        ]
        output = SynthesisGuard._force_prepend_guard_block(sigs, "原始输出")
        assert "劝退A" in output
        assert "劝退B" in output
        assert "数据A" in output
        assert "数据B" in output
        assert "原始输出" in output
        assert "系统风控引擎强制拦截" in output


# ============================================================
# 一站式 enforce 测试
# ============================================================

class TestEnforce:

    def test_no_signals_returns_unchanged(self):
        output = SynthesisGuard.enforce({}, "原始文本")
        assert output == "原始文本"

    def test_risk_signal_enforces_output(self):
        state = {
            "risk_assessment": {
                "is_risk": "true",
                "risk_level": "high",
                "must_say": "绝对不能报考",
                "reason": "高风险",
            }
        }
        # 模拟 LLM 端水输出
        llm_output = "建议您再慎重考虑一下，不过换个角度也有机会。"
        result = SynthesisGuard.enforce(state, llm_output)
        assert "绝对不能报考" in result
        assert "系统风控引擎强制拦截" in result

    def test_compliant_output_passes_unchanged(self):
        state = {
            "risk_assessment": {
                "is_risk": "true",
                "risk_level": "high",
                "must_say": "绝对不能报考",
            }
        }
        llm_output = "风险警告：绝对不能报考。根据数据，你的分数远低于目标线。详细分析如下..."
        result = SynthesisGuard.enforce(state, llm_output)
        # 合规输出不应被修改
        assert "系统风控引擎强制拦截" not in result
        assert result == llm_output

    def test_reality_fail_alone_enforced(self):
        state = {"reality_check": {"is_realistic": "false", "reason": "分数差距50分"}}
        llm_output = "您可能需要调整目标。"
        result = SynthesisGuard.enforce(state, llm_output)
        assert "50分" in result
        assert "系统风控引擎强制拦截" in result
