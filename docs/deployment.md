# 部署指南

## 方式一：本地开发部署

适用场景：个人使用、开发调试。

```bash
# 1. 克隆并进入项目
git clone <repo-url> && cd zx_ai_advisor

# 2. 创建虚拟环境
conda create -n zxf python=3.10 -y && conda activate zxf

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
copy .env.example .env
# 编辑 .env 填写 DEEPSEEK_API_KEY

# 5. 启动
python -m api.main

# 6. 浏览器打开
#    UI:  http://127.0.0.1:5000
#    API: http://127.0.0.1:8000/docs
```

首次启动前建议执行：

```powershell
python -m scripts.init_sqlite
python -m scripts.import_code_artifacts
```

首次启动会自动完成：

1. **RAG 索引生成** — 若 `data/vector_store/zx_experience.json` 不存在则自动生成
2. **SQLite 建表** — 创建 `data/zx_advisor.db`，注入院校/分数线种子数据
3. **ChromaDB 同步** — 若向量库为空则从 JSON 自动同步经验文档
4. **联网缓存表** — 自动创建 `web_search_sessions` / `web_search_pages`
5. **服务预热** — 并行执行数据库、Redis、LangGraph 引擎自检
6. **模型下载** — 首次运行时自动下载 `paraphrase-multilingual-MiniLM-L12-v2` 嵌入模型

---

## 方式二：Docker Compose 部署

适用场景：生产环境、完整服务栈。

```bash
# 1. 克隆项目
git clone <repo-url> && cd zx_ai_advisor

# 2. 设置环境变量
export DEEPSEEK_API_KEY=sk-xxx

# 3. 启动全部服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

**Docker 服务拓扑：**

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16 | 5432 | 关系型数据库 |
| redis | redis:7 | 6379 | 缓存 + Celery broker |
| api | python:3.11-slim | 8000 | FastAPI 主服务 |
| celery-worker | python:3.11-slim | - | 异步任务处理 |
| celery-beat | python:3.11-slim | - | 定时任务调度 |

---

## 方式三：生产环境部署

适用场景：Linux 服务器、公网访问。

### 3.1 前置准备

```bash
# Ubuntu/Debian
apt update && apt install -y python3.10 python3.10-venv nginx redis-server postgresql
```

### 3.2 数据库初始化

```bash
# PostgreSQL
sudo -u postgres psql -c "CREATE USER zx_advisor WITH PASSWORD 'strong_password';"
sudo -u postgres psql -c "CREATE DATABASE zx_advisor OWNER zx_advisor;"
python scripts/init_db.py

# Redis
redis-cli ping
```

### 3.3 应用部署

```bash
mkdir -p /opt/zx_ai_advisor
cd /opt/zx_ai_advisor
git clone <repo-url> .
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cat > .env << 'EOF'
DEEPSEEK_API_KEY=sk-xxx
POSTGRES_PASSWORD=strong_password
HF_ENDPOINT=https://hf-mirror.com
HOST=0.0.0.0
PORT=8000
UI_HOST=0.0.0.0
UI_PORT=5000
RELOAD=0
AUTO_OPEN_UI=0
EOF
```

### 3.4 Systemd 服务

创建 `/etc/systemd/system/zx-ai-advisor.service`：

```ini
[Unit]
Description=小乐AI 高考志愿填报助手
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/zx_ai_advisor
Environment=PATH=/opt/zx_ai_advisor/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/zx_ai_advisor/venv/bin/python -m api.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now zx-ai-advisor
systemctl status zx-ai-advisor
```

### 3.5 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Vue 3 UI
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # FastAPI
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # SSE 流式传输
        proxy_cache off;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API docs
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
}
```

---

## 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必需) | DeepSeek API 密钥 |
| `DASHSCOPE_API_KEY` | (空) | 通义千问 API Key |
| `ZHIPU_API_KEY` | (空) | 智谱 GLM API Key |
| `DOUBAO_API_KEY` | (空) | 豆包 API Key |
| `MOONSHOT_API_KEY` | (空) | Kimi API Key |
| `OPENAI_API_KEY` | (空) | OpenAI API Key |
| `METASO_API_KEY` | (空) | 秘塔搜索 API Key |
| `TAVILY_API_KEY` | (空) | Tavily 搜索 API Key |
| `ADMIN_API_KEY` | (空) | 管理员 API Key |
| `HF_ENDPOINT` | (空) | HuggingFace 镜像 |
| `HOST` | `0.0.0.0` | FastAPI 监听地址 |
| `PORT` | `8000` | FastAPI 监听端口 |
| `UI_HOST` | `127.0.0.1` | Flask UI 监听地址 |
| `UI_PORT` | `5000` | Flask UI 监听端口 |
| `POSTGRES_PASSWORD` | (空) | PostgreSQL 密码（不设则用 SQLite） |
| `REDIS_HOST` | `localhost` | Redis 地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `CORS_ALLOW_ORIGINS` | `*` | CORS 允许的源 |
| `RELOAD` | `1` | 热重载开关 |
| `AUTO_OPEN_UI` | `1` | 启动时自动打开浏览器 |

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
# 上传文件自动解析
curl -X POST http://127.0.0.1:8000/rag/upload -F "file=@your_document.pdf"

# 扫描目录重建索引
curl -X POST http://127.0.0.1:8000/rag/scan-documents
```

**Q: 前端界面如何自定义？**

编辑 `frontend/` 目录下的 Vue 3 组件即可。修改后刷新浏览器生效（无需重新构建）。
