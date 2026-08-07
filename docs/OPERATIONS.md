# 小乐AI · 运维手册

> 版本: v7.0  
> 更新日期: 2026-06-25  
> 适用人员: 运维工程师、后端开发

---

## 一、系统架构

```
┌──────────────────────────────────────────────────┐
│                  用户浏览器                          │
│  http://127.0.0.1:8000 → Vite 构建 SPA             │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│                FastAPI 后端 (uvicorn)               │
│  ┌──────────────┐  ┌──────────────┐               │
│  │  SPA 静态文件  │  │  API 路由     │               │
│  │  dist/ 目录   │  │  /auth       │               │
│  │  (Vite 构建)  │  │  /stream     │               │
│  └──────────────┘  │  /api         │               │
│                    │  /voice       │               │
│                    └──────┬───────┘               │
│                           │                       │
│                    ┌──────▼───────┐               │
│                    │  LangGraph   │               │
│                    │  Agent 图     │               │
│                    └──────────────┘               │
└──────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │  SQLite  │      │  Neo4j   │      │  Redis   │
   │  主数据库 │      │  知识图谱 │      │  缓存    │
   │  (必需)   │      │  (可选)   │      │  (可选)   │
   └──────────┘      └──────────┘      └──────────┘
         │
         ▼
   ┌──────────┐
   │ ChromaDB │
   │ 向量数据库│
   │ (推荐)    │
   └──────────┘
```

> **架构变化（V7.0）**：旧版 Flask UI（端口 5000）已移除，前端改为 Vite 构建的 SPA，由 FastAPI 在 8000 端口统一 serve。不再需要 Node.js 运行时，但部署时需要先执行一次构建。

---

## 二、环境要求

| 依赖 | 最低版本 | 用途 | 必需 |
|------|----------|------|------|
| Python | 3.10+ | 后端运行时 | ✅ |
| Node.js | 18+ | **构建**前端（仅部署时需要，运行期不需要） | ⚠️ 构建时 |
| Neo4j | 5.x | 知识图谱 | ❌ 可选 |
| Redis | 6.x+ | 会话缓存 | ❌ 可选 |
| Docker | 20.x+ | Neo4j 部署（可选） | ❌ 可选 |

---

## 三、部署步骤

### 3.1 首次部署

```bash
# 1. 克隆项目
git clone <repo-url>
cd 小乐高考志愿填报助手

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key（至少一个）

# 4. 构建前端 SPA（关键步骤！）
cd frontend
npm install
npm run build     # 生成 dist/ 目录，由后端直接 serve
cd ..

# 5. 初始化数据库
python scripts/init_sqlite.py

# 6. 导入数据
python scripts/build_rag_index.py
# （可选）python scripts/import_gaokao_from_xlsx.py

# 7. 启动服务
python -m api.main
# 或
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 日常更新（仅前端改动）

如果只改了前端代码（`frontend/src/` 下的 `.vue` / `.js` / `.css` 文件）：

```bash
cd frontend
npm run build     # 重新构建
cd ..
# 重启后端即可，不需要停服
# 按 Ctrl+C 停止后端，重新 python -m api.main
```

### 3.3 Neo4j 部署（可选）

```bash
# Docker 方式
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v neo4j_data:/data \
  neo4j:5.15-community

# 导入图谱数据
python scripts/import_neo4j.py
```

### 3.4 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | ⚠️（至少一个 LLM Key） | — | DeepSeek API 密钥 |
| `DASHSCOPE_API_KEY` | ❌ | — | 通义千问 API Key |
| `ZHIPU_API_KEY` | ❌ | — | 智谱 GLM API Key |
| `NEO4J_URI` | ❌ | `neo4j://127.0.0.1:7687` | Neo4j 连接 |
| `NEO4J_PASSWORD` | ❌ | `password` | Neo4j 密码 |
| `REDIS_HOST` | ❌ | `localhost` | Redis 地址 |
| `REDIS_PORT` | ❌ | `6379` | Redis 端口 |
| `HOST` | ❌ | `0.0.0.0` | 监听地址 |
| `PORT` | ❌ | `8000` | 监听端口 |
| `CORS_ALLOW_ORIGINS` | ❌ | `*` | CORS 白名单 |
| `HF_ENDPOINT` | ❌ | — | HuggingFace 镜像（国内填 `https://hf-mirror.com`） |

---

## 四、健康检查

### 4.1 API 端点

```bash
# 基础健康检查
curl http://localhost:8000/healthz

# 详细状态（包含所有服务模块）
curl http://localhost:8000/status

# 返回示例
# {
#   "db_ready": true,
#   "graph_ready": true,
#   "vector_ready": true,
#   "redis_ready": false,
#   "rag_index_exists": true,
#   "neo4j": { "connected": false }
# }
```

### 4.2 状态字段说明

| 字段 | 说明 |
|------|------|
| `db_ready` | SQLite 数据库连接状态 |
| `graph_ready` | LangGraph 引擎状态 |
| `vector_ready` | ChromaDB 向量库状态 |
| `redis_ready` | Redis 连接状态 |
| `rag_index_exists` | RAG 索引文件是否存在 |
| `neo4j.connected` | Neo4j 知识图谱连接状态 |

---

## 五、数据备份

### 5.1 SQLite 备份

```bash
# 备份数据库
copy data\zx_advisor.db data\zx_advisor.db.backup.%date:~0,4%%date:~5,2%%date:~8,2%

# 恢复数据库
copy data\zx_advisor.db.backup.20260623 data\zx_advisor.db
```

### 5.2 Neo4j 备份

```bash
# 导出图谱数据
docker exec neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/backups/

# 复制备份文件
docker cp neo4j:/var/lib/neo4j/backups/ ./neo4j-backups/
```

---

## 六、常见问题排查

### 6.1 前端页面空白

**可能原因**：前端未构建或构建产物不完整。

```bash
# 检查 dist 目录是否存在
dir frontend\dist

# 如果缺失或文件不完整，重新构建
cd frontend
npm install
npm run build
cd ..
```

**验证**：构建成功后 `frontend/dist/` 目录应包含 `index.html` 和 `assets/` 目录。

### 6.2 端口 8000 被占用

```powershell
# 查找占用端口的进程
netstat -ano | findstr :8000
# 输出示例: TCP 0.0.0.0:8000 0.0.0.0:0 LISTENING 12345

# 终止进程
taskkill /PID 12345 /F

# 如果 PID 显示为 0（TIME_WAIT 状态），等待 2-4 分钟或换端口
```

### 6.3 Neo4j 连接失败

```bash
# 检查 Neo4j 是否运行
docker ps | grep neo4j

# 测试连接
python -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j','password')); print('OK'); d.close()"
```

### 6.4 RAG 索引为空

```bash
# 重建索引
python scripts/build_rag_index.py

# 验证
python -c "import json; d = json.load(open('data/vector_store/zx_experience.json')); print(f'{len(d)} 条文档')"
```

### 6.5 API Key 报 401

验证 API Key 有效性：

```bash
# 检查 .env 是否包含有效的 Key
type .env | findstr API_KEY

# DeepSeek Key 应以 sk- 开头
```

### 6.6 管理员登录后显示异常

清除浏览器缓存的旧数据：

```js
// 浏览器控制台执行
localStorage.removeItem('auth_token')
localStorage.removeItem('user_info')
localStorage.removeItem('xiaole_dark_mode')
```

然后刷新页面重新登录。

---

## 七、监控与告警

### 7.1 健康检查

```bash
# API 健康检查
curl http://127.0.0.1:8000/healthz

# 详细状态
curl http://127.0.0.1:8000/status

# 管理员面板 → 系统监控页面
# 浏览器打开 http://127.0.0.1:8000 → 管理员登录 → 系统监控
```

### 7.2 日志查看

```bash
# 实时日志（控制台）
# 启动后端时直接查看终端输出

# 错误日志过滤
python -m api.main 2>&1 | findstr "ERROR"
```

---

## 八、性能调优

| 参数 | 默认值 | 建议值 | 说明 |
|------|--------|--------|------|
| `MAX_CONNECTIONS` | 50 | 100 | 数据库连接池大小 |
| `REDIS_TTL` | 604800 | 604800 | 缓存过期时间（7天） |
| `RAG_TOP_K` | 5 | 10 | RAG 检索数量 |
| `LLM_TEMPERATURE` | 0.7 | 0.3 | 降低随机性提高稳定性 |

---

## 九、前端构建说明

### 9.1 构建命令

```bash
cd frontend
npm install        # 安装依赖（首次或依赖变更后）
npm run build      # 生产构建
```

### 9.2 构建产物

```
frontend/dist/
├── index.html              # SPA 入口
├── assets/
│   ├── index-xxxx.js       # 主 JS 包
│   ├── index-xxxx.css      # 主 CSS 包
│   ├── StudentView-xxx.js  # 路由懒加载分片
│   ├── RankingView-xxx.js
│   ├── GraphView-xxx.js
│   ├── ...
│   └── apiClient-xxx.js    # API 客户端工具
```

总大小约 50-60 KB（gzip 后约 20 KB）。

### 9.3 开发模式（HMR 热更新）

```bash
cd frontend
npm run dev
# 启动后访问 http://localhost:5173
# 需要后端同时运行并配置 vite.config.js 中的 proxy
```
