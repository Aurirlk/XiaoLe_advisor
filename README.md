<p align="center">
  <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4MCIgaGVpZ2h0PSI4MCIgdmlld0JveD0iMCAwIDgwIDgwIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iODAiIHJ4PSIyMCIgZmlsbD0iIzFlM2E1ZiIvPjx0ZXh0IHg9IjQwIiB5PSI1NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSI0MCIgZmlsbD0iI2YwYTUwMCI+JiN4MWYzOTM7PC90ZXh0Pjwvc3ZnPg==" alt="小乐AI" width="80" />
</p>

<h1 align="center">小乐AI · 高考志愿填报助手</h1>

<p align="center">
  <strong>张雪峰风格 · 多智能体协同高考志愿决策系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/vue-3.3.4-brightgreen" alt="Vue 3" />
  <img src="https://img.shields.io/badge/langgraph-multi--agent-orange" alt="LangGraph" />
  <img src="https://img.shields.io/badge/deepseek-v4--flash-purple" alt="DeepSeek" />
  <img src="https://img.shields.io/badge/version-v0.4.1-darkgreen" alt="Version" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

<p align="center">
  基于 <strong>LangGraph + FastAPI + Vue 3</strong> 的 Supervisor-Worker 多智能体架构<br/>
  十万级录取数据 × 多 Agent 协同 × RAG/Neo4j/GraphRAG 知识库 × Harness 学习协作机制 × 确定性风控引擎</p>

---

## 目录

- [一句话介绍](#一句话介绍)
- [项目简介](#项目简介)
- [项目思路](#项目思路)
- [功能清单](#功能清单)
- [技术栈](#技术栈)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [数据下载](#数据下载)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [文档目录](#文档目录)

---

## 一句话介绍

**小乐AI 是一个"多 Agent 协同 + RAG 知识库"驱动的高考志愿填报决策系统：Supervisor 中枢像指挥员一样调度 8+ 个专业员工 Agent（画像/匹配/就业/联网/写库），用十万级录取数据、张雪峰咨询风格和确定性风控引擎，帮"一家人"吵出共识、做出不后悔的志愿选择。**

## 项目简介

### 项目背景

高考志愿填报是"高信息差 + 高决策风险 + 全家参与"的典型场景：家长看稳定、学生看兴趣、分数看位次、就业看趋势，四者经常冲突（"一家人吵架"）。传统填报工具只给分数线查询，无法完成"从数据到决策"的完整链路；通用大模型又会"端水"——给不出明确建议。小乐AI 针对这一场景，用多 Agent 系统还原"专业顾问团队"的工作方式：先收集画像，再分路查证数据，最后给出有立场、有依据、敢劝退的建议。

### 项目实现功能

- **多 Agent 协同决策**：Supervisor 路由中枢（场景/路径/决心度三层意图识别）→ 8+ Worker 员工（profile/parent/family/match/career/web_search/sql/write）→ Synthesis 合成，Agent 间可经通信总线协作、反思循环自纠、结果融合去冲突
- **RAG 知识库 + 图谱**：ChromaDB 向量检索 + FTS5 全文检索 + 知识域分权（kb_scope）+ Neo4j 知识图谱（院校-专业-职业-城市-政策）+ GraphRAG 多跳查询 + 张雪峰对话语料库（Milvus，硅基 BGE-M3 embedding，风格锚点注入）
- **确定性风控**：SynthesisGuard 防端水引擎 + 红线审计 + 反方审计 + 硬编码过滤（体检/预算/地域），回复不越界、不编数据
- **write_Agent 学习闭环**：联网搜到但知识库没有的内容，由唯一写权限 worker 校验去重后自动写入知识库，实现"越用越懂"
- **全模态交互**：文字对话（SSE 真流式）/ 语音（VAD→ASR→TTS 情绪合成）/ 图片理解（VLLM）/ WebSocket 全双工
- **Harness 数据引导**：数据缺失时引导用户上传 CSV/Excel/PDF/图片，自动解析入库更新
- **工程化能力**：用户画像 CRM 断点续传、RAG 评估体系（Recall@3=0.567）、意图追踪、成本控制、重试熔断、评测与反馈闭环

### 项目思路

1. **中枢-员工（Sisyphus）模式**：不做"对话式多 Agent 互相聊天"，而是 Supervisor 作为指挥中枢，把任务拆解下发给专业 Worker"员工"，员工采集信息后交回中枢汇总——架构清晰、职责单一、可 review
2. **数据分层治理**：确定性数据（分数线/风控规则）走 SQL/硬编码，经验知识走 RAG，关系知识走图谱，对话风格走雪峰语料库——各层各司其职，互相降级兜底
3. **可解释可问责**：每个推荐都带数据理由 + 风险提示 + 审计报告，风控信号不被 LLM 篡改
4. **学习协作机制**：write_Agent 写库 + Harness 引导用户补数据 + 反馈闭环优化，让系统在真实使用中持续进化

## V0.4.0 新增功能

### 🤝 多 Agent 协作体系（蓝图 Phase 3 落地）

```
用户输入
    │
    ▼
┌─────────────────────────────────────────┐
│  Supervisor Agent（三层路由 + 通信总线）   │
│  AgentCommunicationBus 订阅/发布/请求响应  │
└─────────────────────────────────────────┘
    │
    ├─→ profile_agent / parent_agent / family_agent（画像采集）
    ├─→ match_agent（分数线/位次，Neo4j→SQLite 降级）
    ├─→ career_agent（RAG 四源并行，kb_scope 知识域分权）
    ├─→ web_search_agent（联网搜索）
    ├─→ write_agent（唯一写权限：搜索结果校验去重后写入知识库）
    ├─→ sql_agent / decision_detector
    └─→ result_fusion（多源结果融合 → synthesis）
                 │
                 ▼
    Synthesis Agent（+ 雪峰语料风格锚点注入 + 风控）
```

### 🛠️ 新增模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **Agent 通信总线** | `core/agent_bus.py` | 订阅/发布 + 请求-响应 + 广播，asyncio 友好 |
| **自我反思 Agent** | `core/reflexion_agent.py` | 输出质量评估 → 建议 → 重试循环 → 反思记忆沉淀/复用 |
| **结果融合器** | `core/result_fusion.py` | sql/career/web 多源结果融合（合并/投票/加权/专家） |
| **write_Agent** | `agents/workers/write_agent.py` | 唯一写权限 worker，搜索结果校验/去重/双写入库 |
| **雪峰语料库** | `tools/xuefeng_store.py` | Milvus+学科 embedding 对话检索，不可达降级 Chroma |
| **语料构建脚本** | `scripts/build_xuefeng_corpus.py` | 雪峰对话切块入库（轮次边界/专业关键字窗口词） |
| **RAG 知识域分权** | `tools/rag_tools.py` | `kb_scope` 参数按知识域限定检索 + 跨库兜底标记 |

### 🎯 多维意图识别系统

```
用户输入
    │
    ▼
┌─────────────────────────────────────────┐
│  Supervisor Agent（三层路由）             │
│  Layer 1: 场景识别（chat/gaokao/postgrad）│
│  Layer 2: 路径识别（postgrad/employment） │
│  Layer 3: 决心度检测（firm/hesitant/lost）│
└─────────────────────────────────────────┘
    │
    ├─→ chat_agent（普通聊天 + 情感支持）
    ├─→ profile_agent（渐进询问 + 信息差弥合）
    ├─→ match_agent（决策框架 + 现实映射）
    ├─→ career_agent（路径规划 + 现实映射）
    ├─→ decision_detector（回退引导 + 情感支持）
    └─→ synthesis_agent（集成所有增强模块）
```

### 🛠️ 新增模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **信息差弥合** | `skills/info_gap_bridger.py` | 主动告知用户该知道的事 |
| **决策框架** | `skills/decision_framework.py` | 教用户用什么标准做决定 |
| **家庭协调** | `agents/workers/family_agent.py` | 帮助家长和学生达成共识 |
| **情感支持** | `skills/emotional_support.py` | 承认焦虑、提供支持 |
| **意图追踪** | `core/intent_tracker.py` | 记录意图日志、决策旅程 |
| **聊天Agent** | `agents/chat_agent.py` | 普通聊天 + 情感支持 |
| **决心度检测** | `agents/decision_detector.py` | 犹豫检测 + 回退引导 |

### 🎨 前端增强

| 组件 | 功能 |
|------|------|
| `IntentIndicator.js` | 意图指示器（实时显示场景/路径/决心度） |
| `ProgressiveQuestions.js` | 渐进询问卡片 |
| `FallbackCard.js` | 回退引导卡片 |
| `RecommendationReason.js` | 推荐理由展示 |
| `ComparisonPage.js` | 多校/多专业对比分析 |
| `ApplicationFormPage.js` | 冲稳保志愿表生成 |
| `QuestionnaireResult.js` | 问卷结果可视化 |
| `ProfileEditor.js` | 用户画像编辑 |
| `design-system.css` | 设计系统原子类 |
| `animations.css` | 过渡动画库 |
| `dark-mode.css` | 暗色模式 |
| `accessibility.css` | 无障碍优化 |

### 📊 数据增强

| 数据源 | 数据量 | 说明 |
|--------|--------|------|
| 阳光高考网 | 2,817 所院校 | 全国 32 个省份 |
| 阳光高考网 | 883 个专业 | 13 个门类 |
| 国家统计局 | 15 个行业 | 平均工资数据 |
| 国家统计局 | 31 个省份 | 平均工资数据 |
| RAG 索引 | 1,998 条文档 | 389KB |

---

## 功能清单

| 功能 | 状态 | 说明 |
|------|------|------|
| 意图路由 | ✅ | LLM 结构化意图识别 + 关键词回退 + 家长/学生分流 |
| Function Calling | ✅ | 4 个工具：分数线查询、经验检索、新闻查询、政策查询 |
| 时间感知 | ✅ | LLM system prompt 动态注入当前日期/高考倒计时 |
| AI CRM | ✅ | 学生+家长+家庭三维度画像，跨会话断点续传 |
| 服务工厂 | ✅ | LLMFactory/ASRFactory/TTSFactory/VLLMFactory，自动回退 |
| 重试熔断 | ✅ | 指数退避 + 三态熔断器，全 Provider 集成 |
| 成本控制 | ✅ | Token 用量追踪，内嵌 10+ 模型定价表 |
| 向量数据库RAG | ✅ | ChromaDB 向量检索 + SQLite FTS5 全文检索 |
| VAD 流式输入 | ✅ | Silero VAD 实时端点检测（前端 RMS + 后端 ONNX） |
| 意图打断 | ✅ | TTS 播放时支持语音打断（AudioManager 单例） |
| 情感分析 | ✅ | 关键词规则 + LLM 提取双方案，7 种情绪标签 |
| 情绪 TTS | ✅ | 根据情绪调整语音语调（Edge TTS / CosyVoice） |
| VLLM 视觉 | ✅ | GLM-4V / Qwen-VL / GPT-4o 图片分析 |
| Redis 会话 | ✅ | 分布式会话管理，7 天 TTL |
| 流式 TTS | ✅ | WebSocket 边合成边推送 + HTTP 整段模式 |
| WebSocket | ✅ | 全双工 /ws/chat 端点 |
| 用户认证 | ✅ | JWT Token + bcrypt 密码哈希 + 多角色（学生/家长/管理员） |
| Neo4j 知识图谱 | ✅ | 院校-专业-职业-产业集群-就业政策多跳查询 |
| 院校排名页面 | ✅ | QS/US News/泰晤士/软科/校友会/武书连排名查询 |
| 知识图谱可视化 | ✅ | Canvas 渲染图谱节点关系，支持拖拽缩放，真实 API 查询 |
| 高考录取数据 | ✅ | 283,653 条（2016-2020年全国 29 省录取数据） |
| **多维意图识别** | ✅ | **三层路由（场景/路径/决心度）** |
| **渐进询问** | ✅ | **基于 RAG/图谱/CRM 生成引导问题** |
| **信息差弥合** | ✅ | **主动告知用户该知道的事** |
| **决策框架** | ✅ | **教用户用什么标准做决定** |
| **现实映射** | ✅ | **把选择和后果直接关联** |
| **家庭调解** | ✅ | **帮助家长和学生达成共识** |
| **情感支持** | ✅ | **承认焦虑、提供支持** |
| **推荐理由** | ✅ | **分数匹配 + 就业前景 + 城市优势 + 数据支撑** |
| **对比分析** | ✅ | **多校/多专业多维度对比** |
| **志愿表生成** | ✅ | **冲稳保策略 + 录取概率 + 注意事项** |
| **意图追踪** | ✅ | **意图日志 + 决策旅程 + 犹豫模式检测** |
| **暗色模式** | ✅ | **跟随系统 + 手动切换** |
| **PWA 支持** | ✅ | **Service Worker + 离线缓存 + 添加到主屏幕** |
| **真流式输出** | ✅ | **SSE/WS 双流并行（updates+messages），token 级增量推送** |
| **RAG 评估体系** | ✅ | **30 条领域标注集 + Recall@k/MRR/NDCG@k 评估脚本** |
| **RAG 知识域分权** | ✅ | **kb_scope 按知识域限定检索 + 跨库兜底标记** |
| **Agent 通信总线** | ✅ | **订阅/发布 + 请求-响应 + 广播（蓝图 Phase 3）** |
| **自我反思循环** | ✅ | **ReflexionAgent 评估→建议→重试→反思记忆（蓝图 Phase 3）** |
| **结果融合** | ✅ | **ResultFusion 多源融合节点（蓝图 Phase 3，开关可控）** |
| **write_Agent** | ✅ | **唯一写权限 worker：搜索内容校验去重后自动入库** |
| **雪峰语料库** | ✅ | **Milvus+硅基 BGE-M3 embedding 对话检索，风格锚点注入合成** |

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主语言 |
| FastAPI | latest | 异步 API 框架 |
| LangGraph | latest | 多智能体编排 |
| DeepSeek | V4 | 默认大语言模型 |
| SQLite | 3 | 本地嵌入式数据库 |
| Neo4j | 5.x | 知识图谱数据库 |
| Redis | 7 | 缓存与会话 |
| ChromaDB | latest | 向量数据库 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.3.4 | 前端框架 |
| Tailwind CSS | 2.2.19 | 原子化 CSS |
| Font Awesome | 6.4.0 | 图标库 |
| Marked | latest | Markdown 渲染 |
| Highlight.js | 11.8.0 | 代码高亮 |
| DOMPurify | 3.0.6 | XSS 防护 |

---

## 架构概览

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
    │   │   │   └──→ write_agent（唯一写权限）   │
    │   │   │        (校验/去重/双写入库)        │
    └───┴───┴───┴───┴───┴───┴───┴──────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Result Fusion        │   ← 多源结果融合（sql/career/web）
    │   (可选开关)            │
    └────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Synthesis Agent      │
    │   + 雪峰语料风格锚点     │ ← XuefengStore（Milvus/Chroma）
    │   + 情感分析            │
    │   + 时间感知注入         │
    │   + SynthesisGuard     │
    │   + 信息差弥合          │
    │   + 决策框架            │
    │   + 现实映射            │
    │   + 家庭调解            │
    │   + 情感支持            │
    └────────────────────────┘
                 │
                 ▼
         SSE/WebSocket → Vue 3 前端
                 │
                 ▼
    ┌────────────────────────┐
    │   前端增强              │
    │   + 意图指示器          │
    │   + 渐进询问卡片        │
    │   + 回退引导卡片        │
    │   + 推荐理由展示        │
    └────────────────────────┘
```

---

## 数据下载

> **仓库只包含源代码**。考生数据库、本地模型、向量库等大文件（约 550MB）保存在百度网盘，克隆后需手动下载并解压到指定路径。

### 百度网盘链接

**文件**：`xiaozhi-data.zip`  
**链接**：[小乐AI 数据包](https://pan.baidu.com/s/1M0eQFM3nxwdGpLNn898b4Q?pwd=oobb)  
**提取码**：`oobb`

> 上传前请将 `data/` 下未忽略的文件打包为 `xiaole-data.zip`，含：
> - `data/zx_advisor.db`（录取数据库 55MB，含 28 万条录取数据）
> - `data/raw/`（原始爬取数据 13MB）
> - `data/chroma_db/` + `data/vector_store/`（RAG 向量库与索引）
> - `data/crawl_results/`（院校/专业爬取结果）
> - `data/models/`（embedding 模型 465MB，也可通过 HuggingFace 自动下载，见下）

### 解压路径

```bash
# 1. 下载 xiaole-data.zip 后，解压到项目根目录
#    Windows: 右键解压到「小乐高考志愿填报助手」根目录
#    Linux:   unzip xiaole-data.zip -d 小乐高考志愿填报助手/

# 2. 验证关键文件存在
python -c "from pathlib import Path; p=Path('data/zx_advisor.db'); print('✓ 数据库就绪' if p.exists() else '✗ 数据库缺失，请检查解压路径')"
```

### 不下载数据的替代方案（模型自动下载）

如果只想跑通代码、不想下载 550MB 数据包：

1. 数据库：运行 `python scripts/init_sqlite.py` 生成空库 + 种子数据
2. embedding 模型：首次启动自动从 HuggingFace 下载（国内用户先设 `HF_ENDPOINT=https://hf-mirror.com`）
3. RAG 索引：运行 `python scripts/build_rag_index.py` 从 `data/documents/` 重建

> ⚠️ 此方案**没有完整录取数据**，对话可跑但位次/分数线查询会返回空结果。完整功能请下载数据包。

---

## 快速开始

### 前置要求

- Python 3.10+
- Conda（推荐）或 venv
- 至少一个 LLM 的 API Key

### 1. 克隆项目

```bash
git clone <repo-url>
cd 小乐高考志愿填报助手
```

### 2. 创建环境

```bash
conda create -n zxf python=3.10 -y
conda activate zxf
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置

```bash
copy .env.example .env
```

编辑 `.env`，填入 API Key：
```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx   # 硅基流动 embedding（向量库需要，v0.4.1）
```

### 5. 初始化数据库

```bash
python scripts/init_sqlite.py
python scripts/migrate_intent_tables.py
python scripts/migrate_questionnaire_fields.py
```

### 6. 构建知识库

```bash
python scripts/crawl_majors.py
python scripts/crawl_universities_auto.py
python scripts/generate_real_knowledge_docs.py
python scripts/build_rag_index.py
```

### 7. 启动

```bash
python -m api.main
```

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| UI 界面 | http://127.0.0.1:8000 | Vite 构建 SPA（FastAPI 统一 serve） |
| API 文档 | http://127.0.0.1:8000/docs | Swagger UI |
| 健康检查 | http://127.0.0.1:8000/healthz | 服务状态 |

---

## 配置说明

### 模型选择

```yaml
# configs/.config.yaml
selected_module:
  LLM: deepseek-v4-flash    # 切换模型只需改这一行
  ASR: FunASR
  TTS: EdgeTTS
  VLLM: glm-4v-flash
```

### Embedding（v0.4.1）

向量库统一走 `configs/vector_config.yaml` 单一真源，当前默认**硅基流动 API**：

```yaml
# configs/vector_config.yaml
vector:
  embedding_provider: siliconflow   # siliconflow（硅基 API）| local（本地模型）
  embedding_model: BAAI/bge-m3       # 1024 维
```

- `siliconflow` 需要 `.env` 中配置 `SILICONFLOW_API_KEY`
- 切换 provider / 模型后**必须重灌索引**（`python scripts/rebuild_embedding_index.py --force`），否则维度不匹配
- 详见 `docs/交接手册.md` 第 4 节

### 可用 LLM 模型

| 系列 | 预设名 | 模型 |
|------|--------|------|
| DeepSeek V4 | `deepseek-v4-flash` | deepseek-v4-flash（默认） |
| 通义千问 3.7 | `qwen3.7-plus` / `qwen3.7-max` | qwen3.7 系列 |
| 智谱 GLM 5.1 | `glm-5.1-flash` / `glm-5.1-pro` | glm-5.1 系列 |
| 豆包 Seed 2.0 | `doubao-seed-2.1-pro` | doubao-seed-2.1-pro |
| Kimi | `kimi-k2.6` | kimi-k2.6 |
| Ollama 本地 | `local-qwen` | qwen2.5:14b（零成本离线） |

---

## 项目结构

```
小乐高考志愿填报助手/
├── agents/                    # Agent 定义
│   ├── supervisor_agent.py    # 路由中枢（三层意图识别）
│   ├── synthesis_agent.py     # 综合回答生成
│   ├── chat_agent.py          # 普通聊天 Agent
│   ├── decision_detector.py   # 决心度检测 + 回退引导
│   └── workers/               # 工作 Agent
├── api/                       # API 层
│   ├── main.py                # FastAPI 应用入口
│   ├── module_manager.py      # 模块管理
│   └── routers/               # API 路由
├── core/                      # 核心模块
│   ├── state_schema.py        # LangGraph 状态定义
│   ├── graph_builder.py       # Agent 图构建
│   ├── crm_manager.py         # CRM 画像管理
│   ├── intent_tracker.py      # 意图追踪
│   └── ...
├── skills/                    # 技能模块
│   ├── info_gap_bridger.py    # 信息差弥合
│   ├── decision_framework.py  # 决策框架生成
│   ├── emotional_support.py   # 情感支持
│   └── ...
├── tools/                     # 工具层
│   ├── rag_tools.py           # RAG 检索
│   ├── sql_tools.py           # SQL 查询
│   ├── web_search_tools.py    # 联网搜索
│   ├── graph_rag.py           # GraphRAG
│   └── ...
├── frontend/                  # 前端（Vue 3 CDN）
│   ├── index.html             # 主入口
│   ├── assets/                # CSS 样式
│   │   ├── base.css           # 基础变量
│   │   ├── design-system.css  # 设计系统原子类
│   │   ├── animations.css     # 动画库
│   │   ├── dark-mode.css      # 暗色模式
│   │   └── ...
│   ├── components/            # Vue 组件
│   │   ├── core/              # 核心组件
│   │   ├── IntentIndicator.js # 意图指示器
│   │   ├── ProgressiveQuestions.js # 渐进询问卡片
│   │   ├── FallbackCard.js   # 回退引导卡片
│   │   └── ...
│   └── utils/                 # 前端工具
├── scripts/                   # 脚本
│   ├── init_sqlite.py         # 数据库初始化
│   ├── import_neo4j.py        # Neo4j 导入
│   ├── build_rag_index.py     # RAG 索引构建
│   ├── generate_real_knowledge_docs.py # 知识库生成
│   └── ...
├── docs/                      # 文档
│   ├── DELIVERY.md            # 交付手册
│   ├── OPERATIONS.md          # 运维手册
│   └── DEVELOPMENT.md         # 开发者文档
└── tests/                     # 测试
    └── e2e_frontend.spec.js   # 前端 E2E 测试
```

---

## 文档目录

| 文档 | 说明 |
|------|------|
| [docs/交接手册.md](docs/交接手册.md) | **交接手册（环境搭建/启动/已知坑全清单，接手必读）** |
| [docs/DELIVERY.md](docs/DELIVERY.md) | 交付手册（部署/验证/功能清单） |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 运维手册（监控/备份/故障排查） |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 开发者文档（架构/规范/API） |
| [docs/技术文档.md](docs/技术文档.md) | 技术架构文档（12 大体系） |
| [docs/版本历史.md](docs/版本历史.md) | 版本演进记录 |
| [docs/项目简介.md](docs/项目简介.md) | 项目简介（面试叙事） |

---

## 版本历史

### v0.4.1 (2026-08-17) — 硅基 Embedding 接入 + 交接手册

- Embedding 切换硅基流动 API（BGE-M3 1024 维），`tools/embedding_config.py` 统一 provider 入口（siliconflow/local 单一真源），消除本地模型 Windows segfault 依赖 + 双向量空间风险
- 新增 `tools/siliconflow_embedder.py`；`vector_store/xuefeng_store/multi_embedding_store` 全部适配统一入口
- 新增 `docs/交接手册.md`（环境搭建、数据恢复、已知坑全清单）
- 独立脚本补 `load_dotenv`（SILICONFLOW_API_KEY 读取修复）
- ⚠️ 切换后需重灌索引（384→1024 维），见交接手册第 4/5 节

### v0.4.0 (2026-08-06) — 多 Agent 协作体系 + write_Agent + 雪峰语料库

**核心功能：**
- RAG 知识库分权（`kb_scope` 知识域限定检索 + 跨库兜底）
- Agent 通信总线（AgentCommunicationBus：订阅/发布/请求响应/广播）
- 自我反思 Agent（ReflexionAgent：评估→建议→重试→反思记忆）
- 结果融合器激活（ResultFusion：多源结果融合节点）
- write_Agent（唯一写权限：搜索结果校验/去重/双写入库，学习闭环）
- 张雪峰对话语料库（Milvus+学科 embedding，风格锚点注入 synthesis）
- 蓝图 Phase 3 核心落地（`.omo/plans/xiaole-ai-master-plan.md`）

### v0.3.0 (2026-07-31) — 真流式 + Embedding 统一 + RAG 评估

**核心功能：**
- 真流式输出（SSE/WS 双流并行，token 级增量）
- Embedding 模型统一（单一真源配置，本地优先离线可用）
- RAG 评估体系（30 条标注集，Recall@3=0.567 / MRR=0.666）
- FTS5 死路修复（trigram tokenizer + 幂等灌入 2287 条）
- Chroma 同步修复（按条数比对重灌）
- 中文分词修复（CJK 字符级 + 英文单词级混合）
- intent_tracker 写入链路接线

### V7.0 (2026-06-24) — 多维意图识别 + 决策引导系统

**核心功能：**
- 多维意图识别系统（三层路由：场景/路径/决心度）
- 渐进询问引擎（基于 RAG/图谱/CRM 生成引导问题）
- 信息差弥合（主动告知用户该知道的事）
- 决策框架生成（教用户用什么标准做决定）
- 现实映射（把选择和后果直接关联）
- 家庭调解（帮助家长和学生达成共识）
- 情感支持（承认焦虑、提供支持）
- 意图追踪（意图日志 + 决策旅程 + 犹豫模式检测）

**前端增强：**
- 意图指示器（实时显示场景/路径/决心度）
- 渐进询问卡片（基于 RAG/图谱/CRM）
- 回退引导卡片（智能引导 + 接受/跳过）
- 推荐理由展示（数据支撑 + 风险提示）
- 对比分析页面（多校/多专业对比 + 雷达图）
- 志愿表生成页面（冲稳保策略 + 录取概率）
- 问卷结果可视化（雷达图 + MBTI 分析）
- 用户画像编辑（手动编辑 + 从对话分析）
- 暗色模式（跟随系统 + 手动切换）
- PWA 支持（Service Worker + 离线缓存）

**数据增强：**
- 从阳光高考网爬取 2,817 所院校数据
- 从阳光高考网爬取 883 个专业数据
- 从国家统计局获取就业/薪资数据
- RAG 索引重建（1,998 条文档，389KB）

**可维护性：**
- 文件拆分（5 个大文件拆分）
- 运维手册 + 开发者文档 + 交付手册
- E2E 测试脚本

---

<p align="center">
  <sub>纪念张雪峰老师 · 传承"用数据说话，重现实轻幻想"的报考咨询精神</sub>
</p>
