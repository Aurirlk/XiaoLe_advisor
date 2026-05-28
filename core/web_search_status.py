from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

_buffers: Dict[str, List[str]] = defaultdict(list)


def push_status(session_id: str, message: str) -> None:
    if not session_id or not message:
        return
    _buffers[session_id].append(message)


def drain_status(session_id: str) -> List[str]:
    msgs = _buffers.pop(session_id, [])
    return msgs
