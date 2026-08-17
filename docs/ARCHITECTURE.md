# ARCHITECTURE.md — 架构真相源（唯一权威）

> **本文件是全项目架构的唯一权威描述**。其他文档（技术文档/README/交接手册）若与本文件冲突，**以本文件为准**。
> 维护规则：任何影响架构的改动（新增模块/改依赖/改数据流）都必须同步更新本文件。
>
> 配套：`docs/交接手册.md`（操作与坑）、`docs/技术文档.md`（12 大体系细节展开）、`AGENTS.md`（AI 认知引导）。
> 版本：v0.4.1（2026-08-17）

---

## 1. 一句话架构

**LangGraph 编排的多 Agent 决策系统**：Supervisor 中枢做意图路由 → 专业 Worker 员工分工采集（画像/匹配/就业/联网/查询）→ Synthesis 汇总输出；知识分三层（SQL 确定性数据 / RAG 经验知识 / Neo4j 关系知识 + 雪峰语料风格锚点），风控由确定性引擎把关。

## 2. 架构图

```
用户输入（文字/语音/图片）
    │
    ▼
┌──────────────────────────────────────────────┐
│         Supervisor Agent (路由中枢)           │
│   ├─ LLM 结构化意图识别                       │
│   ├─ 三层路由（场景/路径/决心度）              │
│   ├─ AgentCommunicationBus（订阅/发布）        │
│   └─ _fallback_route (确定性关键词兜底)        │
└───┬───┬───┬───┬───┬───┬───┬───┬──────────────┘
    │   │   │   │   │   │   │   │
    ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
 Profile Match Career Web  SQL  Parent Family Chat
 Agent   Agent Agent  Search Agent Agent  Agent Agent
    │   │   │   │   │   │   │   │   │
    │   │   │   └──→ write_agent（唯一写权限，可选）│
    │   │   │        (校验/去重/双写入库)          │
    └───┴───┴───┴───┴───┴───┴───┴──────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Result Fusion        │   ← 多源结果融合（可选开关）
    └────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Synthesis Agent      │
    │   + 雪峰语料风格锚点     │ ← XuefengStore（Milvus/Chroma）
    │   + 情感分析/时间感知    │
    │   + SynthesisGuard     │ ← 确定性风控（防端水）
    └────────────────────────┘
                 │
                 ▼
         SSE/WebSocket → Vue 3 前端
```

## 3. 生产开关（api/dependencies.py 为准）

| 能力 | 开关 | 生产状态 | 说明 |
|---|---|---|---|
| Agent 通信总线 | `enable_agent_bus=True` | ✅ 生产开启 | 蓝图 Phase 3.1 |
| 自我反思质量门 | `enable_reflexion=True` | ✅ 生产开启 | 蓝图 Phase 3.2 |
| 结果融合 | `enable_result_fusion` | ⚠️ 默认关（可选） | 测试/按需开启 |
| write_Agent 写库 | `enable_write_agent` | ⚠️ 默认关（可选） | 测试/按需开启 |
| 雪峰风格锚点 | `xuefeng_store=` 注入 | ⚠️ 注入方决定 | synthesis 接收可选参数 |

> 构造入口：`api/dependencies.py::get_graph()` → `core/graph_builder.py::build_graph()`。

## 4. 核心模块索引（真相）

| 模块 | 文件 | 职责 | 关键依赖 |
|---|---|---|---|
| 路由中枢 | `agents/supervisor_agent.py` | 三层意图识别 + 关键词兜底 + Agent 路由 | LLM |
| 合成回答 | `agents/synthesis_agent.py` | 汇总 worker 输出 + 雪峰锚点注入 + 风控约束 | XuefengStore, SynthesisGuard |
| 图构建 | `core/graph_builder.py` | LangGraph 状态机构建，全部开关在此 | 所有 agent |
| 状态定义 | `core/state_schema.py` | GraphState / 中间状态 | — |
| 通信总线 | `core/agent_bus.py` | 订阅/发布/请求-响应/广播 | asyncio |
| 反思循环 | `core/reflexion_agent.py` | 输出质量门 + 重试 + 反思记忆 | — |
| 结果融合 | `core/result_fusion.py` | 合并/投票/加权/专家 | — |
| RAG 检索 | `tools/rag_tools.py` | kb_scope 分权 + 四级降级链 + RRF | vector_store, FTS5 |
| 向量存储 | `tools/vector_store.py` | Chroma 持久化 + hnsw | chromadb |
| 多维检索 | `tools/multi_embedding_store.py` | Dense+Sparse(BM25)+ColBERT RRF | vector_store |
| Embedding 统一 | `tools/embedding_config.py` | **单一真源**：provider 切换 + get_embedder() | vector_config.yaml |
| 硅基 Embedding | `tools/siliconflow_embedder.py` | BGE-M3 API 客户端（v0.4.1） | SILICONFLOW_API_KEY |
| 雪峰语料库 | `tools/xuefeng_store.py` | Milvus 优先/Chroma 降级 + 关键字窗口词 | pymilvus |
| 写库 worker | `agents/workers/write_agent.py` | 搜索结果校验去重后入库 | — |
| CRM | `core/crm_manager.py` | 学生/家长/家庭画像断点续传 | SQLite |

## 5. 数据流（真相）

### 5.1 主对话链路
```
输入 → Supervisor（三层路由）→ Worker 分工 → （可选 Fusion）→ Synthesis → 输出
```

### 5.2 写库闭环（write_Agent，学习机制）
```
web_search 搜到新内容 → write_agent 校验(MIN_TEXT_LEN=40)/去重(source hash)
    → RAG JSON user:web/ 域 + Chroma 双写 → 下次检索可命中
```

### 5.3 Agent 总线协作（跨 worker，不依赖 state 顺序）
```
match_agent 完成 → bus.publish("match.completed")
career_agent → bus.request("match.admission") 获取"可冲院校参考"
```

### 5.4 反思质量门
```
Worker 输出 → ReflexionAgent 规则评估 → 达标 → 写 reflexion_report
                              ↓ 不达标
                    改进建议 → regenerate（上限控制）→ 反思记忆沉淀
```

## 6. 数据分层（真相，面试叙事核心）

| 层 | 数据 | 存储 | 谁写 | 谁读 |
|---|---|---|---|---|
| 确定性数据 | 分数线/录取 28.3 万条 | SQLite `zx_advisor.db` | 脚本导入 | sql_agent / match_agent |
| 经验知识 | 1,998+ 条文档 | Chroma `zx_experience` + FTS5 | write_agent / 脚本 | career_agent（kb_scope 分权） |
| 关系知识 | 院校-专业-职业-城市 4242 节点 | Neo4j | 导入脚本 | match_agent / 图谱查询 |
| 风格语料 | 雪峰对话 30 条 | Milvus `zx_xuefeng` / Chroma 降级 | build_xuefeng_corpus | synthesis_agent（风格锚点） |
| 会话 | 会话状态 7 天 TTL | Redis | api | 全链路 |

**真相源（可重建）**：`data/vector_store/zx_experience.json`（主 RAG）、`data/vector_store/xuefeng_corpus.json`（雪峰）、`data/zx_advisor.db`（数据库，网盘分发）。Chroma/Milvus 都是派生索引，可删目录后重建（见交接手册 5.3）。

## 7. Embedding 体系（v0.4.1 真相）

- **单一真源**：`configs/vector_config.yaml` → `tools/embedding_config.py::get_embedder()`
- **当前 provider**：`siliconflow`（BGE-M3，1024 维，API 调用）
- **可切回**：`local`（本地 SentenceTransformer，离线）
- **切换后必须重灌索引**（维度变化）：`rebuild_embedding_index.py --force` + `check_xuefeng_milvus.py --enable --rebuild`
- **兼容适配**：所有 `_embed` 统一处理 ndarray/list 两种返回

### 7.1 分类器模型（独立于 RAG 向量空间）

- `vector.classifier_model`（默认 MiniLM-L12-v2）= **web_search_agent 平台分类专用**本地模型
- 与 `embedding_model` 分离的原因：① 每次搜索都要分类，走 API 有延迟+成本；② 模板向量与 query 向量同模型内部自洽，不参与 RAG 向量比较
- 解析入口：`embedding_config.resolve_classifier_model()`；`web_search_agent._build_embedding_model()` 从配置读，**无硬编码**

## 8. 死代码 / 陷阱标注（真相，勿删）

| 文件 | 状态 | 处置 |
|---|---|---|
| `tools/reranker.py` | ⚠️ 零调用方 | 保留（CrossEncoder 重排留用，架构决策未定） |
| `tools/graph_rag.py` | ⚠️ 零调用方 | 保留（图谱多跳检索，同上） |
| `_search_from_milvus/_search_from_es` | ⚠️ 零调用方 | 保留（Milvus/ES 读路径备用） |
| `core/agent_bus.py` | ✅ 已接入 | **曾被误删后重建**，蓝图核心，勿动 |
| `core/reflexion_agent.py` | ✅ 已接入 | 同上 |

**删除任何代码前**：① 对照本文件确认非核心；② 显式告知用户确认。（项目铁律，曾被违反过）

## 9. 已知边界（真相）

- **Windows 专属坑**：chromadb compaction 崩溃、pyarrow segfault、Docker 中文目录名——详见交接手册第 6 节（8 条全清单）
- **内存约束**：开发机 16GB，Docker+Milvus+重灌同时跑会 OOM；重灌主 RAG 需先释放内存
- **Milvus 状态**：代码就绪 + 容器曾跑通，但最终端到端验证因内存不足留待维护期（见交接手册第 9 节待办）
- **语料说明**：雪峰语料为模拟风格（非真实语录），面试需说明或换真实素材

---

*本文件是全项目架构真相源。改动架构必须同步更新；有冲突以本文件为准。*
