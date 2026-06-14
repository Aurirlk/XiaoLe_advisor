from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple

_buffers: Dict[str, List[str]] = defaultdict(list)
_timestamps: Dict[str, float] = {}

_MAX_SESSIONS = 500
_TTL_SECONDS = 3600  # 1 hour


def push_status(session_id: str, message: str) -> None:
    if not session_id or not message:
        return
    _buffers[session_id].append(message)
    _timestamps[session_id] = time.monotonic()
    _evict_stale()


def drain_status(session_id: str) -> List[str]:
    msgs = _buffers.pop(session_id, [])
    _timestamps.pop(session_id, None)
    return msgs


def _evict_stale() -> None:
    now = time.monotonic()
    if len(_buffers) <= _MAX_SESSIONS:
        return
    expired = [sid for sid, ts in _timestamps.items() if now - ts > _TTL_SECONDS]
    for sid in expired:
        _buffers.pop(sid, None)
        _timestamps.pop(sid, None)
    # If still over limit after TTL eviction, remove oldest
    if len(_buffers) > _MAX_SESSIONS:
        oldest = sorted(_timestamps, key=_timestamps.get)[:len(_buffers) - _MAX_SESSIONS]
        for sid in oldest:
            _buffers.pop(sid, None)
            _timestamps.pop(sid, None)
