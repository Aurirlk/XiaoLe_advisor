"""
检索重排序器 - 使用交叉编码器对检索结果进行重排序

依赖:
    pip install sentence-transformers

⚠️ 状态标注（2026-08-06 架构拷打）：本模块当前【零调用方】——
CrossEncoderReranker / SimpleReranker 均未被生产代码引用。
RAG 当前用「RRF 融合 + 关键词重排」替代了交叉编码器重排。
启用条件：语料规模扩大或评估显示 RRF 排序质量不足时，接入
`query_zx_experience_top_docs` 的 rerank 阶段（用 scripts/rag_eval 对比）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import os


class CrossEncoderReranker:
    """
    交叉编码器重排序器
    
    使用交叉编码器对查询-文档对进行精确相关性评分，
    从而对初始检索结果进行重排序，提升检索准确性。
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_api: bool = False,
        api_key: Optional[str] = None,
    ):
        self._model_name = model_name
        self._model = None
        self._use_api = use_api
        self._api_key = api_key or os.getenv("RERANKER_API_KEY", "")
    
    def _load_model(self):
        """延迟加载模型"""
        if self._model is None and not self._use_api:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self._model_name)
            except Exception as e:
                print(f"[WARN] 加载重排序模型失败: {e}")
                self._model = None
    
    def _api_rerank(
        self,
        query: str,
        documents: List[Dict[str, str]],
        top_k: int,
    ) -> List[Dict[str, str]]:
        """使用API进行重排序"""
        import urllib.request
        
        if not self._api_key:
            # 降级到本地模型
            return self._local_rerank(query, documents, top_k)
        
        texts = [doc.get("text", "") for doc in documents]
        
        payload = json.dumps({
            "query": query,
            "documents": texts,
            "top_n": top_k,
        }).encode("utf-8")
        
        request = urllib.request.Request(
            url="https://api.example.com/rerank",  # 替换为实际API
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                # 处理API响应
                reranked = []
                for item in result.get("results", [])[:top_k]:
                    idx = item.get("index", 0)
                    if idx < len(documents):
                        doc = documents[idx].copy()
                        doc["rerank_score"] = item.get("relevance_score", 0)
                        reranked.append(doc)
                return reranked
        except Exception as e:
            print(f"[WARN] API重排序失败: {e}")
            return self._local_rerank(query, documents, top_k)
    
    def _local_rerank(
        self,
        query: str,
        documents: List[Dict[str, str]],
        top_k: int,
    ) -> List[Dict[str, str]]:
        """使用本地模型进行重排序"""
        self._load_model()
        
        if not self._model:
            # 降级到简单排序
            return documents[:top_k]
        
        texts = [doc.get("text", "") for doc in documents]
        
        # 计算查询-文档对的相关性分数
        pairs = [[query, text] for text in texts]
        scores = self._model.predict(pairs)
        
        # 按分数排序
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # 返回top_k结果
        result = []
        for doc, score in scored_docs[:top_k]:
            doc_copy = doc.copy()
            doc_copy["rerank_score"] = float(score)
            result.append(doc_copy)
        
        return result
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, str]],
        top_k: int = 5,
    ) -> List[Dict[str, str]]:
        """
        对检索结果进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序文档列表
            top_k: 返回结果数量
        
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        if self._use_api and self._api_key:
            return self._api_rerank(query, documents, top_k)
        else:
            return self._local_rerank(query, documents, top_k)


class SimpleReranker:
    """
    简单重排序器 - 基于规则的轻量级重排序
    
    不依赖外部模型，使用简单的规则进行重排序。
    适合资源受限环境或作为降级方案。
    """
    
    def __init__(self):
        pass
    
    def _calculate_score(self, query: str, text: str) -> float:
        """计算简单的相关性分数"""
        query_lower = query.lower()
        text_lower = text.lower()
        
        # 关键词匹配分数
        query_terms = set(query_lower.split())
        text_terms = set(text_lower.split())
        overlap = len(query_terms & text_terms)
        keyword_score = overlap / max(len(query_terms), 1)
        
        # 长度惩罚（过短或过长的文档）
        length = len(text)
        if length < 10:
            length_penalty = 0.5
        elif length > 1000:
            length_penalty = 0.8
        else:
            length_penalty = 1.0
        
        return keyword_score * length_penalty
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, str]],
        top_k: int = 5,
    ) -> List[Dict[str, str]]:
        """
        对检索结果进行简单重排序
        
        Args:
            query: 查询文本
            documents: 待排序文档列表
            top_k: 返回结果数量
        
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        # 计算每个文档的分数
        scored_docs = []
        for doc in documents:
            text = doc.get("text", "")
            score = self._calculate_score(query, text)
            doc_copy = doc.copy()
            doc_copy["rerank_score"] = score
            scored_docs.append((doc_copy, score))
        
        # 按分数排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in scored_docs[:top_k]]
