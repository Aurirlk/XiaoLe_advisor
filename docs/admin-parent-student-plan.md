# 管理员 · 家长 · 学生 — 认证与知识库计划

> 本文件记录功能规划与实施状态。

### 实施状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 用户认证系统 | ✅ 已完成 | JWT + bcrypt + 多角色 |
| 咕咕数据API | ✅ 已完成 | 6个API端点封装 |
| RRF混合搜索 | ✅ 已完成 | 并行检索 + RRF融合 |
| B端管理后台 | ✅ 已完成 | 知识库/同步/统计 |

---

## 一、用户认证系统（待实施）

### 1.1 设计思路

在现有 `user_profiles` 表上扩展账号密码字段，不新建表、不引入 MySQL。

```
现有 user_profiles 表 + 新增 username/password_hash/role 字段
    → 登录 API（手机号+密码）
    → JWT token（PyJWT）
    → 前端 localStorage 存 token
    → 请求带 Authorization: Bearer <token>
```

### 1.2 表结构变更

```sql
ALTER TABLE user_profiles ADD COLUMN username TEXT DEFAULT '';
ALTER TABLE user_profiles ADD COLUMN password_hash TEXT DEFAULT '';
ALTER TABLE user_profiles ADD COLUMN role TEXT DEFAULT 'student';  -- student/parent/admin
```

### 1.3 登录页面设计

```
┌──────────────────────────────┐
│  🎓 小乐AI · 高考志愿填报助手  │
│                              │
│  手机号: [____________]      │
│  密码:   [____________]      │
│                              │
│  身份: ○ 学生  ○ 家长        │
│                              │
│  [登 录]  [注 册]            │
└──────────────────────────────┘
```

### 1.4 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册（手机号+密码+角色） |
| POST | `/auth/login` | 登录（手机号+密码 → JWT） |
| GET | `/auth/me` | 获取当前用户信息 |

### 1.5 需要新增的文件

| 文件 | 说明 |
|------|------|
| `core/auth.py` | JWT 生成/验证 + 密码哈希 |
| `api/routers/auth_router.py` | 认证端点 |
| `frontend/components/LoginPage.js` | 登录页面组件 |

### 1.6 待确认

- 密码存储：`hashlib.sha256` + 盐值（零依赖）还是 `bcrypt`（更安全）
- 管理员账号：环境变量预设还是普通注册
- JWT 过期时间：建议 7 天
- 学生/家长是否共用手机号

---

## 二、知识库 API 集成（待实施）

### 2.1 咕咕数据 API

| API | 端点 | 用途 |
|-----|------|------|
| 院校基础信息 | `https://api.gugudata.com/metadata/collegeinfo` | 985/211/双一流信息 |
| 院校录取分数线 | `https://api.gugudata.com/metadata/ceecollegeline` | 按院校查分数线 |
| 专业录取分数线 | `https://api.gugudata.com/metadata/ceemajorline` | 按专业查分数线（核心） |
| 各省批次线 | `https://api.gugudata.com/metadata/ceeprovince` | 省控线/批次线 |
| 录取概率预测 | `https://api.gugudata.com/ai/gaokao/predict` | 冲/稳/保 |
| 高考资讯 | `https://api.gugudata.com/news/gaokao` | 最新新闻 |
| 招生政策 | `https://api.gugudata.com/ai/gaokao/policy` | 各省政策 |

### 2.2 新增工具

| 工具 | 功能 |
|------|------|
| `query_major_admission_tool` | 按专业查询录取分数线 |
| `query_province_cutoff_tool` | 查询各省批次线 |
| `query_admission_chance_tool` | 录取概率预测 |
| `query_college_info_tool` | 查询院校基础信息 |

### 2.3 数据分类

| 数据类型 | 更新频率 | 存储方式 | 来源 |
|----------|---------|---------|------|
| 专业库 | 年更 | SQLite 本地 | CSV 上传 |
| 院校库 | 年更 | SQLite 本地 | CSV 上传 |
| 经验知识 | 不定期 | ChromaDB | 文档上传 |
| 录取分数线 | 年更+实时补充 | SQLite + API | CSV + API |
| 省批次线 | 年更 | SQLite | CSV 上传 |
| 录取概率 | 实时 | API | 咕咕数据 |
| 招生政策 | 实时 | 联网搜索 | DuckDuckGo/Metaso |
| 高考新闻 | 实时 | 联网搜索 | DuckDuckGo/Metaso |

---

## 三、B 端管理后台（待实施）

### 3.1 管理页面结构

```
/admin
├── /admin/knowledge        # 知识库管理
│   ├── 专业库管理
│   ├── 院校库管理
│   ├── 分数线管理
│   ├── 经验库管理
│   └── 批次线管理
├── /admin/sync             # 数据同步
│   ├── API 同步状态
│   ├── 手动触发同步
│   └── 同步历史
├── /admin/system           # 系统管理
│   ├── 模型配置
│   ├── 成本监控
│   └── 服务状态
└── /admin/stats            # 数据统计
```

### 3.2 管理员 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/knowledge/upload` | 上传文档到知识库 |
| GET | `/admin/knowledge/list` | 列出知识库内容 |
| DELETE | `/admin/knowledge/{id}` | 删除知识条目 |
| POST | `/admin/knowledge/sync-api` | 触发 API 数据同步 |
| GET | `/admin/knowledge/sync-status` | 查看同步状态 |

---

## 四、混合搜索增强（待实施）

### 4.1 当前搜索链路

```
L0: ChromaDB 向量语义检索 → 有结果直接返回（串行降级）
L1: SQLite FTS5 全文检索
L2: 内存关键词混合召回
```

### 4.2 改进方案：RRF 融合

```
L0 + L1 + L2 并行执行
    → 三路结果合并
    → RRF (Reciprocal Rank Fusion) 排序
    → 去重 → 最终 top_k
```

RRF 公式：`score = 1/(k+rank_vector) + 1/(k+rank_fts5) + 1/(k+rank_keyword)`，k=60

---

## 五、其他待实施功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 情感分析增强 | LLM 提取方案作为可选项 | 中 |
| VLLM 视觉完善 | 更多图片分析场景 | 低 |
| WebSocket 全双工对话 | 替代 SSE 的双向通道 | 中 |
| 前端管理后台 | 独立的管理员页面 | 高 |
| 数据导入向导 | 引导式 CSV 上传 | 中 |

---

*本文件创建于 2026-06-14，作为功能规划存档。*
