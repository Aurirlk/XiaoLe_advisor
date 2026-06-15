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
from api.routers.admin_router import router as admin_router
from api.routers.feedback_router import router as feedback_router
from api.routers.voice_router import router as voice_router
from api.routers.settings_router import router as settings_router
from api.routers.ws_router import router as ws_router
from api.routers.vision_router import router as vision_router
from api.routers.auth_router import router as auth_router
from api.routers.questionnaire_router import router as questionnaire_router


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
        from api.dependencies import get_web_search_store, get_conversation_turn_store, get_feedback_store

        store = get_web_search_store()
        await store.ensure_tables()
        turn_store = get_conversation_turn_store()
        await turn_store.ensure_tables()
        feedback_store = get_feedback_store()
        await feedback_store.ensure_tables()
        app.state.notes.append("联网查询缓存表已就绪。")
        app.state.notes.append("对话轮次与反馈表已就绪。")
    except Exception:
        app.state.notes.append("联网查询/反馈表初始化失败（已降级，不影响启动）。")

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
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(voice_router)
app.include_router(settings_router)
app.include_router(ws_router)
app.include_router(vision_router)
app.include_router(auth_router)
app.include_router(questionnaire_router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "小乐AI · 高考志愿填报助手",
        "version": app.version,
        "docs": "/docs",
        "healthz": "/healthz",
        "status": "/status",
        "endpoints": {
            "stream": "/stream/advice",
            "websocket": "/ws/chat",
            "chat_save": "/chat/message",
            "chat_history": "/chat/history/{session_id}",
            "voice_asr": "/voice/asr",
            "voice_tts": "/voice/tts",
            "voice_tts_stream": "ws /voice/tts-stream",
            "voice_status": "/voice/status",
            "vision_analyze": "/vision/analyze",
            "vision_chat": "/vision/chat",
            "feedback": "/feedback",
            "feedback_stats": "/feedback/stats",
            "settings": "/settings",
            "settings_models": "/settings/models",
            "rag_ingest": "/rag/ingest",
            "rag_scan": "/rag/scan-documents",
            "rag_upload": "/rag/upload",
            "rag_stats": "/rag/stats",
            "web_search": "/web/search",
            "web_sessions": "/web/sessions",
            "admin_import": "/admin/import",
            "admin_stats": "/admin/data/stats",
            "admin_switch_model": "/admin/switch-model",
            "admin_cost": "/admin/cost-stats",
            "auth_register": "/auth/register",
            "auth_login": "/auth/login",
            "auth_me": "/auth/me",
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


class SwitchModelRequest(BaseModel):
    preset: str


@app.post("/admin/switch-model", tags=["admin"])
async def switch_model(payload: SwitchModelRequest):
    from api.dependencies import _load_user_config, load_llm_config
    from api.routers.voice_router import reload_voice_providers
    user_cfg_path = ROOT / "configs" / ".config.yaml"
    if not user_cfg_path.exists():
        raise HTTPException(status_code=404, detail=".config.yaml 不存在")
    import yaml
    with open(user_cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if payload.preset not in cfg.get("LLM", {}):
        available = list(cfg.get("LLM", {}).keys())
        raise HTTPException(status_code=400, detail=f"预设 {payload.preset} 不存在，可用: {available}")
    cfg["selected_module"]["LLM"] = payload.preset
    with open(user_cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    try:
        from api.dependencies import get_compiled_graph
        get_compiled_graph.cache_clear()
    except Exception:
        pass
    return {"ok": True, "message": f"已切换到 {payload.preset}", "config": load_llm_config()}


@app.get("/admin/model-presets", tags=["admin"])
async def list_model_presets():
    from api.dependencies import list_model_presets as _list
    return {"ok": True, "presets": _list()}


@app.get("/admin/cost-stats", tags=["admin"])
async def cost_stats(days: int = 30):
    from core.cost_tracker import CostTracker
    tracker = CostTracker()
    daily = tracker.get_daily_usage()
    monthly = tracker.get_monthly_usage()
    return {"ok": True, "daily": daily, "monthly": monthly}


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
