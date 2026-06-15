<p align="center">
  <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4MCIgaGVpZ2h0PSI4MCIgdmlld0JveD0iMCAwIDgwIDgwIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iODAiIHJ4PSIyMCIgZmlsbD0iIzFlM2E1ZiIvPjx0ZXh0IHg9IjQwIiB5PSI1NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSI0MCIgZmlsbD0iI2YwYTUwMCI+JiN4MWYzOTM7PC90ZXh0Pjwvc3ZnPg==" alt="小乐AI" width="80" />
</p>

<h1 align="center">小乐AI · 高考志愿填报助手</h1>

<p align="center">
  <strong>张雪峰风格 · 智能高考志愿填报顾问系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/vue-3.3.4-brightgreen" alt="Vue 3" />
  <img src="https://img.shields.io/badge/langgraph-multi--agent-orange" alt="LangGraph" />
  <img src="https://img.shields.io/badge/deepseek-v4--flash-purple" alt="DeepSeek" />
  <img src="https://img.shields.io/badge/tests-125%2B%20passed-27ae60" alt="Tests" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

<p align="center">
  基于 <strong>LangGraph + FastAPI + Vue 3</strong> 的 Supervisor-Worker 多智能体架构<br/>
  十万级录取数据 × AI 智能分析 × 确定性风控引擎 × 语音交互 × 多模态视觉
</p>

---

## 目录

- [项目介绍](#项目介绍)
- [功能清单](#功能清单)
- [技术栈](#技术栈)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 参考](#api-参考)
- [项目结构](#项目结构)
- [测试](#测试)
- [部署指南](#部署指南)
- [设计笔记](#设计笔记)
- [技术问答](#技术问答)
- [常见问题](#常见问题)
- [版本历史](#版本历史)
- [版权声明](#版权声明)
- [许可证](#许可证)
- [文档目录](#文档目录)

---

## 项目介绍

小乐AI 是一个智能高考志愿填报顾问系统，采用**张雪峰老师的咨询风格**——用数据说话、重现实轻幻想、该劝退绝不端水。

系统基于 **LangGraph Supervisor-Worker 多智能体架构**，通过 Supervisor 路由中枢智能调度多个专业 Worker 智能体，配合确定性技能层和防端水约束引擎，为用户提供精准、安全、可控的报考建议。

### 核心亮点

| 能力 | 说明 |
|------|------|
| 智能路由 | LLM 意图识别 + 关键词兜底 + 家长/学生双角色分流 |
| 分层工具 | SQL 四级降级 → ChromaDB 向量检索 → FTS5 全文检索 → 关键词混合召回 |
| 防端水引擎 | 三层防线：信号检测 → Prompt 注入 → 输出校验与强制修正 |
| 多轮对话 | LangGraph Checkpoint 持久化状态，会话隔离，变更可追溯 |
| 用户画像 | 学生画像 + 家长画像 + 家庭背景三维度，CRM 持久化 |
| 语音交互 | ASR → LLM → TTS 全链路，VAD 端点检测，意图打断 |
| 情感分析 | 关键词/LLM 双方案，7 种情绪标签，情绪 TTS 自适应 |
| 多模态视觉 | VLLM 视觉模型图片分析（GLM-4V / Qwen-VL / GPT-4o） |
| 流式输出 | SSE 事件驱动 + WebSocket 全双工，Token 级打字机效果 |
| 服务工厂 | LLM/ASR/TTS 工厂模式，运行时切换，自动回退，熔断保护 |
| 成本控制 | Token 用量追踪，日/月限额，定价表内置 |
| 个性化主题 | 6 套全组件级别主题（深蓝/橙/绿/紫/红/青），边框/背景/按钮全覆盖 |
| 设置界面 | 右侧抽屉式设置面板，6 个 Tab 分类管理 |

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
| 成本控制 | ✅ | Token 用量追踪，内置 10+ 模型定价表 |
| 向量数据库 RAG | ✅ | ChromaDB 向量检索 + SQLite FTS5 全文检索 |
| VAD 流式输入 | ✅ | Silero VAD 实时端点检测（前端 RMS + 后端 ONNX） |
| 意图打断 | ✅ | TTS 播放时支持语音打断（AudioManager 单例） |
| 情感分析 | ✅ | 关键词规则 + LLM 提取双方案，7 种情绪标签 |
| 情绪 TTS | ✅ | 根据情绪调整语速/风格（Edge TTS / CosyVoice） |
| VLLM 视觉 | ✅ | GLM-4V / Qwen-VL / GPT-4o 图片分析 |
| Redis 会话 | ✅ | 分布式会话管理，7 天 TTL |
| 流式 TTS | ✅ | WebSocket 边合成边推送 + HTTP 整段模式 |
| WebSocket | ✅ | 全双工 /ws/chat 端点 |
| Celery 消息队列 | ✅ | RAG 索引构建、CRM 分析、成本报告异步任务 |
| 统一配置 | ✅ | .config.yaml 一行切换模型，${ENV_VAR} 环境变量 |
| 个性化主题 | ✅ | 6 套全组件级别 CSS 变量主题 |
| 设置界面 | ✅ | 右侧抽屉 6 Tab（个性化/网络/AI/语音/情感/高级） |
| 用户认证 | ✅ | JWT Token + bcrypt 密码哈希 + 多角色（学生/家长/管理员） |
| 咕咕数据API | ✅ | 院校分数线/专业分数线/录取概率预测/批次线 |
| RRF混合搜索 | ✅ | ChromaDB + FTS5 + 关键词并行检索 + Reciprocal Rank Fusion |
| B端管理后台 | ✅ | 知识库管理/数据同步/系统管理/成本统计 |
| 调查问卷系统 | ✅ | 三类混合问卷（画像采集/排雷问卷/意向探索）+ MBTI性格测试 |
| 家庭冲突检测 | ✅ | 双向约束矩阵 + 7类冲突检测 + 熔断机制 |
| 反方审计引擎 | ✅ | 5个视角挑刺（招生办/HR/家长/学生/应届生） |
| AI暴露度评估 | ✅ | 专业入门岗位被AI替代风险评估 |
| 量化评分框架 | ✅ | 100分制7维度评分（录取风险/专业适配/就业钱景等） |
| 硬编码过滤器 | ✅ | Python规则引擎（黑名单/体检/预算/地域/偏远校区） |
| Neo4j知识图谱 | ✅ | 院校-专业-职业-产业集群-就业政策多跳查询 |
| 院校排名页面 | ✅ | QS/US News/泰晤士/自然指数/软科排名查询 |
| 知识图谱可视化 | ✅ | Canvas渲染图谱节点关系，支持拖拽缩放 |
| 高考录取数据 | ✅ | 283,653条2016-2020年全国29省录取数据 |

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主语言 |
| FastAPI | latest | 异步 API 框架 |
| LangGraph | latest | 多智能体编排 |
| LangChain | latest | LLM 工具链集成 |
| DeepSeek | V4 | 默认大语言模型 |
| SQLAlchemy | latest | ORM 框架 |
| SQLite | 3 | 本地嵌入式数据库 |
| Redis | 7 | 缓存与会话 |
| Celery | latest | 异步任务队列 |
| ChromaDB | latest | 向量数据库 |
| edge-tts | latest | 免费语音合成 |
| httpx | latest | 异步 HTTP 客户端 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.3.4 | 前端框架 |
| Tailwind CSS | 2.2.19 | 原子化 CSS |
| Font Awesome | 6.4.0 | 图标库 |

---

## 架构概览

```
用户输入（文字/语音/图片）
    │
    ▼
┌──────────────────────────────────────────────┐
│          Supervisor Agent (路由中枢)           │
│   ├─ LLM 结构化意图识别                        │
│   ├─ 家长/学生角色分流                         │
│   └─ _fallback_route (确定性关键词兜底)         │
└───┬───┬───┬───┬───┬───┬───┬───┬──────────────┘
    │   │   │   │   │   │   │   │
    ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
 Profile Match Career Web  SQL  Parent Family
 Agent   Agent Agent  Search Agent Agent  Agent
 (学生)  (查分) (就业) (搜索) (SQL) (家长) (融合)
    │   │   │   │   │   │   │
    └───┴───┴───┴───┴───┴───┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Synthesis Agent      │
    │   + 情感分析            │
    │   + 时间感知注入         │
    │   + SynthesisGuard     │
    │   (防端水硬约束引擎)     │
    └────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   TTS 语音合成          │
    │   (Edge/CosyVoice)     │
    │   + 情绪语调调整         │
    └────────────────────────┘
                 │
                 ▼
         SSE/WebSocket → Vue 3 前端
```

### 路由分支

| 条件 | 目标节点 | 数据通路 |
|------|---------|---------|
| 缺省份/选科/专业 | `profile_agent` | 回路补齐学生画像 |
| 家长在说话 | `parent_agent` | 提取家长画像 |
| 学生+家长画像齐全 | `family_agent` | 融合家庭背景 |
| 分数/位次/录取门槛 | `match_agent` | SQL 硬数据 |
| 就业/考公/薪资/前景 | `career_agent` | RAG 经验库 |
| 政策/官网/最新信息 | `web_search_agent` | 外部搜索 |
| 复杂数据查询 | `sql_agent` | Function Calling |
| 纯框架/价值观 | `synthesis_agent` | 直接合成 |

---

## 快速开始

### 前置要求

- Python 3.10+
- Conda（推荐）或 venv
- 至少一个 LLM 的 API Key

### 1. 克隆项目

```bash
git clone <repo-url>
cd zx_ai_advisor
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

编辑 `.env`，填写 API Key：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

编辑 `configs/.config.yaml`，选择模型：

```yaml
selected_module:
  LLM: deepseek-v4-flash    # 切换模型只需改这一行
  ASR: FunASR
  TTS: EdgeTTS
  VLLM: glm-4v-flash
```

### 5. 启动

```bash
python -m api.main
```

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| UI 界面 | http://127.0.0.1:5000 | Vue 3 对话界面 |
| API 文档 | http://127.0.0.1:8000/docs | Swagger UI |
| 健康检查 | http://127.0.0.1:8000/healthz | 服务状态 |

---

## 配置说明

### 配置文件结构

```
configs/
├── .config.yaml              # 用户配置（改这里就行）
├── llm_config.yaml           # LLM 模型库（11 个预设）
├── asr_config.yaml           # ASR 引擎库（10 个预设）
├── tts_config.yaml           # TTS 引擎库（9 个预设）
├── vllm_config.yaml          # 视觉模型库（6 个预设）
├── web_search_config.yaml    # 联网搜索配置
├── db_config.yaml            # 数据库配置
├── vector_config.yaml        # 向量库配置
└── prompts/                  # 提示词模板
```

### .config.yaml — 用户配置（只需改这个）

```yaml
# 模块选择（改名字即可切换）
selected_module:
  LLM: deepseek-v4-flash
  ASR: FunASR
  TTS: EdgeTTS
  VLLM: glm-4v-flash

# API Key（支持 ${ENV_VAR} 或直接填写）
api_keys:
  DEEPSEEK_API_KEY: "${DEEPSEEK_API_KEY}"
  DASHSCOPE_API_KEY: "${DASHSCOPE_API_KEY}"
  # ...
```

### 可用 LLM 模型

| 系列 | 预设名 | 模型 |
|------|--------|------|
| DeepSeek V4 | `deepseek-v4-flash` | deepseek-v4-flash（默认） |
| DeepSeek V4 | `deepseek-v4-pro` | deepseek-v4-pro |
| DeepSeek R1 | `deepseek-r1` | deepseek-r1（深度推理） |
| 通义千问 3.7 | `qwen3.7-plus` / `qwen3.7-max` / `qwen3.7-flash` | qwen3.7 系列 |
| 智谱 GLM 5.1 | `glm-5.1-flash` / `glm-5.1-pro` | glm-5.1 系列 |
| 豆包 Seed 2.0 | `doubao-seed-2.0-pro` | doubao-seed-2.0-pro |
| Kimi | `kimi-k2.6` | kimi-k2.6 |
| Ollama 本地 | `local-qwen` | qwen2.5:14b（零成本离线） |

### 切换模型

```bash
# 方式一：改配置文件
# 编辑 .config.yaml 的 selected_module.LLM

# 方式二：运行时切换（无需重启）
curl -X POST http://127.0.0.1:8000/settings/switch-model \
  -H "Content-Type: application/json" \
  -d '{"preset": "qwen3.7-flash"}'

# 方式三：设置界面
# 点击右上角 ⚙️ 设置 → AI Tab → 下拉选择模型
```

---

## API 参考

### 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/stream/advice` | SSE 流式对话（核心接口） |
| `WS` | `/ws/chat` | WebSocket 全双工对话 |
| `POST` | `/voice/asr` | 语音识别 |
| `POST` | `/voice/tts` | 语音合成 |
| `WS` | `/voice/tts-stream` | WebSocket 流式语音合成 |
| `POST` | `/vision/analyze` | 图片分析 |
| `POST` | `/feedback` | 提交反馈 |
| `GET` | `/status` | 服务状态 |

### 设置端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/settings` | 获取 UI 设置 |
| `POST` | `/settings` | 保存 UI 设置 |
| `GET` | `/settings/models` | 列出所有可用模型预设 |
| `POST` | `/settings/switch-model` | 运行时切换 LLM 模型 |

### 管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/admin/import` | 上传 CSV/JSON 导入数据 |
| `GET` | `/admin/data/stats` | 数据覆盖统计 |
| `GET` | `/admin/cost-stats` | Token 成本统计 |

### RAG 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/rag/ingest` | 增量入库文档 |
| `POST` | `/rag/upload` | 上传文件自动解析 |
| `POST` | `/rag/scan-documents` | 扫描目录重建索引 |
| `GET` | `/rag/stats` | 向量库统计 |

---

## 项目结构

```
zx_ai_advisor/
├── agents/                         # 智能体层
│   ├── supervisor_agent.py         # 主控路由（8路分流 + 家长识别）
│   ├── synthesis_agent.py          # 终点合成（张雪峰口吻 + 情感 + 时间感知）
│   └── workers/
│       ├── profile_agent.py        # 学生画像（九门学科评分 + 兴趣 + 目标院校）
│       ├── parent_agent.py         # 家长画像（职业/行业/期望/担忧）
│       ├── family_agent.py         # 家庭融合（收入/决策人/一致性）
│       ├── match_agent.py          # 分数院校匹配
│       ├── career_agent.py         # 就业趋势研判
│       ├── sql_agent.py            # Function Calling 数据查询
│       └── web_search_agent.py     # 联网搜索 + 正文抓取
│
├── core/                           # 核心引擎
│   ├── providers/                  # 服务工厂
│   │   ├── base.py                 # CircuitBreaker + RetryMixin
│   │   ├── llm_factory.py          # LLM 工厂（含自动回退）
│   │   ├── asr_factory.py          # ASR 工厂
│   │   ├── tts_factory.py          # TTS 工厂（支持情绪参数 + 流式）
│   │   └── vllm_factory.py         # VLLM 视觉工厂
│   ├── state_schema.py             # 全局状态机（含家长/家庭/情绪字段）
│   ├── graph_builder.py            # LangGraph 拓扑编排（9 Agent）
│   ├── synthesis_guard.py          # 防端水三层防线
│   ├── emotion_analyzer.py         # 情感分析（关键词 + LLM 双方案）
│   ├── cost_tracker.py             # Token 成本追踪
│   ├── vad_detector.py             # Silero VAD 语音活动检测
│   ├── crm_manager.py              # CRM 用户画像持久化
│   └── ...
│
├── tools/                          # 工具层
│   ├── sql_tools.py                # SQL 四级降级链
│   ├── rag_tools.py                # RAG 三级检索（向量 → FTS5 → 关键词）
│   ├── web_search_tools.py         # 联网搜索（DuckDuckGo / Metaso / Tavily）
│   ├── vector_store.py             # ChromaDB 封装
│   ├── page_fetcher.py             # 网页正文抓取
│   └── function_tools.py           # 4 个 Function Calling 工具
│
├── skills/                         # 确定性技能层（纯 Python）
│   ├── risk_assessor.py            # 风险评估
│   ├── reality_checker.py          # 现实校验
│   ├── decision_heuristics.py      # 决策清单
│   ├── roi_calculator.py           # ROI 计算
│   ├── hard_filter.py              # 硬编码过滤器（黑名单/体检/预算/地域）
│   ├── conflict_detector.py        # 家庭冲突检测器
│   ├── red_team_auditor.py         # 反方审计引擎
│   ├── ai_exposure_checker.py      # AI暴露度评估
│   ├── quantitative_scorer.py      # 量化评分框架
│   └── questionnaire_service.py    # 调查问卷服务
│
├── api/                            # 接口层
│   ├── main.py                     # FastAPI 入口（10 个 router）
│   ├── dependencies.py             # 依赖注入
│   └── routers/
│       ├── stream_router.py        # SSE 流式对话
│       ├── ws_router.py            # WebSocket 全双工
│       ├── voice_router.py         # ASR/TTS（含流式 TTS WebSocket）
│       ├── vision_router.py        # 图片分析
│       ├── settings_router.py      # 设置管理
│       ├── feedback_router.py      # 用户反馈
│       ├── chat_router.py          # Redis 会话
│       ├── admin_router.py         # 管理后台
│       ├── rag_router.py           # RAG 管理
│       └── web_router.py           # 联网搜索管理
│
├── frontend/                       # Vue 3 前端
│   ├── index.html                  # 主入口
│   ├── components/
│   │   ├── AppLayout.js            # 主布局（导航 + 设置 + 主题 + 角色切换）
│   │   ├── ChatContainer.js        # 聊天容器
│   │   ├── MessageBubble.js        # 消息气泡（含 TTS 播放 + 反馈）
│   │   ├── SidePanel.js            # 侧边栏（状态 + 画像 + 图片分析）
│   │   ├── ProfileCard.js          # 三段式画像卡片（学生+家长+家庭）
│   │   ├── VoiceInput.js           # 语音录入（VAD + 按住 + 连续对话）
│   │   ├── VoiceOutput.js          # 语音播放（HTTP + WebSocket 流式）
│   │   ├── SettingsDrawer.js       # 设置抽屉（6 Tab）
│   │   ├── ImageAnalyzer.js        # 图片分析（拖拽/粘贴/点击）
│   │   ├── LoginPage.js            # 登录/注册页面
│   │   ├── QuestionnairePage.js    # 调查问卷页面
│   │   ├── UniversityRanking.js    # 院校排名页面（QS/US News/泰晤士等）
│   │   ├── KnowledgeGraph.js       # 知识图谱可视化页面
│   │   └── admin/                  # B端管理后台
│   │       ├── AdminLayout.js      # 管理后台布局
│   │       ├── KnowledgeManagement.js
│   │       ├── DataSync.js
│   │       ├── SystemManagement.js
│   │       └── DataStatistics.js
│   ├── assets/
│   │   ├── styles.css              # 主样式（含院校排名/知识图谱样式）
│   │   └── themes.css              # 6 套主题变量
│   └── utils/
│       ├── apiClient.js            # 带Token注入的HTTP客户端
│       ├── AudioManager.js         # 全局音频管理（barge-in）
│       └── WebSocketClient.js      # WebSocket SDK
│
├── configs/                        # 配置文件
│   ├── .config.yaml                # 用户配置（选择 + API Key）
│   ├── llm_config.yaml             # LLM 模型库（11 预设）
│   ├── asr_config.yaml             # ASR 引擎库（10 预设）
│   ├── tts_config.yaml             # TTS 引擎库（9 预设）
│   ├── vllm_config.yaml            # 视觉模型库（6 预设）
│   ├── neo4j_config.yaml           # Neo4j知识图谱配置
│   ├── questionnaire_config.yaml   # 调查问卷配置（三类问卷+MBTI映射）
│   └── ...
│
├── data/
│   ├── sql_schema/                 # SQL DDL（01-11，含投研级数据表）
│   ├── documents/                  # 用户文档（自动索引）
│   ├── vector_store/               # 向量库数据
│   ├── raw/                        # 原始数据（283,653条录取数据）
│   └── zx_advisor.db               # SQLite数据库
│
├── scripts/                        # 脚本工具
│   ├── init_sqlite.py              # 数据库初始化
│   ├── import_neo4j.py             # Neo4j数据导入
│   ├── import_gaokao_from_xlsx.py  # 高考数据导入
│   ├── download_gaokao_data.py     # 数据下载
│   └── build_rag_index.py          # RAG索引构建
│
├── tasks/                          # Celery 异步任务
│   ├── rag_tasks.py                # RAG 索引构建
│   ├── crm_tasks.py                # CRM 画像分析
│   ├── cost_tasks.py               # 成本报告
│   └── cache_tasks.py              # 缓存清理
│
├── tests/                          # 测试（125+ 用例）
├── docker-compose.yml              # Docker 编排（api + redis + celery-worker + celery-beat）
├── celery_app.py                   # Celery 配置
├── requirements.txt                # Python 依赖
└── .env.example                    # 环境变量模板
```

---

## 测试

```bash
# 运行核心测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_synthesis_guard.py -v
```

测试覆盖：

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_tool_retry.py` | 工具容错 + 省名标准化 + SQL 降级 |
| `test_anti_hallucination.py` | 防幻觉 + 注入安全 + Skills 防穿透 |
| `test_synthesis_guard.py` | 防端水约束引擎（信号/Prompt/输出） |
| `test_skills_edge_cases.py` | 风险评估 + 现实校验 + 决策启发式 |
| `test_checkpoint_state.py` | 多轮对话状态 + 画像合并 + 冲突检测 |
| `test_supervisor_routing.py` | 路由精准度（30 条黄金用例） |
| `test_supervisor_fuzzing.py` | 路由模糊测试（720+ 组合） |
| `test_data_validators.py` | CSV 导入校验 |
| `test_feedback_store.py` | 反馈存储 |
| `test_routing_tuner.py` | 路由关键词调优 |

---

## 部署指南

### Docker Compose

```bash
export DEEPSEEK_API_KEY=sk-xxx
docker-compose up -d
```

服务拓扑：

| 服务 | 端口 | 说明 |
|------|------|------|
| api | 8000 | FastAPI 主服务 |
| redis | 6379 | 缓存 + Celery broker |
| celery-worker | - | 异步任务处理 |
| celery-beat | - | 定时任务调度 |

### Systemd

```ini
[Service]
ExecStart=/opt/zx_ai_advisor/venv/bin/python -m api.main
Restart=always
```

---

## 设计笔记

> 完整内容见 [docs/architecture.md](docs/architecture.md)

记录了项目从构思到落地的完整过程——踩过的坑、做过的取舍、以及每个版本为什么这样演进。

**核心痛点**：检索边界越权、控制流僵化、状态爆炸、同步阻塞、泛LLM依赖。

**解决方案**：Supervisor 路由 + Worker 工具链 + Skills 硬约束 + SynthesisGuard 防端水。

**十一条硬纪律**：数值逻辑不进向量库、规则引擎不交给大模型、服务挂了不阻断启动、LLM不能篡改风控信号、多轮对话不丢状态、工具查不到不直接报错、路由不能因噪音失效。

---

## 技术问答

> 完整内容见 [docs/technical-notes.md](docs/technical-notes.md)

| 问题 | 主题 |
|------|------|
| Q1 | 如何用工程手段建立基于大模型的评测标准？ |
| Q2 | 如何强制约束 Synthesis 节点不篡改硬规则严重程度？ |
| Q3 | 多轮对话的状态继承与覆盖 |
| Q4 | 工具异常的重试策略颗粒度 |
| Q5 | CRM 用户画像与断点续传 |
| Q6 | Supervisor 路由关键词混合测试 — Prompt Fuzzing |
| Q7 | 现代化可视化界面重设计 |
| Q8 | Vue 3 现代化前端架构升级 |

---

## 常见问题

**Q: 首次启动时长时间卡住不动？**

首次启动需要下载 `paraphrase-multilingual-MiniLM-L12-v2` 嵌入模型（约 420MB）。国内用户设置 `HF_ENDPOINT=https://hf-mirror.com`。

**Q: 报错 "DeepSeek API Key 未配置"？**

在 `.env` 文件中设置 `DEEPSEEK_API_KEY=sk-xxx`。

**Q: PostgreSQL 连接不上怎么办？**

系统会自动降级到 SQLite 本地数据库。不配置 PostgreSQL 不影响核心功能。

**Q: 如何更新知识库？**

```bash
curl -X POST http://127.0.0.1:8000/rag/upload -F "file=@your_document.pdf"
curl -X POST http://127.0.0.1:8000/rag/scan-documents
```

**Q: 前端界面如何自定义？**

编辑 `frontend/` 目录下的 Vue 3 组件即可。修改后刷新浏览器生效。

---

## 版本历史

> 完整内容见 [docs/version-history.md](docs/version-history.md)

### V5.0 (2026-06) — 投研级志愿系统

- 调查问卷系统（三类混合问卷：画像采集/排雷问卷/意向探索 + MBTI性格测试）
- 家庭冲突检测（双向约束矩阵 + 7类冲突检测 + 熔断机制）
- 反方审计引擎（5个视角挑刺：招生办/HR/家长/学生/应届生）
- AI暴露度评估（专业入门岗位被AI替代风险评估）
- 量化评分框架（100分制7维度：录取风险/专业适配/就业钱景/城市产业/学校平台/AI暴露/家庭共识）
- 硬编码过滤器（Python规则引擎：黑名单/体检/预算/地域/偏远校区）
- Neo4j知识图谱（院校-专业-职业-产业集群-就业政策多跳查询）
- 院校排名页面（QS/US News/泰晤士/自然指数/软科/中国大学排名）
- 知识图谱可视化（Canvas渲染图谱节点关系，支持拖拽缩放）
- 高考录取数据（283,653条2016-2020年全国29省录取数据）

### V4.5 (2026-06) — Commercial Ready 商业化就绪

- 用户认证系统（JWT Token + bcrypt 密码哈希 + 学生/家长/管理员多角色）
- 咕咕数据API集成（院校分数线/专业分数线/录取概率预测/批次线/院校信息）
- Function Calling 工具扩展（+4个新工具：专业录取、录取概率、批次线、院校信息）
- RRF混合搜索（ChromaDB向量 + FTS5全文 + 关键词 并行检索 + Reciprocal Rank Fusion排序）
- B端管理后台（知识库CRUD / API数据同步 / 系统状态 / 成本统计大屏）
- 前端登录页面 + Token自动注入拦截器

### V4.0 (2026-06) — 全栈能力升级

- 服务工厂（LLM/ASR/TTS/VLLM 四工厂 + 自动回退 + 熔断保护）
- 成本控制（Token 用量追踪 + 日/月限额）
- 情感分析 + 情绪 TTS（7 种情绪标签 + 语速/风格自适应）
- 流式 TTS（WebSocket 边合成边推送）
- WebSocket 全双工对话 + VAD 集成
- VLLM 视觉（GLM-4V / Qwen-VL / GPT-4o 图片分析）
- Celery 消息队列（异步 RAG/CRM/成本任务）
- 学科评分数组 + 家长画像 + 家庭融合
- 设置界面（6 Tab 右侧抽屉）+ 6 套个性化主题
- 配置重构（.config.yaml 精简 + 预设库分离 + 最新模型库）
- 联网搜索多源（DuckDuckGo / Metaso / Tavily）

### V3.7 (2026-05)

- 联网查询 + 本地落库（DuckDuckGo → SQLite + ChromaDB 双写）
- 24h 查询缓存 + REST API

### V3.1 (2026-05)

- RAG 多格式支持（csv/pdf/txt）
- 文档管理 API + 前端架构优化

### V3.0 (2026-05)

- Vue 3 组件化前端架构重建

### V2.6 — V2.0

- HuggingFace 国内镜像适配
- CRM 用户画像 + 路由模糊测试
- 工具多级容错降级
- Function Calling + ChromaDB + SQLite

### V2.1 — SynthesisGuard 防端水引擎

补上了 Agentic 系统中最危险的缺口——确定性风控信号在 LLM 生成阶段的保真传递。

---

## 版权声明

> 完整内容见 [docs/copyright.md](docs/copyright.md)

本项目为**纪念张雪峰老师**而创建，属于**非商业性、文化传承与技术研究**用途。代码采用 MIT 许可证开源，但数据来源声明与使用限制优先于 MIT 许可。

---

## 许可证

MIT License

---

## 文档目录

| 文档 | 说明 |
|------|------|
| [docs/faq.md](docs/faq.md) | **常见问题**（环境/语音/模型/知识库/画像/部署） |
| [docs/config-guide.md](docs/config-guide.md) | **配置指南**（.config.yaml / LLM / ASR / TTS / VLLM / 搜索） |
| [docs/providers.md](docs/providers.md) | **服务工厂**（LLM/ASR/TTS/VLLM 工厂 + 熔断 + 重试 + 自动回退） |
| [docs/voice-guide.md](docs/voice-guide.md) | **语音交互指南**（ASR / TTS / VAD / 意图打断 / WebSocket） |
| [docs/crm.md](docs/crm.md) | **CRM 用户画像系统**（学生+家长+家庭三维度） |
| [docs/knowledge-graph-guide.md](docs/knowledge-graph-guide.md) | **知识图谱指南**（Neo4j部署/图模型/查询工具/可视化） |
| [docs/questionnaire-guide.md](docs/questionnaire-guide.md) | **问卷系统指南**（三类问卷/MBTI/冲突检测/排雷机制） |
| [docs/data-import-guide.md](docs/data-import-guide.md) | **数据导入指南**（高考数据/院校数据/Neo4j导入） |
| [docs/test-plan.md](docs/test-plan.md) | **测试方案**（单元测试 / 集成测试 / 边界测试） |
| [docs/test-report.md](docs/test-report.md) | **测试报告**（125+ 用例全部通过） |
| [docs/v5.0-changelog.md](docs/v5.0-changelog.md) | **V5.0更新日志**（投研级系统完整变更记录） |
| [docs/architecture.md](docs/architecture.md) | 架构设计笔记（初衷/痛点/方案/十一条硬纪律） |
| [docs/technical-notes.md](docs/technical-notes.md) | 技术问答（Q1-Q8，8 个关键技术问题详解） |
| [docs/deployment.md](docs/deployment.md) | 部署指南（本地/Docker/生产环境/Nginx/Systemd） |
| [docs/api-reference.md](docs/api-reference.md) | API 参考（全部端点 + SSE/WebSocket 协议） |
| [docs/version-history.md](docs/version-history.md) | 版本历史（V2.0 至 V5.0 完整演进记录） |
| [docs/copyright.md](docs/copyright.md) | 版权声明与使用限制 |

---

<p align="center">
  <sub>纪念张雪峰老师 · 传承"用数据说话，重现实轻幻想"的报考咨询精神</sub>
</p>
