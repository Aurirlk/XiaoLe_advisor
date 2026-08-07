"""
自我反思 Agent 测试（蓝图 Phase 3.2 重建回归）

覆盖：质量评估、反思循环重试、改进建议、反思记忆沉淀与复用、零 LLM 可离线。
"""
from __future__ import annotations

import asyncio

import pytest

from core.reflexion_agent import ReflectionMemory, ReflexionAgent, ReflectionResult

pytestmark = pytest.mark.asyncio


async def test_satisfied_output_no_reflection():
    """优质输出：不触发反思"""
    agent = ReflexionAgent(max_reflections=2)
    result = await agent.reflect(
        "临床医学就业前景", "医学就业两极分化：顶尖院校+法考通过率高，就业前景好。",
        context={"scene": "career"},
    )
    assert result.satisfied is True
    assert result.reflections == 0
    assert result.output == "医学就业两极分化：顶尖院校+法考通过率高，就业前景好。"


async def test_empty_output_triggers_reflection():
    """空输出：触发反思直到满足或达到上限"""
    agent = ReflexionAgent(max_reflections=2)
    calls = []

    async def regenerate(query, hint, context):
        calls.append(hint)
        return "医学就业两极分化：顶尖院校就业好，前景不错，需要结合分数和位次判断。"

    result = await agent.reflect("临床医学就业", "", context={"scene": "career"}, regenerate=regenerate)
    assert result.satisfied is True
    assert result.reflections >= 1
    assert len(calls) >= 1
    assert "就业" in result.output and "前景" in result.output


async def test_missing_required_element_detected():
    """career 场景缺「就业/前景」要素 → 不满足"""
    agent = ReflexionAgent(max_reflections=0)
    result = await agent.reflect("临床医学就业前景", "医学分数要求很高，录取分数线逐年上涨。",
                                 context={"scene": "career"})
    assert result.satisfied is False
    assert any("就业" in i or "前景" in i for i in result.issues)


async def test_max_reflections_capped():
    """重试次数上限生效"""
    agent = ReflexionAgent(max_reflections=2)
    calls = 0

    async def regenerate(query, hint, context):
        nonlocal calls
        calls += 1
        return "还是不够"  # 永远不满足

    result = await agent.reflect("q", "", context={"scene": "career"}, regenerate=regenerate)
    assert calls == 2  # 最多重试 2 次
    assert result.reflections == 2
    assert result.satisfied is False


async def test_no_regenerate_means_pure_gate():
    """不提供 regenerate → 纯质量门（不重写输出）"""
    agent = ReflexionAgent(max_reflections=3)
    result = await agent.reflect("q", "太短了", context={"scene": "default"})
    assert result.reflections == 0
    assert result.output == "太短了"
    assert result.satisfied is False


async def test_memory_persists_and_reused():
    """反思记忆：失败沉淀（topic 自动从 context.scene 推导），后续同类查询复用建议"""
    agent = ReflexionAgent(max_reflections=0)
    await agent.reflect("临床医学就业", "只有分数", context={"scene": "career"})
    assert agent.memory.size() >= 1
    # topic 自动推导 → 记忆落在 "career" 主题
    suggestions = agent.memory.get_suggestions("career")
    assert suggestions, "career 主题应有建议（topic 自动推导）"
    assert any("就业" in s or "前景" in s or "数据" in s for s in suggestions)
    # 复用：新 agent 共享同一 memory
    agent2 = ReflexionAgent(max_reflections=0, memory=agent.memory)
    result2 = await agent2.reflect("计算机就业", "只有薪资", context={"scene": "career"})
    assert any(s in suggestions for s in result2.suggestions), "历史建议未复用"


async def test_risk_flag_soft_fail():
    """风控高风险 → 提示但不改变 satisfied 判断之外的行为"""
    agent = ReflexionAgent(max_reflections=0)
    result = await agent.reflect(
        "某校录取线", "该校分数线 600 分，值得冲。",
        context={"risk_assessment": {"level": "high"}},
    )
    # 高风险只是附加 issue；若其他规则通过则 satisfied 仍为 True
    assert any("风控" in i for i in result.issues)
