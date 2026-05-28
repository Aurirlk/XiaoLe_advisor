from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.dependencies import get_compiled_graph

DATASET_PATH = ROOT / "data" / "eval" / "golden_dataset.json"
REPORT_PATH = ROOT / "data" / "eval" / "golden_eval_report.json"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _score_case(answer: str, case: dict[str, Any]) -> dict[str, Any]:
    expected_keywords = case.get("expected_keywords", [])
    persona_keywords = case.get("persona_keywords", [])

    faithfulness_hit = _contains_any(answer, expected_keywords)
    persona_hit = _contains_any(answer, persona_keywords)

    return {
        "id": case.get("id", "unknown"),
        "query": case.get("query", ""),
        "answer": answer,
        "faithfulness_pass": faithfulness_hit,
        "persona_pass": persona_hit,
        "score": int(faithfulness_hit) + int(persona_hit),
    }


async def _run_single(graph, query: str) -> str:
    init_state = {"user_query": query, "messages": [{"role": "user", "content": query}]}
    result = await graph.ainvoke(init_state, config={"recursion_limit": 10})
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return str(last.get("content", ""))


async def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"未找到黄金测试集: {DATASET_PATH}")

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    graph = get_compiled_graph()
    results: list[dict[str, Any]] = []

    for case in dataset:
        answer = await _run_single(graph, case.get("query", ""))
        results.append(_score_case(answer, case))

    total = len(results)
    faithfulness_pass = sum(1 for item in results if item["faithfulness_pass"])
    persona_pass = sum(1 for item in results if item["persona_pass"])
    avg_score = round(sum(item["score"] for item in results) / max(total, 1), 3)

    report = {
        "total_cases": total,
        "faithfulness_pass_rate": round(faithfulness_pass / max(total, 1), 3),
        "persona_pass_rate": round(persona_pass / max(total, 1), 3),
        "avg_score": avg_score,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"评测完成，共 {total} 条。")
    print(f"Faithfulness 通过率: {report['faithfulness_pass_rate']}")
    print(f"Persona 通过率: {report['persona_pass_rate']}")
    print(f"报告已写入: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
