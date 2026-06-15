# 版本历史

## V5.0 (2026-06) — 投研级志愿系统

### 调查问卷系统
- **三类混合问卷**：画像采集/排雷问卷/意向探索
- **MBTI性格测试**：简化版4题MBTI + 专业映射
- **问卷服务层**：`skills/questionnaire_service.py` 支持4种题型验证
- **问卷API**：`/questionnaire/types`、`/questionnaire/submit` 等5个端点
- **前端问卷页面**：`QuestionnairePage.js` 支持进度追踪和结果预览

### 家庭冲突检测
- **双向约束矩阵**：家长硬约束 vs 学生软偏好
- **7类冲突检测**：预算vs公办、城市vs分数、专业vs禁止、体检vs专业等
- **熔断机制**：关键冲突未解决前，不给出最终推荐
- **冲突解决提示词**：自动注入SynthesisAgent，强制显性化处理

### 反方审计引擎
- **5个视角挑刺**：招生办/HR/家长/学生/应届生
- **7个审计维度**：预算击穿、体检退档、分数不足、AI暴露、天坑专业、读研不匹配、性价比
- **红线规则库**：高成本专业、体检严格专业、AI高风险任务、天坑专业
- **审计报告**：自动生成结构化审计报告，注入SynthesisAgent

### AI暴露度评估
- **14个专业任务映射**：计算机/会计/金融/法学/医学等
- **高风险任务识别**：基础翻译、传统财会、初级代码、基础客服等
- **高壁垒任务识别**：手术操作、现场勘查、复杂谈判、伦理审查等
- **能力增强建议**：根据风险等级生成职业发展建议

### 量化评分框架
- **100分制7维度评分**：
  - 录取风险（25分）：位次匹配度、录取把握
  - 专业适配（20分）：兴趣匹配、学科基础
  - 就业钱景（18分）：市场容量、薪资区间
  - 城市产业（12分）：产业集群、实习便利
  - 学校平台（10分）：学科声誉、保研比例
  - AI暴露（10分）：技术替代、增强潜力
  - 家庭共识（5分）：冲突解决、意见一致
- **等级划分**：A（85+）/ B（70+）/ C（55+）/ D（40+）/ E（<40）
- **批量评分**：`batch_score()` 方法支持多推荐排序

### 硬编码过滤器
- **五维过滤**：黑名单/体检/预算/地域/偏远校区
- **零Token消耗**：所有规则硬编码在Python中，不调用LLM
- **MBTI映射**：16种性格类型→适合专业推荐
- **铁饭碗识别**：公务员/军校/警校/师范/医学等关键词提取

### Neo4j知识图谱
- **7种节点类型**：University/Province/Major/Career/City/IndustryCluster/Policy
- **5种关系类型**：LOCATED_IN/OFFERS/LEADS_TO/HAS_CLUSTER/HAS_POLICY
- **模板化查询**：禁止Text2Cypher，所有Cypher预定义
- **3个查询工具**：`query_neo4j_admission_tool`/`query_career_path_tool`/`query_university_info_tool`
- **数据导入脚本**：`scripts/import_neo4j.py` 支持从SQLite批量导入

### 院校排名页面
- **6个排名来源**：QS/US News/泰晤士/自然指数/软科/中国大学排名
- **搜索和筛选**：支持关键词搜索和国家筛选
- **排名详情弹窗**：各项指标、相关链接
- **各排名体系对比**：说明各排名的侧重点和指标

### 知识图谱可视化
- **Canvas渲染**：图谱节点和关系可视化
- **4种查询类型**：按院校/专业/城市/职业
- **交互功能**：节点拖拽、缩放、悬停提示
- **节点详情面板**：显示关联节点和属性

### 高考录取数据
- **数据来源**：labolado/gaokao_2016-2020
- **数据量**：283,653条2016-2020年全国29省录取数据
- **覆盖省份**：29个（上海、浙江除外）
- **导入脚本**：`scripts/import_gaokao_from_xlsx.py` 支持xlsx解析

### 投研级数据表
- **4张去水表**：就业去向/收入证据/稳定性线索/发展路径
- **5张新增表**：城市数据/专业薪资/企业招聘/就业政策/校区地理
- **数据来源**：国家统计局/招聘平台/学校报告

### 前端导航升级
- **顶部导航栏**：对话/院校排名/知识图谱三个入口
- **页面切换**：无需刷新页面，Vue组件动态切换
- **样式统一**：新增页面与现有主题风格一致

---

## V4.0 (2026-06) — 全栈能力升级

### 服务工厂 + 容错
- **LLM/ASR/TTS/VLLM 四工厂**：工厂模式动态创建供应商实例，支持运行时切换
- **自动回退**：`ResilientLLMProvider` 主供应商熔断后自动切换备用
- **熔断器**：三态熔断（CLOSED → OPEN → HALF_OPEN），连续失败 5 次自动熔断
- **指数退避重试**：`delay = min(base * 2^attempt + jitter, max)`，全 Provider 集成

### 成本控制
- **Token 用量追踪**：`token_usage` 表记录每次 LLM 调用的 input/output tokens
- **内置定价表**：覆盖 DeepSeek/Qwen/GLM/Doubao 等 10+ 模型
- **日/月限额**：默认日限 10 元、月限 200 元，超限返回友好提示

### 情感分析 + 情绪 TTS
- **情感分析模块**：关键词规则（默认免费）+ LLM 提取双方案
- **7 种情绪标签**：happy/excited/neutral/confused/anxious/sad/disappointed/angry
- **情绪 TTS**：根据情绪调整语速/风格（Edge TTS rate / CosyVoice style）
- **SSE 情绪推送**：profile_update 事件携带 emotion 数据

### 流式 TTS
- **Edge TTS 流式**：`synthesize_stream()` 异步生成器逐 chunk 推送
- **WebSocket TTS 端点**：`ws /voice/tts-stream` 边合成边推送
- **前端双模式**：HTTP 整段 + WebSocket 流式（设置中切换）

### WebSocket 全双工
- **`/ws/chat` 端点**：支持文本对话、流式音频输入、状态推送
- **VAD 集成**：PCM 音频 chunk → SileroVAD 检测端点 → ASR → LLM
- **WebSocket SDK**：`WebSocketClient.js` 自动重连、心跳、事件分发

### VLLM 视觉
- **视觉模型工厂**：`VLLMFactory` 支持 GLM-4V / Qwen-VL / GPT-4o
- **图片分析 API**：`POST /vision/analyze` + `POST /vision/chat`
- **前端图片分析组件**：拖拽/粘贴/点击上传，自定义分析指令

### 情感分析 + Celery
- **Celery 消息队列**：Redis broker，3 个队列（default/rag/crm）
- **异步任务**：RAG 索引构建、CRM 画像分析、成本报告、缓存清理
- **docker-compose**：新增 celery-worker + celery-beat 容器

### 用户画像增强
- **学科评分数组**：9 门学科自评 + 高考分数（未选科 null）
- **强势/弱势学科**：自动提取 + 前端九宫格展示
- **兴趣爱好**：16 类兴趣关键词提取（编程/数学/体育/音乐等）
- **目标院校**：30+ 重点大学名称匹配
- **性别、风险偏好**：新增字段

### 家长画像 + 家庭融合
- **独立 parent_agent**：提取家长角色/职业/行业/学历/期望/担忧/决策风格
- **独立 family_agent**：融合学生+家长画像，推断收入水平/决策人/地域偏好/家校一致性
- **CRM 扩展**：新增 `parent_profiles` + `family_contexts` 表
- **前端三段式画像卡片**：学生画像 + 家长画像 + 家庭背景

### 设置界面 + 个性化主题
- **右侧抽屉设置面板**：6 个 Tab（个性化/网络/AI/语音/情感/高级）
- **6 套全组件级别主题**：深蓝/橙/绿/紫/红/青，覆盖 54 个 CSS 变量
- **主题覆盖范围**：header/按钮/输入框/气泡/侧边栏/卡片/边框/背景/渐变/阴影
- **localStorage 持久化** + 后端同步

### 配置重构
- **`.config.yaml` 精简**：从 305 行精简到 45 行，只保留选择 + API Key
- **预设库分离**：llm_config/asr_config/tts_config/vllm_config 各自独立
- **模型库更新**：DeepSeek V4 / Qwen 3.7 / GLM 5.1 / Seed 2.0 / Kimi K2.6
- **`api_keys` 统一管理**：支持 `${ENV_VAR}` 语法，一处配置全局生效

### 联网搜索增强
- **多搜索源**：DuckDuckGo（免费）/ Metaso（秘塔）/ Tavily
- **配置化切换**：`web_search_config.yaml` 的 `provider` 字段

### 集成修复
- **window.API_BASE 兜底**：直接打开 index.html 不再报错
- **SettingsDrawer 同步后端**：保存设置时同时写入后端
- **.env.example 完善**：覆盖 20+ 环境变量（LLM/ASR/TTS/搜索/基建）

---

## V3.7 (2026-05)

- **联网查询 + 本地落库**：`web_search_agent` 支持 DuckDuckGo 搜索 → httpx/trafilatura 抓取正文 → SQLite + ChromaDB 双写
- **24h 查询缓存**：相同关键词命中本地缓存可跳过外网
- **REST API**：新增 `/web/search`、`/web/sessions`、`/web/cache/check`
- **数据导入**：专业库（8 条）、2024 广东物理类投档线（12 条）、经验库增量（7 条）

## V3.1 (2026-05)

- **RAG 多格式支持**：新增 `.csv` / `.pdf` / `.txt` 文档解析
- **文档管理 API**：`/rag/upload` 文件上传即时解析，`/rag/scan-documents` 目录扫描重建
- **前端架构优化**：Flask 同源代理 SSE 流式传输
- **Vue 响应式修复**：修复消息更新时 raw 对象绕过 Vue Proxy 的问题

## V3.0 (2026-05)

- **前端重建**：从单文件 HTML 升级为 Vue 3 组件化架构
- 新增 7 个独立 Vue 组件
- 引入 Tailwind CSS 和 Font Awesome 图标库
- 响应式布局支持（桌面端双栏 / 移动端自适应）
- 服务状态实时监控（五路指示灯 + 运行时长）

## V2.6

- HuggingFace 国内镜像适配 (`HF_ENDPOINT` 环境变量)
- 环境稳健性增强
- `.env` 自动加载逻辑改进

## V2.5

- CRM 用户画像（手机号主键，断点续传）
- 路由模糊测试（720+ 组合用例）
- 可视化界面重设计

## V2.3

- 工具多级容错降级（SQL 四级 + RAG 双路）
- 省名标准化（37 个省级行政区映射）
- ToolResult 统一返回值

## V2.0

- Function Calling 工具链
- ChromaDB 本地向量数据库
- SQLite 本地数据库
- RAG 更新 API

## V2.1 — SynthesisGuard 防端水引擎

V2.0 → V2.1 的核心升级：补上了 Agentic 系统中最危险的缺口——**确定性风控信号在 LLM 生成阶段的保真传递**。

系统具备了完整的"检测 → 指令注入 → 输出校验 → 强制修正"闭环：
- 即使 LLM 试图"端水"，输出层也会被强制纠正
- 即使 LLM 尝试把 `must_say` 改写或缩写，校验层会检测到缺失并重新注入
- 即使 LLM 把风险警告藏在回复末尾，位置校验会触发强制前置
