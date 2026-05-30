from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERSIST_DIR = ROOT / "data" / "chroma_db"
DEFAULT_COLLECTION_NAME = "zx_experience"
DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        persist_dir = Path(persist_dir or DEFAULT_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._persist_dir = str(persist_dir)
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._embedding_model = SentenceTransformer(embedding_model)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def count(self) -> int:
        return self._collection.count()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._embedding_model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

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
    ) -> List[Dict[str, str]]:
        if self._collection.count() == 0:
            return []

        query_embedding = self._embed([query])
        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
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
        persist_dir = Path(persist_dir or DEFAULT_PERSIST_DIR)
        if not persist_dir.exists():
            return False
        try:
            client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
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
