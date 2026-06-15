from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from core.routing_tuner import apply_tuning, load_tuning, merge_keywords, suggest_tuning


def test_merge_keywords():
    result = merge_keywords(["就业", "考公"], ["考公", "薪资"])
    assert result == ["就业", "考公", "薪资"]


def test_suggest_tuning_routing_miss():
    cases = [
        {
            "user_query": "投档线多少",
            "tags": ["路由错了"],
        }
    ]
    suggestion = suggest_tuning(cases)
    assert "diff" in suggestion


def test_apply_tuning_dry_run(tmp_path, monkeypatch):
    tuning_path = tmp_path / "routing_tuning.yaml"
    tuning_path.write_text("fallback_keywords:\n  match_agent: []\n", encoding="utf-8")
    monkeypatch.setattr("core.routing_tuner.TUNING_PATH", tuning_path)

    result = apply_tuning({"match_agent": ["投档线"]}, approve=False)
    assert result["applied"] is False
    assert "投档线" in result["preview"]["match_agent"]

    result2 = apply_tuning({"match_agent": ["投档线"]}, approve=True)
    assert result2["applied"] is True
    data = yaml.safe_load(tuning_path.read_text(encoding="utf-8"))
    assert "投档线" in data["fallback_keywords"]["match_agent"]


def test_load_tuning_defaults():
    tuning = load_tuning()
    assert "match_agent" in tuning
