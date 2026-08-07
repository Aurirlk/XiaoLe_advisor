# 小乐AI · 交付手册

> 版本: v7.0  
> 更新日期: 2026-06-25  
> 适用人员: 开发团队、运维团队、测试人员

---

## 一、项目概述

### 1.1 项目定位

小乐AI 是一个智能高考志愿填报顾问系统，采用张雪峰老师的咨询风格——用数据说话、重现实轻幻想、该劝退绝不端水。

### 1.2 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| **多维意图识别** | 三层路由（场景/路径/决心度） | ✅ |
| **渐进询问** | 基于 RAG/图谱/CRM 生成引导问题 | ✅ |
| **信息差弥合** | 主动告知用户该知道的事 | ✅ |
| **决策框架** | 教用户用什么标准做决定 | ✅ |
| **现实映射** | 把选择和后果直接关联 | ✅ |
| **家庭调解** | 帮助家长和学生达成共识 | ✅ |
| **情感支持** | 承认焦虑、提供支持 | ✅ |
| **知识图谱** | Neo4j 院校-专业-职业关联 | ✅ |
| **多维排名** | QS/US News/泰晤士/软科等 6 个来源 | ✅ |
| **志愿表生成** | 冲稳保策略 + 录取概率 | ✅ |
| **就业数据** | 联网搜索 + 国家统计局数据 | ✅ |

---

## 二、技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主语言 |
| FastAPI | latest | 异步 API 框架 |
| LangGraph | latest | 多智能体编排 |
| DeepSeek / Qwen / GLM 等 | V4 | 大语言模型 |
| SQLite | 3 | 本地嵌入式数据库（默认） |
| Neo4j | 5.x | 知识图谱数据库（可选） |
| Redis | 7 | 缓存与会话（可选） |
| ChromaDB | latest | 向量数据库 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.3+ | 前端框架 |
| Vue Router | 4.x | 路由管理 |
| Vite | 5.x | 构建工具 |
| Font Awesome | 6.4.0 | 图标库 |

> **架构变化**：V7.0 从 Flask CDN 模式迁移到 Vite + Vue 3 SPA 模式，前端由 FastAPI 在 port 8000 统一 serve。

---

## 三、部署清单

### 3.1 环境要求

| 依赖 | 最低版本 | 用途 | 必需 |
|------|----------|------|------|
| Python | 3.10+ | 后端运行时 | ✅ |
| Node.js | 18+ | **构建**前端（仅部署时需要） | ⚠️ |
| Neo4j | 5.x | 知识图谱 | ❌ |
| Redis | 6.x+ | 会话缓存 | ❌ |

### 3.2 部署步骤

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key

# 3. 构建前端 SPA（关键步骤！）
cd frontend
npm install
npm run build
cd ..

# 4. 初始化数据库
python scripts/init_sqlite.py

# 5. 运行数据库迁移
python scripts/migrate_intent_tables.py
python scripts/migrate_questionnaire_fields.py

# 6. 导入数据
python scripts/build_rag_index.py
# （可选）python scripts/import_gaokao_from_xlsx.py

# 7. 导入 Neo4j（可选，需先启动 Neo4j）
python scripts/import_neo4j.py

# 8. 启动服务
python -m api.main
```

### 3.3 验证清单

| 验证项 | 命令 | 预期结果 |
|--------|------|----------|
| 服务启动 | `python -m api.main` | 预加载完成，无 ERROR |
| 健康检查 | `curl http://127.0.0.1:8000/healthz` | `{"ok": true}` |
| 状态检查 | `curl http://127.0.0.1:8000/status` | 含 db_ready / graph_ready |
| 前端访问 | 浏览器打开 `http://127.0.0.1:8000` | 显示登录页面 |
| 登录测试 | 输入测试账号登录 | 跳转到对话界面 |
| 对话测试 | 发送一条消息 | SSE 流式响应 |
| 院校排名 | 点击"院校排名"标签 | 显示排名表格 + 滑动器 |
| 知识图谱 | 点击"知识图谱"标签 | Canvas 渲染图谱节点 |
| 暗色模式 | 点击左下角 🌙/☀️ 按钮 | 切换深色/浅色主题 |
| 设置面板 | 点击右上角 ⚙ 按钮 | 弹出设置抽屉 |
| 语音输入 | 点击输入框左侧 🎤 | 开始录音（需麦克风权限） |
| 管理员端 | 管理员账号登录 | 系统监控/知识库/同步/统计面板 |

### 3.4 测试账号

| 角色 | 手机号 | 密码 |
|------|--------|------|
| 管理员 | `13800000000` | `admin123` |
| 学生 | `13800000001` | `student123` |
| 家长 | `13800000002` | `parent123` |

---

## 四、交付物清单

### 4.1 后端交付

| 类别 | 文件 | 说明 |
|------|------|------|
| Agent | `agents/supervisor_agent.py` | 三层路由中枢 |
| Agent | `agents/chat_agent.py` | 普通聊天 + 情感支持 |
| Agent | `agents/decision_detector.py` | 决心度检测 + 回退引导 |
| Agent | `agents/synthesis_agent.py` | 综合回答生成 |
| Worker | `agents/workers/*.py` | 专业 Worker Agent |
| Skill | `skills/info_gap_bridger.py` | 信息差弥合 |
| Skill | `skills/decision_framework.py` | 决策框架生成 |
| Skill | `skills/reality_mapper.py` | 现实映射 |
| Skill | `skills/family_mediator.py` | 家庭调解 |
| Skill | `skills/emotional_support.py` | 情感支持 |
| Core | `core/intent_tracker.py` | 意图追踪 |
| Core | `core/graph_builder.py` | Agent 图构建 |
| API | `api/main.py` | FastAPI 应用入口 + SPA serve |
| API | `api/routers/*.py` | API 路由 |

### 4.2 前端交付

| 类别 | 文件 | 说明 |
|------|------|------|
| 入口 | `frontend/src/main.js` | Vue 3 应用入口 |
| 路由 | `frontend/src/router/index.js` | 7 条路由 + auth guard |
| 视图 | `frontend/src/views/LoginView.vue` | 登录/注册页 |
| 视图 | `frontend/src/views/StudentView.vue` | 学生对话页 |
| 视图 | `frontend/src/views/ParentView.vue` | 家长对话页 |
| 视图 | `frontend/src/views/AdminView.vue` | 管理后台（4 面板） |
| 视图 | `frontend/src/views/RankingView.vue` | 院校排名（滑动器+分页） |
| 视图 | `frontend/src/views/GraphView.vue` | 知识图谱 Canvas |
| 视图 | `frontend/src/views/QuestionnaireView.vue` | 问卷填写 |
| 组件 | `frontend/src/components/ChatContainer.vue` | SSE 流式对话核心 |
| 组件 | `frontend/src/components/SettingsDrawer.vue` | 设置面板（深色/主题/语音） |
| 组件 | `frontend/src/components/VoiceInput.vue` | 语音输入按钮 |
| 组件 | `frontend/src/components/SidePanel.vue` | 侧边栏（状态+画像） |
| 组件 | `frontend/src/components/MessageBubble.vue` | 消息气泡（Markdown） |
| 工具 | `frontend/src/utils/apiClient.js` | API 客户端 |
| 样式 | `frontend/src/assets/global.css` | 全局样式（66KB） |
| 样式 | `frontend/src/assets/chat.css` | 对话样式（60KB） |

### 4.3 脚本交付

| 文件 | 说明 |
|------|------|
| `scripts/init_sqlite.py` | 数据库初始化 |
| `scripts/build_rag_index.py` | RAG 索引构建 |
| `scripts/import_neo4j.py` | Neo4j 数据导入 |
| `scripts/import_all.py` | 一键数据导入 |
| `scripts/create_admin.py` | 创建管理员账号 |

### 4.4 文档交付

| 文件 | 说明 |
|------|------|
| `docs/部署指南.md` | 部署指南（本地/Docker/生产） |
| `docs/常见问题.md` | 常见问题 FAQ（31 条） |
| `docs/OPERATIONS.md` | 运维手册（架构/部署/监控） |
| `docs/DELIVERY.md` | 交付手册（本文件） |
| `docs/架构设计笔记.md` | 架构设计说明 |
| `docs/技术文档.md` | 技术实现细节 |

---

## 五、路由清单

| 路径 | 名称 | 角色限制 | 说明 |
|------|------|----------|------|
| `/#/login` | Login | 游客 | 登录/注册 |
| `/#/student/chat` | StudentChat | 学生 | 对话咨询 |
| `/#/student/ranking` | StudentRanking | 学生 | 院校排名 |
| `/#/student/graph` | StudentGraph | 学生 | 知识图谱 |
| `/#/parent/chat` | ParentChat | 家长 | 对话咨询 |
| `/#/parent/questionnaire` | ParentQuestionnaire | 家长 | 问卷填写 |
| `/#/admin` | Admin | 管理员 | 管理后台 |

---

## 六、数据清单

### 6.1 数据库表

| 表名 | 用途 | 记录数 |
|------|------|--------|
| `universities` | 院校信息 | 2,817 |
| `admission_scores` | 录取分数线 | 283,653 |
| `majors` | 专业信息 | 883 |
| `user_profiles` | 用户画像 | 动态 |
| `user_intent_log` | 意图日志 | 动态 |
| `user_decision_journey` | 决策旅程 | 动态 |

### 6.2 RAG 索引

| 指标 | 值 |
|------|-----|
| 文档数量 | 1,998 条 |
| 索引大小 | 389KB |
| 覆盖范围 | 46 个文档（13 专业门类 + 33 院校省份） |

---

## 七、验收标准

### 7.1 功能验收

| 功能 | 测试方法 | 通过标准 |
|------|----------|----------|
| 登录/注册 | 使用测试账号登录 | 跳转到对应角色的对话页面 |
| 对话咨询 | 发送"江西518分应该报考什么学校" | 收到 SSE 流式回答 |
| 院校排名 | 选择 QS 排名来源 | 显示排名表格，滑动器可用 |
| 知识图谱 | 搜索"计算机" | Canvas 显示图谱节点 |
| 问卷提交 | 填写完整问卷 | 显示提交成功 |
| 暗色模式 | 点击左下角切换按钮 | 页面切换深色/浅色 |
| 设置面板 | 点击右上角 ⚙ | 弹出设置抽屉 |
| 管理员面板 | 查看系统监控 | 显示各服务状态 |

### 7.2 性能指标

| 指标 | 目标值 |
|------|--------|
| 首次响应时间 | ≤2s |
| 前端构建时间 | ≤3s |
| 主 JS 包大小（gzip） | ≤45KB |
| 首页加载时间 | ≤3s |
