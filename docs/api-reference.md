# API 参考

## 端点总览

### 用户认证 (V4.5新增)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/auth/register` | 注册新用户（手机号+密码+角色） |
| `POST` | `/auth/login` | 登录（返回JWT Token） |
| `GET` | `/auth/me` | 获取当前用户信息（需Bearer Token） |

**请求示例:**

```bash
# 注册
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "13800138000", "password": "test123", "role": "student"}'

# 登录
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "13800138000", "password": "test123"}'

# 获取用户信息（需Token）
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

### 核心对话

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/stream/advice` | SSE 流式对话（核心接口） |
| `WS` | `/ws/chat` | WebSocket 全双工对话 |
| `GET` | `/stream/state/{session_id}` | 当前对话状态与用户画像 |
| `GET` | `/stream/history/{session_id}` | 画像变更历史 |

### 语音交互

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/voice/asr` | 语音识别 |
| `POST` | `/voice/tts` | 语音合成 |
| `WS` | `/voice/tts-stream` | WebSocket 流式语音合成 |
| `GET` | `/voice/voices` | 列出可用音色 |
| `GET` | `/voice/status` | 语音模块状态 |

### 视觉分析

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/vision/analyze` | 图片分析 |
| `POST` | `/vision/chat` | 图文对话（带上下文） |
| `GET` | `/vision/models` | 列出可用视觉模型 |
| `GET` | `/vision/status` | 视觉模块状态 |

### 反馈系统

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/feedback` | 提交反馈 |
| `GET` | `/feedback/stats` | 反馈统计 |
| `GET` | `/feedback/turns/{turn_id}` | 单轮详情 |
| `GET` | `/feedback/tags` | 可用标签列表 |

### 设置管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/settings` | 获取 UI 设置 |
| `POST` | `/settings` | 保存 UI 设置 |
| `GET` | `/settings/models` | 列出所有可用模型预设 |
| `POST` | `/settings/switch-model` | 运行时切换 LLM 模型 |

### 管理后台

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/admin/import` | 上传 CSV/JSON 导入数据 |
| `GET` | `/admin/import/batches` | 查看导入历史 |
| `GET` | `/admin/data/stats` | 数据覆盖统计 |
| `DELETE` | `/admin/import/batches/{id}` | 按批次回滚 |
| `GET` | `/admin/model-presets` | 列出模型预设 |
| `GET` | `/admin/cost-stats` | Token 成本统计 |
| `GET` | `/admin/knowledge/list` | 列出知识库内容 (V4.5) |
| `POST` | `/admin/knowledge/upload` | 上传知识 (V4.5) |
| `DELETE` | `/admin/knowledge/{index}` | 删除知识条目 (V4.5) |
| `POST` | `/admin/knowledge/sync-api` | 咕咕数据API同步 (V4.5) |

### 调查问卷 (V5.0新增)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/questionnaire/types` | 获取所有问卷类型列表 |
| `GET` | `/questionnaire/{type}` | 获取指定问卷详情 |
| `POST` | `/questionnaire/validate` | 验证问卷答案 |
| `POST` | `/questionnaire/submit` | 提交问卷并转换为画像 |
| `GET` | `/questionnaire/stats/completion` | 获取问卷完成度统计 |

**请求示例:**

```bash
# 获取问卷类型
curl http://127.0.0.1:8000/questionnaire/types

# 获取学生基础问卷
curl http://127.0.0.1:8000/questionnaire/profile_basic

# 提交问卷
curl -X POST http://127.0.0.1:8000/questionnaire/submit \
  -H "Content-Type: application/json" \
  -d '{
    "questionnaire_type": "profile_basic",
    "answers": {
      "pb_province": "广东省",
      "pb_subject_type": "物理类",
      "pb_score": 620,
      "pb_gender": "男",
      "pb_mbti_ei": "主动与很多人交流，包括陌生人 → E",
      "pb_mbti_sn": "具体的事实和细节 → S",
      "pb_mbti_tf": "逻辑和客观分析 → T",
      "pb_mbti_jp": "有计划、有条理 → J"
    }
  }'
```

### RAG 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/rag/ingest` | 增量入库文档 |
| `POST` | `/rag/upload` | 上传文件自动解析 |
| `POST` | `/rag/scan-documents` | 扫描目录重建索引 |
| `POST` | `/rag/rebuild` | 清空重建索引 |
| `POST` | `/rag/sync-from-json` | 从 JSON 同步向量库 |
| `GET` | `/rag/stats` | 向量库统计 |
| `DELETE` | `/rag/collection` | 清空向量集合 |

### 联网搜索

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/web/search` | 联网搜索 + 抓取正文 + 落库 |
| `GET` | `/web/sessions` | 联网查询历史列表 |
| `GET` | `/web/sessions/{id}` | 单次查询的页面明细 |
| `GET` | `/web/cache/check` | 检查缓存 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat/message` | 保存消息到 Redis |
| `GET` | `/chat/history/{session_id}` | 查询历史消息 |
| `DELETE` | `/chat/history/{session_id}` | 清空会话历史 |

### 元信息

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/healthz` | 健康检查 |
| `GET` | `/status` | 服务状态详情 |

---

## 流式建议接口

**请求：**

```bash
curl -X POST http://127.0.0.1:8000/stream/advice \
  -H "Content-Type: application/json" \
  -d '{"query": "广东省物理类600分，想读计算机", "session_id": "", "conversation_role": "student"}'
```

**请求体：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户问题 |
| `session_id` | string | 否 | 会话 ID，空则自动生成 |
| `conversation_role` | string | 否 | student 或 parent |

**SSE 事件类型：**

| type | 说明 |
|------|------|
| `token` | LLM 生成的文本片段 |
| `status` | 系统状态消息 |
| `profile_update` | 用户画像更新（含家长/家庭/学科/情绪） |
| `meta` | 元信息（session_id, turn_id） |

---

## WebSocket 对话接口

**连接：** `ws://host:8000/ws/chat`

**客户端 → 服务端：**

```json
{"type": "text", "query": "...", "session_id": "...", "role": "student"}
{"type": "audio_start", "session_id": "..."}
binary: PCM 16-bit 16kHz 单声道音频 chunk
{"type": "audio_end"}
```

**服务端 → 客户端：**

```json
{"type": "status", "msg": "..."}
{"type": "token", "msg": "..."}
{"type": "asr_result", "text": "..."}
{"type": "profile_update", "profile": {...}, "emotion": {...}}
{"type": "meta", "session_id": "...", "turn_id": "..."}
{"type": "done"}
{"type": "error", "msg": "..."}
```

---

## 流式 TTS WebSocket

**连接：** `ws://host:8000/voice/tts-stream`

**客户端 → 服务端：**

```json
{"text": "...", "emotion": "happy", "emotion_intensity": 0.8}
```

**服务端 → 客户端：**

- binary: 音频 chunk（逐块推送）
- text: `{"type": "done"}` 或 `{"type": "error", "msg": "..."}`
