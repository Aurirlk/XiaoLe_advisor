"""
RAG 知识库分权（逻辑分库）测试（2026-08-06 多 Agent 知识库分权）

覆盖：
1. kb_scope 归一化（None/单键/多键/前缀）
2. 三路检索的 scope 过滤（keyword 路 _hybrid_recall）
3. 跨库兜底触发（scope 空结果 → 全库 + fallback_cross_kb 标记）
4. 跨库兜底不触发（scope 内有结果 → 不污染）
"""
from __future__ import annotations

from unittest.mock import patch

from tools.rag_tools import RAGTools, _normalize_scope, _in_scope, KB_SCOPES


class TestScopeNormalize:
    def test_none_means_all(self):
        assert _normalize_scope(None) is None

    def test_single_key(self):
        assert _normalize_scope("majors") == ["user:majors/"]

    def test_multi_key(self):
        assert _normalize_scope(["employment", "majors"]) == [
            "user:employment/", "user:majors/",
        ]

    def test_raw_prefix(self):
        assert _normalize_scope("user:employment/") == ["user:employment/"]
        # 无尾斜杠自动补
        assert _normalize_scope("user:employment") == ["user:employment/"]

    def test_unknown_key_ignored(self):
        assert _normalize_scope(["majors", "nonsense"]) == ["user:majors/"]

    def test_scope_keys_defined(self):
        # 语料 source 前缀必须都有对应 key（防止配置漂移）
        assert set(KB_SCOPES) == {"majors", "universities", "employment", "guides", "policies"}


class TestInScope:
    def test_all_scope_passes(self):
        assert _in_scope("user:majors/x.md#1", None) is True

    def test_matching_prefix(self):
        assert _in_scope("user:majors/法学.md#1", ["user:majors/"]) is True

    def test_non_matching_prefix(self):
        assert _in_scope("user:universities/985.md#1", ["user:majors/"]) is False

    def test_multi_prefix(self):
        prefixes = ["user:employment/", "user:majors/"]
        assert _in_scope("user:majors/x.md#1", prefixes) is True
        assert _in_scope("user:employment/y.md#1", prefixes) is True
        assert _in_scope("user:universities/z.md#1", prefixes) is False


class TestHybridRecallScope:
    def setup_method(self):
        self.rag = RAGTools()
        # 注入确定性的迷你语料（覆盖各知识域）
        self.rag._docs = [
            {"source": "user:majors/计算机.md#1", "text": "计算机专业就业薪资高"},
            {"source": "user:universities/清华大学.md#1", "text": "清华大学位于北京"},
            {"source": "user:employment/互联网就业.md#1", "text": "互联网行业平均薪资高"},
            {"source": "user:policies/高考政策.md#1", "text": "高考志愿填报政策说明"},
        ]

    def test_hybrid_recall_scoped(self):
        recalled = self.rag._hybrid_recall("就业薪资", ["user:majors/", "user:employment/"])
        sources = [doc["source"] for _, doc in recalled]
        # 院校库/政策库文档不应出现
        assert all(s.startswith(("user:majors/", "user:employment/")) for s in sources)
        assert "user:universities/清华大学.md#1" not in sources
        assert "user:policies/高考政策.md#1" not in sources

    def test_hybrid_recall_all(self):
        recalled = self.rag._hybrid_recall("就业")
        assert len(recalled) == 4  # 全库无过滤


class TestCrossKBFallback:
    def setup_method(self):
        self.rag = RAGTools()
        self.rag._docs = [
            {"source": "user:majors/计算机.md#1", "text": "计算机专业就业薪资高"},
            {"source": "user:universities/清华大学.md#1", "text": "清华大学位于北京"},
        ]

    def test_fallback_triggers_when_empty(self):
        """scope 内无结果 → 跨库兜底 + fallback_cross_kb 标记"""
        # scope 内三路全空；全库查询（fallback）有结果
        def scoped_empty(query, top_k, prefixes=None):
            return [] if prefixes else [
                {"source": "user:universities/清华大学.md#1", "text": "清华大学位于北京"}
            ]

        with patch.object(self.rag, "_search_embedding", side_effect=scoped_empty), \
             patch.object(self.rag, "_search_fts5", side_effect=scoped_empty), \
             patch.object(self.rag, "_hybrid_recall",
                          side_effect=lambda q, prefixes=None: [] if prefixes else
                          [(1.0, {"source": "user:universities/清华大学.md#1", "text": "x"})]):
            docs = self.rag.query_zx_experience_top_docs(
                "清华 北京 名校", top_k=3, kb_scope="majors"
            )
        assert len(docs) >= 1
        assert all(d.get("fallback_cross_kb") for d in docs), "兜底结果必须打标记"

    def test_no_fallback_when_in_scope(self):
        """scope 内有结果 → 不跨库、不打标记（防污染）"""
        with patch.object(self.rag, "_search_embedding", return_value=[]), \
             patch.object(self.rag, "_search_fts5", return_value=[]), \
             patch.object(self.rag, "_hybrid_recall",
                          return_value=[(1.0, {"source": "user:majors/计算机.md#1", "text": "x"})]):
            docs = self.rag.query_zx_experience_top_docs(
                "计算机", top_k=3, kb_scope="majors"
            )
        assert len(docs) == 1
        assert not docs[0].get("fallback_cross_kb"), "域内有结果时不得兜底"
        assert docs[0]["source"].startswith("user:majors/")
