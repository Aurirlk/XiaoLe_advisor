from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERSIST_DIR = ROOT / "data" / "chroma_db"
DEFAULT_COLLECTION_NAME = "zx_experience"

# ── Embedding 模型统一（P1-9）───────────────────────────────────
# 模型名一律从 tools/embedding_config 单一真源解析（vector_config.yaml
# 的 vector.embedding_model，支持 ${ENV_VAR}），此处不再各自硬编码，
# 杜绝 MiniLM(384维) 与 BGE-M3(1024维) 双向量空间不互通的问题。
# 本地目录优先：若 data/models/<model> 已存在则用本地路径（离线可用）。
from tools.embedding_config import resolve_embedding_model

DEFAULT_EMBEDDING_MODEL_NAME = resolve_embedding_model()
_LOCAL_MODEL_DIR = ROOT / "data" / "models" / DEFAULT_EMBEDDING_MODEL_NAME
DEFAULT_EMBEDDING_MODEL = str(_LOCAL_MODEL_DIR) if _LOCAL_MODEL_DIR.exists() else DEFAULT_EMBEDDING_MODEL_NAME


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        # 环境缺陷修复（chromadb 1.5.9 + Windows）：
        #   Rust 后端对绝对路径解析 hnsw 段失败（报 "Error loading hnsw index"），
        #   相对路径（相对项目根）正常。统一转成项目根相对路径，
        #   保证写入/读取/跨进程行为一致。
        persist_dir = self._normalize_persist_dir(persist_dir)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        # ── 本地优先（P1-9）：模型名先查 data/models/，命中则用本地路径 ──
        # 避免每次 SentenceTransformer(name) 联网访问 HuggingFace 导致启动超时。
        resolved_model = self._resolve_local_model_path(embedding_model)

        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._embedding_model_name = resolved_model
        # 非默认 settings 会触发 SharedSystemClient identifier 冲突（同路径不同
        # settings 报 ValueError），统一用默认 settings。
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine", "hnsw:sync_threshold": 100},
        )
        self._embedding_model = None  # 懒加载，首次使用时才加载

    @staticmethod
    def _normalize_persist_dir(persist_dir: str | Path | None) -> str:
        """把持久化目录统一为『项目根相对路径』（Windows 分隔符 bug 规避）。"""
        ROOT = Path(__file__).resolve().parents[1]
        p = Path(persist_dir or DEFAULT_PERSIST_DIR)
        if p.is_absolute():
            try:
                p = p.resolve().relative_to(ROOT)
            except ValueError:
                # 项目外目录：退回绝对路径（无法相对化）
                return str(p.resolve())
        return p.as_posix()

    @staticmethod
    def _resolve_local_model_path(model: str) -> str:
        """若 data/models/<模型名> 存在，返回本地路径（离线可用），否则原样返回。"""
        name = str(model).strip()
        if name and not Path(name).exists():
            local = ROOT / "data" / "models" / name
            if local.exists():
                return str(local)
        return name

    def _get_embedding_model(self):
        """懒加载 embedding 模型（统一入口 get_embedder，provider 单一真源）"""
        if self._embedding_model is None:
            import logging
            from tools.embedding_config import get_embedder

            logger = logging.getLogger(__name__)
            logger.info(f"首次使用，加载 embedding（{self._embedding_model_name}）")
            self._embedding_model = get_embedder(model=self._embedding_model_name)
            logger.info("embedding 加载完成")
        return self._embedding_model

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def count(self) -> int:
        return self._collection.count()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        model = self._get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        # SentenceTransformer 返回 ndarray；SiliconFlowEmbedder 返回 list，统一转 list
        return embeddings.tolist() if hasattr(embeddings, "tolist") else list(embeddings)

    def add_documents(
        self,
        documents: List[Dict[str, str]],
        batch_size: int = 64,
        id_key: Optional[str] = None,
    ) -> int:
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [doc["text"] for doc in batch]
            sources = [doc.get("source", "") for doc in batch]
            embeddings = self._embed(texts)
            if id_key and id_key in batch[0]:
                ids = [str(doc[id_key]) for doc in batch]
            else:
                ids = [f"doc_{total + j}" for j in range(len(batch))]
            metadatas = []
            for doc in batch:
                meta = {"source": doc.get("source", "")}
                for k, v in doc.items():
                    if k.startswith("meta_") and v is not None:
                        meta[k[5:]] = str(v)
                metadatas.append(meta)
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            total += len(batch)
        return total

    def upsert_documents(
        self,
        documents: List[Dict[str, str]],
        batch_size: int = 64,
        id_key: str = "id",
    ) -> int:
        """Insert or update documents using stable ids (e.g. url_hash)."""
        if not documents:
            return 0
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [doc["text"] for doc in batch]
            ids = [str(doc[id_key]) for doc in batch]
            embeddings = self._embed(texts)
            metadatas = []
            for doc in batch:
                meta = {"source": doc.get("source", "")}
                for k, v in doc.items():
                    if k.startswith("meta_") and v is not None:
                        meta[k[5:]] = str(v)
                metadatas.append(meta)
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            total += len(batch)
        return total

    def query(
        self,
        query: str,
        top_k: int = 3,
        source_prefixes: list[str] | None = None,
    ) -> List[Dict[str, str]]:
        if self._collection.count() == 0:
            return []

        query_embedding = self._embed([query])
        # 逻辑分库：source_prefixes 非 None 时用 where 限定知识域（source 前缀匹配）
        where: dict | None = None
        if source_prefixes:
            where = {"$or": [{"source": {"$like": f"{p}%"}} for p in source_prefixes]}
        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where,
        )
        items: List[Dict[str, str]] = []
        for i in range(len(results.get("ids", [[]])[0])):
            doc = results.get("documents", [[]])[0][i] if results.get("documents") else ""
            meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
            source = meta.get("source", "") if isinstance(meta, dict) else ""
            items.append({"source": source, "text": doc, "score": ""})
        return items

    def rebuild(
        self,
        documents: List[Dict[str, str]],
    ) -> int:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self.add_documents(documents)

    def delete_collection(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def close(self) -> None:
        """显式关闭 Chroma 系统（flush hnsw 索引）。

        环境缺陷修复：chromadb 1.5.x Rust 后端在进程退出时不保证 hnsw 段
        落盘完整，跨进程重新打开会报 "Error loading hnsw index"。
        写入/重建后必须调用本方法（幂等）。
        """
        try:
            system = getattr(self._client, "_system", None)
            if system is not None:
                system.stop()
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collection_name": self._collection_name,
            "document_count": self._collection.count(),
            "persist_dir": self._persist_dir,
            "embedding_model": str(self._embedding_model),
        }

    @staticmethod
    def collection_has_data(
        persist_dir: str | Path | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> bool:
        persist_dir = ChromaVectorStore._normalize_persist_dir(persist_dir)
        if not Path(persist_dir).exists():
            return False
        try:
            # 与 __init__ 一致：默认 settings + 项目根相对路径
            client = chromadb.PersistentClient(path=persist_dir)
            collection = client.get_collection(collection_name)
            return collection.count() > 0
        except Exception:
            return False

    @classmethod
    def from_config(cls, config: Dict[str, Any] | None) -> "ChromaVectorStore":
        if not config:
            return cls()
        return cls(
            persist_dir=config.get("persist_dir"),
            collection_name=config.get("collection_name", DEFAULT_COLLECTION_NAME),
            embedding_model=config.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
        )
