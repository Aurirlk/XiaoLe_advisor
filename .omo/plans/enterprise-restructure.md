# 小乐AI · 企业级架构重构 Plan

## TL;DR

> **目标**: 参照 `smart-recruit-ai` 的工程规范，将现有高考报考系统重构为企业级架构——前端采用 Element Plus 替代手写 CSS，后端分层重组为 `backend/app/{routers,services,utils}`，保持现有业务功能不变。
>
> **核心改动**:
> - 前端: Element Plus + 角色化布局 + Axios 统一封装 + 嵌套路由
> - 后端: 目录重组 + 服务层抽取 + 统一响应格式
> - 不动: agents/ core/ skills/ tools/ 的业务逻辑（只迁移位置，不改内容）
>
> **预计工作量**: Large
> **并行执行**: YES — 3 waves
> **关键路径**: Task 1 → Task 4 → Task 7 → Task 11 → Task 13

---

## Context

### 现状问题

| 维度 | 现在 | 目标 |
|------|------|------|
| UI 框架 | 手写 CSS 126KB + inline style | Element Plus 成熟组件库 |
| 布局 | App.vue 单一 header | 学生/家长/管理员三端独立 Layout |
| API 调用 | 各 View 内直接 fetch | Axios 统一封装 + 拦截器 |
| 后端结构 | `api/` 根目录平铺 | `backend/app/{routers,services,utils}` 分层 |
| 路由 | 简单 auth guard | 嵌套路由 + 布局级守卫 |
| 响应格式 | 不一致 | 统一 `{code, data, message}` |

### 参考项目

- **smart-recruit-ai** (WanFrancon): Vue 3 + Vite + Element Plus + FastAPI + MySQL
- 采用 Element Plus 组件库，三端分离布局，Axios 封装，服务层分离

---

## Work Objectives

### Core Objective
将现有小乐AI高考报考系统重构为企业级架构，前端使用 Element Plus 组件库，后端分层重组，保持所有现有功能不变。

### Concrete Deliverables
- `frontend/src/layouts/` — 学生/家长/管理员三端布局
- `frontend/src/api/` — Axios 统一封装 + 按模块拆分的 API 接口
- `frontend/src/router/index.js` — 嵌套路由 + 角色守卫
- 所有 `.vue` 文件改用 Element Plus 组件，去除 inline style
- `backend/app/` — routers/ + services/ + utils/ 分层
- `backend/app/utils/response.py` — 统一响应格式
- `backend/app/services/` — 业务逻辑从 routers 中抽取

### Definition of Done
- [ ] `npm run build` 无报错
- [ ] `python -m api.main` 无报错
- [ ] 登录 → 学生对话/排名/图谱 全部可访问
- [ ] 登录 → 家长对话/问卷 全部可访问
- [ ] 登录 → 管理员面板 可访问
- [ ] 暗色模式/设置面板 仍可用
- [ ] 所有 API 端点响应正常

### Must Have
- Element Plus 作为 UI 框架
- 角色化布局（学生/家长/管理员独立 Layout）
- Axios 统一封装（Token 自动注入 + 错误拦截）
- 后端服务层分离
- 统一 API 响应格式

### Must NOT Have (Guardrails)
- 不改动 agents/ core/ skills/ tools/ 的业务逻辑
- 不引入 MySQL/PostgreSQL（保持 SQLite）
- 不引入 Docker
- 不引入 Redis（保持可选）
- 不做复杂 RBAC（保持现有角色简单鉴权）
- 不做向量数据库迁移（保持 ChromaDB）
- 不做新功能开发（纯架构重构）
- 不删除任何现有功能

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None（纯重构，不加新测试）
- **Agent-Executed QA**: 每个 task 都有 QA 场景

### QA Policy
- **Frontend**: 使用 Playwright 导航到各路由，验证 Element Plus 组件渲染
- **Backend**: 使用 curl 测试 API 端点响应
- **Build**: 每个 wave 结束后执行 `npm run build` + `python -m api.main`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation + infrastructure):
├── Task 1: 安装 Element Plus + 配置 main.js [quick]
├── Task 2: 后端目录重组 (backend/app/{routers,services,utils}) [quick]
├── Task 3: 创建 Axios 统一封装 (api/request.js) [quick]
├── Task 4: 创建三端布局 (layouts/) [visual-engineering]
├── Task 5: 创建统一响应格式 + 集中配置 [quick]
└── Task 6: 创建 API 模块 (auth.js, chat.js, dashboard.js) [quick]

Wave 2 (After Wave 1 — core views + services):
├── Task 7: 重写 LoginView (Element Plus 表单) [visual-engineering]
├── Task 8: 重写 StudentView + ChatContainer (Element Plus 对话) [visual-engineering]
├── Task 9: 重写 ParentView (Element Plus 对话) [visual-engineering]
├── Task 10: 重写 AdminView (Element Plus 面板) [visual-engineering]
├── Task 11: 重写 Router (嵌套路由 + 布局级守卫) [unspecified-high]
└── Task 12: 后端服务层抽取 (auth_service, chat_service) [unspecified-high]

Wave 3 (After Wave 2 — feature views + polish):
├── Task 13: 重写 RankingView + GraphView + QuestionnaireView [visual-engineering]
├── Task 14: 重写 SettingsDrawer + VoiceInput + SidePanel [visual-engineering]
├── Task 15: 清理旧 CSS + 构建验证 [quick]
└── Task 16: 文档更新 [writing]

Wave FINAL (After ALL tasks):
├── Task F1: 全路由功能验证 [unspecified-high]
├── Task F2: 构建 + Lint 验证 [unspecified-high]
└── Task F3: 旧文件清理确认 [unspecified-high]

Critical Path: Task 1 → Task 7/8 → Task 11 → Task 13 → Task 15 → F1-F3
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 6 (Wave 1)
```

---

## TODOs

- [ ] 1. 安装 Element Plus + 配置 main.js + vite.config.js

  **What to do**:
  - 在 `frontend/` 目录执行 `npm install element-plus @element-plus/icons-vue`
  - 在 `frontend/src/main.js` 中全局注册 Element Plus：
    ```js
    import ElementPlus from 'element-plus'
    import 'element-plus/dist/index.css'
    import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
    app.use(ElementPlus, { locale: zhCn })
    ```
  - 在 `frontend/vite.config.js` 中添加 Element Plus 自动导入（可选，手动注册更稳定）
  - 验证：`npm run build` 无报错

  **Must NOT do**:
  - 不要引入 unplugin-auto-import / unplugin-vue-components（手动注册更稳定）
  - 不要修改现有组件（后续 task 再迁移）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2,3,4,5,6)
  - **Blocks**: Task 7,8,9,10,13,14
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `npm run build` 无报错
  - [ ] `main.js` 中 Element Plus 正确注册

  **QA Scenarios**:
  ```
  Scenario: Element Plus 安装成功
    Tool: Bash
    Steps:
      1. cd frontend && npm list element-plus
      2. 检查输出包含 element-plus
    Expected Result: element-plus 版本号显示
  ```

  **Commit**: YES
  - Message: `feat(frontend): install Element Plus`

- [ ] 2. 后端目录重组 (backend/app/{routers,services,utils,models})

  **What to do**:
  - 创建目录结构：
    ```
    backend/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py           # 从 api/main.py 迁移
    │   ├── config.py          # 集中配置（新文件）
    │   ├── database.py        # 数据库连接管理（新文件）
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── auth.py        # 从 api/routers/auth_router.py 迁移
    │   │   ├── chat.py        # 从 api/routers/stream_router.py 迁移
    │   │   ├── ranking.py     # 从 api/routers/ranking_router.py 迁移
    │   │   ├── graph.py       # 从 api/routers/graph_router.py 迁移
    │   │   └── admin.py       # 从 api/routers/admin_router.py 迁移
    │   ├── services/
    │   │   └── __init__.py
    │   └── utils/
    │       ├── __init__.py
    │       └── response.py    # 统一响应格式
    ├── agents/                # 保持现有位置不动
    ├── core/                  # 保持现有位置不动
    ├── skills/                # 保持现有位置不动
    ├── tools/                 # 保持现有位置不动
    └── uploads/
    ```
  - 将 `api/main.py` 的内容迁移到 `backend/app/main.py`
  - 将 `api/routers/*.py` 的内容迁移到 `backend/app/routers/`
  - 更新 `backend/app/main.py` 中的 import 路径
  - 更新 `backend/app/routers/*.py` 中的 import 路径
  - 保留 `api/` 目录作为兼容层（可选删除）
  - 验证：`python -m backend.app.main` 能启动

  **Must NOT do**:
  - 不要改动 agents/ core/ skills/ tools/ 的任何文件
  - 不要改动现有业务逻辑
  - 不要删除 `api/` 目录（保留兼容）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,3,4,5,6)
  - **Blocks**: Task 12
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `backend/app/` 目录结构正确
  - [ ] `backend/app/main.py` 内容正确
  - [ ] `backend/app/routers/*.py` 内容正确
  - [ ] `python -m backend.app.main` 能启动

  **QA Scenarios**:
  ```
  Scenario: 后端目录结构正确
    Tool: Bash
    Steps:
      1. Test-Path backend/app/main.py
      2. Test-Path backend/app/routers/auth.py
      3. Test-Path backend/app/utils/response.py
    Expected Result: 所有路径返回 True
  ```

  **Commit**: YES
  - Message: `refactor(backend): restructure to backend/app/{routers,services,utils}`

- [ ] 3. 创建 Axios 统一封装 (frontend/src/api/request.js)

  **What to do**:
  - 创建 `frontend/src/api/request.js`：
    ```js
    import axios from 'axios'
    import { ElMessage } from 'element-plus'
    
    const request = axios.create({
      baseURL: window.API_BASE || '',
      timeout: 30000,
    })
    
    // 请求拦截器：自动注入 Token
    request.interceptors.request.use(config => {
      const token = localStorage.getItem('auth_token')
      if (token) config.headers.Authorization = `Bearer ${token}`
      return config
    })
    
    // 响应拦截器：统一错误处理
    request.interceptors.response.use(
      res => res.data,
      err => {
        if (err.response?.status === 401) {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('user_info')
          window.location.hash = '#/login'
        }
        ElMessage.error(err.response?.data?.detail || '请求失败')
        return Promise.reject(err)
      }
    )
    
    export default request
    ```
  - 安装 axios：`npm install axios`
  - 验证：`npm run build` 无报错

  **Must NOT do**:
  - 不要修改现有 fetch 调用（后续 task 再迁移）
  - 不要删除 window.API_BASE

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,4,5,6)
  - **Blocks**: Task 6
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `frontend/src/api/request.js` 存在且内容正确
  - [ ] `npm list axios` 显示已安装
  - [ ] `npm run build` 无报错

  **QA Scenarios**:
  ```
  Scenario: Axios 封装正确
    Tool: Bash
    Steps:
      1. Test-Path frontend/src/api/request.js
      2. npm list axios
    Expected Result: 文件存在，axios 已安装
  ```

  **Commit**: YES (groups with Task 6)
  - Message: `feat(frontend): add Axios request wrapper`

- [ ] 4. 创建三端布局 (frontend/src/layouts/)

  **What to do**:
  - 创建 `frontend/src/layouts/StudentLayout.vue`：
    - 使用 Element Plus `el-container` + `el-aside` + `el-header` + `el-main`
    - 左侧侧边栏：el-menu 导航（对话/院校排名/知识图谱）
    - 顶部 header：品牌名 + 用户信息 + 设置按钮 + 退出按钮
    - 右侧 el-main：`<router-view />` 渲染子路由
    - 暗色模式切换按钮（使用 Element Plus el-switch）
    - 设置抽屉（el-drawer）
  - 创建 `frontend/src/layouts/ParentLayout.vue`：
    - 侧边栏：对话/问卷
    - 其余同 StudentLayout
  - 创建 `frontend/src/layouts/AdminLayout.vue`：
    - 侧边栏：系统监控/知识库管理/数据同步/数据统计
    - 使用 el-menu + el-menu-item
    - 顶部 header：品牌名 + 管理员信息 + 退出
  - 所有布局使用 Element Plus 组件，不使用 inline style
  - 使用 `<style scoped>` 编写组件样式

  **Must NOT do**:
  - 不要修改现有 App.vue（后续 task 再改）
  - 不要使用 inline style

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,3,5,6)
  - **Blocks**: Task 11
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] 三个 Layout 文件存在
  - [ ] 使用 Element Plus 组件（el-container, el-aside, el-menu 等）
  - [ ] 无 inline style
  - [ ] `<router-view />` 正确放置在 el-main 中

  **QA Scenarios**:
  ```
  Scenario: Layout 文件结构正确
    Tool: Bash
    Steps:
      1. Test-Path frontend/src/layouts/StudentLayout.vue
      2. Test-Path frontend/src/layouts/ParentLayout.vue
      3. Test-Path frontend/src/layouts/AdminLayout.vue
    Expected Result: 三个文件都存在
  ```

  **Commit**: YES
  - Message: `feat(frontend): add role-based layouts with Element Plus`

- [ ] 5. 创建统一响应格式 + 集中配置 (backend/app/utils/response.py, config.py)

  **What to do**:
  - 创建 `backend/app/utils/response.py`：
    ```python
    from fastapi.responses import JSONResponse
    
    def ok(data=None, message="success"):
        return JSONResponse({"code": 0, "data": data, "message": message})
    
    def fail(message="error", code=1):
        return JSONResponse({"code": code, "data": None, "message": message})
    ```
  - 创建 `backend/app/config.py`：
    ```python
    import os
    from pathlib import Path
    
    ROOT = Path(__file__).resolve().parents[2]
    DATA_DIR = ROOT / "data"
    UPLOAD_DIR = ROOT / "uploads"
    
    # 从环境变量读取配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    ```
  - 创建 `backend/app/database.py`：
    - 封装 SQLite 连接管理
    - 提供 `get_db()` 依赖注入函数
  - 验证：import 无报错

  **Must NOT do**:
  - 不要修改现有 routers 的响应格式（后续 task 再迁移）
  - 不要删除旧的 api/ 目录

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,3,4,6)
  - **Blocks**: Task 12
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `backend/app/utils/response.py` 存在
  - [ ] `backend/app/config.py` 存在
  - [ ] `backend/app/database.py` 存在
  - [ ] import 无报错

  **QA Scenarios**:
  ```
  Scenario: 统一响应格式正确
    Tool: Bash
    Steps:
      1. python -c "from backend.app.utils.response import ok, fail; print(ok({'test': 1}))"
    Expected Result: JSON 输出 {"code": 0, "data": {"test": 1}, "message": "success"}
  ```

  **Commit**: YES
  - Message: `feat(backend): add unified response format + config`

- [ ] 6. 创建 API 模块 (frontend/src/api/auth.js, chat.js, dashboard.js)

  **What to do**:
  - 创建 `frontend/src/api/auth.js`：
    ```js
    import request from './request'
    export const login = (data) => request.post('/auth/login', data)
    export const register = (data) => request.post('/auth/register', data)
    export const getMe = () => request.get('/auth/me')
    ```
  - 创建 `frontend/src/api/chat.js`：
    ```js
    import request from './request'
    export const sendAdvice = (query) => request.post('/stream/advice', { query })
    export const getStatus = () => request.get('/status')
    ```
  - 创建 `frontend/src/api/dashboard.js`：
    ```js
    import request from './request'
    export const getSummary = () => request.get('/api/dashboard/summary')
    export const getFunnel = () => request.get('/api/dashboard/funnel')
    ```
  - 验证：import 无报错

  **Must NOT do**:
  - 不要修改现有 fetch 调用（后续 task 再迁移）
  - 不要删除 window.API_BASE

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,3,4,5)
  - **Blocks**: Task 7,8,9,10
  - **Blocked By**: Task 3

  **Acceptance Criteria**:
  - [ ] 三个 API 文件存在
  - [ ] 使用 request 实例
  - [ ] import 无报错

  **QA Scenarios**:
  ```
  Scenario: API 模块结构正确
    Tool: Bash
    Steps:
      1. Test-Path frontend/src/api/auth.js
      2. Test-Path frontend/src/api/chat.js
      3. Test-Path frontend/src/api/dashboard.js
    Expected Result: 三个文件都存在
  ```

  **Commit**: YES
  - Message: `feat(frontend): add API modules (auth, chat, dashboard)`

- [ ] 7. 重写 LoginView (Element Plus 表单)

  **What to do**:
  - 重写 `frontend/src/views/LoginView.vue`：
    - 使用 `el-form` + `el-form-item` + `el-input` + `el-button`
    - 使用 `el-tabs` 切换登录/注册
    - 使用 `el-radio-group` 选择角色
    - 使用 `el-message` 显示错误信息
    - 使用 `api/auth.js` 的 `login` 函数替代直接 fetch
    - 去除所有 inline style，使用 scoped CSS + Element Plus 属性
  - 保留现有业务逻辑（角色选择、登录/注册切换）

  **Must NOT do**:
  - 不要修改登录/注册的后端 API
  - 不要改变角色类型（student/parent/admin）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8,9,10,11,12)
  - **Blocks**: Task 11
  - **Blocked By**: Task 1, Task 6

  **Acceptance Criteria**:
  - [ ] 使用 Element Plus 表单组件
  - [ ] 使用 api/auth.js 的 login 函数
  - [ ] 无 inline style
  - [ ] 登录功能正常

  **QA Scenarios**:
  ```
  Scenario: 登录页面渲染正确
    Tool: Playwright
    Steps:
      1. 导航到 http://127.0.0.1:8000/#/login
      2. 检查 el-form 组件存在
      3. 检查 el-tabs 组件存在
    Expected Result: Element Plus 组件正确渲染
  ```

  **Commit**: YES (groups with Tasks 8,9,10)
  - Message: `refactor(frontend): migrate LoginView to Element Plus`

- [ ] 8. 重写 StudentView + ChatContainer (Element Plus 对话)

  **What to do**:
  - 重写 `frontend/src/views/StudentView.vue`：
    - 使用 StudentLayout 包裹
    - 使用 `api/chat.js` 的 `sendAdvice` 替代直接 fetch
    - 保留 SSE 流式响应逻辑
  - 重写 `frontend/src/components/ChatContainer.vue`：
    - 使用 `el-input` + `el-button` 替代手写输入框
    - 使用 `el-scrollbar` 替代手写滚动条
    - 使用 `el-upload` 替代手写上传按钮
    - 使用 `el-tag` 显示 QuickChips
    - 去除所有 inline style
  - 保留 SSE 流式响应、语音输入、文件上传功能

  **Must NOT do**:
  - 不要修改 SSE 流式响应的后端 API
  - 不要删除 QuickChips、VoiceInput 组件

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7,9,10,11,12)
  - **Blocks**: Task 13
  - **Blocked By**: Task 1, Task 4, Task 6

  **Acceptance Criteria**:
  - [ ] 使用 Element Plus 组件
  - [ ] 使用 api/chat.js 的函数
  - [ ] SSE 流式响应正常
  - [ ] 无 inline style

  **QA Scenarios**:
  ```
  Scenario: 学生对话页面正常
    Tool: Playwright
    Steps:
      1. 以学生身份登录
      2. 导航到 /#/student/chat
      3. 发送消息
      4. 检查 SSE 响应
    Expected Element: Element Plus 组件渲染，消息正常显示
  ```

  **Commit**: YES
  - Message: `refactor(frontend): migrate StudentView to Element Plus`

- [ ] 9. 重写 ParentView (Element Plus 对话)

  **What to do**:
  - 重写 `frontend/src/views/ParentView.vue`：
    - 使用 ParentLayout 包裹
    - 使用 `el-input` + `el-button` 替代手写输入框
    - 使用 `el-scrollbar` 替代手写滚动条
    - 使用 `api/chat.js` 的 `sendAdvice` 替代直接 fetch
    - 去除所有 inline style
  - 保留 SSE 流式响应逻辑

  **Must NOT do**:
  - 不要修改 SSE 流式响应的后端 API

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7,8,10,11,12)
  - **Blocks**: Task 13
  - **Blocked By**: Task 1, Task 4, Task 6

  **Acceptance Criteria**:
  - [ ] 使用 Element Plus 组件
  - [ ] 使用 api/chat.js 的函数
  - [ ] SSE 流式响应正常
  - [ ] 无 inline style

  **QA Scenarios**:
  ```
  Scenario: 家长对话页面正常
    Tool: Playwright
    Steps:
      1. 以家长身份登录
      2. 导航到 /#/parent/chat
      3. 发送消息
    Expected Result: Element Plus 组件渲染，消息正常显示
  ```

  **Commit**: YES
  - Message: `refactor(frontend): migrate ParentView to Element Plus`

- [ ] 10. 重写 AdminView (Element Plus 面板)

  **What to do**:
  - 重写 `frontend/src/views/AdminView.vue`：
    - 使用 AdminLayout 包裹
    - 使用 `el-table` 显示系统状态
    - 使用 `el-card` 显示统计卡片
    - 使用 `el-button` 替代手写按钮
    - 使用 `api/dashboard.js` 的函数替代直接 fetch
    - 去除所有 inline style
  - 保留现有业务逻辑（系统监控、知识库管理、数据同步、数据统计）

  **Must NOT do**:
  - 不要修改后端 API

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7,8,9,11,12)
  - **Blocks**: Task 13
  - **Blocked By**: Task 1, Task 4, Task 6

  **Acceptance Criteria**:
  - [ ] 使用 Element Plus 组件
  - [ ] 使用 api/dashboard.js 的函数
  - [ ] 无 inline style
  - [ ] 管理面板功能正常

  **QA Scenarios**:
  ```
  Scenario: 管理员面板正常
    Tool: Playwright
    Steps:
      1. 以管理员身份登录
      2. 导航到 /#/admin
      3. 检查 el-card 组件存在
    Expected Result: Element Plus 组件渲染，系统状态正常显示
  ```

  **Commit**: YES
  - Message: `refactor(frontend): migrate AdminView to Element Plus`

- [ ] 11. 重写 Router (嵌套路由 + 布局级守卫)

  **What to do**:
  - 重写 `frontend/src/router/index.js`：
    - 使用嵌套路由：每个 Layout 内嵌套子路由
    - 示例：
      ```js
      {
        path: '/student',
        component: () => import('../layouts/StudentLayout.vue'),
        meta: { requiresAuth: true, role: 'student' },
        children: [
          { path: '', redirect: '/student/chat' },
          { path: 'chat', name: 'StudentChat', component: () => import('../views/student/ChatView.vue') },
          { path: 'ranking', name: 'StudentRanking', component: () => import('../views/student/RankingView.vue') },
          { path: 'graph', name: 'StudentGraph', component: () => import('../views/student/GraphView.vue') },
        ]
      }
      ```
    - 家长端、管理员端同理
    - 更新 `beforeEach` 守卫：检查角色权限
    - 更新 `App.vue`：简化为 `<router-view />`，Layout 内部处理导航
  - 验证：所有路由正常工作

  **Must NOT do**:
  - 不要删除任何现有路由
  - 不要改变路由路径（保持 `/#/student/chat` 等）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7,8,9,10,12)
  - **Blocks**: Task 13,14
  - **Blocked By**: Task 4

  **Acceptance Criteria**:
  - [ ] 嵌套路由正确工作
  - [ ] Layout 内 `<router-view />` 正确渲染子路由
  - [ ] 角色守卫正确（student 不能访问 /admin）
  - [ ] 所有现有路由路径不变

  **QA Scenarios**:
  ```
  Scenario: 嵌套路由正确
    Tool: Playwright
    Steps:
      1. 以学生身份登录
      2. 导航到 /#/student/chat
      3. 检查 StudentLayout 渲染
      4. 检查 ChatView 在 el-main 中渲染
    Expected Result: Layout + 子路由正确嵌套
  ```

  **Commit**: YES
  - Message: `refactor(frontend): rewrite router with nested routes + role guards`

- [ ] 12. 后端服务层抽取 (auth_service, chat_service)

  **What to do**:
  - 创建 `backend/app/services/auth_service.py`：
    - 从 `backend/app/routers/auth.py` 抽取业务逻辑
    - 提供 `login_user()`, `register_user()`, `get_current_user()` 函数
  - 创建 `backend/app/services/chat_service.py`：
    - 从 `backend/app/routers/chat.py` 抽取业务逻辑
    - 提供 `process_advice()` 函数
  - 更新 `backend/app/routers/auth.py`：调用 service 层
  - 更新 `backend/app/routers/chat.py`：调用 service 层
  - 验证：API 端点响应正常

  **Must NOT do**:
  - 不要修改 agents/ core/ skills/ tools/ 的任何文件
  - 不要改变 API 端点路径

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7,8,9,10,11)
  - **Blocks**: Task 15
  - **Blocked By**: Task 2, Task 5

  **Acceptance Criteria**:
  - [ ] `backend/app/services/auth_service.py` 存在
  - [ ] `backend/app/services/chat_service.py` 存在
  - [ ] API 端点响应正常
  - [ ] 业务逻辑从 routers 中抽离

  **QA Scenarios**:
  ```
  Scenario: 服务层抽取正确
    Tool: Bash
    Steps:
      1. python -c "from backend.app.services.auth_service import login_user"
      2. python -c "from backend.app.services.chat_service import process_advice"
    Expected Result: import 无报错
  ```

  **Commit**: YES
  - Message: `refactor(backend): extract service layer (auth, chat)`

- [ ] 13. 重写 RankingView + GraphView + QuestionnaireView (Element Plus)

  **What to do**:
  - 重写 `frontend/src/views/RankingView.vue`：
    - 使用 `el-select` + `el-input` + `el-button` 替代手写表单
    - 使用 `el-table` + `el-table-column` 替代手写表格
    - 使用 `el-slider` 替代手写滑动器
    - 使用 `el-pagination` 替代手写分页
    - 使用 `api/ranking.js`（新建）替代直接 fetch
  - 重写 `frontend/src/views/GraphView.vue`：
    - 保留 Canvas 渲染逻辑
    - 使用 `el-select` + `el-input` + `el-button` 替代手写表单
    - 使用 `el-card` 显示节点详情
  - 重写 `frontend/src/views/QuestionnaireView.vue`：
    - 使用 `el-form` + `el-form-item` + `el-input` + `el-select`
    - 使用 `el-checkbox-group` 替代手写多选
    - 使用 `el-button` 替代手写按钮
  - 创建 `frontend/src/api/ranking.js`：
    ```js
    import request from './request'
    export const getRanking = (source, params) => request.get(`/api/ranking/${source}`, { params })
    ```
  - 去除所有 inline style

  **Must NOT do**:
  - 不要修改后端 API
  - 不要删除 Canvas 渲染逻辑

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 14,15,16)
  - **Blocks**: Task 15
  - **Blocked By**: Task 1, Task 6, Task 11

  **Acceptance Criteria**:
  - [ ] 三个 View 文件使用 Element Plus 组件
  - [ ] 使用 api/ranking.js 的函数
  - [ ] 无 inline style
  - [ ] 排名滑动器/分页正常工作

  **QA Scenarios**:
  ```
  Scenario: 排名页面正常
    Tool: Playwright
    Steps:
      1. 以学生身份登录
      2. 导航到 /#/student/ranking
      3. 检查 el-table 组件存在
      4. 检查 el-slider 组件存在
    Expected Result: Element Plus 组件渲染，排名数据正常显示
  ```

  **Commit**: YES
  - Message: `refactor(frontend): migrate RankingView/GraphView/QuestionnaireView to Element Plus`

- [ ] 14. 重写 SettingsDrawer + VoiceInput + SidePanel (Element Plus)

  **What to do**:
  - 重写 `frontend/src/components/SettingsDrawer.vue`：
    - 使用 `el-drawer` 替代手写抽屉
    - 使用 `el-switch` 替代手写开关
    - 使用 `el-color-picker` 替代手写颜色选择
  - 重写 `frontend/src/components/VoiceInput.vue`：
    - 使用 `el-button` + `el-icon` 替代手写按钮
    - 使用 `el-message` 显示错误信息
  - 重写 `frontend/src/components/SidePanel.vue`：
    - 使用 `el-card` 替代手写卡片
    - 使用 `el-descriptions` 显示用户画像
  - 去除所有 inline style

  **Must NOT do**:
  - 不要修改语音录制逻辑
  - 不要删除暗色模式功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13,15,16)
  - **Blocks**: Task 15
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [ ] 三个组件使用 Element Plus 组件
  - [ ] 无 inline style
  - [ ] 设置抽屉正常打开/关闭

  **QA Scenarios**:
  ```
  Scenario: 设置抽屉正常
    Tool: Playwright
    Steps:
      1. 点击设置按钮
      2. 检查 el-drawer 组件打开
      3. 检查 el-switch 组件存在
    Expected Result: Element Plus 组件渲染
  ```

  **Commit**: YES
  - Message: `refactor(frontend): migrate SettingsDrawer/VoiceInput/SidePanel to Element Plus`

- [ ] 15. 清理旧 CSS + 构建验证

  **What to do**:
  - 删除 `frontend/src/assets/global.css`（已被 Element Plus 替代）
  - 删除 `frontend/src/assets/chat.css`（已被 Element Plus 替代）
  - 更新 `frontend/src/main.js`：移除旧 CSS import
  - 更新 `frontend/index.html`：移除旧 CSS link
  - 执行 `npm run build` 验证无报错
  - 执行 `python -m api.main` 验证后端启动正常

  **Must NOT do**:
  - 不要删除 `frontend/src/assets/` 目录（可能有其他文件）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Tasks 13,14)
  - **Blocks**: Task F1,F2,F3
  - **Blocked By**: Task 13,14

  **Acceptance Criteria**:
  - [ ] 旧 CSS 文件已删除
  - [ ] `npm run build` 无报错
  - [ ] `python -m api.main` 无报错

  **QA Scenarios**:
  ```
  Scenario: 构建成功
    Tool: Bash
    Steps:
      1. cd frontend && npm run build
      2. python -m api.main
    Expected Result: 两个命令都无报错
  ```

  **Commit**: YES
  - Message: `chore(frontend): remove old CSS files + verify build`

- [ ] 16. 文档更新

  **What to do**:
  - 更新 `README.md`：技术栈加入 Element Plus
  - 更新 `docs/DEVELOPMENT.md`：项目结构更新
  - 更新 `docs/部署指南.md`：前端构建步骤更新
  - 更新 `docs/OPERATIONS.md`：架构图更新

  **Must NOT do**:
  - 不要删除现有文档内容

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13,14,15)
  - **Blocks**: None
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] README.md 包含 Element Plus
  - [ ] docs/DEVELOPMENT.md 项目结构正确
  - [ ] docs/部署指南.md 前端构建步骤正确

  **QA Scenarios**:
  ```
  Scenario: 文档正确
    Tool: Bash
    Steps:
      1. Select-String -Path README.md -Pattern "Element Plus"
    Expected Result: 匹配到 Element Plus
  ```

  **Commit**: YES
  - Message: `docs: update for Element Plus architecture`

---

## Final Verification Wave

> 3 review agents run in PARALLEL. ALL must APPROVE.

- [ ] F1. **全路由功能验证** — `unspecified-high`
  从登录页开始，逐一访问所有 7 条路由，验证页面正常渲染、API 调用正常、无 JS 错误。
  Output: `Routes [7/7 pass] | VERDICT: APPROVE/REJECT`

- [ ] F2. **构建 + Lint 验证** — `unspecified-high`
  执行 `npm run build` + `python -m api.main`，确认无报错。检查所有 `.vue` 文件无 unused imports、无 inline style 残留。
  Output: `Build [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **旧文件清理确认** — `unspecified-high`
  确认旧的 CSS 文件（global.css/chat.css）已被新的 Element Plus 样式替代。确认旧的直接 fetch 调用已被 Axios 替代。
  Output: `Old CSS [CLEAN/N remaining] | Fetch calls [CLEAN/N remaining] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(frontend): install Element Plus + create layouts + Axios layer`
- **Wave 2**: `refactor(views): migrate all views to Element Plus`
- **Wave 3**: `refactor(backend): extract service layer + unify response format`

---

## Success Criteria

### Verification Commands
```bash
cd frontend && npm run build    # Expected: build success, 0 errors
python -m api.main              # Expected: Application startup complete
curl http://127.0.0.1:8000/healthz  # Expected: {"ok": true}
```

### Final Checklist
- [ ] Element Plus 正确安装并全局注册
- [ ] 三端布局正确渲染（学生/家长/管理员）
- [ ] Axios 封装正确（Token 注入、错误拦截）
- [ ] 嵌套路由正确工作（Layout 内嵌套子路由）
- [ ] 所有 API 端点响应正常
- [ ] 旧 CSS 已清理
- [ ] 业务逻辑无变化（agents/core/skills/tools 未改动）
