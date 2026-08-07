"""
张雪峰对话语料知识库（2026-08-06 实现）

用途：雪峰对话历史的语料知识库——把直播/访谈/语录切块入库，
按专业关键字 + 向量混合检索，作为 synthesis_agent 的风格锚点。

技术选型（用户指定 + 面试叙事）：
- **Milvus 后端**（面试 JD 要求：向量库 Milvus/FAISS/PGVector 部署与优化）
  - pymilvus 3.0 已装；Milvus 服务通过 `MILVUS_ENABLED=1` 开启
  - 服务不可达时自动降级本地 Chroma（`user:xuefeng/` 域），保证可跑
- **学科 embedding 模型**：复用全项目统一 embedding（tools/embedding_config
  单一真源），保证与主 RAG 向量空间一致
- **对话切块**：按对话轮次边界切（每轮一问一答为一块），单块超长再按句切，
  与主 RAG 的长度分块策略区分（对话语料走"轮次/语义"边界）

库结构：
- Chroma collection `zx_xuefeng`（本地降级）
- Milvus collection `zx_xuefeng`（field: id/source/text/vector，HNSW）
- JSON 索引 `data/vector_store/xuefeng_corpus.json`（真相源）
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "vector_store" / "xuefeng_corpus.json"
XUEFENG_COLLECTION = "zx_xuefeng"
MAX_TURN_CHARS = 800  # 单轮对话块上限（超长按句切）


def _split_turns(text: str) -> list[str]:
    """对话切块：按轮次边界切（问句/答句模式），超长再按句切。

    简单启发式：按换行分段，每段作为一个对话轮；段落超长按句号切。
    （更精确的轮次识别依赖语料格式，这里保留通用入口，语料入库脚本可自定义。）
    """
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    turns: list[str] = []
    for para in paragraphs:
        if len(para) <= MAX_TURN_CHARS:
            turns.append(para)
        else:
            # 超长段按句切
            sentences = re.split(r"(?<=[。！？])", para)
            buf = ""
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(buf) + len(s) <= MAX_TURN_CHARS:
                    buf += s
                else:
                    if buf:
                        turns.append(buf)
                    buf = s
            if buf:
                turns.append(buf)
    return turns


def _normalize_query(query: str) -> str:
    """专业关键字归一化：去空白、统一标点（供关键字路检索）。"""
    return re.sub(r"\s+", "", query).strip()


class XuefengStore:
    """雪峰对话语料知识库：Milvus 优先，Chroma 降级，JSON 真相源。"""

    def __init__(
        self,
        corpus_path: Path | None = None,
        embedding_model: str | None = None,
        use_milvus: bool | None = None,
        milvus_cfg: Dict[str, Any] | None = None,
    ) -> None:
        self._corpus_path = corpus_path or CORPUS_PATH
        self._use_milvus = (
            os.getenv("MILVUS_ENABLED", "0").lower() in ("1", "true", "yes")
            if use_milvus is None
            else use_milvus
        )
        self._milvus_cfg = milvus_cfg or {
            "host": os.getenv("MILVUS_HOST", "localhost"),
            "port": int(os.getenv("MILVUS_PORT", "19530")),
        }
        self._embedding_model_name = embedding_model
        self._embedder = None          # SentenceTransformer（懒加载）
        self._chroma_store = None      # ChromaVectorStore（降级）
        self._milvus_client = None     # pymilvus MilvusClient（优先）
        self._milvus_ready: Optional[bool] = None
        self._docs: List[Dict[str, str]] = []

    # ── 数据加载 ────────────────────────────────────────────

    def load_corpus(self) -> List[Dict[str, str]]:
        """加载语料 JSON（真相源）。结构：[{source, text}]"""
        if not self._corpus_path.exists():
            return []
        try:
            return json.loads(self._corpus_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("雪峰语料解析失败", exc_info=True)
            return []

    # ── embedding（懒加载，复用统一模型）─────────────────────

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            from tools.embedding_config import resolve_embedding_model

            model_name = self._embedding_model_name or resolve_embedding_model()
            # 本地优先（防联网超时）
            local = ROOT / "data" / "models" / model_name
            model_ref = str(local) if local.exists() else model_name
            self._embedder = SentenceTransformer(model_ref)
        return self._embedder

    def _embed(self, texts: List[str]) -> List[List[float]]:
        model = self._get_embedder()
        return model.encode(texts, normalize_embeddings=True).tolist()

    # ── Milvus 后端（可切换，面试叙事核心）───────────────────

    def _get_milvus(self):
        """返回 MilvusClient；不可用返回 None（调用方降级 Chroma）。"""
        if self._milvus_ready is not None:
            return self._milvus_client if self._milvus_ready else None
        if not self._use_milvus:
            self._milvus_ready = False
            return None
        try:
            from pymilvus import MilvusClient

            client = MilvusClient(
                uri=f"http://{self._milvus_cfg['host']}:{self._milvus_cfg['port']}"
            )
            # 探活
            client.list_collections()
            self._milvus_client = client
            self._milvus_ready = True
            logger.info("[XuefengStore] Milvus 连接成功 %s:%s",
                        self._milvus_cfg["host"], self._milvus_cfg["port"])
            return client
        except Exception as e:
            self._milvus_ready = False
            logger.warning("[XuefengStore] Milvus 不可用（降级 Chroma）: %s", str(e)[:80])
            return None

    def _ensure_milvus_collection(self, client, dim: int) -> None:
        """幂等创建 Milvus 集合（HNSW 索引）。"""
        if client.has_collection(XUEFENG_COLLECTION):
            return
        client.create_collection(
            collection_name=XUEFENG_COLLECTION,
            dimension=dim,
            metric_type="COSINE",
            auto_id=False,
        )
        client.create_index(
            collection_name=XUEFENG_COLLECTION,
            index_params={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
        logger.info("[XuefengStore] Milvus 集合 %s 已创建（dim=%d）", XUEFENG_COLLECTION, dim)

    # ── Chroma 降级后端 ─────────────────────────────────────

    def _get_chroma(self):
        if self._chroma_store is None:
            from tools.vector_store import ChromaVectorStore

            self._chroma_store = ChromaVectorStore(
                persist_dir=ROOT / "data" / "chroma_db",
                collection_name=XUEFENG_COLLECTION,
                embedding_model=self._embedding_model_name,
            )
        return self._chroma_store

    # ── 入库 ────────────────────────────────────────────────

    def build_corpus(self, dialogues: List[Dict[str, str]], force: bool = False) -> Dict[str, Any]:
        """把对话语料切块入库（JSON 真相源 + Milvus/Chroma）。

        dialogues: [{source: "2023直播#1", text: "完整对话文本"}]
        """
        # 1. 切块
        chunks: List[Dict[str, str]] = []
        for item in dialogues:
            source_base = item.get("source", "xuefeng")
            text = item.get("text", "")
            if not text.strip():
                continue
            turns = _split_turns(text)
            for i, turn in enumerate(turns, 1):
                chunks.append({"source": f"{source_base}#turn{i}", "text": turn})

        if not chunks:
            return {"ok": False, "reason": "语料切块后为空"}

        # 2. JSON 真相源
        self._corpus_path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.load_corpus() if not force else []
        existing_sources = {d.get("source") for d in existing}
        new_chunks = [c for c in chunks if c["source"] not in existing_sources]
        if not new_chunks:
            return {"ok": True, "written": 0, "skipped": len(chunks), "reason": "全部已存在"}
        self._corpus_path.write_text(
            json.dumps(existing + new_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 3. 向量入库（Milvus 优先 / Chroma 降级）
        texts = [c["text"] for c in new_chunks]
        vectors = self._embed(texts)
        dim = len(vectors[0])

        milvus_client = self._get_milvus()
        written = 0
        if milvus_client is not None:
            try:
                self._ensure_milvus_collection(milvus_client, dim)
                rows = [
                    {"id": i, "source": c["source"], "text": c["text"], "vector": vectors[i]}
                    for i, c in enumerate(new_chunks)
                ]
                milvus_client.insert(collection_name=XUEFENG_COLLECTION, data=rows)
                written = len(rows)
                logger.info("[XuefengStore] Milvus 写入 %d 条", written)
            except Exception:
                logger.warning("[XuefengStore] Milvus 写入失败（JSON 已落盘）", exc_info=True)
                written = 0
        if written == 0:
            try:
                chroma = self._get_chroma()
                written = chroma.add_documents(new_chunks)
                logger.info("[XuefengStore] Chroma 降级写入 %d 条", written)
            except Exception:
                logger.warning("[XuefengStore] Chroma 写入失败（JSON 已落盘）", exc_info=True)

        return {
            "ok": True, "written": len(new_chunks), "skipped": len(chunks) - len(new_chunks),
            "backend": "milvus" if milvus_client is not None else "chroma",
            "source_count": len(dialogues),
        }

    # ── 检索（专业关键字 + 向量混合）─────────────────────────

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """检索雪峰语料：向量召回 + 专业关键字过滤/加成。

        专业关键字策略：query 中的领域词（专业名/分数/位次等）先做关键字
        命中筛选——语料块含该词则优先；否则退回纯向量召回。
        """
        if not self._docs:
            self._docs = self.load_corpus()
        if not self._docs:
            return []

        # 关键字路：从 query 的中文串拆出 2-3 字窗口词（"学医要多少钱" →
        # "学医"/"医要"/"多少"），保证能命中语料中的局部词（"学医周期长"）。
        norm_query = _normalize_query(query)
        cjk_runs = re.findall(r"[\u4e00-\u9fff]+", norm_query)
        keywords: List[str] = []
        for run in cjk_runs:
            for i in range(len(run)):
                if len(run) - i >= 2:
                    keywords.append(run[i:i + 2])   # 2 字窗口
                if len(run) - i >= 3:
                    keywords.append(run[i:i + 3])   # 3 字窗口
        # 去重保序、限量
        seen_kw = set()
        keywords = [k for k in keywords if not (k in seen_kw or seen_kw.add(k))][:8]
        kw_hits: List[Dict[str, str]] = []
        if keywords:
            for doc in self._docs:
                if any(kw in doc["text"] for kw in keywords):
                    kw_hits.append(doc)

        # 向量路
        vec_hits: List[Dict[str, str]] = []
        try:
            query_vec = self._embed([query])[0]
            milvus_client = self._get_milvus()
            if milvus_client is not None and milvus_client.has_collection(XUEFENG_COLLECTION):
                res = milvus_client.search(
                    collection_name=XUEFENG_COLLECTION,
                    data=[query_vec],
                    limit=top_k,
                    output_fields=["source", "text"],
                )
                for hit in (res[0] if res else []):
                    entity = hit.get("entity", {})
                    vec_hits.append({
                        "source": entity.get("source", ""),
                        "text": entity.get("text", ""),
                        "score": round(float(hit.get("distance", 0)), 4),
                    })
            else:
                chroma = self._get_chroma()
                results = chroma.query(query, top_k=top_k, source_prefixes=["user:xuefeng/"])
                vec_hits.extend(results)
        except Exception:
            logger.warning("[XuefengStore] 向量检索失败，仅用关键字", exc_info=True)

        # 混合排序：关键字命中优先，向量兜底
        seen = set()
        merged: List[Dict[str, str]] = []
        for doc in kw_hits[:top_k]:
            key = doc.get("source", "")
            if key not in seen:
                seen.add(key)
                doc = dict(doc)
                doc["match"] = "keyword"
                merged.append(doc)
        for doc in vec_hits:
            key = doc.get("source", "")
            if key not in seen and len(merged) < top_k:
                seen.add(key)
                doc = dict(doc)
                doc.setdefault("match", "vector")
                merged.append(doc)
        return merged[:top_k]
