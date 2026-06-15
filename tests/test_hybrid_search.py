"""RRF混合搜索算法测试"""
import pytest
from tools.rag_tools import RAGTools


class TestRRFFusion:
    """测试RRF (Reciprocal Rank Fusion) 混合融合算法"""

    def setup_method(self):
        self.rag = RAGTools()

    def test_rrf_fusion_basic(self):
        """测试基本RRF融合功能"""
        vector_results = [
            {"source": "向量1", "text": "计算机专业就业前景好"},
            {"source": "向量2", "text": "软件工程薪资高"},
        ]
        fts_results = [
            {"source": "FTS1", "text": "计算机专业就业前景分析"},
            {"source": "FTS2", "text": "人工智能发展趋势"},
        ]
        keyword_results = [
            {"source": "关键词1", "text": "计算机科学与技术专业"},
        ]

        result = self.rag._rrf_fusion(
            "计算机专业",
            vector_results,
            fts_results,
            keyword_results,
            top_k=5,
            k=60,
        )

        assert len(result) <= 5
        assert all("rrf_score" in doc for doc in result)
        # 验证分数递减
        scores = [doc["rrf_score"] for doc in result]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_fusion_deduplication(self):
        """测试RRF融合去重功能"""
        vector_results = [
            {"source": "来源A", "text": "相同的文本内容"},
        ]
        fts_results = [
            {"source": "来源A", "text": "相同的文本内容"},  # 重复
        ]
        keyword_results = [
            {"source": "来源B", "text": "不同的文本内容"},
        ]

        result = self.rag._rrf_fusion(
            "测试查询",
            vector_results,
            fts_results,
            keyword_results,
            top_k=10,
        )

        # 应该去重，只有2个唯一文档
        assert len(result) == 2

    def test_rrf_fusion_empty_results(self):
        """测试空结果处理"""
        result = self.rag._rrf_fusion(
            "测试查询",
            [],
            [],
            [],
            top_k=5,
        )
        assert result == []

    def test_rrf_fusion_single_source(self):
        """测试单一来源结果"""
        vector_results = [
            {"source": "向量库", "text": "测试文本1"},
            {"source": "向量库", "text": "测试文本2"},
        ]

        result = self.rag._rrf_fusion(
            "测试查询",
            vector_results,
            [],
            [],
            top_k=5,
        )

        assert len(result) == 2
        # 来自单一来源的文档分数应该相同
        assert result[0]["rrf_score"] == result[1]["rrf_score"]

    def test_rrf_fusion_top_k_limit(self):
        """测试Top-K限制"""
        vector_results = [{"source": f"向量{i}", "text": f"文本{i}"} for i in range(10)]
        fts_results = [{"source": f"FTS{i}", "text": f"全文{i}"} for i in range(10)]

        result = self.rag._rrf_fusion(
            "测试查询",
            vector_results,
            fts_results,
            [],
            top_k=5,
        )

        assert len(result) == 5

    def test_rrf_fusion_k_parameter(self):
        """测试k参数对分数的影响"""
        vector_results = [{"source": "测试", "text": "测试文本"}]

        result_k60 = self.rag._rrf_fusion(
            "测试", vector_results, [], [], top_k=1, k=60
        )
        result_k1 = self.rag._rrf_fusion(
            "测试", vector_results, [], [], top_k=1, k=1
        )

        # k越小，分数越高
        assert result_k1[0]["rrf_score"] > result_k60[0]["rrf_score"]

    def test_local_search_integration(self):
        """测试本地搜索集成（使用默认数据）"""
        result = self.rag._local_search("高考志愿", top_k=3)
        assert isinstance(result, list)
        # 默认数据中应该有相关内容
        if result:
            assert all("source" in doc and "text" in doc for doc in result)

    def test_query_zx_experience_integration(self):
        """测试完整查询流程"""
        result = self.rag.query_zx_experience("计算机专业", top_k=3)
        assert isinstance(result, str)
        # 应该返回格式化的结果
        if result:
            assert "[来源：" in result


class TestRRFEdgeCases:
    """测试RRF边缘情况"""

    def setup_method(self):
        self.rag = RAGTools()

    def test_unicode_query(self):
        """测试Unicode查询"""
        vector_results = [{"source": "测试", "text": "包含中文的文本"}]
        result = self.rag._rrf_fusion(
            "中文查询测试", vector_results, [], [], top_k=3
        )
        assert len(result) == 1

    def test_special_characters(self):
        """测试特殊字符"""
        vector_results = [{"source": "测试", "text": "包含@#$%^&*的文本"}]
        result = self.rag._rrf_fusion(
            "特殊字符!@#", vector_results, [], [], top_k=3
        )
        assert len(result) == 1

    def test_long_text(self):
        """测试长文本"""
        long_text = "这是一段非常长的文本。" * 100
        vector_results = [{"source": "测试", "text": long_text}]
        result = self.rag._rrf_fusion(
            "长文本测试", vector_results, [], [], top_k=3
        )
        assert len(result) == 1
        assert len(result[0]["text"]) == len(long_text)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
