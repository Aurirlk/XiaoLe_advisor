# v0.3.0 架构升级交付概览（2026-07-31）

## 本轮完成：5 大架构项 + P1-P7 真缺陷修复

### 一、真流式输出（原 P1-1）
- `stream_router.py` / `ws_router.py`：`graph.astream(stream_mode=["updates","messages"])` 双流并行
- `synthesis_agent.py`：`llm.ainvoke` → `llm.astream` 聚合（关键：ainvoke 走一次性生成，token 回调不触发）
- `dependencies.py`：LLM 构造加 `streaming=True`
- 只放行 `AIMessageChunk` 增量：过滤 supervisor 内部推理 + 最终完整 AIMessage（防重复拼接）
- 无流式时自动兜底整段回复

### 二、Embedding 模型统一（原 P1-9）
- 新建 `tools/embedding_config.py`：模型名单一真源（vector_config.yaml，支持 ${ENV_VAR}）
- `vector_store` 与 `multi_embedding_store` 共用同一模型，杜绝双向量空间
- 本地模型目录优先（离线可用，防 HF 联网超时）
- `scripts/rebuild_embedding_index.py`：模型切换后一键重灌

### 三、RAG 评估体系（原 P1-12）
- `scripts/rag_eval/`：30 条���域标注集 + Recall@k / Precision@k / MRR / NDCG@k + 可选 LLM faithfulness
- 复用生产检索链路（评估结果 = 线上效果）
- **修复前 Recall@3=0.189 / MRR=0.391 → 修复后 0.567 / 0.666**

### 四、RAG 融合权重配置化
- `rag_config.yaml` 新增 `fusion` 段：rrf_k、四路权重、recall_multiplier 全可配
- `rag_tools.py` / `multi_embedding_store.py` 全部读配置，代码零魔法数字
- **评估标定**：dense_weight 1.0→0.3（MiniLM 中文噪声大，满权重会把 FTS5 优质结果挤出 top-k）

### 五、intent_tracker 离线沉淀（断链修复）
- `log_intent`/`log_decision_journey` 此前**零调用方**（写入链路完全断裂）
- `_make_crm_callback` 接线：scene/path/decision_state/hesitation_signals/query/response 全量落库
- `graph_builder`：synthesis 结果合并进 state 再回调（否则回调读不到最终回复）
- `init_sqlite.py`：建 user_intent_log / user_decision_journey 表

### P1-P7 顺带挖出的真缺陷（评估暴露，比预想严重）
| 缺陷 | 影响 | 修复 |
|---|---|---|
| FTS5 从未灌数据 + unicode61 中文无效 | 全文路永远返回空 | trigram tokenizer + 幂等灌 2287 条 |
| Chroma 只同步 10/2287 条 | 向量路接近死亡 | 按条数比对自动重灌 |
| 中文分词失效（整句当单 token） | dense/sparse 打分失真 | CJK 字符级 + 英文单词级 |
| chromadb 1.5.9 Windows 绝对路径坑 | hnsw 加载报错 | 统一项目根相对路径 |
| chromadb 非默认 settings 冲突 | SharedSystemClient identifier 冲突 | 默认 settings |

## 测试
- 新增 3 个测试文件（真流式 4 用例 / intent 链路 7 用例 / vector_store 持久化 5 用例）
- 修正 test_hybrid_search 的 RRF"分数相同"错误断言
- 本轮相关 7 个测试文件 **77 passed, 0 failed**

## 文件变更
- 修改：`tools/rag_tools.py`、`tools/multi_embedding_store.py`、`tools/vector_store.py`、`core/graph_builder.py`、`api/dependencies.py`、`api/main.py`、`api/routers/stream_router.py`、`api/routers/ws_router.py`、`agents/synthesis_agent.py`、`scripts/init_sqlite.py`、`configs/rag_config.yaml`、`configs/vector_config.yaml`、`交付手册.md`、`tests/test_hybrid_search.py`
- 新增：`tools/embedding_config.py`、`scripts/rebuild_embedding_index.py`、`scripts/rag_eval/`、`tests/test_streaming_mode.py`、`tests/test_intent_tracker_chain.py`、`tests/test_vector_store_persist.py`

## 待办（不在本轮范围）
- Human-in-the-loop（P1-4）、反幻觉 claim-level NLI（P1-11）、Neo4j 客户端收敛（P1-13）、VAD/TTS 引擎（P1-14/15）、前端工程（P2-14）、黄金用例扩充（P2-15）
