"""
RAG 检索评估（P1-12 修复核心）

对标 RAGAS 的轻量版领域评估：不引入重型依赖，复用现有 RAGTools 检索链路，
产出可对比的检索质量指标：

  - Recall@k     ：golden 相关文档出现在 top-k 的比例（召回率）
  - Precision@k  ：top-k 中 golden 相关文档占比
  - MRR          ：第一个 golden 相关文档的倒数排名
  - NDCG@k       ：排序质量（相关文档越靠前分越高）
  - Faithfulness（可选）：LLM 判定的回答忠于检索上下文的比例
    （需 --faithfulness 且配置 LLM，默认关闭避免烧钱）

用法：
  python scripts/rag_eval/run_rag_eval.py                 # 检索指标
  python scripts/rag_eval/run_rag_eval.py -k 3 5 10       # 自定义 k 集合
  python scripts/rag_eval/run_rag_eval.py --faithfulness  # 追加 LLM 忠实度（需 LLM）
  python scripts/rag_eval/run_rag_eval.py --case 0        # 只���第 0 条用例

退出码：0 = 成功（无论指标高低）；指标打印到 stdout，便于 CI 收集。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# scripts/rag_eval/run_rag_eval.py → 项目根是 parents[2]
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DEFAULT_K_SET = (3, 5, 10)


def _is_golden(doc: dict, case: dict) -> bool:
    """判断检索文档是否命中 golden 标注（source 前缀 or 关键词，任一命中即相关）。"""
    text = (doc.get("text") or "").lower()
    source = (doc.get("source") or "").lower()
    for prefix in case.get("golden_sources", []):
        if prefix.lower() in source:
            return True
    for kw in case.get("golden_keywords", []):
        if kw.lower() in text:
            return True
    return False


def _recall_at_k(ranked: list[dict], case: dict, k: int) -> float:
    hits = sum(1 for doc in ranked[:k] if _is_golden(doc, case))
    return hits / k if k else 0.0


def _precision_at_k(ranked: list[dict], case: dict, k: int) -> float:
    if not k:
        return 0.0
    return sum(1 for doc in ranked[:k] if _is_golden(doc, case)) / min(k, len(ranked) or 1)


def _mrr(ranked: list[dict], case: dict) -> float:
    for i, doc in enumerate(ranked, 1):
        if _is_golden(doc, case):
            return 1.0 / i
    return 0.0


def _dcg_at_k(ranked: list[dict], case: dict, k: int) -> float:
    dcg = 0.0
    for i, doc in enumerate(ranked[:k], 1):
        rel = 1.0 if _is_golden(doc, case) else 0.0
        dcg += rel / math.log2(i + 1)
    return dcg


def _ndcg_at_k(ranked: list[dict], case: dict, k: int) -> float:
    # 理想排序：全部相关
    ideal = 0.0
    for i in range(1, min(k, sum(1 for d in ranked if _is_golden(d, case)) or 1) + 1):
        ideal += 1.0 / math.log2(i + 1)
    if ideal == 0:
        return 0.0
    return _dcg_at_k(ranked, case, k) / ideal


def load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("cases", [])


def build_retriever(backend: str = "local_file"):
    """复用生产 RAG 链路（RAGTools.from_config + 生产同款 ChromaVectorStore）。"""
    import yaml
    from tools.rag_tools import RAGTools
    from tools.vector_store import ChromaVectorStore

    cfg_path = ROOT / "configs" / "rag_config.yaml"
    rag_cfg = {}
    if cfg_path.exists():
        rag_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")).get("rag", {})
    rag_cfg["backend"] = backend

    # 与 api/dependencies.get_vector_store() 同款：读取 vector_config.yaml 构造
    vec_cfg_path = ROOT / "configs" / "vector_config.yaml"
    vec_cfg = {}
    if vec_cfg_path.exists():
        vec_cfg = yaml.safe_load(vec_cfg_path.read_text(encoding="utf-8")).get("vector", {}) or {}
    vector_store = ChromaVectorStore.from_config(vec_cfg)

    return RAGTools.from_config(rag_cfg, vector_store=vector_store)


def run_retrieval_eval(cases: list[dict], k_set: tuple[int, ...], backend: str = "local_file") -> dict:
    """跑检索指标：返回 {k: {...}} + 汇总。"""
    retriever = build_retriever(backend)
    agg = {k: {"recall": 0.0, "precision": 0.0, "ndcg": 0.0} for k in k_set}
    agg["mrr"] = 0.0
    n = len(cases)

    for case in cases:
        query = case["query"]
        try:
            ranked = retriever.query_zx_experience_top_docs(query, top_k=max(k_set))
        except AttributeError:
            # 兜底：旧接口返回字符串时拆回文档结构
            text = retriever.query_zx_experience(query, top_k=max(k_set))
            ranked = []
            for line in text.split("\n"):
                if line.startswith("[来源："):
                    src = line[4 : line.index("]")]
                    body = line[line.index("]") + 1 :]
                    ranked.append({"source": src, "text": body})
        for k in k_set:
            agg[k]["recall"] += _recall_at_k(ranked, case, k) / n
            agg[k]["precision"] += _precision_at_k(ranked, case, k) / n
            agg[k]["ndcg"] += _ndcg_at_k(ranked, case, k) / n
        agg["mrr"] += _mrr(ranked, case) / n
    return agg


def run_faithfulness_eval(cases: list[dict], k: int = 3) -> dict:
    """LLM 判定 faithfulness：回答是否忠于检索上下文（可选，烧钱）。

    简化：用检索 top-k 文本 + LLM 判断「回答中的关键事实是否都在上下文中」。
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError:
        return {"skipped": True, "reason": "langchain_openai 未安装"}

    from api.dependencies import load_llm_config

    llm_cfg = load_llm_config()
    llm = ChatOpenAI(
        model=llm_cfg["model_name"],
        temperature=0.0,
        base_url=llm_cfg.get("base_url") or None,
        api_key=llm_cfg.get("api_key", ""),
    )
    retriever = build_retriever()
    scores = []
    failures = []

    for case in cases:
        query = case["query"]
        try:
            docs = retriever.query_zx_experience_top_docs(query, top_k=k)
        except AttributeError:
            docs = []
        context = "\n".join(f"[{d.get('source','')}] {d.get('text','')}" for d in docs)
        try:
            resp = llm.invoke([
                SystemMessage(content=(
                    "你是评估员。判断 AI 回答是否忠于给定上下文（没有编造上下文之外的事实）。"
                    "只输出 JSON: {\"faithful\": true/false, \"reason\": \"...\"}"
                )),
                HumanMessage(content=f"上下文：\n{context}\n\nAI 回答：\n{case.get('query','')}"),
            ])
            import re, json as _json
            m = re.search(r"\{.*\}", resp.content or "", re.DOTALL)
            verdict = _json.loads(m.group(0)) if m else {"faithful": False}
            scores.append(1.0 if verdict.get("faithful") else 0.0)
            if not verdict.get("faithful"):
                failures.append({"query": query, "reason": verdict.get("reason", "")})
        except Exception as exc:
            failures.append({"query": query, "reason": f"LLM 调用失败: {exc}"})

    if not scores:
        return {"skipped": True, "reason": "无有效判定"}
    return {
        "faithfulness": round(sum(scores) / len(scores), 4),
        "cases": len(scores),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 检索评估")
    parser.add_argument("-k", type=int, nargs="*", default=list(DEFAULT_K_SET), help="top-k 集合")
    parser.add_argument("--case", type=int, default=None, help="只跑单条用例（索引）")
    parser.add_argument("--backend", default="local_file", help="检索后端")
    parser.add_argument("--faithfulness", action="store_true", help="追加 LLM faithfulness 评估（烧钱）")
    args = parser.parse_args()

    k_set = tuple(sorted(set(args.k or DEFAULT_K_SET)))
    cases_path = Path(__file__).resolve().parent / "eval_dataset.json"
    cases = load_cases(cases_path)
    if args.case is not None:
        if args.case >= len(cases):
            print(f"[ERROR] case 索引 {args.case} 超出范围（共 {len(cases)} 条）")
            sys.exit(2)
        cases = [cases[args.case]]

    print(f"═" * 56)
    print(f"  RAG 检索评估  |  用例 {len(cases)} 条  |  backend={args.backend}")
    print(f"═" * 56)

    agg = run_retrieval_eval(cases, k_set, backend=args.backend)
    for k in k_set:
        print(f"  Recall@{k:<3} {agg[k]['recall']:.3f}   Precision@{k:<3} {agg[k]['precision']:.3f}   NDCG@{k:<3} {agg[k]['ndcg']:.3f}")
    print(f"  MRR      {agg['mrr']:.3f}")

    if args.faithfulness:
        print("-" * 56)
        fa = run_faithfulness_eval(cases)
        if fa.get("skipped"):
            print(f"  Faithfulness 跳过：{fa.get('reason','')}")
        else:
            print(f"  Faithfulness {fa['faithfulness']:.3f}  （{fa['cases']} 例）")
            for f in fa.get("failures", [])[:5]:
                print(f"    ✗ {f['query'][:30]}… {f.get('reason','')[:60]}")

    print(f"═" * 56)
    sys.exit(0)


if __name__ == "__main__":
    main()
