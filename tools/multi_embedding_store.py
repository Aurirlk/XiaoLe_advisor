"""
多维Embedding向量存储 - 支持Dense + Sparse + ColBERT三路检索

使用BGE-M3模型实现多维嵌入，配合RRF融合排序提升检索准确性。

依赖:
    pip install FlagEmbedding rank_bm25
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]


class BM25Index:
    """BM25稀疏检索索引"""
    
    def __init__(self):
        self._corpus: List[str] = []
        self._docs: List[Dict[str, str]] = []
        self._bm25 = None
    
    def build(self, documents: List[Dict[str, str]]) -> None:
        """构建BM25索引"""
        from rank_bm25 import BM25Okapi
        
        self._docs = documents
        self._corpus = [doc.get("text", "") for doc in documents]
        tokenized_corpus = [list(text) for text in self._corpus]  # 字符级分词（中文友好）
        self._bm25 = BM25Okapi(tokenized_corpus)
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """BM25检索，返回(文档索引, 分数)列表"""
        if not self._bm25 or not self._corpus:
            return []
        tokenized_query = list(query)
        scores = self._bm25.get_scores(tokenized_query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


class MultiEmbeddingStore:
    """
    多维嵌入向量存储
    
    支持三路检索:
    1. Dense: BGE-M3稠密向量 (1024维)
    2. Sparse: BM25稀疏检索
    3. ColBERT: 细粒度交互检索
    
    通过RRF融合排序合并结果
    """
    
    def __init__(
        self,
        dense_model_name: str | None = None,
        use_colbert: bool = False,
        rrf_k: int = 60,
        weights: Optional[Dict[str, float]] = None,
    ):
        # P1-9：模型名与 vector_store 统一从 embedding_config 单一真源解析，
        # 避免 MiniLM(384) 与 BGE-M3(1024) 双向量空间不互通。
        if dense_model_name is None:
            from tools.embedding_config import resolve_embedding_model
            dense_model_name = resolve_embedding_model()
        self._dense_model = None
        self._dense_model_name = dense_model_name
        self._bm25_index = BM25Index()
        self._colbert_model = None
        self._use_colbert = use_colbert
        self._docs: List[Dict[str, str]] = []
        self._dense_embeddings = None
        # P1 权重配置化：rrf_k 与三路权重可配，缺省与旧行为一致
        self._rrf_k = int(rrf_k)
        self._weights = {
            "dense": 1.0,
            "sparse": 1.0,
            "colbert": 1.0,
            **(weights or {}),
        }
    
    def _load_dense_model(self):
        """延迟加载稠密嵌入模型（P1-9：本地模型目录优先，避免联网超时）"""
        if self._dense_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                from pathlib import Path

                model_ref = self._dense_model_name
                local = Path(__file__).resolve().parents[1] / "data" / "models" / model_ref
                if local.exists():
                    model_ref = str(local)
                self._dense_model = SentenceTransformer(model_ref)
            except Exception as e:
                print(f"[WARN] 加载稠密模型失败: {e}")
                self._dense_model = None
    
    def _load_colbert_model(self):
        """延迟加载ColBERT模型"""
        if self._colbert_model is None and self._use_colbert:
            try:
                from FlagEmbedding import BGEM3FlagModel
                self._colbert_model = BGEM3FlagModel(self._dense_model_name, use_fp16=True)
            except Exception as e:
                print(f"[WARN] 加载ColBERT模型失败: {e}")
                self._colbert_model = None
    
    def build_index(self, documents: List[Dict[str, str]]) -> None:
        """构建多维索引"""
        self._docs = documents
        texts = [doc.get("text", "") for doc in documents]
        
        # 构建BM25索引
        self._bm25_index.build(documents)
        
        # 构建稠密向量索引
        self._load_dense_model()
        if self._dense_model:
            self._dense_embeddings = self._dense_model.encode(texts, normalize_embeddings=True)
        
        print(f"[INFO] 多维索引构建完成: {len(documents)} 文档")
    
    def _dense_search(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        """稠密向量检索"""
        if self._dense_model is None or self._dense_embeddings is None:
            return []
        
        query_embedding = self._dense_model.encode([query], normalize_embeddings=True)
        similarities = query_embedding @ self._dense_embeddings.T
        similarities = similarities[0]
        
        ranked = sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    
    def _sparse_search(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        """BM25稀疏检索"""
        return self._bm25_index.search(query, top_k)
    
    def _colbert_search(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        """ColBERT细粒度检索

        P1-10：模型缺失/编码失败时返回空列表并告警，禁止静默降级到 dense——
        否则 RRF 融合里 dense 被变相加权两倍，调用方以为三路结果实际两路重复。
        """
        if not self._colbert_model or not self._docs:
            logger.warning("ColBERT 模型未加载，colbert 路返回空（dense/sparse 照常参与融合）")
            return []
        try:
            import numpy as np
            texts = [doc.get("text", "") for doc in self._docs]
            query_vec = self._colbert_model.encode(
                [query],
                return_dense=False,
                return_sparse=False,
                return_colbert_vecs=True,
            )
            doc_vecs = self._colbert_model.encode(
                texts,
                return_dense=False,
                return_sparse=False,
                return_colbert_vecs=True,
            )
            # ColBERT 晚期交互：query token × doc token 最大相似度求和
            scores = []
            q_tokens = np.asarray(query_vec["colbert_vecs"][0], dtype=np.float32)
            for dv in doc_vecs["colbert_vecs"]:
                d_tokens = np.asarray(dv, dtype=np.float32)
                # 余弦相似度矩阵 → 每行取 max → 求和
                q_norm = q_tokens / (np.linalg.norm(q_tokens, axis=1, keepdims=True) + 1e-9)
                d_norm = d_tokens / (np.linalg.norm(d_tokens, axis=1, keepdims=True) + 1e-9)
                sim = q_norm @ d_norm.T
                scores.append(float(sim.max(axis=1).sum()))
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            return ranked[:top_k]
        except Exception:
            logger.warning("ColBERT 编码失败，colbert 路返回空", exc_info=True)
            return []
    
    def _rrf_fusion(
        self,
        results_list: List[List[Tuple[int, float]]],
        top_k: int,
        k: int | None = None,
        weights: Optional[List[float]] = None,
    ) -> List[Dict[str, str]]:
        """RRF融合排序（支持每路权重，P1 权重配置化）

        score = Σ w_i / (k + rank_i)
        k 与 weights 缺省时使用构造时配置（与旧行为一致）。
        """
        k = int(k if k is not None else self._rrf_k)
        default_w = [self._weights.get("dense", 1.0), self._weights.get("sparse", 1.0)]
        if len(results_list) > 2:
            default_w.append(self._weights.get("colbert", 1.0))
        if weights is None:
            weights = default_w[: len(results_list)]

        doc_scores: Dict[int, float] = {}

        for road_results, w in zip(results_list, weights):
            for rank, (doc_idx, _) in enumerate(road_results, 1):
                doc_scores[doc_idx] = doc_scores.get(doc_idx, 0) + w / (k + rank)
        
        sorted_indices = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        
        result = []
        for idx in sorted_indices[:top_k]:
            if idx < len(self._docs):
                doc = self._docs[idx].copy()
                doc["rrf_score"] = doc_scores[idx]
                result.append(doc)
        
        return result
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        """多维检索 - 融合三路结果"""
        # 并行执行三路检索
        dense_results = self._dense_search(query, top_k * 2)
        sparse_results = self._sparse_search(query, top_k * 2)
        
        results_list = [dense_results, sparse_results]
        
        # ColBERT可选
        if self._use_colbert:
            colbert_results = self._colbert_search(query, top_k * 2)
            results_list.append(colbert_results)
        
        # RRF融合
        return self._rrf_fusion(results_list, top_k)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            "total_documents": len(self._docs),
            "dense_model": self._dense_model_name,
            "dense_embedding_dim": 1024 if self._dense_model else 0,
            "bm25_ready": self._bm25_index._bm25 is not None,
            "colbert_enabled": self._use_colbert,
        }


class HybridRAGStore:
    """
    混合RAG存储 - 结合ChromaDB和多维Embedding
    
    提供统一的检索接口，自动选择最佳检索策略
    """
    
    def __init__(
        self,
        chroma_store=None,
        multi_embed_store: Optional[MultiEmbeddingStore] = None,
    ):
        self._chroma_store = chroma_store
        self._multi_embed_store = multi_embed_store
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        """混合检索 - 融合ChromaDB和多维Embedding结果"""
        results = []
        
        # ChromaDB向量检索
        if self._chroma_store:
            try:
                chroma_results = self._chroma_store.query(query, top_k=top_k)
                results.extend(chroma_results)
            except Exception:
                pass
        
        # 多维Embedding检索
        if self._multi_embed_store:
            try:
                multi_results = self._multi_embed_store.search(query, top_k=top_k)
                results.extend(multi_results)
            except Exception:
                pass
        
        # 去重并排序
        seen = set()
        unique_results = []
        for doc in results:
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            if key not in seen:
                seen.add(key)
                unique_results.append(doc)
        
        return unique_results[:top_k]
