# Vite + Vue 3 + FastAPI 前端重构方案

## TL;DR

> **核心目标**：将当前手动管理的 Vue CDN + 多 HTML 页面架构迁移到 Vite + Vue 3 SFC + Vue Router 标准工程化架构，消除 CDN 被墙风险、CSS 冗余和组件管理混乱。
>
> **方案概括**：在 `frontend/` 中初始化 Vite 项目，将 27 个 `.js` 组件转换为 `.vue` SFC，用 Vue Router 替代多页面跳转，合并 12 个 CSS 文件，FastAPI 仅 serve `dist/` 静态目录。
>
> **关键指标**：CSS 文件从 12 → 3，HTML 文件从 5 → 1，构建步骤从无到有（但开发效率提升 5x+ 通过 HMR），组件加载从串行 import 变为 tree-shaken 打包。

---

## 上下文

### 当前架构

```
frontend/
├── index.html              # V6 单页入口（登录后切视图）
├── pages/                  # V7 多页面结构
│   ├── login.html          # 登录页
│   ├── student.html        # 学生端
│   ├── parent.html         # 家长端
│   └── admin.html          # 管理端
├── components/             # 27 个 .js Vue 组件（Options API + 字符串模板）
├── utils/                  # apiClient.js 等工具
├── assets/                 # 12 个 CSS 文件（大量重复变量）
└── lib/                    # 手动下载的 CDN 库（临时方案）
```

### 冗余分析

| 类别 | 当前 | 问题 |
|------|------|------|
| CSS 文件 | 12 个 | `base.css` + `design-system.css` + `themes.css` 都有 `--primary` 等变量定义；`chat.css` + `voice.css` + `widgets.css` 部分重复 |
| HTML 页面 | 5 个 | 每个页面 `<head>` 区大量重复的 CDN/样式/脚本引用 |
| 组件注册 | 2 处 | `index.html` 和 `student.html` 各有一份 `app.component()` 注册列表 |
| 静态挂载 | 7 个 | FastAPI 中 4 个 `StaticFiles` + 7 个 `_serve_html` 路由 |
| 旧代码 | 1 个 | `api/flask_ui.py` (844 行) 已不再使用 |

---

## 工作目标

### 核心目标
在**不动后端 Agent 逻辑和 API 路由**的前提下，将前端迁移到 Vite + Vue 3 + Vue Router 标准工程化架构。

### 具体交付物
1. `frontend/package.json` — 项目依赖（Vue 3, Vue Router, Vite）
2. `frontend/vite.config.js` — Vite 配置
3. `frontend/src/main.js` — Vue 应用入口（Vue Router + Pinia 可选）
4. `frontend/src/App.vue` — 根组件（带 Vue Router `<router-view>`）
5. `frontend/src/router/index.js` — 路由定义（/login, /student, /parent, /admin）
6. `frontend/src/views/*.vue` — 4 个页面组件（替换 pages/*.html）
7. `frontend/src/components/*.vue` — 27 个 .vue SFC（替换 components/*.js）
8. `frontend/src/assets/*.css` — 合并为 3 个 CSS 文件
9. `frontend/src/utils/apiClient.js` — 保持原样
10. `frontend/dist/` — 构建产物
11. `api/main.py` 更新 — 移除 4 个 StaticFiles + 7 个 _serve_html，改为单行 mount `dist/`

### 不作变更
- `api/` 下所有后端逻辑和路由
- `core/` 下所有核心业务逻辑
- `agents/` 下所有 Agent 定义
- `tools/` 下所有工具函数
- `scripts/` 下所有数据脚本
- `configs/` 下所有配置

---

## 验证策略

### 测试方法
- `npm run dev` 启动 Vite 开发服务器 → HMR 实时预览
- `npm run build` → FastAPI serve `dist/` → 验证生产模式
- 浏览器打开 `http://localhost:5173` 测试开发模式
- 浏览器打开 `http://localhost:8000` 测试生产模式
- 验证登录、对话、排名、知识图谱功能完整性

### 验收标准
- [ ] `npm run dev` 启动无报错
- [ ] `npm run build` 构建成功且产物 <2MB
- [ ] 4 个页面路由均可正常访问
- [ ] 登录 → 学生/家长/管理员页面跳转正常
- [ ] 对话功能正常运行
- [ ] FastAPI 启动日志无 `StaticFiles` 或路由警告
- [ ] `api/flask_ui.py` 可安全删除

---

## 执行策略

### Wave 1 — 项目初始化 + 脚手架（4 个并行任务）

```
Wave 1 (Start Immediately):
├── 1. package.json + vite.config.js + index.html 脚手架
├── 2. Vue Router 配置（4 条路由）
├── 3. App.vue 根组件（layout + router-view）
└── 4. 全局 CSS 合并（12 → 3）
```

### Wave 2 — 页面组件（4 个并行任务）

```
Wave 2 (After Wave 1):
├── 5. LoginView.vue（替换 login-page 逻辑）
├── 6. StudentView.vue（替换 student.html 逻辑）
├── 7. ParentView.vue（替换 parent.html 逻辑）
└── 8. AdminView.vue（替换 admin.html 逻辑）
```

### Wave 3 — 核心组件迁移（6 个并行任务）

```
Wave 3 (After Wave 2, MAX PARALLEL):
├── 9. ChatContainer.vue（模板从 ChatContainer.js）
├── 10. SidePanel.vue + ProfileCard.vue
├── 11. MessageBubble.vue + MarkdownRenderer.vue
├── 12. SettingsDrawer.vue
├── 13. UniversityRanking.vue + KnowledgeGraph.vue
└── 14. IntentIndicator + QuickChips + ProgressiveQuestions + FallbackCard + RecommendationReason
```

### Wave 4 — 辅助组件迁移（3 个并行任务）

```
Wave 4 (After Wave 3):
├── 15. VoiceInput.vue + VoiceOutput.vue + ImageAnalyzer.vue
├── 16. MiniQuestionnaire.vue + FileUploader.vue + LoginPage.vue
└── 17. StatusIndicator.vue + AppLayout.vue + core/*.vue
```

### Wave FINAL — 集成 + 清理

```
Wave FINAL (After all tasks):
├── F1. FastAPI 更新（dist/ mount + 清理旧挂载）
├── F2. 清理旧文件（pages/, *.js components, 12 CSS → 备份）
├── F3. 构建测试（npm run build + 启动验证）
└── F4. 删除 flask_ui.py（确认无引用后）
```

---

## TODOs

- [ ] 1. 初始化 Vite 项目 + package.json

  **做什么**：
  - 在 `frontend/` 创建 `package.json`
  - 安装依赖：`vue@3`, `vue-router@4`, `vite`, `@vitejs/plugin-vue`
  - 创建 `vite.config.js`，配置 build output 到 `dist/`
  - 创建 `index.html`（Vite 入口，含 `<script type="module" src="/src/main.js">`）
  - 创建 `src/main.js`（Vue app 初始化 + router 注册）
  - 删除旧的 `frontend/lib/` 目录（不再需要手动 CDN 下载）

  **必须不做**：
  - 不要修改 FastAPI 后端
  - 不要删除旧组件文件（迁移完成后再清理）

  **接受标准**：
  - `npm install` 成功
  - `npm run dev` 启动 Vite 开发服务器不报错
  - `npm run build` 生成 `dist/` 目录

  **参考模式**：
  - 官方 Vite + Vue 3 模板：创建标准 `vite.config.js` + `src/main.js` + `src/App.vue`
  - 路由参考：Vue Router 4 hash 模式（避免和 FastAPI 路由冲突）

  **QA 场景**：
  ```
  Scenario: Vite 开发服务器启动
    Tool: interactive_bash (tmux)
    Steps:
      1. cd frontend && npm run dev
      2. 等待 terminal 显示 "Local: http://localhost:5173"
    Expected: 开发服务器启动成功，无警告
    Evidence: .omo/evidence/task-1-vite-dev.txt

  Scenario: Vite 构建成功
    Tool: interactive_bash (tmux)
    Steps:
      1. cd frontend && npm run build
      2. 检查 dist/ 目录存在且有 index.html + assets/
    Expected: 构建成功，dist/index.html 包含打包后的 script link
    Evidence: .omo/evidence/task-1-vite-build.txt
  ```

- [ ] 2. 配置 Vue Router（4 条路由 + 导航守卫）

  **做什么**：
  - 创建 `src/router/index.js`
  - 路由表：`/login` → LoginView, `/student` → StudentView, `/parent` → ParentView, `/admin` → AdminView
  - 添加导航守卫：未登录访问 /student、/parent、/admin 时重定向到 `/login`
  - 已登录访问 `/login` 时重定向到 `/student`
  - 根路径 `/` 重定向到 `/student`

  **参考模式**：
  - 使用 `createRouter` + `createWebHashHistory`（避免与 FastAPI 路由冲突）

  **QA 场景**：
  ```
  Scenario: 路由配置正确
    Tool: Bash (node)
    Steps:
      1. node -e "import('./src/router/index.js').then(m => console.log(Object.keys(m)))"
    Expected: 导出 createRouter 函数
    Evidence: .omo/evidence/task-2-router.txt
  ```

- [ ] 3. 创建 App.vue 根组件

  **做什么**：
  - 创建 `src/App.vue`，包含 header 导航 + `<router-view>`
  - Header 导航按钮根据当前路由高亮
  - 用户信息显示 + 退出按钮
  - 整合原 `index.html` 和 `pages/*.html` 中的 header 逻辑

  **必须不做**：
  - 不包含业务逻辑（只在 mounted 中检查 token）

  **参考**：
  - 原 `student.html` line 27-69 的 header 结构
  - 原 `index.html` line 65-78 的全局组件注册

- [ ] 4. 合并全局 CSS（12 文件 → 3 文件）

  **做什么**：
  - 创建 `src/assets/global.css`（合并 base.css + design-system.css + themes.css）
  - 创建 `src/assets/chat.css`（合并 chat.css + voice.css + widgets.css）  
  - 创建 `src/assets/admin.css`（单独保留，仅管理端使用）
  - 删除 `frontend/assets/` 中旧的 12 个 CSS 文件（备份到 `.omo/backup/assets/`）
  - 删除 `frontend/lib/` 目录

  **必须不做**：
  - 不改变 CSS 变量名或主题逻辑

  **QA 场景**：
  ```
  Scenario: CSS 合并后主题变量完整
    Tool: Bash (grep)
    Steps: grep -c "var(--primary)" src/assets/global.css
    Expected: 变量定义完整，无遗漏
    Evidence: .omo/evidence/task-4-css-vars.txt
  ```

- [ ] 5. 创建 LoginView.vue 页面组件
  
  **做什么**：
  - 创建 `src/views/LoginView.vue`，嵌入原 LoginPage 组件模板
  - 登录成功后 `router.push('/student')`
  
  **参考**：原 `pages/login.html` 和 `components/LoginPage.js`

- [ ] 6. 创建 StudentView.vue 页面组件

  **做什么**：
  - ChatContainer + SidePanel + SettingsDrawer
  - UniversityRanking 和 KnowledgeGraph 作为子视图（v-if 切换）
  
  **参考**：原 `pages/student.html` 的 template 结构

- [ ] 7. 创建 ParentView.vue 页面组件

  **做什么**：
  - ChatContainer + SidePanel + MiniQuestionnaire
  
  **参考**：原 `pages/parent.html` 的 template 结构

- [ ] 8. 创建 AdminView.vue 页面组件

  **做什么**：
  - AdminLayout 组件
  
  **参考**：原 `pages/admin.html` 的 template 结构

- [ ] 9. 迁移核心小组件（MessageBubble, StatusIndicator, ProfileCard, QuickChips）

  **做什么**：
  - 将 `components/MessageBubble.js` → `src/components/MessageBubble.vue`
  - 将 `components/StatusIndicator.js` → `src/components/StatusIndicator.vue`
  - 将 `components/ProfileCard.js` → `src/components/ProfileCard.vue`
  - 将 `components/QuickChips.js` → `src/components/QuickChips.vue`
  - 模板从 `template: \`...\`` 改为 `<template>` 标签
  - 纯模板迁移，不改逻辑

- [ ] 10. 迁移聚合组件（ChatContainer, SidePanel, SettingsDrawer）

  **做什么**：
  - 将 `components/ChatContainer.js` → `src/components/ChatContainer.vue`
  - 将 `components/SidePanel.js` → `src/components/SidePanel.vue`
  - 将 `components/SettingsDrawer.js` → `src/components/SettingsDrawer.vue`
  - 更新导入路径：子组件引用从 `./X.js` 改为 `./X.vue`

- [ ] 11. 迁移 V7 新增组件（IntentIndicator, QuickChips, ProgressiveQuestions 等）

  **做什么**：
  - 迁移：IntentIndicator, ProgressiveQuestions, FallbackCard, RecommendationReason
  - 迁移：FileUploader, VoiceInput, VoiceOutput, ImageAnalyzer
  - 迁移：MiniQuestionnaire, LoginPage, AppLayout, AdminLayout, UniversityRanking, KnowledgeGraph

- [ ] 12. 迁移 core/ 子目录组件

  **做什么**：
  - 迁移 `components/core/MarkdownRenderer.js` → `src/components/core/MarkdownRenderer.vue`
  - 迁移 `components/core/*.js` 中其他组件

---

## Final Verification Wave

- [ ] F1. **FastAPI 配置验证** — 确认 `StaticFiles` mount 正确，API 路由不受影响
- [ ] F2. **构建验证** — `npm run build` 产物完整，无警告
- [ ] F3. **全功能冒烟测试** — 打开 4 个页面，验证登录和对话功能
- [ ] F4. **清理验证** — 旧文件备份完成，flask_ui.py 确认可删除

---

## 提交策略

- 1: `chore(frontend): init Vite + Vue 3 + Router`
- 2-4: `feat(frontend): add router, App.vue, scoped CSS`
- 5-8: `feat(frontend): add page views (Login/Student/Parent/Admin)`
- 9-17: `refactor(frontend): migrate 27 components to .vue SFC`
- F1: `refactor(api): serve frontend from dist/, remove old mounts`
- F2: `chore: cleanup old files (pages, js components, flask_ui)`
- F3: `chore: build and verify`

---

## 成功标准

- [ ] `npm run dev` → HMR 热更新正常工作
- [ ] `npm run build` → `dist/` 产物 < 1.5MB (gzip)
- [ ] 4 个页面路由均可访问
- [ ] 登录/登出流程完整
- [ ] 对话、排名、知识图谱功能正常
- [ ] FastAPI 无 `StaticFiles` 相关警告
- [ ] 无 CDN 外部依赖（Font Awesome 保留 bootcdn）
