from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import os
import subprocess
import sys
import threading
import time
import webbrowser

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.routers.chat_router import router as chat_router
from api.routers.stream_router import router as stream_router
from api.routers.rag_router import router as rag_router
from api.routers.web_router import router as web_router


ROOT = Path(__file__).resolve().parents[1]
RAG_INDEX_PATH = ROOT / "data" / "vector_store" / "zx_experience.json"


class ServiceStatus(BaseModel):
    ok: bool
    started_at: float
    uptime_seconds: float
    rag_index_exists: bool
    graph_ready: bool
    db_ready: bool
    redis_ready: bool
    vector_ready: bool
    notes: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    started_at = time.time()
    app.state.started_at = started_at
    app.state.notes = []
    app.state.graph_ready = False
    app.state.db_ready = False
    app.state.redis_ready = False
    app.state.vector_ready = False

    # 1) 确保本地 RAG 索引存在
    try:
        if not RAG_INDEX_PATH.exists():
            from scripts.build_rag_index import main as build_rag_index_main

            build_rag_index_main()
            app.state.notes.append("RAG 索引不存在，已自动生成 zx_experience.json。")
    except Exception:
        app.state.notes.append("RAG 索引生成失败（已降级，不阻断启动）。")

    # 2) 确保本地 SQLite 数据库就绪
    try:
        from scripts.init_sqlite import init_sqlite

        init_sqlite()
        app.state.notes.append("SQLite 数据库已就绪。")
    except Exception:
        app.state.notes.append("SQLite 初始化失败（将影响本地 SQL 查询能力）。")

    try:
        from api.dependencies import get_web_search_store

        store = get_web_search_store()
        await store.ensure_tables()
        app.state.notes.append("联网查询缓存表已就绪。")
    except Exception:
        app.state.notes.append("联网查询表初始化失败（已降级，不影响启动）。")

    # 3) ChromaDB 向量库自动同步（懒加载模型，避免每次启动 ~13s 开销）
    try:
        from tools.vector_store import ChromaVectorStore

        if ChromaVectorStore.collection_has_data():
            app.state.vector_ready = True
            app.state.notes.append("向量数据库已就绪（从磁盘缓存加载）。")
        elif RAG_INDEX_PATH.exists():
            from api.dependencies import get_vector_store
            import json

            store = get_vector_store()
            docs = json.loads(RAG_INDEX_PATH.read_text(encoding="utf-8"))
            store.add_documents(docs)
            app.state.vector_ready = True
            app.state.notes.append(f"向量数据库已自动同步 {store.count} 条文档。")
        else:
            app.state.vector_ready = False
            app.state.notes.append("向量数据库暂无数据，将在首次查询时初始化。")
    except Exception:
        app.state.notes.append("向量数据库初始化失败（已降级，不阻断启动）。")

    # 4) 依赖自检与预热（并行执行，单条失败不阻塞全局）
    async def _check_db():
        try:
            from api.dependencies import get_db_engine
            _ = get_db_engine()
            app.state.db_ready = True
        except Exception:
            app.state.notes.append("数据库引擎初始化失败（将影响 SQL 查询能力）。")

    async def _check_redis():
        try:
            from api.dependencies import get_redis_client
            redis = get_redis_client()
            await asyncio.wait_for(redis.ping(), timeout=1.5)
            app.state.redis_ready = True
        except Exception:
            app.state.notes.append("Redis 连接失败（本地模式不影响核心功能）。")

    async def _check_graph():
        try:
            from api.dependencies import get_compiled_graph
            _ = get_compiled_graph()
            app.state.graph_ready = True
        except Exception:
            app.state.notes.append("LangGraph 编译/预热失败（将影响核心对话流程）。")

    await asyncio.gather(_check_db(), _check_redis(), _check_graph(), return_exceptions=True)

    yield


app = FastAPI(title="ZX AI Advisor", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(stream_router)
app.include_router(rag_router)
app.include_router(web_router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "ZX AI Advisor",
        "version": app.version,
        "docs": "/docs",
        "healthz": "/healthz",
        "status": "/status",
        "endpoints": {
            "stream": "/stream/advice",
            "chat_save": "/chat/message",
            "chat_history": "/chat/history/{session_id}",
            "rag_ingest": "/rag/ingest",
            "rag_rebuild": "/rag/rebuild",
            "rag_stats": "/rag/stats",
            "rag_sync": "/rag/sync-from-json",
            "rag_scan": "/rag/scan-documents",
            "rag_upload": "/rag/upload",
            "web_search": "/web/search",
            "web_sessions": "/web/sessions",
        },
    }


@app.get("/status", response_model=ServiceStatus, tags=["meta"])
async def status():
    started_at = float(getattr(app.state, "started_at", time.time()))
    uptime = time.time() - started_at
    notes = list(getattr(app.state, "notes", []))
    return ServiceStatus(
        ok=True,
        started_at=started_at,
        uptime_seconds=uptime,
        rag_index_exists=RAG_INDEX_PATH.exists(),
        graph_ready=bool(getattr(app.state, "graph_ready", False)),
        db_ready=bool(getattr(app.state, "db_ready", False)),
        redis_ready=bool(getattr(app.state, "redis_ready", False)),
        vector_ready=bool(getattr(app.state, "vector_ready", False)),
        notes=notes,
    )


if __name__ == "__main__":
    import uvicorn
    from api.flask_ui import create_flask_ui

    run_tests_on_start = os.getenv("RUN_TESTS_ON_START", "0") == "1"
    if run_tests_on_start:
        subprocess.run([sys.executable, "-m", "pytest"], check=True)

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "1") == "1"

    ui_host = os.getenv("UI_HOST", "127.0.0.1")
    ui_port = int(os.getenv("UI_PORT", "5000"))
    api_base_url = os.getenv("UI_API_BASE_URL", f"http://127.0.0.1:{port}")
    auto_open_ui = os.getenv("AUTO_OPEN_UI", "1") == "1"

    flask_ui = create_flask_ui(api_base_url=api_base_url)

    def _run_flask_ui() -> None:
        flask_ui.run(host=ui_host, port=ui_port, debug=False, use_reloader=False)

    threading.Thread(target=_run_flask_ui, daemon=True).start()

    if auto_open_ui:
        webbrowser.open(f"http://{ui_host}:{ui_port}")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )
