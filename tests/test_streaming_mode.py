"""
真流式输出回归测试（P1-1 修复）

验证 LangGraph 1.2 `stream_mode=["updates","messages"]` 双流模式下：
1. messages 流逐 token 输出（synthesis_agent 节点）
2. 中间节点（supervisor 等）的 LLM 输出被过滤，不推给用户
3. updates 流保留节点完成事件
4. token 拼接后与完整回复一致
"""
from __future__ import annotations

import asyncio

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langgraph.graph import END, START, StateGraph

pytestmark = pytest.mark.asyncio


class _StreamState(dict):
    pass


class _FakeStreamLLM(BaseChatModel):
    """逐 token 流式假 LLM：synthesis 回复 + supervisor 推理两部分"""
    _streamed: list[str]

    def __init__(self, tokens: list[str]):
        super().__init__()
        self._streamed = tokens

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        for t in self._streamed:
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=t))
            if run_manager:
                run_manager.on_llm_new_token(t, chunk=chunk)
            yield chunk

    @property
    def _llm_type(self):
        return "fake-stream"


def _build_graph(supervisor_tokens: list[str], synthesis_tokens: list[str]):
    """双节点图：supervisor_agent → synthesis_agent → END"""
    g = StateGraph(_StreamState)

    async def supervisor(state):
        llm = _FakeStreamLLM(supervisor_tokens)
        resp = await llm.ainvoke([HumanMessage("q")])
        return {"messages": [resp], "next_node": "synthesis_agent"}

    async def synthesis(state):
        llm = _FakeStreamLLM(synthesis_tokens)
        resp = await llm.ainvoke([HumanMessage("q")])
        return {"messages": [resp], "scene_type": "gaokao"}

    g.add_node("supervisor_agent", supervisor)
    g.add_node("synthesis_agent", synthesis)
    g.add_edge(START, "supervisor_agent")
    g.add_edge("supervisor_agent", "synthesis_agent")
    g.add_edge("synthesis_agent", END)
    return g.compile()


async def _collect_stream(comp, state) -> tuple[list[str], list[str]]:
    """收集 token 流（仅 synthesis_agent 的 AIMessageChunk 增量）与节点事件

    与 stream_router/ws_router 的过滤逻辑一致：只收逐 token 的 AIMessageChunk，
    跳过节点返回的完整 AIMessage（防重复拼接）。
    """
    tokens: list[str] = []
    node_events: list[str] = []
    async for mode_val in comp.astream(
        dict(state), stream_mode=["updates", "messages"]
    ):
        mode, value = mode_val
        if mode == "messages":
            msg, meta = value
            node = (meta or {}).get("langgraph_node", "") if isinstance(meta, dict) else ""
            if node == "synthesis_agent" and type(msg).__name__ == "AIMessageChunk":
                content = getattr(msg, "content", "")
                if content:
                    tokens.append(str(content))
        else:
            node_events.extend(value.keys())
    return tokens, node_events


async def test_true_streaming_token_flow():
    """synthesis_agent 的回复逐 token 流出，拼接后完整"""
    comp = _build_graph(["路由", "推理"], ["综合", "你的", "分数", "建议"])
    tokens, nodes = await _collect_stream(comp, {"messages": [], "scene_type": ""})
    assert tokens == ["综合", "你的", "分数", "建议"], f"token 流不完整: {tokens}"
    assert "".join(tokens) == "综合你的分数建议"
    assert "supervisor_agent" in nodes
    assert "synthesis_agent" in nodes


async def test_intermediate_llm_output_filtered():
    """supervisor 的 LLM 输出（内部推理）不得进入用户 token 流"""
    comp = _build_graph(["内部路由推理"], ["最终回复"])
    tokens, _ = await _collect_stream(comp, {"messages": [], "scene_type": ""})
    assert tokens == ["最终回复"]
    assert "内部路由推理" not in "".join(tokens)


async def test_no_token_stream_still_emits_node_events():
    """无 LLM 的纯逻辑节点（messages 流无 token）时，updates 节点事件仍完整"""
    g = StateGraph(_StreamState)

    async def fallback(state):
        # 纯逻辑回复：不走 LLM，无任何流式 token
        return {"messages": [{"role": "assistant", "content": "信息还不够，请补充省份/选科/专业。"}], "next_node": "END"}

    g.add_node("synthesis_agent", fallback)
    g.add_edge(START, "synthesis_agent")
    g.add_edge("synthesis_agent", END)
    comp = g.compile()

    tokens, nodes = await _collect_stream(comp, {"messages": []})
    assert tokens == []
    assert "synthesis_agent" in nodes


async def test_final_aimessage_not_duplicated():
    """节点返回完整 AIMessage 时不得重复推送到 token 流（防重复拼接回归）"""
    from langchain_core.messages import AIMessage

    g = StateGraph(_StreamState)

    async def synth_with_full_msg(state):
        # 同时产生逐 token chunk 与最终完整消息的场景
        llm = _FakeStreamLLM(["你好", "小乐"])
        await llm.ainvoke([HumanMessage("q")])  # 触发 chunk 回调
        return {"messages": [AIMessage(content="你好小乐")]}

    g.add_node("synthesis_agent", synth_with_full_msg)
    g.add_edge(START, "synthesis_agent")
    g.add_edge("synthesis_agent", END)
    comp = g.compile()

    tokens, _ = await _collect_stream(comp, {"messages": []})
    # 只应有 chunk 增量，完整 AIMessage 被过滤
    assert tokens == ["你好", "小乐"], f"完整消息混入 token 流: {tokens}"
    assert "".join(tokens) == "你好小乐"
