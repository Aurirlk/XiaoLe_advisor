"""
Checkpoint 管理器 — 多轮对话状态持久化与 Thread 隔离（交接手册 P0-8）

后端选择（环境变量 CHECKPOINT_BACKEND，小写）：
- memory   ：MemorySaver，进程内存，重启即丢。仅允许开发/测试环境。
- sqlite   ：SQLite 持久化（需 pip install langgraph-checkpoint-sqlite）
- postgres ：PostgreSQL 持久化（需 pip install langgraph-checkpoint-postgres psycopg[binary]），
             生产推荐：多实例共享 + 异步驱动。

生产环境（APP_ENV=production）强制约束（fail-fast，禁止静默降级）：
- 不允许 memory；未显式配置时默认 postgres；缺 DATABASE_URL 直接启动失败。
- 扩展包缺失时抛出 RuntimeError 并给出安装指引，绝不回退到 MemorySaver。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE_PATH = ROOT / "data" / "checkpoints.db"
_DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zx_advisor")


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def _validate_backend(backend: str) -> None:
    """校验后端取值 + 生产环境禁止 memory。"""
    if backend not in ("memory", "sqlite", "postgres"):
        raise RuntimeError(
            f"CHECKPOINT_BACKEND 取值非法: {backend!r}（可选: memory / sqlite / postgres）"
        )
    if _is_production() and backend == "memory":
        raise RuntimeError(
            "生产环境禁止使用 memory Checkpoint 后端（重启丢状态、无多实例隔离）。"
            "请设置 CHECKPOINT_BACKEND=postgres（推荐）或 sqlite，并配置 DATABASE_URL / 数据库文件。"
        )


def _resolve_backend() -> str:
    backend = (os.getenv("CHECKPOINT_BACKEND", "") or "").strip().lower()
    if not backend:
        backend = "postgres" if _is_production() else "memory"
    _validate_backend(backend)
    return backend


class CheckpointManager:
    def __init__(self, backend: str | None = None, db_path: str | Path | None = None,
                 database_url: str | None = None) -> None:
        if backend:
            _validate_backend(backend)
        self.backend = backend or _resolve_backend()
        self._db_path = str(db_path or _DEFAULT_SQLITE_PATH)
        self._database_url = database_url or os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL)
        self._saver: BaseCheckpointSaver | None = None

    # ── 同步接口（兼容旧调用点；postgres 后端必须走 aget_saver）──────────

    def get_saver(self) -> BaseCheckpointSaver:
        if self._saver is not None:
            return self._saver
        if self.backend == "postgres":
            raise RuntimeError(
                "postgres Checkpoint 后端需要异步初始化，请在 FastAPI lifespan（或事件循环内）"
                "调用 await get_checkpoint_manager().aget_saver()，然后再编译图。"
            )
        if self.backend == "sqlite":
            self._saver = self._build_sqlite_saver_sync()
        else:
            self._saver = MemorySaver()
        return self._saver

    # ── 异步接口（生产后端推荐）────────────────────────────────────────

    async def aget_saver(self) -> BaseCheckpointSaver:
        """异步初始化 saver（AsyncSqliteSaver / AsyncPostgresSaver 需要 await setup）。

        幂等：重复调用返回同一实例。
        """
        if self._saver is not None:
            return self._saver

        if self.backend == "sqlite":
            saver = self._build_sqlite_saver_sync()
        elif self.backend == "postgres":
            saver = await self._build_postgres_saver_async()
        else:
            saver = MemorySaver()

        self._saver = saver
        return saver

    # ── 后端构建（缺失依赖一律 fail-fast，不静默降级）───────────────────

    def _build_sqlite_saver_sync(self) -> BaseCheckpointSaver:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError as e:
            raise RuntimeError(
                "sqlite Checkpoint 后端需要额外依赖，请执行："
                "pip install langgraph-checkpoint-sqlite"
            ) from e
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver.from_conn_string(self._db_path)

    async def _build_postgres_saver_async(self) -> BaseCheckpointSaver:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as e:
            raise RuntimeError(
                "postgres Checkpoint 后端需要额外依赖，请执行："
                "pip install langgraph-checkpoint-postgres psycopg[binary]"
            ) from e
        try:
            saver = AsyncPostgresSaver.from_conn_string(self._database_url)
            await saver.setup()  # 建表（CREATE TABLE IF NOT EXISTS）
            return saver
        except Exception as e:
            raise RuntimeError(f"无法连接 PostgreSQL（DATABASE_URL={self._database_url!r}）: {e}") from e

    # ── 配置构造 ────────────────────────────────────────────────────────

    @staticmethod
    def build_config(session_id: str, **extra: Any) -> Dict[str, Any]:
        return {
            "configurable": {
                "thread_id": session_id,
            },
            **extra,
        }

    @staticmethod
    def build_init_state(
        query: str,
        session_id: str = "",
        phone_number: str = "",
        crm_profile: dict | None = None,
    ) -> dict:
        """
        构建每次调用的初始 state payload。

        若提供 crm_profile（从 CRM 加载的历史画像），则作为初始 user_profile
        注入，实现断点续传，避免重复收集画像。
        """
        init = {
            "user_query": query,
            "session_id": session_id,
            "phone_number": phone_number,
            "messages": [{"role": "user", "content": query}],
        }
        if crm_profile:
            init["user_profile"] = crm_profile
        return init

    # ── TTL 清理（建议由定时任务调用；默认保留 30 天）──────────────────

    async def cleanup_old_checkpoints(self, max_age_days: int = 30) -> int:
        """删除超过 max_age_days 的旧 checkpoint（按 metadata.created_at）。

        返回删除行数。memory 后端无操作；sqlite/postgres 后端各按自身表结构删除；
        任何后端实现不兼容时仅告警，不影响主流程。
        """
        if self.backend == "memory":
            return 0
        if self._saver is None:
            return 0

        deleted = 0
        if self.backend == "postgres":
            deleted = await self._cleanup_postgres(max_age_days)
        elif self.backend == "sqlite":
            deleted = await self._cleanup_sqlite(max_age_days)
        if deleted:
            logger.info("Checkpoint TTL 清理完成，删除 %d 行（> %d 天）", deleted, max_age_days)
        return deleted

    async def _cleanup_postgres(self, max_age_days: int) -> int:
        import asyncpg  # 与 AsyncPostgresSaver 同栈
        conn = None
        try:
            conn = await asyncpg.connect(self._database_url)
            rows = await conn.execute(
                """
                DELETE FROM checkpoints
                WHERE (metadata->>'created_at')::timestamptz
                      < now() - make_interval(days => $1)
                """,
                max_age_days,
            )
            return _parse_delete_count(rows)
        except Exception as e:  # 表不存在 / 列结构差异等：仅告警
            logger.warning("Checkpoint TTL 清理（postgres）跳过: %s", e)
            return 0
        finally:
            if conn is not None:
                await conn.close()

    async def _cleanup_sqlite(self, max_age_days: int) -> int:
        import asyncio

        def _run() -> int:
            import sqlite3
            db_path = Path(self._db_path)
            if not db_path.exists():
                return 0
            try:
                conn = sqlite3.connect(str(db_path))
                try:
                    cur = conn.execute(
                        "DELETE FROM checkpoints WHERE json_extract(metadata, '$.created_at') "
                        "< datetime('now', ?)",
                        (f"-{max_age_days} days",),
                    )
                    conn.commit()
                    return cur.rowcount
                finally:
                    conn.close()
            except Exception as e:
                logger.warning("Checkpoint TTL 清理（sqlite）跳过: %s", e)
                return 0

        return await asyncio.to_thread(_run)


def _parse_delete_count(pg_execute_result: str) -> int:
    """asyncpg execute 返回 'DELETE N'，解析 N；解析失败按 0 处理。"""
    try:
        return int(pg_execute_result.rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return 0
