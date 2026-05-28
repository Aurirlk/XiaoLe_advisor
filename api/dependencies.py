from functools import lru_cache
from pathlib import Path
import os

from redis.asyncio import Redis
import yaml
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.checkpoint_manager import CheckpointManager
from core.crm_manager import CRMProfileManager
from core.web_search_service import WebSearchService
from core.web_search_store import WebSearchStore
from tools.rag_tools import RAGTools
from tools.vector_store import ChromaVectorStore, DEFAULT_EMBEDDING_MODEL, DEFAULT_PERSIST_DIR

ROOT = Path(__file__).resolve().parents[1]

_crm_manager: CRMProfileManager | None = None


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

    with open(ROOT / "configs" / "llm_config.yaml", "r", encoding="utf-8") as f:
        llm_cfg = yaml.safe_load(f)["llm"]
    api_key = os.getenv(llm_cfg["api_key_env"], "")
    llm = ChatOpenAI(
        model=llm_cfg["model"],
        temperature=llm_cfg["temperature"],
        base_url=llm_cfg.get("base_url") or None,
        api_key=api_key,
        timeout=llm_cfg["timeout_seconds"],
    )
    rag_cfg_path = ROOT / "configs" / "rag_config.yaml"
    rag_cfg = None
    if rag_cfg_path.exists():
        with open(rag_cfg_path, "r", encoding="utf-8") as f:
            rag_cfg = yaml.safe_load(f).get("rag", {})
    rag_tools = RAGTools.from_config(rag_cfg)

    checkpointer = get_checkpoint_manager().get_saver()
    crm = get_crm_manager()
    return build_graph(
        get_db_engine(),
        llm,
        rag_tools,
        checkpointer=checkpointer,
        on_conversation_end=_make_crm_callback(crm),
        web_search_service=get_web_search_service(),
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
