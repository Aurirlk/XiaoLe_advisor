# RAG 评估体系（P1-12）

轻量版领域 RAG 评估，不引入 RAGAS 等重型依赖，复用生产检索链路
（`RAGTools.from_config` 读取 `configs/rag_config.yaml`），确保
**评估结果 = 线上效果**。

## 文件

| 文件 | 说明 |
|---|---|
| `eval_dataset.json` | 领域标注集（30 条）：query + golden_sources + golden_keywords |
| `run_rag_eval.py` | 评估脚本：Recall@k / Precision@k / MRR / NDCG@k / 可选 Faithfulness |
| `README.md` | 本文档 |

## 用法

```bash
# 检索指标（默认 k = 3/5/10）
python scripts/rag_eval/run_rag_eval.py

# 自定义 k
python scripts/rag_eval/run_rag_eval.py -k 1 3 5 10

# 只跑单条用例（调试标注质量）
python scripts/rag_eval/run_rag_eval.py --case 0

# 追加 LLM faithfulness（烧钱，需配置 LLM）
python scripts/rag_eval/run_rag_eval.py --faithfulness
```

## 指标说明

- **Recall@k**：golden 相关文档出现在 top-k 的比例（召回率，核心指标）
- **Precision@k**：top-k 中 golden 相关文档占比（精确率）
- **MRR**：第一个 golden 相关文档的倒数排名（首命位置）
- **NDCG@k**：排序质量（相关文档越靠前分越高）
- **Faithfulness**（可选）：LLM 判定「回答忠于检索上下文、无编造」的比例

## 命中判定

一条文档命中 golden 满足任一条件：
1. `source` 包含 `golden_sources` 中任一子串
2. `text` 包含 `golden_keywords` 中任一关键词

## 基线目标

| 指标 | 当前基线（首次运行输出） | 目标 |
|---|---|---|
| Recall@5 | — | ≥ 0.60 |
| MRR | — | ≥ 0.40 |

## CI 集成建议

```yaml
# .github/workflows/ci.yml 追加 job
- name: RAG eval
  run: python scripts/rag_eval/run_rag_eval.py -k 5
```

## 扩展标注集

新增用例：在 `eval_dataset.json` 的 `cases` 数组追加对象，注意
golden_sources 用语料里真实存在的 source 前缀（先 `grep` 语料确认）。

语料位置：`data/vector_store/zx_experience.json`（2287 条）。
