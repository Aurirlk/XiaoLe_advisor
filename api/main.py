from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import asyncio
from contextlib import asynccontextmanager
import os
import subprocess
import sys
import time
import webbrowser

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from api.routers.chat_router import router as chat_router
from api.routers.stream_router import router as stream_router
from api.routers.admin_router import router as admin_router
from api.routers.feedback_router import router as feedback_router
from api.routers.settings_router import router as settings_router
from api.routers.ws_router import router as ws_router
from api.routers.auth_router import router as auth_router
from api.routers.questionnaire_router import router as questionnaire_router
from api.routers.ranking_router import router as ranking_router
from api.routers.harness_router import router as harness_router
from api.routers.admin_crud_router import router as admin_crud_router
from api.routers.user_notification_router import router as user_notification_router
from api.routers.zhihu_router import router as zhihu_router
from api.routers.web_search_router import router as web_search_router
from api.routers.career_path_router import router as career_path_router

# 按需加载的模块（根据 enabled_modules 配置决定是否导入）
_optional_routers = {}


def _load_optional_routers():
    """根据配置延迟加载可选 router，避免无用依赖阻塞启动"""
    import yaml
    config_path = ROOT / "configs" / ".config.yaml"
    enabled = {"voice": True, "vision": True, "knowledge_graph": True, "rag": True, "web_search": True}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        enabled.update(cfg.get("enabled_modules", {}))

    if enabled.get("rag", True):
        from api.routers.rag_router import router as rag_router
        _optional_routers["rag"] = rag_router

    if enabled.get("web_search", True):
        from api.routers.web_router import router as web_router
        _optional_routers["web_search"] = web_router

    if enabled.get("voice", True):
        from api.routers.voice_router import router as voice_router
        _optional_routers["voice"] = voice_router

    if enabled.get("vision", True):
        from api.routers.vision_router import router as vision_router
        _optional_routers["vision"] = vision_router

    if enabled.get("knowledge_graph", True):
        from api.routers.graph_router import router as graph_router
        _optional_routers["knowledge_graph"] = graph_router


ROOT = Path(__file__).resolve().parents[1]
RAG_INDEX_PATH = ROOT / "data" / "vector_store" / "zx_experience.json"

# ==================== 模块管理（已拆分到 module_manager.py）====================
from api.module_manager import (
    MODULE_STATUS,
    MODULE_LOAD_PROGRESS,
    get_enabled_modules as _get_enabled_modules,
    save_enabled_modules as _save_enabled_modules,
    get_user_module_overrides as _get_user_module_overrides,
    save_user_module_overrides as _save_user_module_overrides,
    resolve_effective_modules as _resolve_effective_modules,
    set_module_status as _set_module_status,
    set_started_at as _set_started_at,
    log_progress as _log_progress_mod,
)


class ServiceStatus(BaseModel):
    ok: bool
    started_at: float
    uptime_seconds: float
    rag_index_exists: bool
    graph_ready: bool
    db_ready: bool
    redis_ready: bool
    vector_ready: bool
    modules: dict = {}  # 模块状态
    load_progress: list = []  # 加载日志
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

    # 设置启动时间戳
    _set_started_at(started_at)

    # 获取启用的模块配置
    enabled = _get_enabled_modules()
    
    from api.module_manager import log_progress as _log_progress_mod

    def _log_progress(msg: str, success: bool = True):
        """记录加载进度（写入模块管理器和 app.state）"""
        _log_progress_mod(msg, success, started_at)
        app.state.notes.append(msg)

    # ==================== 阶段 1：核心模块加载 ====================
    _log_progress("[START] 开始预加载...")
    
    # 加载可选 router
    _load_optional_routers()
    for name, r in _optional_routers.items():
        _set_module_status(name, loaded=True)
        _log_progress(f"[OK] 模块 [{name}] 加载成功")
    for name in ["voice", "vision", "knowledge_graph", "rag", "web_search"]:
        if name not in _optional_routers and enabled.get(name, False):
            _set_module_status(name, loaded=False, error="跳过加载")
            _log_progress(f"[SKIP] 模块 [{name}] 已禁用", success=False)

    # ==================== 阶段 2：数据库初始化 ====================
    _log_progress("[DB] 初始化数据库...")
    
    # SQLite（快速）
    try:
        from scripts.init_sqlite import init_sqlite
        init_sqlite()
        MODULE_STATUS["sqlite"] = {"loaded": True, "error": None, "load_time": 0}
        _log_progress("[OK] SQLite 数据库就绪")
    except Exception as e:
        MODULE_STATUS["sqlite"] = {"loaded": False, "error": str(e), "load_time": 0}
        _log_progress(f"[ERROR] SQLite 初始化失败: {e}", success=False)

    # 联网查询/反馈表
    try:
        from api.dependencies import get_web_search_store, get_conversation_turn_store, get_feedback_store
        store = get_web_search_store()
        await store.ensure_tables()
        turn_store = get_conversation_turn_store()
        await turn_store.ensure_tables()
        feedback_store = get_feedback_store()
        await feedback_store.ensure_tables()
        MODULE_STATUS["stores"] = {"loaded": True, "error": None, "load_time": 0}
        _log_progress("[OK] 联网查询/反馈表就绪")
    except Exception as e:
        MODULE_STATUS["stores"] = {"loaded": False, "error": str(e), "load_time": 0}
        _log_progress(f"[ERROR] 表初始化失败: {e}", success=False)

    # ==================== 阶段 3：RAG 索引 ====================
    if "rag" in _optional_routers:
        _log_progress("[RAG] 检查 RAG 索引...")
        try:
            if not RAG_INDEX_PATH.exists():
                from scripts.build_rag_index import main as build_rag_index_main
                build_rag_index_main()
                MODULE_STATUS["rag_index"] = {"loaded": True, "error": None, "load_time": 0}
                _log_progress("[OK] RAG 索引已生成")
            else:
                MODULE_STATUS["rag_index"] = {"loaded": True, "error": None, "load_time": 0}
                _log_progress("[OK] RAG 索引已存在")
        except Exception as e:
            MODULE_STATUS["rag_index"] = {"loaded": False, "error": str(e), "load_time": 0}
            _log_progress(f"[ERROR] RAG 索引生成失败: {e}", success=False)

    # ==================== 阶段 4：向量库（后台异步） ====================
    if "rag" in _optional_routers:
        async def _sync_vector():
            try:
                import json
                from api.dependencies import get_vector_store
                from tools.vector_store import ChromaVectorStore
                store = get_vector_store()

                # ── P1-7 修复：原逻辑「collection_has_data 非空即跳过」──
                # 曾导致 2287 条语料只同步 10 条后永不补齐（向量路接近死亡）。
                # 改为按文档条数比对：语料条数 > 现有条数 则重灌补齐。
                docs = []
                if RAG_INDEX_PATH.exists():
                    docs = json.loads(RAG_INDEX_PATH.read_text(encoding="utf-8"))
                existing = store.count
                if not docs:
                    app.state.vector_ready = bool(existing)
                    MODULE_STATUS["vector"] = {"loaded": True, "error": None, "load_time": 0}
                    _log_progress("[OK] 向量数据库就绪（无语料，仅缓存）")
                elif existing >= len(docs):
                    app.state.vector_ready = True
                    MODULE_STATUS["vector"] = {"loaded": True, "error": None, "load_time": 0}
                    _log_progress(f"[OK] 向量数据库就绪（{existing} 条，与语料一致）")
                else:
                    if existing > 0:
                        _log_progress(f"[INFO] 向量库 {existing} 条 < 语料 {len(docs)} 条，重灌补齐...")
                    store.rebuild(docs)
                    # chromadb 1.5 Rust 后端：写入后必须显式关闭 flush，
                    # 否则 hnsw 段未落盘，跨进程查询报 "Error loading hnsw index"
                    store.close()
                    app.state.vector_ready = True
                    MODULE_STATUS["vector"] = {"loaded": True, "error": None, "load_time": 0}
                    _log_progress(f"[OK] 向量数据库已同步 {store.count} 条")
            except Exception as e:
                MODULE_STATUS["vector"] = {"loaded": False, "error": str(e), "load_time": 0}
                _log_progress(f"[ERROR] 向量数据库失败: {e}", success=False)
        asyncio.create_task(_sync_vector())
        _log_progress("[WAIT] 向量数据库同步中（后台）...")

    # ==================== 阶段 5：依赖检查（并行） ====================
    _log_progress("[CHECK] 检查服务依赖...")
    
    async def _check_db():
        try:
            from api.dependencies import get_db_engine
            _ = get_db_engine()
            app.state.db_ready = True
            MODULE_STATUS["db"] = {"loaded": True, "error": None, "load_time": 0}
            _log_progress("[OK] 数据库引擎就绪")
        except Exception as e:
            MODULE_STATUS["db"] = {"loaded": False, "error": str(e), "load_time": 0}
            _log_progress(f"[ERROR] 数据库引擎失败: {e}", success=False)

    async def _check_redis():
        try:
            from api.dependencies import get_redis_client
            redis = get_redis_client()
            await asyncio.wait_for(redis.ping(), timeout=1.5)
            app.state.redis_ready = True
            MODULE_STATUS["redis"] = {"loaded": True, "error": None, "load_time": 0}
            _log_progress("[OK] Redis 就绪")
        except Exception as e:
            MODULE_STATUS["redis"] = {"loaded": False, "error": str(e), "load_time": 0}
            _log_progress(f"[WARN] Redis 不可用: {e}", success=False)

    async def _check_graph():
        if "knowledge_graph" not in _optional_routers:
            return
        try:
            from api.dependencies import get_compiled_graph, get_checkpoint_manager
            # 生产 Checkpoint 后端（postgres/sqlite）需要异步初始化；memory 为幂等空操作
            await get_checkpoint_manager().aget_saver()
            _ = get_compiled_graph()
            app.state.graph_ready = True
            MODULE_STATUS["graph"] = {"loaded": True, "error": None, "load_time": 0}
            _log_progress("[OK] LangGraph 就绪")
        except Exception as e:
            MODULE_STATUS["graph"] = {"loaded": False, "error": str(e), "load_time": 0}
            _log_progress(f"[ERROR] LangGraph 失败: {e}", success=False)

    await asyncio.gather(_check_db(), _check_redis(), _check_graph(), return_exceptions=True)

    # Checkpoint TTL 清理（可选）：CHECKPOINT_TTL_DAYS > 0 时启用每日后台清理
    _ttl_task = None
    _ttl_days = int(os.getenv("CHECKPOINT_TTL_DAYS", "0") or "0")
    if _ttl_days > 0:
        from api.dependencies import get_checkpoint_manager as _get_cm

        async def _ttl_loop():
            while True:
                try:
                    await _get_cm().cleanup_old_checkpoints(max_age_days=_ttl_days)
                except Exception:
                    logging.getLogger(__name__).exception("Checkpoint TTL 清理失败")
                await asyncio.sleep(24 * 3600)

        _ttl_task = asyncio.create_task(_ttl_loop())
        _log_progress(f"[OK] Checkpoint TTL 清理已启用（保留 {_ttl_days} 天）")

    load_time = time.time() - started_at
    _log_progress(f"[DONE] 预加载完成，耗时 {load_time:.1f}s")

    yield

    if _ttl_task is not None:
        _ttl_task.cancel()


app = FastAPI(title="ZX AI Advisor", version="0.2.0", lifespan=lifespan)

# CORS：默认仅放行本地开发前端；生产必须显式配置 CORS_ALLOW_ORIGINS，禁止 "*"
# （"*" + allow_credentials=True 的组合违反 Fetch 规范，等于对所有站点开放凭据请求）
_cors_origins = [o.strip() for o in os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
).split(",") if o.strip()]
if "*" in _cors_origins:
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("生产环境禁止 CORS_ALLOW_ORIGINS=*，请配置具体域名")
    _cors_kwargs = dict(allow_origins=["*"], allow_credentials=False)
else:
    _cors_kwargs = dict(allow_origins=_cors_origins, allow_credentials=True)

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    **_cors_kwargs,
)

app.include_router(chat_router)
app.include_router(stream_router)
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(settings_router)
app.include_router(ws_router)
app.include_router(auth_router)
app.include_router(questionnaire_router)
app.include_router(ranking_router)
app.include_router(harness_router)
app.include_router(admin_crud_router)
app.include_router(user_notification_router)
app.include_router(zhihu_router)
app.include_router(web_search_router)
app.include_router(career_path_router)
# 可选模块在 lifespan 中根据配置动态加载

# ---------- 前端 SPA 静态服务（Vite 构建产物） ----------
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
_dist_dir = _frontend_dir / "dist"

# 挂载 dist/assets（CSS/JS 静态文件）
if _dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="dist_assets")


@app.get("/{full_path:path}", tags=["ui"])
async def serve_spa(full_path: str = ""):
    """SPA 路由兜底：所有非 API 路由均返回 index.html，由 Vue Router 处理"""
    # 已由 API 路由处理的路径不会到达这里
    index_path = _dist_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>前端未构建。请执行: cd frontend && npm run build</h1>", status_code=200)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/", tags=["ui"], response_class=HTMLResponse)
async def root():
    """SPA 入口"""
    index_path = _dist_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_bytes(), media_type="text/html")
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
        modules=MODULE_STATUS,
        load_progress=MODULE_LOAD_PROGRESS,
        notes=notes,
    )


class SwitchModelRequest(BaseModel):
    preset: str


class ModuleOverrideRequest(BaseModel):
    """用户模块开关请求"""
    module: str
    enabled: bool


class AdminModuleConfigRequest(BaseModel):
    """管理员模块配置请求"""
    modules: dict[str, bool]


@app.get("/modules/status", tags=["modules"])
async def get_module_status():
    """获取所有模块的加载状态（启动进度）"""
    return {
        "ok": True,
        "modules": MODULE_STATUS,
        "load_progress": MODULE_LOAD_PROGRESS,
        "admin_config": {k: v for k, v in _get_enabled_modules().items() if not k.startswith("_")},
        "descriptions": _get_enabled_modules().get("_descriptions", {}),
    }


@app.get("/modules/effective", tags=["modules"])
async def get_effective_modules(session_id: str = Query(None)):
    """获取当前生效的模块配置（考虑用户覆盖）"""
    return {
        "ok": True,
        "effective": _resolve_effective_modules(session_id),
    }


@app.post("/modules/user-override", tags=["modules"])
async def set_user_module_override(payload: ModuleOverrideRequest, session_id: str = Query(...)):
    """用户临时开关某个模块（只影响自己）"""
    overrides = _get_user_module_overrides(session_id)
    overrides[payload.module] = payload.enabled
    _save_user_module_overrides(session_id, overrides)
    return {
        "ok": True,
        "message": f"模块 [{payload.module}] 已{'启用' if payload.enabled else '禁用'}",
        "effective": _resolve_effective_modules(session_id),
    }


@app.get("/admin/modules", tags=["admin"])
async def admin_get_modules():
    """管理员获取模块配置"""
    return {
        "ok": True,
        "config": {k: v for k, v in _get_enabled_modules().items() if not k.startswith("_")},
        "descriptions": _get_enabled_modules().get("_descriptions", {}),
        "status": MODULE_STATUS,
    }


@app.post("/admin/modules", tags=["admin"])
async def admin_set_modules(payload: AdminModuleConfigRequest):
    """管理员设置默认模块配置（影响所有新用户）"""
    admin_config = _get_enabled_modules()
    # 保留描述
    descriptions = admin_config.get("_descriptions", {})
    admin_config.update(payload.modules)
    admin_config["_descriptions"] = descriptions
    _save_enabled_modules(admin_config)
    return {
        "ok": True,
        "message": "模块配置已更新",
        "config": {k: v for k, v in admin_config.items() if not k.startswith("_")},
    }


@app.get("/modules/stream", tags=["modules"])
async def stream_module_progress():
    """SSE 流式推送启动进度（连接后立即推送历史日志 + 实时更新）"""
    from fastapi.responses import StreamingResponse
    import json

    async def event_generator():
        # 先推送已完成的启动日志
        sent = 0
        while sent < len(MODULE_LOAD_PROGRESS):
            log = MODULE_LOAD_PROGRESS[sent]
            yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
            sent += 1

        # 持续监听新日志（轮询，最多等 30s）
        timeout = 300  # 3s × 100 次
        waited = 0
        while waited < timeout:
            while sent < len(MODULE_LOAD_PROGRESS):
                log = MODULE_LOAD_PROGRESS[sent]
                yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
                sent += 1
            # 检查是否所有模块都加载完了
            if all(v.get("loaded") is not None for v in MODULE_STATUS.values()):
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                return
            await asyncio.sleep(1)
            waited += 1

        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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

    run_tests_on_start = os.getenv("RUN_TESTS_ON_START", "0") == "1"
    if run_tests_on_start:
        subprocess.run([sys.executable, "-m", "pytest"], check=True)

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "1") == "1"

    auto_open_ui = os.getenv("AUTO_OPEN_UI", "1") == "1"
    if auto_open_ui:
        webbrowser.open(f"http://127.0.0.1:{port}/")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )
