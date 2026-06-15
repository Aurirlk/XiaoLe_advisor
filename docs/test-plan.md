# 测试方案

## 一、测试环境

| 项目 | 值 |
|------|------|
| 后端地址 | http://127.0.0.1:8000 |
| Web UI 地址 | http://127.0.0.1:5000 |
| 测试工具 | pytest / curl / 浏览器 |
| 默认 LLM | DeepSeek V4 Flash |
| 默认 ASR | FunASR (本地) |
| 默认 TTS | EdgeTTS (免费) |
| Python 版本 | 3.10+ |
| 操作系统 | Windows / Linux / macOS |

---

## 二、单元测试

### 2.1 工具容错测试 (test_tool_retry.py)

| 编号 | 测试项 | 输入 | 预期 |
|------|--------|------|------|
| TR-01 | ToolResult 五级状态 | 各种 tier | 正确创建 |
| TR-02 | 省名标准化 "粤" | "粤" | "广东省" |
| TR-03 | 省名标准化 "桂" | "桂" | "广西壮族自治区" |
| TR-04 | 选科标准化 | "物理" | "物理类" |
| TR-05 | SQL 精确匹配 | 正确参数 | exact |
| TR-06 | SQL 模糊匹配 | "计算机科学" | fuzzy, 匹配到"计算机科学与技术" |
| TR-07 | SQL 放宽年份 | 错误年份 | degraded |
| TR-08 | SQL 空结果建议 | 不存在的组合 | empty + suggestions |
| TR-09 | RAG 正常查询 | 有效关键词 | 返回结果 |
| TR-10 | RAG 空查询 | "" | 返回空 |
| TR-11 | RAG 无关查询 | 无相关内容 | 返回降级结果 |
| TR-12 | WebSearch 空查询 | "" | 返回空 |

### 2.2 防幻觉测试 (test_anti_hallucination.py)

| 编号 | 测试项 | 场景 | 预期 |
|------|--------|------|------|
| AH-01 | safe_node_call 同步函数 | 正常返回 | 返回结果 |
| AH-02 | safe_node_call 异常捕获 | 抛出异常 | 返回 fallback |
| AH-03 | safe_node_call async 函数 | 正常返回 | 返回结果 |
| AH-04 | safe_node_call None 返回 | 返回 None | 安全处理 |
| AH-05 | 状态注入攻击 | query 含注入文本 | 不影响路由 |
| AH-06 | 空字节输入 | query 含 \x00 | 不崩溃 |
| AH-07 | Unicode 溢出 | 超长 Unicode | 不崩溃 |
| AH-08 | 零除异常 | 工具内 1/0 | safe_node_call 兜底 |
| AH-09 | 递归异常 | 无限递归 | safe_node_call 兜底 |
| AH-10 | Skills 极端输入 | None/garbage | 不崩溃 |

### 2.3 防端水测试 (test_synthesis_guard.py)

| 编号 | 测试项 | 场景 | 预期 |
|------|--------|------|------|
| SG-01 | 信号检测 - 高风险 | risk_assessment.is_risk=true | 检出 critical |
| SG-02 | 信号检测 - 现实校验 | reality_check.is_realistic=false | 检出 critical |
| SG-03 | 信号检测 - 无信号 | 空 state | 返回空 |
| SG-04 | Prompt 注入 - 必须包含 | must_say 存在 | 注入到 prompt |
| SG-05 | Prompt 注入 - 禁止端水 | critical 信号 | 注入禁止端水词 |
| SG-06 | 输出校验 - must_say 缺失 | LLM 未包含 | 强制插入 |
| SG-07 | 输出校验 - 端水词 | 包含"各有利弊" | 检出 |
| SG-08 | 输出校验 - 风险后置 | 风险在 500 字后 | 检出 |
| SG-09 | 输出校验 - 合规输出 | 正常输出 | 通过 |
| SG-10 | enforce - 空输出 | "" + critical | 强制修正 |

### 2.4 路由测试 (test_supervisor_routing.py)

| 编号 | 测试项 | 场景 | 预期 |
|------|--------|------|------|
| SR-01 | 分数查询 | "600分能上什么" | match_agent |
| SR-02 | 就业前景 | "计算机好就业吗" | career_agent |
| SR-03 | 联网搜索 | "帮我搜一下最新政策" | web_search_agent |
| SR-04 | 画像缺失 | 无省份信息 | profile_agent |
| SR-05 | 家长对话 | "我是家长" | parent_agent |
| SR-06 | 默认路由 | "你好" | synthesis_agent |
| SR-07 | LLM 路由 | API 可用时 | 准确率 > 70% |

### 2.5 路由模糊测试 (test_supervisor_fuzzing.py)

| 编号 | 测试维度 | 用例数 |
|------|---------|--------|
| SF-01 | 标准路由组合 | 504 |
| SF-02 | 噪音干扰 | 45 |
| SF-03 | 错别字鲁棒 | 7 |
| SF-04 | 混合意图边界 | 5 |
| SF-05 | 关键词优先级 | 6 |

### 2.6 技能边缘测试 (test_skills_edge_cases.py)

| 编号 | 测试项 | 场景 |
|------|--------|------|
| SE-01 | risk_assessor - 四大天坑 | 生化环材 × 各 tier |
| SE-02 | risk_assessor - 医学预算 | 79999 vs 80000 |
| SE-03 | reality_checker - tolerance 边界 | -9 vs -8 |
| SE-04 | reality_checker - 高分低报 | 35 vs 36 |
| SE-05 | decision_heuristics - 空画像 | 无任何字段 |
| SE-06 | decision_heuristics - 全画像 | 所有字段 |
| SE-07 | roi_calculator - 零薪资 | salary=0 |

---

## 三、集成测试

### 3.1 API 端点测试

| 编号 | 端点 | 方法 | 预期 |
|------|------|------|------|
| API-01 | `/stream/advice` | POST | SSE 流式响应 |
| API-02 | `/voice/asr` | POST | 识别结果 |
| API-03 | `/voice/tts` | POST | 音频数据 |
| API-04 | `/vision/analyze` | POST | 图片分析 |
| API-05 | `/settings/models` | GET | 模型列表 |
| API-06 | `/settings/switch-model` | POST | 切换成功 |
| API-07 | `/feedback` | POST | 反馈保存 |
| API-08 | `/rag/stats` | GET | 向量库统计 |
| API-09 | `/status` | GET | 服务状态 |
| API-10 | `/healthz` | GET | 健康检查 |

### 3.2 语音交互测试

| 编号 | 流程 | 预期 |
|------|------|------|
| VOICE-01 | 录音 → ASR → 文本 | 识别成功 |
| VOICE-02 | 文本 → TTS → 音频 | 合成成功 |
| VOICE-03 | 录音 → ASR → LLM → TTS | 全链路通畅 |
| VOICE-04 | 静音录音 | 返回提示 |
| VOICE-05 | 噪音录音 | 容错处理 |

### 3.3 WebSocket 测试

| 编号 | 场景 | 预期 |
|------|------|------|
| WS-01 | 连接 /ws/chat | 连接成功 |
| WS-02 | 发送 text 消息 | 收到回复 |
| WS-03 | 发送音频流 | ASR + 回复 |
| WS-04 | 心跳 ping | 返回 pong |
| WS-05 | 断开重连 | 自动重连 |

---

## 四、边界与异常测试

### 4.1 输入边界

| 编号 | 场景 | 预期 |
|------|------|------|
| EXC-01 | 空字符串输入 | 提示输入 |
| EXC-02 | 超长文本 (10000字) | 正常处理 |
| EXC-03 | 纯 emoji | 正常处理 |
| EXC-04 | SQL 注入 `' OR 1=1` | 安全处理 |
| EXC-05 | XSS `<script>alert(1)</script>` | 安全处理 |

### 4.2 网络异常

| 编号 | 场景 | 预期 |
|------|------|------|
| NET-01 | LLM API 不可用 | 回退到关键词路由 |
| NET-02 | ASR 服务不可用 | 返回错误提示 |
| NET-03 | TTS 服务不可用 | 返回文本回复 |
| NET-04 | Redis 不可用 | 降级到内存 |
| NET-05 | 并发 10 请求 | 正常响应 |

### 4.3 成本控制

| 编号 | 场景 | 预期 |
|------|------|------|
| COST-01 | 日用量超限 | 返回提示 |
| COST-02 | 月用量超限 | 返回提示 |
| COST-03 | Token 统计准确 | 输入+输出 tokens 正确 |

---

## 五、测试执行

### 运行命令

```bash
# 全部测试
python -m pytest tests/ -v

# 核心测试
python -m pytest tests/test_tool_retry.py tests/test_anti_hallucination.py tests/test_synthesis_guard.py -v

# 路由测试
python -m pytest tests/test_supervisor_routing.py tests/test_supervisor_fuzzing.py -v

# 技能测试
python -m pytest tests/test_skills_edge_cases.py -v

# 编译检查
python -m pytest tests/test_all_python_files_compile.py -v
```

### 通过标准

- 单元测试：100% 通过
- 集成测试：95%+ 通过
- 路由测试：fallback 100% 通过，LLM 70%+ 通过
- 无 P0/P1 级别 bug
