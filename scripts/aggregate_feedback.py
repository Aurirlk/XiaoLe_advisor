"""
聚合满意度反馈周报。

用法:
  python -m scripts.aggregate_feedback --days 7
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.dependencies import get_conversation_turn_store, get_feedback_store

REPORT_PATH = ROOT / "data" / "eval" / "weekly_feedback_report.json"
PREV_REPORT_PATH = ROOT / "data" / "eval" / "weekly_feedback_report_prev.json"


async def _run(days: int) -> dict:
    feedback_store = get_feedback_store()
    turn_store = get_conversation_turn_store()
    await feedback_store.ensure_tables()
    await turn_store.ensure_tables()

    stats = await feedback_store.get_stats(days=days)
    turn_count = await turn_store.count_turns_since(days)
    feedback_count = stats.get("feedback_count", 0)
    feedback_rate = round(feedback_count / turn_count, 3) if turn_count else 0.0

    prev_delta = {}
    if REPORT_PATH.exists():
        PREV_REPORT_PATH.write_text(REPORT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        prev = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        prev_rate = prev.get("satisfaction_rate", 0)
        prev_delta = {
            "satisfaction_rate_delta": round(stats.get("satisfaction_rate", 0) - prev_rate, 3),
            "feedback_count_delta": feedback_count - prev.get("feedback_count", 0),
        }

    negative = await feedback_store.list_negative_feedback(days=days)
    top_negative_samples = [
        {
            "turn_id": item.get("turn_id"),
            "query": item.get("user_query", "")[:120],
            "tags": item.get("tags", []),
        }
        for item in negative[:5]
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "turn_count": turn_count,
        "feedback_count": feedback_count,
        "feedback_rate": feedback_rate,
        "satisfaction_rate": stats.get("satisfaction_rate", 0),
        "positive_count": stats.get("positive_count", 0),
        "negative_count": stats.get("negative_count", 0),
        "tag_distribution": stats.get("tag_distribution", {}),
        "by_route_path": stats.get("by_route_path", {}),
        "top_negative_samples": top_negative_samples,
        "delta_vs_previous": prev_delta,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate feedback weekly report")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    report = asyncio.run(_run(args.days))
    print(f"Report written to {REPORT_PATH}")
    print(f"turns={report['turn_count']} feedback_rate={report['feedback_rate']}")
    print(f"satisfaction_rate={report['satisfaction_rate']}")


if __name__ == "__main__":
    main()
