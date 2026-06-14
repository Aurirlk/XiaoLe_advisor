from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
TUNING_PATH = ROOT / "configs" / "routing_tuning.yaml"

DEFAULT_TUNING: Dict[str, List[str]] = {
    "web_search_agent": [],
    "career_agent": [],
    "match_agent": [],
    "profile_agent": [],
    "synthesis_agent": [],
}


def load_tuning() -> Dict[str, List[str]]:
    if not TUNING_PATH.exists():
        return dict(DEFAULT_TUNING)
    data = yaml.safe_load(TUNING_PATH.read_text(encoding="utf-8")) or {}
    keywords = data.get("fallback_keywords", {})
    result = dict(DEFAULT_TUNING)
    for agent, words in keywords.items():
        if isinstance(words, list):
            result[agent] = [str(w) for w in words]
    return result


def merge_keywords(base: List[str], extra: List[str]) -> List[str]:
    seen = set()
    merged: List[str] = []
    for word in base + extra:
        if word and word not in seen:
            seen.add(word)
            merged.append(word)
    return merged


def extract_query_tokens(query: str, min_len: int = 2) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|\d{4}", query)
    return [t for t in tokens if len(t) >= min_len]


def analyze_routing_misses(negative_cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    routing_cases = [
        c for c in negative_cases
        if "路由错了" in (c.get("tags") or [])
    ]
    counter: Counter[str] = Counter()
    for case in routing_cases:
        for token in extract_query_tokens(case.get("user_query", "")):
            counter[token] += 1
    top_tokens = [t for t, _ in counter.most_common(10)]
    return {"match_agent": top_tokens[:5], "career_agent": [], "web_search_agent": []}


def suggest_tuning(negative_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    current = load_tuning()
    suggested_additions = analyze_routing_misses(negative_cases)
    diff: Dict[str, Dict[str, List[str]]] = {}
    for agent, tokens in suggested_additions.items():
        new_tokens = [t for t in tokens if t not in current.get(agent, [])]
        if new_tokens:
            diff[agent] = {"add": new_tokens, "current": current.get(agent, [])}
    return {"diff": diff, "suggested_additions": suggested_additions}


def apply_tuning(suggested: Dict[str, List[str]], approve: bool = False) -> Dict[str, Any]:
    current = load_tuning()
    preview = {}
    for agent, tokens in suggested.items():
        preview[agent] = merge_keywords(current.get(agent, []), tokens)
    if not approve:
        return {"applied": False, "preview": preview}

    TUNING_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fallback_keywords": preview}
    TUNING_PATH.write_text(
        yaml.dump(payload, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return {"applied": True, "preview": preview, "path": str(TUNING_PATH)}
