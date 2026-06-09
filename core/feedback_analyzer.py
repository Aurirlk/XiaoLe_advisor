from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "eval" / "feedback_candidates.json"


def _load_candidates() -> List[Dict[str, Any]]:
    if not CANDIDATES_PATH.exists():
        return []
    return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))


def _save_candidates(items: List[Dict[str, Any]]) -> None:
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_negative_feedback_candidate(
    turn_id: str,
    query: str,
    bad_answer: str,
    tags: List[str],
) -> Dict[str, Any]:
    items = _load_candidates()
    existing_ids = {item.get("source_turn_id") for item in items}
    if turn_id in existing_ids:
        return next(i for i in items if i.get("source_turn_id") == turn_id)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    candidate_id = f"fb_{ts}_{len(items) + 1:03d}"
    candidate = {
        "id": candidate_id,
        "source_turn_id": turn_id,
        "query": query,
        "bad_answer": bad_answer[:2000],
        "tags": tags,
        "suggested_expected_keywords": [],
        "status": "pending_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    items.append(candidate)
    _save_candidates(items)
    return candidate


def list_pending_candidates() -> List[Dict[str, Any]]:
    return [c for c in _load_candidates() if c.get("status") == "pending_review"]
