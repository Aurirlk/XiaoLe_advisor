from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core import feedback_analyzer as fa


def test_append_negative_feedback_candidate(tmp_path, monkeypatch):
    candidates_path = tmp_path / "feedback_candidates.json"
    monkeypatch.setattr(fa, "CANDIDATES_PATH", candidates_path)

    c1 = fa.append_negative_feedback_candidate(
        "turn-x",
        "广东省物理类多少分",
        "建议再考虑",
        ["太端水"],
    )
    assert c1["status"] == "pending_review"

    c2 = fa.append_negative_feedback_candidate(
        "turn-x",
        "广东省物理类多少分",
        "建议再考虑",
        ["太端水"],
    )
    assert c2["id"] == c1["id"]

    items = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert len(items) == 1
