from pathlib import Path
import json
import re
import asyncio
from collections import Counter
from typing import Any, Dict, List, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen


# ── 融合权重默认值（P1 权重配置化）────────────────────────────
# 代码内禁止再硬编码 0.6/0.4/0.2/k=60 等魔法数字；
# 默认值与旧行为完全一致，配置缺省时使用这些默认。
DEFAULT_FUSION_CFG = {
    "rrf_k": 60,
    "dense_weight": 0.3,   # 评估标定（2026-07-31）：MiniLM 中文语义噪声大，满权重稀释 FTS5
    "sparse_weight": 1.0,
    "keyword_weight": 1.0,
    "colbert_weight": 1.0,
    "hybrid_dense_weight": 0.6,
    "hybrid_sparse_weight": 0.4,
    "rerank_dense_weight": 1.0,
    "rerank_sparse_weight": 0.2,
    "recall_multiplier": 2,
    "keyword_min_recall": 3,
}


def _merge_fusion_cfg(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    """将配置中的 fusion 段与默认值合并，未配置的键取默认。"""
    merged = dict(DEFAULT_FUSION_CFG)
    if raw:
        for k, v in raw.items():
            if k in merged and v is not None:
                merged[k] = v
    return merged


# ── 知识库作用域（逻辑分库，2026-08-06 多 Agent 知识库分权）─────────
# 语料 source 前缀天然划分知识域：
#   user:majors/         专业库（1821 条）
#   user:universities/   院校库（393 条）
#   user:employment/     就业库（32 条）
#   user:guides/         策略指南（19 条）
#   user:policies/       政策库（15 条）
#   user:README.md       元数据（7 条）
# kb_scope 参数（None=全库；或前缀列表）用于把检索限定到某个 Agent
# 的知识域（逻辑分库，而非物理分库——单库 + source 过滤，维护成本最低）。
KB_SCOPES = {
    "majors": ["user:majors/"],
    "universities": ["user:universities/"],
    "employment": ["user:employment/"],
    "guides": ["user:guides/"],
    "policies": ["user:policies/"],
    "xuefeng": ["user:xuefeng/"],   # 张雪峰对话语料（2026-08-06，synthesis 风格锚点）
    "web": ["user:web/"],           # write_agent 写入的联网检索结果
}


def _normalize_scope(scope) -> List[str] | None:
    """把 kb_scope 归一为前缀列表；None / 空 = 全库。

    支持：None、单个键名（"majors"）、多个键名（["employment","majors"]）、
    直接前缀（"user:employment/"）。
    """
    if scope is None:
        return None
    if isinstance(scope, str):
        scope = [scope]
    prefixes: List[str] = []
    for item in scope:
        item = (item or "").strip()
        if not item:
            continue
        if item.startswith("user:"):
            prefixes.append(item if item.endswith("/") else item + "/")
        elif item in KB_SCOPES:
            prefixes.extend(KB_SCOPES[item])
    return prefixes or None


def _in_scope(source: str, prefixes: List[str] | None) -> bool:
    """source 是否落在知识域前缀内（prefixes=None = 全库放行）"""
    if prefixes is None:
        return True
    return any(source.startswith(p) for p in prefixes)


class RAGTools:
    def __init__(
        self,
        backend: str = "local_file",
        index_path: Path | None = None,
        milvus_cfg: Dict[str, Any] | None = None,
        es_cfg: Dict[str, Any] | None = None,
        vector_store=None,
        use_multi_embedding: bool = False,
        fusion_cfg: Dict[str, Any] | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.backend = backend
        self.milvus_cfg = milvus_cfg or {}
        self.es_cfg = es_cfg or {}
        self.fusion = _merge_fusion_cfg(fusion_cfg)
        self._vector_store = vector_store
        self._multi_embed_store = None
        index_path = index_path or (root / "data" / "vector_store" / "zx_experience.json")
        if index_path.exists():
            self._docs: List[Dict[str, str]] = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            self._docs = [
                {"source": "2023年6月直播切片", "text": "医学周期长、成本高，家庭预算必须先算清楚。"},
                {"source": "2024年咨询复盘", "text": "分数边缘不要硬冲热门，先保底再谈理想。"},
                {"source": "经典语录整理", "text": "报志愿是策略问题，不是情绪问题。"},
            ]
        
        # 初始化多维Embedding存储
        if use_multi_embedding:
            try:
                from tools.multi_embedding_store import MultiEmbeddingStore
                self._multi_embed_store = MultiEmbeddingStore(
                    rrf_k=self.fusion["rrf_k"],
                    weights={
                        "dense": self.fusion["dense_weight"],
                        "sparse": self.fusion["sparse_weight"],
                        "colbert": self.fusion["colbert_weight"],
                    },
                )
                self._multi_embed_store.build_index(self._docs)
            except Exception as e:
                print(f"[WARN] 多维Embedding初始化失败，使用传统检索: {e}")
                self._multi_embed_store = None

    @classmethod
    def from_config(cls, config: Dict[str, Any] | None, vector_store=None) -> "RAGTools":
        if not config:
            return cls(vector_store=vector_store)
        backend = config.get("backend", "local_file")
        index_rel_path = config.get("index_path", "data/vector_store/zx_experience.json")
        milvus_cfg = config.get("milvus", {})
        es_cfg = config.get("elasticsearch", {})
        use_multi_embedding = config.get("use_multi_embedding", False)
        fusion_cfg = config.get("fusion", {})
        root = Path(__file__).resolve().parents[1]
        index_path = root / index_rel_path
        return cls(
            backend=backend,
            index_path=index_path,
            milvus_cfg=milvus_cfg,
            es_cfg=es_cfg,
            vector_store=vector_store,
            use_multi_embedding=use_multi_embedding,
            fusion_cfg=fusion_cfg,
        )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """中英混合分词（P1-7 修复）：原 `re.split(r"\\W+")` 对中文近乎无效
        （整个中文句被当作单 token，dense/sparse 打分全部失真）。

        策略：CJK 按字符级切分（中文信息密度高，字符级即可覆盖绝大多数
        领域词命中），英文/数字保留单词级。与 multi_embedding_store 的
        BM25 字符级分词保持一致。
        """
        cjk = re.findall(r"[\u4e00-\u9fff]", text)
        tokens: List[str] = cjk
        tokens.extend(t for t in re.split(r"\s+", text.lower()) if re.search(r"[a-z0-9]", t))
        return tokens

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

    def _hybrid_recall(self, query: str, prefixes: List[str] | None = None) -> List[Tuple[float, Dict[str, str]]]:
        ranked = []
        w_dense = float(self.fusion["hybrid_dense_weight"])
        w_sparse = float(self.fusion["hybrid_sparse_weight"])
        for item in self._docs:
            if not _in_scope(item.get("source", ""), prefixes):
                continue
            text = item.get("text", "")
            dense = self._dense_score(query, text)
            sparse = self._sparse_score(query, text)
            score = w_dense * dense + w_sparse * sparse
            ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return ranked

    def _rerank(self, query: str, candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
        w_dense = float(self.fusion["rerank_dense_weight"])
        w_sparse = float(self.fusion["rerank_sparse_weight"])

        def rerank_score(doc: Dict[str, str]) -> float:
            text = doc.get("text", "")
            return w_dense * self._dense_score(query, text) + w_sparse * self._sparse_score(query, text)

        return sorted(candidates, key=rerank_score, reverse=True)

    def _local_search(
        self,
        query: str,
        top_k: int,
        prefixes: List[str] | None = None,
    ) -> List[Dict[str, str]]:
        """本地搜索 - RRF混合融合（并行执行三路检索）

        prefixes（知识域前缀）非 None 时只检索该知识域内的文档（逻辑分库）。
        """
        # 优先使用多维Embedding检索
        if self._multi_embed_store:
            try:
                multi_results = self._multi_embed_store.search(query, top_k)
                if multi_results:
                    return [r for r in multi_results if _in_scope(r.get("source", ""), prefixes)]
            except Exception:
                pass

        # 降级到传统三路检索
        recall_mult = max(int(self.fusion["recall_multiplier"]), 1)
        keyword_min = max(int(self.fusion["keyword_min_recall"]), 1)
        embedding_results = self._search_embedding(query, top_k * recall_mult, prefixes)
        fts_results = self._search_fts5(query, top_k * recall_mult, prefixes)
        recalled = self._hybrid_recall(query, prefixes)
        keyword_docs = [doc for _, doc in recalled[:max(top_k * recall_mult, keyword_min)]]
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
        k: int | None = None,
    ) -> List[Dict[str, str]]:
        """RRF (Reciprocal Rank Fusion) 混合融合排序算法

        score = w_dense/(k+rank_vector) + w_sparse/(k+rank_fts5) + w_keyword/(k+rank_keyword)
        k=60 为标准参数（可用 fusion.rrf_k 配置）
        """
        k = int(k if k is not None else self.fusion["rrf_k"])
        w_dense = float(self.fusion["dense_weight"])
        w_sparse = float(self.fusion["sparse_weight"])
        w_keyword = float(self.fusion["keyword_weight"])

        # 构建文档到排名的映射
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, str]] = {}

        # 向量检索结果
        for rank, doc in enumerate(vector_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + w_dense / (k + rank)
            doc_map[key] = doc

        # FTS5检索结果
        for rank, doc in enumerate(fts_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + w_sparse / (k + rank)
            if key not in doc_map:
                doc_map[key] = doc

        # 关键词召回结果
        for rank, doc in enumerate(keyword_results, 1):
            key = f"{doc.get('source', '')}::{doc.get('text', '')[:50]}"
            doc_scores[key] = doc_scores.get(key, 0) + w_keyword / (k + rank)
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

    def _search_embedding(
        self, query: str, top_k: int, prefixes: List[str] | None = None
    ) -> List[Dict[str, str]]:
        """ChromaDB embedding 向量语义检索（prefixes 非 None 时用 where 限定知识域）"""
        if not self._vector_store:
            return []
        try:
            results = self._vector_store.query(query, top_k=top_k, source_prefixes=prefixes)
            if results:
                return [{"source": r.get("source", ""), "text": r.get("text", "")} for r in results]
        except Exception:
            pass
        return []

    def _search_fts5(
        self, query: str, top_k: int, prefixes: List[str] | None = None
    ) -> List[Dict[str, str]]:
        """SQLite FTS5 全文检索（P1-7 修复：trigram tokenizer 适配）

        FTS5 trigram 要求查询短语 ≥3 字符，否则匹配为空；
        对 <3 字符的短查询降级到 LIKE 兜底，避免短词（如"医学"两字）漏召回。
        prefixes 非 None 时附加 source LIKE 条件限定知识域（逻辑分库）。
        """
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).resolve().parents[1] / "data" / "zx_advisor.db"
            if not db_path.exists():
                return []
            conn = sqlite3.connect(str(db_path))
            try:
                scope_clause = ""
                scope_params: tuple = ()
                if prefixes:
                    # 多个前缀用 OR 拼接 source LIKE 'user:majors/%' ...
                    like_clauses = " OR ".join(["source LIKE ?"] * len(prefixes))
                    scope_clause = f" AND ({like_clauses})"
                    scope_params = tuple(f"{p}%" for p in prefixes)

                # trigram：查询词 ≥3 字符时用 MATCH；否则 LIKE 兜底
                stripped = query.strip()
                if len(stripped) >= 3:
                    rows = conn.execute(
                        f"SELECT source, text FROM rag_fts WHERE rag_fts MATCH ?{scope_clause} ORDER BY rank LIMIT ?",
                        (stripped,) + scope_params + (top_k,),
                    ).fetchall()
                else:
                    like = f"%{stripped}%"
                    params: tuple = (like, like) + scope_params + (top_k,)
                    rows = conn.execute(
                        f"SELECT source, text FROM rag_fts WHERE (text LIKE ? OR source LIKE ?){scope_clause} LIMIT ?",
                        params,
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
        """⚠️ 未启用（2026-08-06 标注）：仅 backend="milvus_es" 时被调，
        当前配置 backend=local_file，本方法与 _search_from_es 均为死路径。
        启用条件：语料规模 >5 万条 / 多实例共享向量库时，把配置切为 milvus_es
        并补集成测试（当前 Milvus 侧只有 build 时双写、无读路径测试）。"""
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

    def query_zx_experience(self, query: str, top_k: int = 3, kb_scope=None) -> str:
        selected = self.query_zx_experience_top_docs(query, top_k, kb_scope)
        return "\n".join([f"[来源：{item['source']}] {item['text']}" for item in selected])

    async def query_zx_experience_async(self, query: str, top_k: int = 3, kb_scope=None) -> str:
        """异步版本的查询方法，支持并行执行（kb_scope 见 query_zx_experience_top_docs）"""
        return await asyncio.to_thread(self.query_zx_experience, query, top_k, kb_scope)

    def query_zx_experience_top_docs(
        self, query: str, top_k: int = 3, kb_scope=None
    ) -> List[Dict[str, str]]:
        """结构化召回（P1-12 RAG 评估用）：返回文档列表而非拼接字符串。

        与 query_zx_experience 共用同一检索路径，保证评估结果即线上效果。

        kb_scope（2026-08-06 知识库分权）：
          None = 全库；"majors"/"universities"/"employment"/"guides"/"policies"
          或前缀列表 ["user:employment/", "user:majors/"]。
        跨库兜底：scope 内无结果时自动 fallback 全库，并在每个文档上打
        `fallback_cross_kb: True` 标记，供评估体系统计"多少查询靠跨库救回"。
        """
        prefixes = _normalize_scope(kb_scope)
        if self.backend == "milvus_es":
            selected = self._search_milvus_es(query, top_k)
            if not selected:
                selected = self._local_search(query, top_k, prefixes)
        else:
            selected = self._local_search(query, top_k, prefixes)

        # 跨库兜底：scope 内无结果 → 全库重查 + 标记（不静默）
        if prefixes and not selected:
            fallback = self._local_search(query, top_k, None)
            if fallback:
                for doc in fallback:
                    doc["fallback_cross_kb"] = True
                selected = fallback
        return selected
