# 服务工厂 (Provider Factory)

## 一、概述

服务工厂采用**工厂模式**动态创建 LLM/ASR/TTS/VLLM 供应商实例，支持：

- **运行时切换** — 修改配置即可切换供应商，无需重启
- **自动回退** — 主供应商熔断后自动切换到备用供应商
- **熔断保护** — 连续失败 N 次后自动熔断，定时恢复
- **指数退避重试** — 网络超时自动重试，延迟指数增长

---

## 二、架构

```
core/providers/
├── base.py              # 基础抽象层
│   ├── CircuitBreaker   # 三态熔断器
│   ├── RetryMixin       # 指数退避重试
│   └── BaseProvider     # 供应商基类
├── llm_factory.py       # LLM 工厂
├── asr_factory.py       # ASR 工厂
├── tts_factory.py       # TTS 工厂
└── vllm_factory.py      # VLLM 视觉工厂
```

---

## 三、熔断器 (CircuitBreaker)

### 状态机

```
         失败次数 >= threshold
CLOSED ─────────────────────→ OPEN
   ↑                            │
   │  成功                      │ recovery_timeout 到期
   └──────── HALF_OPEN ←────────┘
              (试探性放行 1 个请求)
```

### 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| failure_threshold | 5 | 连续失败多少次触发熔断 |
| recovery_timeout | 60.0 | 熔断后多少秒进入半开状态 |

---

## 四、LLM 工厂

### 支持的供应商

| 类型 | 供应商 | 说明 |
|------|--------|------|
| openai | DeepSeek / Qwen / GLM / Doubao / Kimi | OpenAI 兼容接口 |
| gemini | Google Gemini | 需要 langchain-google-genai |
| ollama | 本地模型 | 零成本离线 |

### 自动回退

```python
from core.providers.llm_factory import LLMFactory

# 创建带回退的 LLM
provider = LLMFactory.create_from_config(fallback_preset="local-qwen")

# 主供应商熔断时自动切换到 local-qwen
result = await provider.invoke(messages)
```

### 配置示例

```yaml
# .config.yaml
selected_module:
  LLM: deepseek-v4-flash  # 主模型

api_keys:
  DEEPSEEK_API_KEY: "${DEEPSEEK_API_KEY}"
```

---

## 五、ASR 工厂

### 支持的供应商

| 类型 | 供应商 | 说明 |
|------|--------|------|
| fun_local | FunASR | 本地免费，中文最佳 |
| openai | Whisper API | 多语言通用 |
| qwen3_asr_flash | 通义千问 ASR | 大模型增强识别 |
| sherpa_onnx_local | Sherpa-ONNX | 本地离线 |

### 使用

```python
from core.providers.asr_factory import ASRFactory

provider = ASRFactory.create_from_config()
text = await provider.transcribe(audio_bytes)
```

---

## 六、TTS 工厂

### 支持的供应商

| 类型 | 供应商 | 说明 |
|------|--------|------|
| edge | Edge TTS | 免费，音色丰富 |
| siliconflow | CosyVoice | 中文音色自然 |
| aliyun_stream | 阿里 CosyVoice | 龙系列音色 |

### 情绪 TTS

```python
from core.providers.tts_factory import TTSFactory
from core.emotion_analyzer import EmotionResult, get_emotion_tts_params

provider = TTSFactory.create_from_config()
emotion = EmotionResult(label="happy", intensity=0.8, valence=0.8, confidence=0.9, raw_tags=[])
params = get_emotion_tts_params(emotion, provider.config.get("type", "edge"))

# 整段合成
audio = await provider.synthesize(text, emotion=params)

# 流式合成
async for chunk in provider.synthesize_stream(text, emotion=params):
    yield chunk
```

---

## 七、VLLM 视觉工厂

### 支持的供应商

| 类型 | 供应商 | 说明 |
|------|--------|------|
| openai | GLM-4V / Qwen-VL / GPT-4o | OpenAI 兼容接口 |

### 使用

```python
from core.providers.vllm_factory import VLLMFactory

provider = VLLMFactory.create_from_config()
result = await provider.analyze_image(image_bytes, "请描述这张图片")
```

---

## 八、添加自定义供应商

```python
from core.providers.tts_factory import TTSFactory, TTSProvider

class MyTTSProvider(TTSProvider):
    async def _do_synthesize(self, text, emotion=None):
        # 实现你的 TTS 逻辑
        return audio_bytes

# 注册
TTSFactory.register("my_tts", MyTTSProvider)

# 使用
# .config.yaml 中 selected_module.TTS: MyTTS
```
