# 小乐AI · 后台 CRUD 模块集成 Plan

## TL;DR

> **目标**: 为管理员后台集成完整的 CRUD 管理能力，同时为用户端补充通知接收、FAQ 浏览、反馈提交等缺失功能。
>
> **新增模块 (10 个)**:
> 1. 用户管理 — 列表/搜索/详情/禁用/启用
> 2. 公告管理 — 新增/编辑/发布/下架/删除 + 发送范围
> 3. FAQ 管理 — 新增/编辑/分类/置顶/删除
> 4. 知识库管理 — 在线编辑文档 + 分类 + RAG 重建
> 5. 用户反馈管理 — 查看/标记处理/批量操作
> 6. 报考指南管理 — 分类 + 富文本编辑
> 7. 快捷提问词管理 — 分组管理
> 8. 系统配置 UI — 模块开关 + 模型选择
> 9. 院校管理 — 搜索/编辑
> 10. 专业管理 — 搜索/编辑
>
> **用户端补充 (4 项)**:
> 1. 通知铃铛组件 — header 显示未读数
> 2. 通知列表页 — 已读/未读标记 + 清空
> 3. FAQ 浏览页 — 分类展示常见问题
> 4. 反馈提交 — 对话中提交评价
>
> **预计工作量**: Large
> **并行执行**: YES — 4 waves
> **关键路径**: Task 1 → Task 4 → Task 11 → Task 21 → Task 25

---

## Context

### 问题

系统管理员没有运营后台——用户管理靠 SQL 命令、知识库靠脚本导入、公告靠口口相传。学生/家长端缺少通知接收、FAQ 浏览、反馈提交等标准 C 端功能。

### 约束

- 保持 SQLite，不引入 MySQL/PostgreSQL
- 保持现有 AI 逻辑不变（agents/core/skills/tools 零改动）
- 所有新页面使用 Element Plus 组件库
- 统一响应格式 `{code: 0, data: ..., message: "success"}`

---

## Work Objectives

### Must Have
- 用户管理（admin CRUD + 搜索 + 禁用/启用）
- 公告管理 + 通知系统（admin 发 + user 收）
- FAQ 管理 + 用户端浏览
- 知识库在线编辑（替代脚本导入）
- 用户反馈管理（admin 查看 + 处理）
- 快捷提问词管理
- 系统配置 UI
- 院校/专业信息在线编辑

### Must NOT Have
- 不改动 agents/ core/ skills/ tools/
- 不引入 Redis / MySQL / Docker
- 不做复杂 RBAC（保持 admin / student / parent 三角色）
- 不做数据导出 Excel（P2，后续迭代）
- 不做轮播图 / 敏感词过滤 / 画像编辑（P2）
- 不做对话日志查看（只读功能，后续迭代）

---

## Verification Strategy

### QA Policy
- **Admin 页面**: Playwright 导航 → 表格渲染 → 表单提交 → 验证数据
- **User 页面**: Playwright 导航 → 通知铃铛 → FAQ 列表 → 反馈提交
- **Backend**: curl 测试 API 端点

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — DB + Backend foundation):
├── Task 1: 创建新数据库表 (announcements/faqs/guides/keywords/feedback/notifications) [quick]
├── Task 2: 创建 admin CRUD 服务层 (10 个模块) [unspecified-high]
├── Task 3: 创建 admin API 路由 (全部 CRUD 端点) [unspecified-high]
├── Task 4: 创建通知 + 反馈服务层 [unspecified-high]
├── Task 5: 创建通知 + 反馈 API 端点 [unspecified-high]
└── Task 6: 更新 adminLayout 路由 (新增 9 个菜单项) [quick]

Wave 2 (After Wave 1 — Admin 10 个管理页面):
├── Task 7: Admin - 用户管理页 [visual-engineering]
├── Task 8: Admin - 公告管理页 [visual-engineering]
├── Task 9: Admin - FAQ 管理页 [visual-engineering]
├── Task 10: Admin - 知识库管理页 [visual-engineering]
├── Task 11: Admin - 用户反馈管理页 [visual-engineering]
├── Task 12: Admin - 报考指南管理页 [visual-engineering]
├── Task 13: Admin - 快捷提问词管理页 [visual-engineering]
├── Task 14: Admin - 系统配置页 [visual-engineering]
├── Task 15: Admin - 院校管理页 [visual-engineering]
└── Task 16: Admin - 专业管理页 [visual-engineering]

Wave 3 (After Wave 2 — User-side 4 项):
├── Task 17: 通知铃铛组件 (header 集成) [visual-engineering]
├── Task 18: 通知列表页 [visual-engineering]
├── Task 19: FAQ 浏览页 [visual-engineering]
├── Task 20: 反馈提交组件 [visual-engineering]
├── Task 21: 路由 + 布局更新 (集成新页面) [unspecified-high]
└── Task 22: 通知铃铛集成到 StudentLayout + ParentLayout [visual-engineering]

Wave 4 (After Wave 3 — Polish + Verify):
├── Task 23: 构建验证 + 功能测试 [unspecified-high]
├── Task 24: 文档更新 [writing]
└── Task 25: 最终验收 [unspecified-high]

Critical Path: Task 1 → Task 4 → Task 11 → Task 21 → Task 23 → Task 25
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 10 (Wave 2)
```

---

## TODOs

- [ ] 1. 创建新数据库表

  **What to do**:
  - 在 `data/zx_advisor.db` 中创建以下表（使用 `CREATE TABLE IF NOT EXISTS`）：

  ```sql
  -- 公告表
  CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    target_role TEXT DEFAULT 'all',  -- all/student/parent
    is_pinned INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',     -- draft/published/archived
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- FAQ 表
  CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT DEFAULT '通用',
    sort_order INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 报考指南表
  CREATE TABLE IF NOT EXISTS guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT '志愿填报',
    status TEXT DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 快捷提问词表
  CREATE TABLE IF NOT EXISTS quick_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    group_name TEXT DEFAULT '默认',
    sort_order INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 用户反馈表
  CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    conversation_id TEXT,
    rating INTEGER DEFAULT 0,       -- 1-5 或 👍/👎
    comment TEXT,
    status TEXT DEFAULT 'pending',  -- pending/processed/dismissed
    admin_reply TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 通知表
  CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    type TEXT DEFAULT 'system',     -- system/announcement/feedback
    is_read INTEGER DEFAULT 0,
    related_id INTEGER,             -- 关联公告/反馈 ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  ```

  - 创建 Python 脚本 `scripts/create_admin_tables.py` 执行上述 SQL
  - 验证：`python scripts/create_admin_tables.py` 无报错

  **Must NOT do**:
  - 不修改现有表结构
  - 不删除任何现有数据

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2,3,4,5,6)
  - **Blocks**: Tasks 2,3,4,5
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] 6 个新表创建成功
  - [ ] `python scripts/create_admin_tables.py` 无报错

  **QA Scenarios**:
  ```
  Scenario: 表创建成功
    Tool: Bash
    Steps:
      1. python scripts/create_admin_tables.py
      2. python -c "import sqlite3; conn=sqlite3.connect('data/zx_advisor.db'); print([r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()])"
    Expected Result: 输出包含 announcements, faqs, guides, quick_keywords, feedback, notifications
  ```

  **Commit**: YES
  - Message: `feat(db): add admin CRUD tables`

- [ ] 2. 创建 admin CRUD 服务层

  **What to do**:
  - 创建 `backend/app/services/admin_service.py`，包含以下函数：

  ```python
  # 用户管理
  def list_users(page=1, size=20, keyword=None) -> dict
  def get_user_detail(user_id: int) -> dict
  def toggle_user_status(user_id: int, enabled: bool) -> dict

  # 公告管理
  def list_announcements(page=1, size=20) -> dict
  def create_announcement(title, content, target_role='all', is_pinned=False) -> dict
  def update_announcement(id, **kwargs) -> dict
  def delete_announcement(id) -> dict

  # FAQ 管理
  def list_faqs(page=1, size=20, category=None) -> dict
  def create_faq(question, answer, category='通用') -> dict
  def update_faq(id, **kwargs) -> dict
  def delete_faq(id) -> dict

  # 知识库管理
  def list_documents(page=1, size=20) -> dict
  def create_document(title, content, category='通用') -> dict
  def update_document(id, **kwargs) -> dict
  def delete_document(id) -> dict

  # 反馈管理
  def list_feedback(page=1, size=20, status=None) -> dict
  def update_feedback_status(id, status, admin_reply=None) -> dict

  # 指南管理
  def list_guides(page=1, size=20) -> dict
  def create_guide(title, content, category) -> dict
  def update_guide(id, **kwargs) -> dict
  def delete_guide(id) -> dict

  # 关键词管理
  def list_keywords(page=1, size=20) -> dict
  def create_keyword(text, group_name='默认') -> dict
  def update_keyword(id, **kwargs) -> dict
  def delete_keyword(id) -> dict

  # 院校管理
  def list_universities(page=1, size=20, keyword=None) -> dict
  def update_university(id, **kwargs) -> dict

  # 专业管理
  def list_majors(page=1, size=20, keyword=None) -> dict
  def update_major(id, **kwargs) -> dict

  # 系统配置
  def get_system_config() -> dict
  def update_system_config(config: dict) -> dict
  ```

  - 所有函数使用统一的 `ok()` / `fail()` 返回格式
  - 使用 `backend/app/database.py` 的 `get_connection()` 获取 DB 连接

  **Must NOT do**:
  - 不改动 agents/ core/ skills/ tools/
  - 不修改现有表结构

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,3,4,5,6)
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [ ] `backend/app/services/admin_service.py` 存在
  - [ ] 包含所有 10 个模块的 CRUD 函数
  - [ ] 使用统一响应格式

  **QA Scenarios**:
  ```
  Scenario: 服务层函数可导入
    Tool: Bash
    Steps:
      1. python -c "from backend.app.services.admin_service import list_users, create_announcement, list_faqs"
    Expected Result: import 无报错
  ```

  **Commit**: YES
  - Message: `feat(backend): add admin CRUD service layer`

- [ ] 3. 创建 admin API 路由

  **What to do**:
  - 创建 `backend/app/routers/admin_crud_router.py`，包含所有 CRUD 端点：

  ```
  # 用户管理
  GET    /api/admin/users          → list_users
  GET    /api/admin/users/{id}     → get_user_detail
  PUT    /api/admin/users/{id}/status → toggle_user_status

  # 公告管理
  GET    /api/admin/announcements          → list
  POST   /api/admin/announcements          → create
  PUT    /api/admin/announcements/{id}     → update
  DELETE /api/admin/announcements/{id}     → delete

  # FAQ 管理
  GET    /api/admin/faqs          → list
  POST   /api/admin/faqs          → create
  PUT    /api/admin/faqs/{id}     → update
  DELETE /api/admin/faqs/{id}     → delete

  # 知识库管理
  GET    /api/admin/knowledge          → list
  POST   /api/admin/knowledge          → create
  PUT    /api/admin/knowledge/{id}     → update
  DELETE /api/admin/knowledge/{id}     → delete

  # 反馈管理
  GET    /api/admin/feedback          → list
  PUT    /api/admin/feedback/{id}     → update

  # 指南管理
  GET    /api/admin/guides          → list
  POST   /api/admin/guides          → create
  PUT    /api/admin/guides/{id}     → update
  DELETE /api/admin/guides/{id}     → delete

  # 关键词管理
  GET    /api/admin/keywords          → list
  POST   /api/admin/keywords          → create
  PUT    /api/admin/keywords/{id}     → update
  DELETE /api/admin/keywords/{id}     → delete

  # 院校管理
  GET    /api/admin/universities          → list
  PUT    /api/admin/universities/{id}     → update

  # 专业管理
  GET    /api/admin/majors          → list
  PUT    /api/admin/majors/{id}     → update

  # 系统配置
  GET    /api/admin/config          → get_config
  PUT    /api/admin/config          → update_config
  ```

  - 在 `backend/app/main.py` 中注册此路由

  **Must NOT do**:
  - 不修改现有 API 端点
  - 不改变现有路由路径

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,4,5,6)
  - **Blocks**: Task 7-16
  - **Blocked By**: Task 2

  **Acceptance Criteria**:
  - [ ] `backend/app/routers/admin_crud_router.py` 存在
  - [ ] 包含所有 CRUD 端点
  - [ ] 在 `backend/app/main.py` 中注册

  **QA Scenarios**:
  ```
  Scenario: API 端点可访问
    Tool: curl
    Steps:
      1. curl http://127.0.0.1:8000/api/admin/users
      2. curl http://127.0.0.1:8000/api/admin/announcements
    Expected Result: 返回 200 + JSON 响应
  ```

  **Commit**: YES
  - Message: `feat(backend): add admin CRUD API routes`

- [ ] 4. 创建通知 + 反馈服务层

  **What to do**:
  - 创建 `backend/app/services/notification_service.py`：

  ```python
  def send_notification(user_id, title, content, type='system', related_id=None)
  def send_announcement_notification(announcement_id, target_role='all')
  def list_notifications(user_id, page=1, size=20)
  def mark_as_read(notification_id, user_id)
  def mark_all_as_read(user_id)
  def get_unread_count(user_id)
  ```

  - 创建 `backend/app/services/feedback_service.py`：

  ```python
  def submit_feedback(user_id, conversation_id, rating, comment=None)
  def list_user_feedback(user_id, page=1, size=20)
  ```

  **Must NOT do**:
  - 不改动现有对话逻辑

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1,2,3,5,6)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [ ] 两个服务文件存在
  - [ ] 通知发送 + 标记已读 + 未读计数功能正常
  - [ ] 反馈提交 + 列表功能正常

  **QA Scenarios**:
  ```
  Scenario: 通知服务可导入
    Tool: Bash
    Steps:
      1. python -c "from backend.app.services.notification_service import send_notification, get_unread_count"
    Expected Result: import 无报错
  ```

  **Commit**: YES (groups with Task 5)
  - Message: `feat(backend): add notification + feedback services`

---

## Final Verification Wave

- [ ] F1. **全路由功能验证** — `unspecified-high`
  访问所有新增管理页面，验证表格渲染、CRUD 操作正常。
  Output: `Pages [10/10 pass] | VERDICT: APPROVE/REJECT`

- [ ] F2. **构建 + API 验证** — `unspecified-high`
  `npm run build` + `python -m api.main` 无报错，所有新 API 端点响应正常。
  Output: `Build [PASS] | APIs [N/N] | VERDICT`

- [ ] F3. **用户端验证** — `unspecified-high`
  通知铃铛显示、通知列表、FAQ 浏览、反馈提交全部可访问。
  Output: `User Features [4/4] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(backend): add CRUD tables + services + API for admin modules`
- **Wave 2**: `feat(admin): add 10 management pages`
- **Wave 3**: `feat(user): add notification bell + FAQ browser + feedback`
- **Wave 4**: `docs: update admin module documentation`

---

## Success Criteria

### Verification Commands
```bash
cd frontend && npm run build    # Expected: build success
python -m api.main              # Expected: startup complete
curl http://127.0.0.1:8000/api/admin/users  # Expected: 200
curl http://127.0.0.1:8000/api/announcements  # Expected: 200
```

### Final Checklist
- [ ] 所有 10 个管理页面可正常 CRUD
- [ ] 通知系统 admin → user 链路正常
- [ ] FAQ 用户端浏览正常
- [ ] 反馈提交 + 管理端查看正常
- [ ] 院校/专业在线编辑正常
- [ ] 系统配置 UI 可用
