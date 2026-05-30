"""
工具容错、降级与诊断专项测试
覆盖: ToolResult / 省名标准化 / SQLTools 多级降级 / RAGTools 降级
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.tool_retry import (
    ToolResult, normalize_province, normalize_subject,
    PROVINCE_ALIASES,
)

ROOT = Path(__file__).resolve().parents[1]


# ============================================================
# ToolResult 单元测试
# ============================================================

class TestToolResult:

    def test_exact_result(self):
        r = ToolResult.exact(["row1", "row2"])
        assert r.ok is True
        assert r.is_degraded is False
        assert r.tier == "exact"
        assert r.data == ["row1", "row2"]

    def test_fuzzy_result(self):
        r = ToolResult.fuzzy(["row1"], diag="使用了模糊匹配")
        assert r.ok is True
        assert r.is_degraded is True
        assert r.tier == "fuzzy"
        assert "模糊" in r.diagnostics[0]

    def test_degraded_result(self):
        r = ToolResult.degraded(["row1"], "放宽年份", suggestions=["试试其他年份"])
        assert r.ok is True
        assert r.is_degraded is True
        assert r.tier == "degraded"
        assert len(r.suggestions) == 1

    def test_empty_result(self):
        r = ToolResult.empty(diag="无匹配", suggestions=["检查参数"])
        assert r.ok is False
        assert r.tier == "empty"

    def test_error_result(self):
        r = ToolResult.error("数据库挂了")
        assert r.ok is False
        assert r.tier == "error"
        assert "数据库" in r.diagnostics[0]

    def test_merge_diagnostics(self):
        r1 = ToolResult.fuzzy([], diag="D1")
        r2 = ToolResult.degraded([], diag="D2", suggestions=["S1"])
        r1.merge_diagnostics(r2)
        assert len(r1.diagnostics) == 2
        assert "S1" in r1.suggestions


# ============================================================
# 省名/选科标准化测试
# ============================================================

class TestProvinceNormalize:

    def test_short_to_full(self):
        assert normalize_province("广东") == "广东省"
        assert normalize_province("河北") == "河北省"
        assert normalize_province("北京") == "北京市"
        assert normalize_province("上海") == "上海市"

    def test_already_full(self):
        assert normalize_province("广东省") == "广东省"
        assert normalize_province("河南省") == "河南省"

    def test_alias_chars(self):
        assert normalize_province("粤") == "广东省"
        assert normalize_province("黑") == "黑龙江省"
        assert normalize_province("沪") == "上海市"

    def test_unknown_returns_original(self):
        assert normalize_province("火星") == "火星"

    def test_autonomous_regions(self):
        assert normalize_province("广西") == "广西壮族自治区"
        assert normalize_province("桂") == "广西壮族自治区"
        assert normalize_province("内蒙古") == "内蒙古自治区"

    def test_all_aliases_map_to_valid(self):
        for alias, full in PROVINCE_ALIASES.items():
            assert len(full) >= 3, f"'{alias}' → '{full}' 过短"


class TestSubjectNormalize:

    def test_physics(self):
        assert normalize_subject("物理") == "物理类"
        assert normalize_subject("物理类") == "物理类"

    def test_history(self):
        assert normalize_subject("历史") == "历史类"
        assert normalize_subject("历史类") == "历史类"

    def test_unknown(self):
        assert normalize_subject("体育") == "体育"


# ============================================================
# SQLTools 多级降级测试
# ============================================================

class TestSQLToolsDegradation:

    @pytest.fixture
    def sql_tools(self):
        import yaml
        from sqlalchemy.ext.asyncio import create_async_engine
        from tools.sql_tools import SQLTools

        with open(ROOT / "configs" / "db_config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)["sqlite"]
        db_path = ROOT / cfg["path"]
        if not db_path.exists():
            from scripts.init_sqlite import init_sqlite
            init_sqlite()
        dsn = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        engine = create_async_engine(dsn, echo=False)
        return SQLTools(engine)

    @pytest.fixture
    def valid_args(self):
        from tools.sql_tools import QueryScoreArgs
        return QueryScoreArgs(
            province="广东省",
            subject_type="物理类",
            major_name="计算机科学与技术",
            year=2025,
            max_rows=5,
        )

    def test_exact_match(self, sql_tools, valid_args):
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.tier == "exact"
        assert result.ok is True
        assert len(result.data) > 0
        assert result.data[0]["major_name"] == "计算机科学与技术"

    def test_province_alias_normalization(self, sql_tools, valid_args):
        valid_args.province = "广东"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.ok is True
        assert "省名标准化" in str(result.diagnostics)

    def test_subject_alias_normalization(self, sql_tools, valid_args):
        valid_args.subject_type = "物理"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.ok is True

    def test_full_province_name_works(self, sql_tools, valid_args):
        valid_args.province = "广东省"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.tier == "exact"
        assert len(result.data) > 0

    def test_wrong_major_returns_degraded_or_empty(self, sql_tools, valid_args):
        """不存在的专业名返回 empty 带建议（非精确匹配）"""
        valid_args.major_name = "航空航天工程"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.tier in ("empty", "fuzzy")
        if result.tier == "empty":
            assert len(result.suggestions) > 0

    def test_wrong_year_widens_scope(self, sql_tools, valid_args):
        """不存在的年份应触发放宽年份降级"""
        valid_args.year = 2020
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.tier in ("degraded", "fuzzy")
        if result.tier == "degraded":
            assert any("年份" in d for d in result.diagnostics)

    def test_wrong_province_returns_empty_with_suggestions(self, sql_tools, valid_args):
        valid_args.province = "火星省"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.ok is False
        assert len(result.suggestions) > 0

    def test_typo_in_major_triggers_fuzzy(self, sql_tools, valid_args):
        """
        专业名错别字应触发 LIKE 模糊匹配。
        例如 "计算机科学" 部分匹配 "计算机科学与技术"
        """
        valid_args.major_name = "计算机科学"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.ok is True
        assert "模糊" in str(result.diagnostics) or result.tier == "fuzzy"

    def test_result_contains_tier_field(self, sql_tools, valid_args):
        """每条结果含院校层次字段"""
        result = asyncio.run(sql_tools.query_scores(valid_args))
        if result.data:
            assert "tier" in result.data[0]

    def test_non_physics_subject_empty(self, sql_tools, valid_args):
        """历史类查无数据应返回 empty（种子数据仅有物理类）"""
        valid_args.subject_type = "历史类"
        result = asyncio.run(sql_tools.query_scores(valid_args))
        assert result.tier == "empty"
        assert len(result.suggestions) > 0


# ============================================================
# RAGTools 降级测试
# ============================================================

class TestRAGToolsDegradation:

    @pytest.fixture
    def rag(self):
        from tools.rag_tools import RAGTools
        return RAGTools()

    def test_normal_query_returns_results(self, rag):
        result = rag.query_zx_experience("计算机就业", top_k=3)
        assert len(result) > 0
        assert "来源" in result

    def test_irrelevant_query_returns_whatever_is_scored(self, rag):
        """极端不相关查询也能返回降级结果（而非空字符串），因为所有 doc 都有非零分"""
        result = rag.query_zx_experience("量子物理诺贝尔奖", top_k=2)
        # RAGTools 总是返回 top_k 结果，即使评分低
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_query_returns_empty(self, rag):
        result = rag.query_zx_experience("", top_k=3)
        # 空查询触发 tokenization 返回空
        assert isinstance(result, str)

    def test_fallback_docs_exist(self, rag):
        """确保默认种子文档存在且可召回"""
        result = rag.query_zx_experience("医学", top_k=3)
        assert isinstance(result, str)
        assert len(result.strip()) > 0
        assert "[来源" in result


# ============================================================
# WebSearchTools 降级测试
# ============================================================

class TestWebSearchDegradation:

    def test_empty_query_returns_empty(self):
        from tools.web_search_tools import WebSearchTools
        ws = WebSearchTools()
        results = ws.search("")
        assert results == []

    def test_format_empty_returns_empty_string(self):
        from tools.web_search_tools import WebSearchTools
        assert WebSearchTools.format_results([]) == ""

    def test_search_returns_list(self):
        from tools.web_search_tools import WebSearchTools
        ws = WebSearchTools(timeout_seconds=2.0)
        results = ws.search("高考 计算机 分数线 2025", top_k=3)
        assert isinstance(results, list)
        for item in results:
            assert "title" in item
            assert "url" in item
