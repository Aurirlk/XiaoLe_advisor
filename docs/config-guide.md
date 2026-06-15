# 配置指南

## 一、配置文件结构

```
configs/
├── .config.yaml              # 用户配置（改这里就行）
├── .config.yaml.example      # 配置模板
├── llm_config.yaml           # LLM 模型库
├── asr_config.yaml           # ASR 引擎库
├── tts_config.yaml           # TTS 引擎库
├── vllm_config.yaml          # 视觉模型库
├── web_search_config.yaml    # 联网搜索配置
├── db_config.yaml            # 数据库配置
├── vector_config.yaml        # 向量库配置
├── rag_config.yaml           # RAG 配置
├── routing_tuning.yaml       # 路由关键词调优
├── synthesis_patches.yaml    # 负反馈补丁
└── prompts/                  # 提示词模板
    ├── zx_system_prompt.md
    └── synthesis_system_prompt.txt
```

---

## 二、.config.yaml — 用户配置

这是唯一需要修改的文件。

### 2.1 模块选择

```yaml
selected_module:
  LLM: deepseek-v4-flash    # 大模型
  ASR: FunASR                # 语音识别
  TTS: EdgeTTS               # 语音合成
  VLLM: glm-4v-flash         # 视觉大模型
```

切换模型只需改对应行的名称。

### 2.2 API Key

```yaml
api_keys:
  DEEPSEEK_API_KEY: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
  DASHSCOPE_API_KEY: "sk-xxx"              # 直接填写
```

支持 `${ENV_VAR}` 语法，也可直接填写。

---

## 三、LLM 模型配置

### 3.1 可用模型

| 系列 | 预设名 | 模型 | 说明 |
|------|--------|------|------|
| DeepSeek V4 | deepseek-v4-flash | deepseek-v4-flash | 默认，性价比最高 |
| DeepSeek V4 | deepseek-v4-pro | deepseek-v4-pro | 最强能力 |
| DeepSeek R1 | deepseek-r1 | deepseek-r1 | 深度推理 |
| 通义千问 3.7 | qwen3.7-plus | qwen3.7-plus | 均衡性能 |
| 通义千问 3.7 | qwen3.7-max | qwen3.7-max | 最强能力 |
| 通义千问 3.7 | qwen3.7-flash | qwen3.7-flash | 免费额度充足 |
| 智谱 GLM 5.1 | glm-5.1-flash | glm-5.1-flash | 免费 |
| 智谱 GLM 5.1 | glm-5.1-pro | glm-5.1-pro | 全量 API |
| 豆包 Seed 2.0 | doubao-seed-2.0-pro | doubao-seed-2.0-pro | 字节最新旗舰 |
| Kimi | kimi-k2.6 | kimi-k2.6 | 月之暗面最新 |
| Ollama | local-qwen | qwen2.5:14b | 本地离线免费 |

### 3.2 切换方式

```bash
# 方式一：改配置
# 编辑 .config.yaml 的 selected_module.LLM

# 方式二：API 运行时切换
curl -X POST http://127.0.0.1:8000/settings/switch-model \
  -H "Content-Type: application/json" \
  -d '{"preset": "qwen3.7-flash"}'

# 方式三：设置界面
# 点击 ⚙️ 设置 → AI Tab → 下拉选择
```

### 3.3 添加自定义模型

编辑 `configs/llm_config.yaml`，在 `presets` 下添加：

```yaml
my-model:
  type: openai
  model_name: my-model-name
  base_url: https://my-api.com/v1
  api_key: ${MY_API_KEY}
  description: "我的自定义模型"
```

然后在 `.config.yaml` 中选择：

```yaml
selected_module:
  LLM: my-model
```

---

## 四、ASR 语音识别配置

### 4.1 可用引擎

| 预设名 | 引擎 | 费用 | 说明 |
|--------|------|------|------|
| FunASR | 本地 FunASR | 免费 | 中文最佳 |
| Qwen3ASR | 通义千问 ASR | 按量 | 大模型增强 |
| OpenAI Whisper | Whisper API | 按量 | 多语言 |
| SherpaLocal | Sherpa-ONNX | 免费 | 离线 |

### 4.2 切换方式

```yaml
selected_module:
  ASR: Qwen3ASR
```

---

## 五、TTS 语音合成配置

### 5.1 可用引擎

| 预设名 | 引擎 | 费用 | 说明 |
|--------|------|------|------|
| EdgeTTS | 微软 Edge | 免费 | 音色丰富 |
| CosyVoice | 硅基流动 | 按量 | 中文最自然 |
| AliyunStream | 阿里云 | 按量 | 龙系列音色 |

### 5.2 切换方式

```yaml
selected_module:
  TTS: CosyVoice
```

---

## 六、VLLM 视觉配置

### 6.1 可用模型

| 预设名 | 模型 | 费用 | 说明 |
|--------|------|------|------|
| GLM4VFlash | glm-4v-flash | 免费 | 推荐 |
| QwenVLPlus | qwen-vl-plus | 按量 | 中文理解好 |
| QwenVLMax | qwen-vl-max | 按量 | 最强 |
| GPT4o | gpt-4o | 按量 | 需海外网络 |

### 6.2 切换方式

```yaml
selected_module:
  VLLM: QwenVLPlus
```

---

## 七、联网搜索配置

### 7.1 可用搜索源

| 搜索源 | 费用 | 说明 |
|--------|------|------|
| duckduckgo | 免费 | 默认，无需 Key |
| metaso | 按量 | 秘塔搜索，国内可用，质量高 |
| tavily | 按量 | 海外搜索 |

### 7.2 配置

```yaml
# configs/web_search_config.yaml
web_search:
  provider: metaso  # 切换搜索源

  metaso:
    api_key: "${METASO_API_KEY}"
```

---

## 八、数据库配置

### 8.1 SQLite（默认）

无需配置，自动使用 `data/zx_advisor.db`。

### 8.2 PostgreSQL

```yaml
# configs/db_config.yaml
postgres:
  host: localhost
  port: 5432
  database: zx_advisor
  user: postgres
  password_env: POSTGRES_PASSWORD
```

---

## 九、环境变量

### 9.1 必填

```ini
DEEPSEEK_API_KEY=sk-xxx
```

### 9.2 可选

```ini
# 其他 LLM
DASHSCOPE_API_KEY=
ZHIPU_API_KEY=
DOUBAO_API_KEY=
MOONSHOT_API_KEY=

# ASR/TTS
SILICONFLOW_API_KEY=
DOUBAO_APPID=
DOUBAO_ACCESS_TOKEN=

# 联网搜索
METASO_API_KEY=
TAVILY_API_KEY=

# 基建
REDIS_HOST=localhost
REDIS_PORT=6379
POSTGRES_PASSWORD=

# 服务
HOST=0.0.0.0
PORT=8000
```

---

## 十、配置优先级

```
.config.yaml (用户配置，最高优先级)
    ↓ 不存在或为空
*_config.yaml (预设库，次优先级)
    ↓
代码中的默认值
```

API Key 优先级：
```
.config.yaml api_keys 直接填写
    ↓ 未填写
.config.yaml api_keys ${ENV_VAR}
    ↓ 环境变量未设置
*_config.yaml 中的 ${ENV_VAR}
```
