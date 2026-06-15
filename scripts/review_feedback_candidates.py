"""
审核 feedback_candidates.json 并合并到黄金评测集。

用法:
  python -m scripts.review_feedback_candidates --list
  python -m scripts.review_feedback_candidates --approve fb_20260529_001 --target golden
  python -m scripts.review_feedback_candidates --approve fb_20260529_001 --target routing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "eval" / "feedback_candidates.json"
GOLDEN_PATH = ROOT / "data" / "eval" / "golden_dataset.json"
ROUTING_PATH = ROOT / "data" / "eval" / "routing_golden.json"


def _load(path: Path):
    if not path.exists():
        return [] if path.name.endswith(".json") and "routing" not in path.name else {"cases": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Review feedback candidates")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--approve", type=str, help="candidate id")
    parser.add_argument("--target", choices=["golden", "routing"], default="golden")
    parser.add_argument("--expected-route", default="match_agent")
    args = parser.parse_args()

    candidates = _load(CANDIDATES_PATH)
    if not isinstance(candidates, list):
        candidates = []

    if args.list:
        pending = [c for c in candidates if c.get("status") == "pending_review"]
        print(json.dumps(pending, ensure_ascii=False, indent=2))
        return

    if not args.approve:
        parser.print_help()
        return

    candidate = next((c for c in candidates if c.get("id") == args.approve), None)
    if not candidate:
        print(f"Candidate not found: {args.approve}")
        sys.exit(1)

    if args.target == "golden":
        golden = _load(GOLDEN_PATH)
        if not isinstance(golden, list):
            golden = []
        golden.append({
            "id": candidate["id"],
            "query": candidate.get("query", ""),
            "expected_keywords": candidate.get("suggested_expected_keywords", []),
            "persona_keywords": ["建议", "风险"],
            "source": "feedback",
            "source_turn_id": candidate.get("source_turn_id", ""),
            "original_tags": candidate.get("tags", []),
        })
        GOLDEN_PATH.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        routing = _load(ROUTING_PATH)
        cases = routing.get("cases", [])
        cases.append({
            "id": candidate["id"],
            "category": "feedback_routing",
            "query": candidate.get("query", ""),
            "profile": {},
            "expected_fallback": args.expected_route,
            "expected_llm": args.expected_route,
            "reason": "from negative feedback",
            "source_turn_id": candidate.get("source_turn_id", ""),
            "original_tags": candidate.get("tags", []),
        })
        routing["cases"] = cases
        ROUTING_PATH.write_text(json.dumps(routing, ensure_ascii=False, indent=2), encoding="utf-8")

    for item in candidates:
        if item.get("id") == args.approve:
            item["status"] = "approved"
    CANDIDATES_PATH.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Approved {args.approve} -> {args.target}")


if __name__ == "__main__":
    main()
