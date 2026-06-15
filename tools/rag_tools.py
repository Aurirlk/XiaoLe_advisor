from pathlib import Path
import json
import re
import asyncio
from collections import Counter
from typing import Any, Dict, List, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen


class RAGTools:
    def __init__(
        self,
        backend: str = "local_file",
        index_path: Path | None = None,
        milvus_cfg: Dict[str, Any] | None = None,
        es_cfg: Dict[str, Any] | None = None,
        vector_store=None,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.backend = backend
        self.milvus_cfg = milvus_cfg or {}
        self.es_cfg = es_cfg or {}
        self._vector_store = vector_store
        index_path = index_path or (root / "data" / "vector_store" / "zx_experience.json")
        if index_path.exists():
            self._docs: List[Dict[str, str]] = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            self._docs = [
                {"source": "2023年6月直播切片", "text": "医学周期长、成本高，家庭预算必须先算清楚。"},
                {"source": "2024年咨询复盘", "text": "分数边缘不要硬冲热门，先保底再谈理想。"},
                {"source": "经典语录整理", "text": "报志愿是策略问题，不是情绪问题。"},
            ]

    @classmethod
    def from_config(cls, config: Dict[str, Any] | None, vector_store=None) -> "RAGTools":
        if not config:
            return cls(vector_store=vector_store)
        backend = config.get("backend", "local_file")
        index_rel_path = config.get("index_path", "data/vector_store/zx_experience.json")
        milvus_cfg = config.get("milvus", {})
        es_cfg = config.get("elasticsearch", {})
        root = Path(__file__).resolve().parents[1]
        index_path = root / index_rel_path
        return cls(backend=backend, index_path=index_path, milvus_cfg=milvus_cfg, es_cfg=es_cfg, vector_store=vector_store)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token for token in re.split(r"\W+", text.lower()) if token]

    def _dense_score(self, query: str, text: str) -> float:
        query_terms = set(self._tokenize(query))
        text_terms = set(self._tokenize(text))
        if not query_terms or not text_terms:
            return 0.0
        overlap = len(query_terms & text_terms)
        return overlap / max(len(query_terms), 1)

    def _sparse_score(self, query: str, text: str) -> float:
        q_counter = Counter(self._tokenize(query))
        t_counter = Counter(self._tokenize(text))
        if not q_counter or not t_counter:
            return 0.0
        score = 0.0
        for term, freq in q_counter.items():
            score += min(freq, t_counter.get(term, 0))
        return score

    def _hybrid_recall(self, query: str) -> List[Tuple[float, Dict[str, str]]]:
        ranked = []
        for item in self._docs:
            text = item.get("text", "")
            dense = self._dense_score(query, text)
            sparse = self._sparse_score(query, text)
            score = 0.6 * dense + 0.4 * sparse
            ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return ranked

    def _rerank(self, query: str, candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
        def rerank_score(doc: Dict[str, str]) -> float:
            text = doc.get("text", "")
            return self._dense_score(query, text) + 0.2 * self._sparse_score(query, text)

        return sorted(candidates, key=rerank_score, reverse=True)

    def _local_search(self, query: str, top_k: int) -> List[Dict[str, str]]:
        """本地搜索 - RRF混合融合（并行执行三路检索）"""
        # 并行执行三路检索
        embedding_results = self._search_embedding(query, top_k)
        fts_results = self._search_fts5(query, top_k)
        recalled = self._hybrid_recall(query)
        keyword_docs = [doc for _, doc in recalled[:max(top_k * 2, 3)]]
        keyword_results = self._rerank(query, keyword_docs)[:top_k]

        # 如果所有结果都为空，返回空列表
        if not embedding_results and not fts_results and not keyword_results:
            return []

        # RRF融合排序
        return self._rrf_fusion(query, embedding_results, fts_results, keyword_results, top_k)

    def _rrf_fusion(
        self,
        query: str,
        vector_results: List[Dict[str, str]],
        fts_results: List[Dict[str, str]],
        keyword_results: List[Dict[str, str]],
        top_k: int,
        k: int = 60,
    ) -> List[Dict[str, str]]:
        """RRF (Reciprocal Rank Fusion) 混合融合排序算法
        
        score = 1/(k+rank_vector) + 1/(k+rank_fts5) + 1/(k+rank_keyword)
        k=60 为标准参数
        """
        # 构建文档到排名的映射
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, str]] = {}

        # 向量检索结果
        for rank, doc in enumerate(vector_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + 1 / (k + rank)
            doc_map[key] = doc

        # FTS5检索结果
        for rank, doc in enumerate(fts_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + 1 / (k + rank)
            if key not in doc_map:
                doc_map[key] = doc

        # 关键词召回结果
        for rank, doc in enumerate(keyword_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + 1 / (k + rank)
            if key not in doc_map:
                doc_map[key] = doc

        # 按RRF分数排序
        sorted_keys = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        # 返回Top-K结果
        result = []
        for key in sorted_keys[:top_k]:
            doc = doc_map[key].copy()
            doc["rrf_score"] = doc_scores[key]
            result.append(doc)

        return result

    def _search_embedding(self, query: str, top_k: int) -> List[Dict[str, str]]:
        """ChromaDB embedding 向量语义检索"""
        if not self._vector_store:
            return []
        try:
            results = self._vector_store.query(query, top_k=top_k)
            if results:
                return [{"source": r.get("source", ""), "text": r.get("text", "")} for r in results]
        except Exception:
            pass
        return []

    def _search_fts5(self, query: str, top_k: int) -> List[Dict[str, str]]:
        """SQLite FTS5 全文检索"""
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).resolve().parents[1] / "data" / "zx_advisor.db"
            if not db_path.exists():
                return []
            conn = sqlite3.connect(str(db_path))
            try:
                rows = conn.execute(
                    "SELECT source, text FROM rag_fts WHERE rag_fts MATCH ? ORDER BY rank LIMIT ?",
                    (query, top_k),
                ).fetchall()
                return [{"source": r[0], "text": r[1]} for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def _search_from_es(self, query: str, top_k: int) -> List[Dict[str, str]]:
        endpoint = self.es_cfg.get("endpoint", "").rstrip("/")
        index_name = self.es_cfg.get("index", "")
        if not endpoint or not index_name:
            return []

        payload = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text^2", "source"],
                }
            },
        }
        url = f"{endpoint}/{index_name}/_search"
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=float(self.es_cfg.get("timeout_seconds", 2.0))) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError):
            return []

        hits = result.get("hits", {}).get("hits", [])
        docs: List[Dict[str, str]] = []
        for hit in hits:
            source = hit.get("_source", {})
            text = source.get("text")
            if not text:
                continue
            docs.append({"source": source.get("source", "ES"), "text": text})
        return docs

    def _search_from_milvus(self, query: str, top_k: int) -> List[Dict[str, str]]:
        host = self.milvus_cfg.get("host", "")
        port = self.milvus_cfg.get("port", 19530)
        collection_name = self.milvus_cfg.get("collection", "")
        if not host or not collection_name:
            return []

        try:
            from pymilvus import Collection, connections
        except Exception:
            return []

        alias = "zx_ai_advisor_rag"
        try:
            connections.connect(alias=alias, host=host, port=port)
            try:
                collection = Collection(name=collection_name, using=alias)
                expr = self.milvus_cfg.get("expr") or ""
                # 这里假设 Milvus 中 text/source 字段可直接查询；若无向量检索条件，则做轻量过滤召回。
                rows = collection.query(
                    expr=expr,
                    output_fields=["text", "source"],
                    limit=max(top_k * 3, 10),
                )
            finally:
                connections.disconnect(alias=alias)
        except Exception:
            return []

        docs: List[Dict[str, str]] = []
        for row in rows:
            text = row.get("text")
            if not text:
                continue
            docs.append({"source": row.get("source", "Milvus"), "text": text})
        return self._rerank(query, docs)[:top_k]

    def _search_milvus_es(self, query: str, top_k: int) -> List[Dict[str, str]]:
        milvus_docs = self._search_from_milvus(query, top_k)
        es_docs = self._search_from_es(query, top_k)
        merged = milvus_docs + es_docs
        if not merged:
            return []

        # 去重：source+text 作为唯一键，避免双路召回重复内容。
        unique_docs: Dict[str, Dict[str, str]] = {}
        for doc in merged:
            key = f"{doc.get('source', '')}::{doc.get('text', '')}"
            unique_docs[key] = doc
        reranked = self._rerank(query, list(unique_docs.values()))
        return reranked[:top_k]

    def query_zx_experience(self, query: str, top_k: int = 3) -> str:
        selected: List[Dict[str, str]]
        if self.backend == "milvus_es":
            selected = self._search_milvus_es(query, top_k)
            if not selected:
                selected = self._local_search(query, top_k)
        else:
            selected = self._local_search(query, top_k)
        return "\n".join([f"[来源：{item['source']}] {item['text']}" for item in selected])

    async def query_zx_experience_async(self, query: str, top_k: int = 3) -> str:
        """异步版本的查询方法，支持并行执行"""
        return await asyncio.to_thread(self.query_zx_experience, query, top_k)
