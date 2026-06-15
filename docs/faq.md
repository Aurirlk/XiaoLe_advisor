# 常见问题 ❓

## 一、环境与启动

### 1. 首次启动时长时间卡住不动？

首次启动需要下载 `paraphrase-multilingual-MiniLM-L12-v2` 嵌入模型（约 420MB）。

**解决方案**：
- **国内用户**：设置 `HF_ENDPOINT=https://hf-mirror.com`（在 `.env` 中）
- **已下载过**：模型会缓存在 HuggingFace 本地目录，后续启动秒开

```bash
# .env 中添加
HF_ENDPOINT=https://hf-mirror.com
```

### 2. 报错 "DeepSeek API Key 未配置"？

在 `.env` 文件中设置：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

或在 `configs/.config.yaml` 的 `api_keys` 段直接填写：

```yaml
api_keys:
  DEEPSEEK_API_KEY: "sk-xxxxxxxxxxxxxxxx"
```

### 3. PostgreSQL 连接不上怎么办？

系统会自动降级到 SQLite 本地数据库。不配置 PostgreSQL 不影响核心功能。

如果需要使用 PostgreSQL：

```bash
# 确认 PostgreSQL 已启动
sudo systemctl status postgresql

# 检查 .env 中的密码配置
POSTGRES_PASSWORD=your_password
```

### 4. Redis 连接失败怎么办？

Redis 用于会话历史存储，连接失败不影响核心对话功能。系统会自动降级。

```bash
# 确认 Redis 已启动
redis-cli ping
# 应返回 PONG

# .env 中配置
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 5. `trafilatura` 模块找不到？

```bash
pip install trafilatura
```

如果安装失败（网络问题），可使用国内镜像：

```bash
pip install trafilatura -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 6. 端口被占用？

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/macOS
lsof -i :8000
kill -9 <pid>
```

---

## 二、语音交互

### 7. 语音识别不准确？

- 确保麦克风权限已授予浏览器
- 在安静环境下录音
- 说话清晰，语速适中
- 检查 `configs/.config.yaml` 中 ASR 引擎是否正确配置

### 8. TTS 语音合成失败？

**Edge TTS（默认，免费）**：
- 需要网络连接（访问微软 Edge TTS 服务）
- 如果使用代理，可能需要关闭代理

**阿里 CosyVoice**：
- 需要配置 `SILICONFLOW_API_KEY`
- 在 `configs/.config.yaml` 中切换 TTS 引擎

### 9. 语音打断（barge-in）不生效？

语音打断需要在"连续对话"模式下才能生效：

1. 点击设置 → 语音 Tab
2. VAD 模式选择"连续对话"
3. 系统会自动检测用户说话并打断 TTS 播放

### 10. VAD 检测不到语音？

VAD 灵敏度可在设置中调整：

- 降低阈值 → 更灵敏（但可能误触发）
- 升高阈值 → 更严格（但可能漏检）

默认阈值 0.015 适合大多数场景。

---

## 三、模型与配置

### 11. 如何切换 LLM 模型？

**方式一**：编辑配置文件

```yaml
# configs/.config.yaml
selected_module:
  LLM: qwen3.7-flash  # 改成你要用的模型
```

**方式二**：运行时切换（无需重启）

```bash
curl -X POST http://127.0.0.1:8000/settings/switch-model \
  -H "Content-Type: application/json" \
  -d '{"preset": "qwen3.7-flash"}'
```

**方式三**：设置界面

点击右上角 ⚙️ 设置 → AI Tab → 下拉选择模型

### 12. 如何查看所有可用模型？

```bash
curl http://127.0.0.1:8000/settings/models
```

或在设置界面的 AI Tab 中查看下拉列表。

### 13. 切换模型后需要重启吗？

通过 API 或设置界面切换不需要重启。编辑 `.config.yaml` 文件需要重启。

### 14. 如何使用本地 Ollama 模型？

1. 安装 Ollama：https://ollama.ai
2. 拉取模型：`ollama pull qwen2.5:14b`
3. 配置 `.config.yaml`：

```yaml
selected_module:
  LLM: LocalQwen
```

### 15. API Key 支持哪些配置方式？

三种方式（优先级从高到低）：

1. `.config.yaml` 的 `api_keys` 段直接填写
2. `.config.yaml` 的 `api_keys` 段用 `${ENV_VAR}` 引用环境变量
3. `.env` 文件中的环境变量

---

## 四、知识库与 RAG

### 16. 如何更新知识库？

```bash
# 方式一：上传文件自动解析
curl -X POST http://127.0.0.1:8000/rag/upload -F "file=@document.pdf"

# 方式二：扫描目录重建索引
curl -X POST http://127.0.0.1:8000/rag/scan-documents

# 方式三：通过设置界面
# 设置 → 高级 → 知识库管理
```

### 17. 支持哪些文件格式？

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Markdown | `.md` | 按段落分块 |
| CSV | `.csv` | 按行列拼接 |
| PDF | `.pdf` | pdfplumber 提取 |
| 纯文本 | `.txt` | 原样提取 |

### 18. 向量检索和全文检索有什么区别？

- **向量检索（ChromaDB）**：语义相似度匹配，"计算机就业前景" 能匹配到 "IT 行业发展"
- **全文检索（SQLite FTS5）**：关键词精确匹配，"计算机" 只匹配包含 "计算机" 的文档
- **关键词混合召回**：本地 JSON 文件的词频+语义混合匹配

系统自动按优先级使用：向量 → 全文 → 关键词

---

## 五、对话与画像

### 19. 用户画像是什么？

用户画像是系统从对话中自动提取的结构化信息，包括：

- **学生画像**：省份、选科、分数、位次、目标城市、专业意向、兴趣爱好
- **家长画像**：职业、行业、学历、期望、担忧
- **家庭背景**：收入水平、预算、决策人、独生子女

### 20. 如何查看当前画像？

- **前端**：右侧侧边栏自动显示
- **API**：`GET /stream/state/{session_id}`

### 21. 画像会跨会话保存吗？

如果配置了手机号（CRM），画像会持久化保存。下次同一手机号的会话会自动加载历史画像。

### 22. 学科评分怎么用？

用户可以说：

- "我数学最好，物理也不错" → 系统标记数学、物理为强势学科
- "我英语很差" → 系统标记英语为弱势学科
- "数学考了 135 分" → 系统记录数学高考分数

这些信息会帮助系统给出更精准的建议。

---

## 六、成本与安全

### 23. 如何控制 LLM 调用成本？

```yaml
# configs/.config.yaml（未来版本）
cost:
  daily_limit: 10.0    # 日限额（元）
  monthly_limit: 200.0 # 月限额（元）
```

查看当前用量：

```bash
curl http://127.0.0.1:8000/admin/cost-stats
```

### 24. 如何保护管理接口？

设置 `ADMIN_API_KEY` 环境变量：

```bash
# .env
ADMIN_API_KEY=your-secret-key
```

所有管理接口（`/admin/*`、`/rag/*` 写入操作）都需要在 Header 中传入：

```bash
curl -H "X-Admin-Key: your-secret-key" http://127.0.0.1:8000/admin/data/stats
```

### 25. 如何查看 Token 用量？

```bash
# 日用量
curl http://127.0.0.1:8000/admin/cost-stats

# 返回示例
{
  "daily": {"total_cost_yuan": 2.35, "request_count": 42},
  "monthly": {"total_cost_yuan": 45.6, "request_count": 856}
}
```

---

## 七、部署与运维

### 26. Docker 部署失败？

```bash
# 检查 Docker 是否运行
docker info

# 重建容器
docker-compose down
docker-compose up -d --build

# 查看日志
docker-compose logs -f api
```

### 27. 如何备份数据？

```bash
# SQLite
cp data/zx_advisor.db backup/zx_advisor_$(date +%Y%m%d).db

# ChromaDB
cp -r data/chroma_db backup/chroma_db_$(date +%Y%m%d)

# 配置
cp configs/.config.yaml backup/config_$(date +%Y%m%d).yaml
```

### 28. 如何查看服务状态？

```bash
# API 健康检查
curl http://127.0.0.1:8000/healthz

# 详细状态
curl http://127.0.0.1:8000/status
```

### 29. 日志在哪里？

- 控制台输出：启动时直接可见
- 日志文件：`logs/` 目录（如果配置了文件日志）

---

## 八、更多问题

如果以上内容没有解答你的问题，可以通过以下方式获取帮助：

1. 查看 [API 参考文档](api-reference.md)
2. 查看 [配置指南](config-guide.md)
3. 查看 [部署手册](deployment.md)
4. 在项目 Issues 中提交问题
