# AGENTS.md — 给接手 AI 的第一封信

> **如果你是 AI（或人）第一次接触这个仓库，先读我。**
> 本文件是认知引导，不是技术文档。技术真相在 `docs/ARCHITECTURE.md`，操作指南在 `docs/交接手册.md`。

---

## 1. 这是什么（30 秒）

**小乐AI**：高考志愿填报决策系统。基于 **LangGraph 多 Agent 编排**（Supervisor 中枢 + 8+ 专业 Worker 员工）的"中枢-员工（Sisyphus）"架构，叠加 **RAG 知识库**（ChromaDB + FTS5 + 知识域分权）、**Neo4j 知识图谱**、**张雪峰对话语料风格锚点**（Milvus/Chroma 双后端）与 **确定性风控引擎**（SynthesisGuard 防端水）。

定位：**作品集 / 面试展示项目**（非上线产品）。所有架构决策以"能否讲清楚、可 review、与简历叙事自洽"为标准。

## 2. 你的认知路径（按此顺序，别跳）

| 步骤 | 读什么 | 获得什么 |
|---|---|---|
| ① | `docs/ARCHITECTURE.md` | **唯一架构真相源**：组件图、数据流、模块职责、死代码标注 |
| ② | `docs/交接手册.md` | 环境搭建、启动、**全部已知坑**（8 条，务必读）、数据恢复 |
| ③ | `README.md` | 给人类看的名片（功能清单/快速开始，可能有滞后） |
| ④ | 跑 `python scripts/smoke_test.py` | **验证你的理解**：30 秒内输出各子系统状态 |
| ⑤ | 需要细节时 | `docs/技术文档.md`（12 大体系展开）、`docs/版本历史.md`（演进）、`docs/项目简介.md`（面试叙事） |

> ⚠️ **文档优先级**：`ARCHITECTURE.md` > `交接手册.md` > `README.md`。如果几份文档说法冲突，**以 ARCHITECTURE.md 为准**，并把冲突记入交接手册待办。

## 3. 红线（永远不要做）

1. **不要删除任何"看起来没用"的文件/代码**——本项目有血泪教训：`agent_bus.py` / `reflexion_agent.py` / `core/result_fusion.py` 曾因"零引用"被误删，实为蓝图「多智能体协作体系」核心组件。删除前必须：① 对照 `docs/ARCHITECTURE.md` 确认非核心组件；② 显式告知用户确认。
2. **不要升级 `pyarrow`**（requirements 锁 `>=21,<22`）——24.x 会让 `import sentence_transformers` 段错误崩溃（Windows DLL 冲突），详见交接手册坑 1。
3. **不要只改 `configs/vector_config.yaml` 的 embedding 配置而不重灌索引**——换模型/provider 后维度变化，旧索引直接不可用，必须跑 `scripts/rebuild_embedding_index.py --force`。
4. **不要 `docker compose up` 不带 `-p`**——项目目录是中文名，project name 会解析为空报错，必须 `docker compose -p xiaole up -d ...`。
5. **不要动 `data/` 下的数据库/向量库就提交**——大文件 gitignore，走百度网盘分发（README「数据下载」）。
6. **`.env` 里有真实 API Key，永不提交**（已 gitignore）。

## 4. 快速验证（跑一次就知道环境对不对）

```bash
# 环境就绪性自检（不调外部 API，mock embedding）
python scripts/smoke_test.py

# 跑核心测试（若已装依赖）
python -m pytest tests/test_agent_bus.py tests/test_reflexion_agent.py tests/test_write_agent_xuefeng.py -q
```

预期：`smoke_test.py` 输出各子系统 `✅/⚠️` 状态矩阵；**不要因为 ⚠️ 就认为系统坏了**——⚠️ 表示该子系统依赖外部服务（Milvus/API Key/数据库文件），缺了不影响代码阅读与其他子系统。

## 5. 面试叙事速记（这个项目的"为什么"）

- **多 Agent 协同**（中枢-员工 Sisyphus 模式）：Supervisor 拆任务 → Worker 采集 → 中枢汇总，职责单一、可 review
- **数据分层治理**：确定性数据走 SQL、经验知识走 RAG、关系知识走图谱、对话风格走雪峰语料库——各层各司其职、互相降级兜底
- **Milvus 线是面试 JD 锚点**（向量库部署与优化）：雪峰库 Milvus（HNSW/COSINE）→ 不可达自动降级 Chroma，体现按需选型 + 降级兜底
- **Embedding 选型**：本地 MiniLM（384 维）中文弱 + Windows DLL 冲突 → 切硅基 BGE-M3（1024 维）API，体现识别环境约束、选择更优方案

## 6. 已知的"陷阱文件"（别被误导）

| 文件 | 状态 | 说明 |
|---|---|---|
| `tools/reranker.py` | ⚠️ 零调用方，**勿删** | CrossEncoder 重排，标注留用（架构决策未定） |
| `tools/graph_rag.py` | ⚠️ 零调用方，**勿删** | 图谱多跳检索，同上 |
| `core/agent_bus.py` 等 | ✅ 已接入 | 曾被误删后重建，蓝图核心 |
| `data/` 全部 | 运行期数据 | 可删可重建（JSON 真相源在 `data/vector_store/`） |

---

*最后更新：v0.4.1（2026-08-17）。有疑问先看交接手册，再不行看 git log 找历史。*
