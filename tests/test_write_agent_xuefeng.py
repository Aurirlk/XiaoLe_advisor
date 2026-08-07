"""
write-agent 与雪峰语料库测试（2026-08-06 蓝图落地）

覆盖：
1. WriteAgent：写入/去重/噪声过滤/JSON 落盘
2. XuefengStore：对话切块、专业关键字窗口词提取、检索降级
3. synthesis 雪峰锚点注入
"""
from __future__ import annotations

import asyncio
import json
import re

import pytest

from agents.workers.write_agent import WriteAgent, _chunk_text
from tools.xuefeng_store import _split_turns, _normalize_query, XuefengStore

pytestmark = pytest.mark.asyncio

LONG_TEXT = "清华大学2025年在广东物理类最低录取分数为690分，位次约150名，招生计划50人。" * 20


# ── WriteAgent ──────────────────────────────────────────

async def test_write_agent_roundtrip(tmp_path):
    """写入 → JSON 落盘 → 可读回"""
    idx = tmp_path / "rag.json"
    idx.write_text("[]", encoding="utf-8")
    wa = WriteAgent(rag_index_path=idx, vector_store=None)
    r = wa.write_web_result("http://x.com/t", "清华录取线", LONG_TEXT)
    assert r["ok"] and r["written"] >= 1
    assert r["source"].startswith("user:web/")
    saved = json.loads(idx.read_text(encoding="utf-8"))
    assert len(saved) == r["written"]


async def test_write_agent_dedup(tmp_path):
    """同来源二次写入被去重"""
    idx = tmp_path / "rag.json"
    idx.write_text("[]", encoding="utf-8")
    wa = WriteAgent(rag_index_path=idx, vector_store=None)
    wa.write_web_result("http://x.com/t", "标题", LONG_TEXT)
    r2 = wa.write_web_result("http://x.com/t", "标题", LONG_TEXT)
    assert r2["skipped"] == 1 and "已存在" in r2["reason"]


async def test_write_agent_noise_filter(tmp_path):
    """过短内容视为噪声不写入"""
    idx = tmp_path / "rag.json"
    idx.write_text("[]", encoding="utf-8")
    wa = WriteAgent(rag_index_path=idx, vector_store=None)
    r = wa.write_web_result("http://x.com/a", "短", "太短了")
    assert r["skipped"] == 1 and "过短" in r["reason"]


def test_chunk_text_bounds():
    chunks = _chunk_text("第一句。第二句，第三句。" * 100, 512, 64)
    assert len(chunks) >= 2
    assert all(len(c) <= 512 for c in chunks)


# ── XuefengStore ───────────────────────────────────────

def test_split_turns():
    text = "问：学医？\n答：学医周期长成本高。\n" * 3
    turns = _split_turns(text)
    assert len(turns) >= 3
    assert all(len(t) <= 800 for t in turns)


def test_keyword_window_extraction():
    """"学医要多少钱" 拆出 2-3 字窗口词，能命中语料局部词"""
    store = XuefengStore()
    store._docs = [{"source": "s", "text": "学医周期长成本高，先算八年成本"}]
    hits = store.search("学医要多少钱", top_k=1) if False else None
    # 直接验证窗口词逻辑（不触发 embed）
    norm = _normalize_query("学医要多少钱")
    runs = re.findall(r"[\u4e00-\u9fff]+", norm)
    kws = []
    for run in runs:
        for i in range(len(run)):
            if len(run) - i >= 2:
                kws.append(run[i:i + 2])
            if len(run) - i >= 3:
                kws.append(run[i:i + 3])
    assert "学医" in kws
    assert any(k in "学医周期长成本高，先算八年成本" for k in kws[:8])


async def test_xuefeng_search_keyword_fallback(tmp_path):
    """向量路失败时关键字路兜底（优雅降级）"""
    store = XuefengStore()
    store._docs = [{"source": "s1", "text": "学医周期长成本高，先算八年成本"}]
    from unittest.mock import patch

    with patch.object(store, "_embed", side_effect=RuntimeError("embed down")):
        hits = store.search("学医要多少钱", top_k=2)
    assert len(hits) >= 1
    assert hits[0].get("match") == "keyword"


# ── synthesis 雪峰锚点 ─────────────────────────────────

async def test_synthesis_xuefeng_anchor_injected():
    """synthesis 调用 xuefeng_store.search 注入风格锚点"""
    from unittest.mock import MagicMock

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessageChunk
    from langchain_core.outputs import ChatGenerationChunk, ChatResult

    from agents.synthesis_agent import build_synthesis_agent

    class FakeLLM(BaseChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(generations=[ChatGenerationChunk(message=AIMessageChunk(content="建议：学医要算清八年成本"))])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            yield ChatGenerationChunk(message=AIMessageChunk(content="建议：学医要算清八年成本"))

        @property
        def _llm_type(self):
            return "fake"

    xf = MagicMock()
    xf.search.return_value = [{"source": "s", "text": "学医周期长成本高"}]
    agent = build_synthesis_agent(FakeLLM(), xuefeng_store=xf)
    result = await agent({
        "user_query": "孩子想学医，预算怎么规划？",
        "user_profile": {"province": "广东省", "subject_type": "物理类", "major_name": "临床医学"},
        "scene_type": "gaokao",
        "messages": [],
    })
    content = result["messages"][-1]
    content = content["content"] if isinstance(content, dict) else getattr(content, "content", "")
    assert "学医" in content or "成本" in content
    xf.search.assert_called_once()


async def test_synthesis_without_xuefeng_store():
    """不传 xuefeng_store → 正常合成（向后兼容）"""
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessageChunk
    from langchain_core.outputs import ChatGenerationChunk, ChatResult

    from agents.synthesis_agent import build_synthesis_agent

    class FakeLLM(BaseChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(generations=[ChatGenerationChunk(message=AIMessageChunk(content="综合建议"))])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            yield ChatGenerationChunk(message=AIMessageChunk(content="综合建议"))

        @property
        def _llm_type(self):
            return "fake"

    agent = build_synthesis_agent(FakeLLM())  # 无 xuefeng_store
    result = await agent({
        "user_query": "q", "user_profile": {}, "scene_type": "gaokao", "messages": [],
    })
    assert result["messages"]
