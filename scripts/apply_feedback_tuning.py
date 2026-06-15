"""
基于负反馈半自动调优路由关键词。

用法:
  python -m scripts.apply_feedback_tuning --dry-run
  python -m scripts.apply_feedback_tuning --approve
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.dependencies import get_feedback_store
from core.routing_tuner import apply_tuning, suggest_tuning


async def _run(approve: bool) -> None:
    store = get_feedback_store()
    await store.ensure_tables()
    negative = await store.list_negative_feedback(days=30)
    suggestion = suggest_tuning(negative)
    print(json.dumps(suggestion, ensure_ascii=False, indent=2))

    merged: dict[str, list[str]] = {}
    for agent, payload in suggestion.get("diff", {}).items():
        merged[agent] = payload.get("add", [])

    if not merged:
        print("No routing tuning suggestions.")
        return

    result = apply_tuning(merged, approve=approve)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply feedback-based routing tuning")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    parser.add_argument("--approve", action="store_true", help="写入 routing_tuning.yaml")
    args = parser.parse_args()
    approve = bool(args.approve)
    asyncio.run(_run(approve=approve))


if __name__ == "__main__":
    main()
