"""
RAG 异步任务
"""
from __future__ import annotations

import logging
from pathlib import Path

from celery_app import app

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


@app.task(name="tasks.rag_tasks.build_rag_index", bind=True, max_retries=2)
def build_rag_index(self) -> dict:
    """异步构建 RAG 索引"""
    try:
        from scripts.build_rag_index import main as build_index
        build_index()

        json_path = ROOT / "data" / "vector_store" / "zx_experience.json"
        if json_path.exists():
            import json
            docs = json.loads(json_path.read_text(encoding="utf-8"))
            return {"ok": True, "doc_count": len(docs)}
        return {"ok": True, "doc_count": 0}
    except Exception as exc:
        logger.exception("RAG 索引构建失败")
        raise self.retry(exc=exc, countdown=60)


@app.task(name="tasks.rag_tasks.sync_to_chromadb")
def sync_to_chromadb() -> dict:
    """从 JSON 同步到 ChromaDB"""
    try:
        import json
        from tools.vector_store import ChromaVectorStore

        json_path = ROOT / "data" / "vector_store" / "zx_experience.json"
        if not json_path.exists():
            return {"ok": False, "error": "zx_experience.json 不存在"}

        docs = json.loads(json_path.read_text(encoding="utf-8"))
        store = ChromaVectorStore()
        count = store.rebuild(docs)
        return {"ok": True, "synced_count": count}
    except Exception as e:
        logger.exception("ChromaDB 同步失败")
        return {"ok": False, "error": str(e)}
