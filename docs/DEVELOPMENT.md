# 小乐AI · 开发者文档

> 版本: v7.0  
> 更新日期: 2026-06-25  
> 适用人员: 后端开发、前端开发

---

## 一、项目结构

```
小乐高考志愿填报助手/
├── agents/                    # Agent 定义
│   ├── supervisor_agent.py    # 路由中枢（三层意图识别）
│   ├── synthesis_agent.py     # 综合回答生成
│   ├── chat_agent.py          # 普通聊天 Agent
│   ├── decision_detector.py   # 决心度检测 + 回退引导
│   └── workers/               # 工作 Agent
│       ├── profile_agent.py   # 学生画像提取
│       ├── profile_keywords.py # 关键词库（从 profile_agent 拆分）
│       ├── parent_agent.py    # 家长画像提取
│       ├── family_agent.py    # 家庭融合
│       ├── match_agent.py     # 分数线匹配
│       ├── career_agent.py    # 职业分析
│       ├── web_search_agent.py # 联网搜索
│       └── sql_agent.py       # 数据库查询
├── api/                       # API 层
│   ├── main.py                # FastAPI 应用入口 + SPA 静态文件 serve
│   ├── module_manager.py      # 模块管理（从 main.py 拆分）
│   ├── dependencies.py        # 依赖注入
│   └── routers/               # API 路由
│       ├── auth_router.py     # 认证
│       ├── chat_router.py     # 对话
│       ├── stream_router.py   # SSE 流式
│       ├── admin_router.py    # 管理后台
│       ├── graph_router.py    # 知识图谱
│       ├── ranking_router.py  # 院校排名
│       └── ...
├── core/                      # 核心模块
│   ├── state_schema.py        # LangGraph 状态定义
│   ├── graph_builder.py       # Agent 图构建
│   ├── crm_manager.py         # CRM 画像管理
│   ├── intent_tracker.py      # 意图追踪（从 crm_manager 拆分）
│   ├── kg_client.py           # Neo4j 客户端
│   ├── auth.py                # JWT 认证
│   ├── harness.py             # 数据引导引擎
│   ├── harness_scenarios.py   # 场景定义（从 harness 拆分）
│   └── ...
├── skills/                    # 技能模块
│   ├── info_gap_bridger.py    # 信息差弥合
│   ├── decision_framework.py  # 决策框架生成
│   ├── emotional_support.py   # 情感支持
│   ├── decision_heuristics.py # 渐进询问
│   ├── reason_generator.py    # 推荐理由
│   ├── scoring_dimensions.py  # 评分维度（从 quantitative_scorer 拆分）
│   └── ...
├── tools/                     # 工具层
│   ├── rag_tools.py           # RAG 检索
│   ├── sql_tools.py           # SQL 查询
│   ├── web_search_tools.py    # 联网搜索
│   ├── graph_rag.py           # GraphRAG
│   ├── employment_search.py   # 就业数据搜索
│   └── ...
├── frontend/                  # 前端（Vite + Vue 3 SPA）
│   ├── index.html             # 开发模式入口
│   ├── src/                   # 源码目录
│   │   ├── main.js            # Vue 3 应用入口
│   │   ├── App.vue            # 根组件（header/路由/暗色模式/设置抽屉）
│   │   ├── router/index.js    # Vue Router（7 条哈希路由 + auth guard）
│   │   ├── views/             # 页面视图
│   │   │   ├── LoginView.vue
│   │   │   ├── StudentView.vue
│   │   │   ├── ParentView.vue
│   │   │   ├── AdminView.vue
│   │   │   ├── RankingView.vue
│   │   │   ├── GraphView.vue
│   │   │   └── QuestionnaireView.vue
│   │   ├── components/        # Vue SFC 组件
│   │   │   ├── ChatContainer.vue
│   │   │   ├── SettingsDrawer.vue
│   │   │   ├── VoiceInput.vue
│   │   │   ├── MessageBubble.vue
│   │   │   ├── SidePanel.vue
│   │   │   └── ...
│   │   ├── assets/            # CSS 样式（global.css + chat.css）
│   │   └── utils/             # 前端工具
│   │       └── apiClient.js   # HTTP 客户端
│   ├── dist/                  # 构建产物（由后端 serve）
│   ├── vite.config.js         # Vite 配置
│   └── package.json           # 依赖管理
├── scripts/                   # 脚本
│   ├── init_sqlite.py         # 数据库初始化
│   ├── import_gaokao_from_xlsx.py  # 数据导入
│   ├── import_neo4j.py        # Neo4j 导入
│   ├── build_rag_index.py     # RAG 索引构建
│   ├── generate_real_knowledge_docs.py # 知识库生成
│   ├── download_employment_data.py # 就业数据下载
│   ├── create_admin.py        # 创建管理员账号
│   ├── test_e2e_api.py        # API 测试
│   └── migrate_*.py           # 数据库迁移脚本
├── configs/                   # 配置文件
│   ├── .config.yaml           # 运行时配置
│   ├── neo4j_config.yaml      # Neo4j 配置
│   ├── web_search_config.yaml # 联网搜索配置
│   └── ...
├── data/                      # 数据目录
│   ├── zx_advisor.db          # SQLite 数据库
│   ├── ranking_data.json      # 排名数据
│   ├── vector_store/          # 向量索引
│   ├── documents/             # 知识库文档
│   └── crawl_results/         # 爬取数据
├── docs/                      # 文档
│   ├── DELIVERY.md            # 交付手册
│   ├── OPERATIONS.md          # 运维手册
│   ├── 部署指南.md             # 部署指南
│   ├── 常见问题.md             # 常见问题 FAQ
│   ├── 配置指南.md             # 配置指南
│   └── DEVELOPMENT.md         # 开发者文档（本文件）
└── tests/                     # 测试
    └── e2e_frontend.spec.js   # 前端 E2E 测试
```

---

## 二、核心架构

### 2.1 Agent 图（LangGraph）

```
用户输入 → scene_router（场景识别）
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
  chat    gaokao    postgraduate
    │         │         │
    ▼         ▼         ▼
 chat_agent  supervisor  path_router
    │         │         │
    ▼         ▼         ▼
   END    worker_agents  decision_detector
              │         │
              ▼         ▼
          synthesis_agent
              │
              ▼
             END
```

### 2.2 状态定义

`core/state_schema.py` 定义了 `GraphState`，包含：

| 类别 | 字段 | 说明 |
|------|------|------|
| 对话基础 | `user_query`, `session_id`, `messages` | 用户输入和对话历史 |
| 学生画像 | `user_profile`, `extracted_score`, `subject_scores` | 学生信息 |
| 家长画像 | `parent_profile`, `parent_constraints` | 家长信息 |
| 家庭背景 | `family_context`, `family_conflict` | 家庭分析 |
| 意图识别 | `scene_type`, `path_type`, `decision_state` | 三层路由状态 |
| 渐进询问 | `progressive_questions`, `missing_info` | 引导问题 |
| 增强模块 | `info_gap_content`, `decision_framework`, `reality_mapping` | 内容注入 |
| 推荐理由 | `recommendation_reasons` | 数据支撑 |
| 情绪 | `emotion_label`, `emotion_intensity` | 情绪分析 |

### 2.3 数据流

```
用户输入
  ↓
SSE 流式接口（stream_router.py）
  ↓
LangGraph 执行（graph_builder.py）
  ├→ supervisor_agent → 路由决策
  ├→ worker_agent → 数据采集（SQL/RAG/Web/Neo4j）
  ├→ synthesis_agent → 综合回答（+ 信息差/决策框架/现实映射/情感支持）
  └→ 返回前端（+ 意图/渐进询问/回退/推荐理由）
```

---

## 三、开发规范

### 3.1 文件命名

- Python: `snake_case.py`
- Vue: `PascalCase.vue`（组件）/ `camelCase.js`（工具）
- CSS: `kebab-case.css`

### 3.2 代码风格

- Python: 遵循 PEP 8，使用 type hints
- Vue 3: Options API，`<template>` + `<script>` + `<style scoped>`
- CSS: 使用 CSS 变量（`var(--xxx)`），不硬编码颜色

### 3.3 提交规范

```
feat: 新功能
fix: 修复
refactor: 重构
docs: 文档
style: 样式
test: 测试
chore: 构建/工具
```

---

## 四、新增 Agent 开发

### 4.1 创建 Agent

```python
# agents/workers/my_agent.py
from core.state_schema import GraphState

def build_my_agent(tools):
    async def my_agent(state: GraphState) -> dict:
        query = state.get("user_query", "")
        # 业务逻辑
        result = do_something(query)
        return {
            "my_result": result,
            "next_node": "synthesis_agent",
        }
    return my_agent
```

### 4.2 注册到图

```python
# core/graph_builder.py
from agents.workers.my_agent import build_my_agent

my_agent = build_my_agent(some_tools)
graph.add_node("my_agent", safe_node_call(my_agent, state))
graph.add_edge("my_agent", "synthesis_agent")

# 在 supervisor_agent 的路由中添加
"my_agent": "my_agent"
```

---

## 五、新增 API 端点

```python
# api/routers/my_router.py
from fastapi import APIRouter
router = APIRouter(prefix="/my", tags=["my"])

@router.get("/endpoint")
async def my_endpoint():
    return {"ok": True}
```

在 `api/main.py` 中注册：
```python
from api.routers.my_router import router as my_router
app.include_router(my_router)
```

---

## 六、前端组件开发

### 6.1 组件模板

```vue
<!-- frontend/src/components/MyComponent.vue -->
<template>
  <div>...</div>
</template>

<script>
export default {
  name: 'MyComponent',
  props: { ... },
  emits: ['event'],
  data() { return { ... } },
  methods: { ... },
}
</script>

<style scoped>
/* 组件样式 */
</style>
```

### 6.2 注册组件

在 `frontend/src/main.js` 中：
```javascript
import MyComponent from './components/MyComponent.vue'
app.component('MyComponent', MyComponent)
```

### 6.3 添加路由

在 `frontend/src/router/index.js` 中新增：
```javascript
{
  path: '/my-route',
  name: 'MyRoute',
  component: () => import('../views/MyView.vue'),
  meta: { requiresAuth: true }
}
```

---

## 七、前端开发须知

### 7.1 构建流程

```bash
cd frontend
npm install          # 安装依赖
npm run build        # 生产构建（输出到 dist/）
npm run dev          # 开发模式（HMR + proxy → localhost:8000）
```

### 7.2 开发模式（HMR）

确保后端在 8000 端口运行，然后：
```bash
cd frontend
npm run dev
```
访问 `http://localhost:5173`，HMR 自动刷新。API 请求通过 Vite proxy 转发到 `localhost:8000`。

### 7.3 生产构建

`npm run build` 生成 `frontend/dist/` 目录，由后端 FastAPI 的 `StaticFiles` 中间件 serve。每次修改前端代码后需要重新构建才能在生产环境生效。

### 7.4 路由列表

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

## 八、数据库迁移

```python
# scripts/migrate_xxx.py
import sqlite3
conn = sqlite3.connect("data/zx_advisor.db")
conn.execute("ALTER TABLE xxx ADD COLUMN yyy TEXT DEFAULT ''")
conn.commit()
conn.close()
```

---

## 九、测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_supervisor_routing.py

# 运行前端 E2E 测试
npx playwright test tests/e2e_frontend.spec.js
```
