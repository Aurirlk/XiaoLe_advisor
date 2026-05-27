"""
Checkpoint 管理器 — 多轮对话状态持久化与 Thread 隔离

提供两种后端:
- MemorySaver: 内存存储 (开发/测试用, 重启丢失)
- SqliteSaver: SQLite 持久化 (生产用, 重启保留)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE_PATH = ROOT / "data" / "checkpoints.db"


class CheckpointManager:
    def __init__(self, backend: str = "memory", db_path: str | Path | None = None) -> None:
        self.backend = backend
        self._db_path = str(db_path or _DEFAULT_SQLITE_PATH)
        self._saver: BaseCheckpointSaver | None = None

    def get_saver(self) -> BaseCheckpointSaver:
        if self._saver is not None:
            return self._saver

        if self.backend == "sqlite":
            self._saver = self._build_sqlite_saver()
        else:
            self._saver = MemorySaver()
        return self._saver

    def _build_sqlite_saver(self) -> BaseCheckpointSaver:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError:
            return MemorySaver()
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver.from_conn_string(self._db_path)

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
