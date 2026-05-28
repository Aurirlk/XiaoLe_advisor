from pathlib import Path
import json
import re
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
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.backend = backend
        self.milvus_cfg = milvus_cfg or {}
        self.es_cfg = es_cfg or {}
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
    def from_config(cls, config: Dict[str, Any] | None) -> "RAGTools":
        if not config:
            return cls()
        backend = config.get("backend", "local_file")
        index_rel_path = config.get("index_path", "data/vector_store/zx_experience.json")
        milvus_cfg = config.get("milvus", {})
        es_cfg = config.get("elasticsearch", {})
        root = Path(__file__).resolve().parents[1]
        index_path = root / index_rel_path
        return cls(backend=backend, index_path=index_path, milvus_cfg=milvus_cfg, es_cfg=es_cfg)

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
        recalled = self._hybrid_recall(query)
        recalled_docs = [doc for _, doc in recalled[: max(top_k * 2, 3)]]
        return self._rerank(query, recalled_docs)[:top_k]

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
            collection = Collection(name=collection_name, using=alias)
            expr = self.milvus_cfg.get("expr") or ""
            # 这里假设 Milvus 中 text/source 字段可直接查询；若无向量检索条件，则做轻量过滤召回。
            rows = collection.query(
                expr=expr,
                output_fields=["text", "source"],
                limit=max(top_k * 3, 10),
            )
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
