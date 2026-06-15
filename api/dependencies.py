from functools import lru_cache
from pathlib import Path
import os

from redis.asyncio import Redis
import yaml
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.checkpoint_manager import CheckpointManager
from core.conversation_turn_store import ConversationTurnStore
from core.crm_manager import CRMProfileManager
from core.feedback_analyzer import append_negative_feedback_candidate
from core.feedback_store import FeedbackStore
from core.web_search_service import WebSearchService
from core.web_search_store import WebSearchStore
from tools.rag_tools import RAGTools
from tools.vector_store import ChromaVectorStore, DEFAULT_EMBEDDING_MODEL, DEFAULT_PERSIST_DIR

ROOT = Path(__file__).resolve().parents[1]

_crm_manager: CRMProfileManager | None = None


def _load_user_config() -> dict | None:
    """加载用户配置文件 .config.yaml，不存在则返回 None。"""
    config_path = ROOT / "configs" / ".config.yaml"
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_api_key(raw: str) -> str:
    """解析 api_key，支持 ${ENV_VAR} 语法。"""
    if raw.startswith("${") and raw.endswith("}"):
        return os.getenv(raw[2:-1], "")
    return raw


def load_llm_config() -> dict:
    """加载 LLM 配置。

    流程：
    1. 从 .config.yaml 读取 selected_module.LLM（预设名）
    2. 从 llm_config.yaml 的 presets 中查找该预设的详情
    3. api_key 优先用 .config.yaml 的 api_keys 覆盖

    如果 .config.yaml 中 LLM 段有内联配置（旧格式），直接使用。
    """
    user_cfg = _load_user_config() or {}

    # 尝试从 .config.yaml 内联配置加载（旧格式兼容）
    llm_section = user_cfg.get("LLM", {})
    selected = user_cfg.get("selected_module", {}).get("LLM", "")
    if selected and selected in llm_section and isinstance(llm_section[selected], dict) and "model_name" in llm_section[selected]:
        preset = llm_section[selected]
        return _build_llm_result(preset, user_cfg)

    # 新格式：从 llm_config.yaml 查找预设
    llm_cfg_path = ROOT / "configs" / "llm_config.yaml"
    if llm_cfg_path.exists():
        with open(llm_cfg_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)["llm"]
        presets = raw.get("presets", {})
        defaults = raw.get("defaults", {})
        # 用 selected_module 的值，或 llm_config.yaml 自己的 active
        target = selected or raw.get("active", "")
        if target and target in presets:
            preset = presets[target]
            return _build_llm_result(preset, user_cfg, defaults)

    raise ValueError(f"无法加载 LLM 配置：selected_module.LLM='{selected}' 在 llm_config.yaml 中未找到")


def _build_llm_result(preset: dict, user_cfg: dict, defaults: dict | None = None) -> dict:
    """从预设配置构建统一的 LLM 结果 dict"""
    defaults = defaults or {}
    api_keys = user_cfg.get("api_keys", {})
    # 优先用预设自己的 api_key，再用 .config.yaml 的 api_keys 覆盖
    raw_key = preset.get("api_key", "")
    # 从预设的 api_key 中提取 env var 名，去 api_keys 查找
    if raw_key.startswith("${") and raw_key.endswith("}"):
        env_name = raw_key[2:-1]
        override = api_keys.get(env_name, "")
        if override:
            raw_key = override
    api_key = _resolve_api_key(raw_key)
    return {
        "model_name": preset.get("model_name") or preset.get("model", ""),
        "temperature": preset.get("temperature", defaults.get("temperature", 0.7)),
        "base_url": preset.get("base_url") or preset.get("url"),
        "api_key": api_key,
        "timeout": defaults.get("timeout", 60),
        "max_tokens": defaults.get("max_tokens", 4096),
        "description": preset.get("description", ""),
    }


def list_model_presets() -> list[dict]:
    """列出所有可用的模型预设（供前端/API 使用）。"""
    user_cfg = _load_user_config() or {}
    selected = user_cfg.get("selected_module", {}).get("LLM", "")

    # 从 llm_config.yaml 读取预设列表
    llm_cfg_path = ROOT / "configs" / "llm_config.yaml"
    if not llm_cfg_path.exists():
        return []

    with open(llm_cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)["llm"]

    presets = raw.get("presets") or raw.get("model_presets", {})
    if not presets:
        return [{"name": "default", "model": raw.get("model", ""), "description": "旧版单模型配置"}]

    # selected_module 优先，否则用 llm_config.yaml 自己的 active
    active = selected or raw.get("active", "")
    return [
        {
            "name": name,
            "model": cfg.get("model_name") or cfg.get("model", ""),
            "provider": cfg.get("type", ""),
            "description": cfg.get("description", ""),
            "is_active": name == active,
        }
        for name, cfg in presets.items()
    ]


@lru_cache(maxsize=1)
def get_db_engine() -> AsyncEngine:
    with open(ROOT / "configs" / "db_config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["postgres"]
    password = os.getenv(cfg["password_env"], "")
    dsn = (
        f"postgresql+asyncpg://{cfg['user']}:{password}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )
    return create_async_engine(dsn, pool_size=cfg["pool_size"], max_overflow=cfg.get("max_overflow", 10))


@lru_cache(maxsize=1)
def get_compiled_graph():
    from core.graph_builder import build_graph

    llm_cfg = load_llm_config()
    llm = ChatOpenAI(
        model=llm_cfg["model_name"],
        temperature=llm_cfg["temperature"],
        base_url=llm_cfg.get("base_url") or None,
        api_key=llm_cfg.get("api_key", ""),
        timeout=llm_cfg["timeout"],
    )
    rag_cfg_path = ROOT / "configs" / "rag_config.yaml"
    rag_cfg = None
    if rag_cfg_path.exists():
        with open(rag_cfg_path, "r", encoding="utf-8") as f:
            rag_cfg = yaml.safe_load(f).get("rag", {})
    rag_tools = RAGTools.from_config(rag_cfg, vector_store=get_vector_store())

    checkpointer = get_checkpoint_manager().get_saver()
    crm = get_crm_manager()
    return build_graph(
        get_db_engine(),
        llm,
        rag_tools,
        checkpointer=checkpointer,
        on_conversation_end=_make_crm_callback(crm),
        web_search_service=get_web_search_service(),
        feedback_store=get_feedback_store(),
    )


@lru_cache(maxsize=1)
def get_checkpoint_manager() -> CheckpointManager:
    backend = os.getenv("CHECKPOINT_BACKEND", "memory")
    return CheckpointManager(backend=backend)


def get_crm_manager() -> CRMProfileManager:
    global _crm_manager
    if _crm_manager is None:
        _crm_manager = CRMProfileManager(get_sqlite_engine())
    return _crm_manager


def _make_crm_callback(crm: CRMProfileManager):
    async def _on_conversation_end(state) -> None:
        phone = (state.get("phone_number") or "").strip()
        profile = state.get("user_profile") or {}
        if not phone:
            return
        last_intent = state.get("next_node", "")
        last_query = state.get("user_query", "")
        await crm.save_profile(phone, profile, last_query, last_intent)
    return _on_conversation_end


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    with open(ROOT / "configs" / "db_config.yaml", "r", encoding="utf-8") as f:
        redis_cfg = yaml.safe_load(f)["redis"]
    return Redis(
        host=redis_cfg["host"],
        port=redis_cfg["port"],
        db=redis_cfg["db"],
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        socket_keepalive=True,
        retry_on_timeout=False,
    )


@lru_cache(maxsize=1)
def get_sqlite_engine() -> AsyncEngine:
    with open(ROOT / "configs" / "db_config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["sqlite"]
    db_path = ROOT / cfg["path"]
    dsn = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    return create_async_engine(dsn, echo=False)


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    cfg_path = ROOT / "configs" / "vector_config.yaml"
    cfg = {}
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f).get("vector", {})
    return ChromaVectorStore.from_config(cfg)


@lru_cache(maxsize=1)
def get_web_search_store() -> WebSearchStore:
    return WebSearchStore(get_sqlite_engine())


@lru_cache(maxsize=1)
def get_web_vector_store() -> ChromaVectorStore:
    from core.web_search_service import WebSearchConfig

    cfg_path = ROOT / "configs" / "vector_config.yaml"
    vector_cfg: dict = {}
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            vector_cfg = yaml.safe_load(f).get("vector", {}) or {}
    ws_cfg = WebSearchConfig.load()
    collection = vector_cfg.get("web_cache_collection", ws_cfg.vector_collection)
    return ChromaVectorStore(
        persist_dir=vector_cfg.get("persist_dir", DEFAULT_PERSIST_DIR),
        collection_name=collection,
        embedding_model=vector_cfg.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
    )


@lru_cache(maxsize=1)
def get_web_search_service() -> WebSearchService:
    return WebSearchService(
        store=get_web_search_store(),
        vector_store=get_web_vector_store(),
    )


@lru_cache(maxsize=1)
def get_rag_tools() -> RAGTools:
    rag_cfg_path = ROOT / "configs" / "rag_config.yaml"
    rag_cfg = {}
    if rag_cfg_path.exists():
        with open(rag_cfg_path, "r", encoding="utf-8") as f:
            rag_cfg = yaml.safe_load(f).get("rag", {})
    return RAGTools.from_config(rag_cfg)


@lru_cache(maxsize=1)
def get_conversation_turn_store() -> ConversationTurnStore:
    return ConversationTurnStore(get_sqlite_engine())


@lru_cache(maxsize=1)
def get_feedback_store() -> FeedbackStore:
    return FeedbackStore(get_sqlite_engine())


def get_feedback_analyzer_callback():
    async def _on_negative(
        turn_id: str,
        query: str,
        bad_answer: str,
        tags: list,
    ) -> None:
        append_negative_feedback_candidate(turn_id, query, bad_answer, tags)

    return _on_negative


# ── Neo4j 知识图谱 ──

_neo4j_driver = None


def get_neo4j_driver():
    """获取Neo4j驱动（懒加载，单例模式）"""
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver
    
    try:
        from neo4j import GraphDatabase
        
        config_path = ROOT / "configs" / "neo4j_config.yaml"
        if not config_path.exists():
            return None
        
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f).get("neo4j", {})
        
        if not cfg:
            return None
        
        _neo4j_driver = GraphDatabase.driver(
            cfg.get("uri", "bolt://localhost:7687"),
            auth=(cfg.get("username", "neo4j"), cfg.get("password", "password")),
            max_connection_lifetime=cfg.get("max_connection_lifetime", 3600),
            max_connection_pool_size=cfg.get("max_connection_pool_size", 50),
        )
        return _neo4j_driver
    except Exception:
        return None
