# 语音交互指南

## 一、概述

小乐AI 支持完整的语音交互链路：

```
用户说话 → ASR 语音识别 → LLM 对话 → TTS 语音合成 → 播放音频
```

支持三种交互模式：
- **按住说话** — 按住麦克风按钮录音
- **点击录音** — 点击开始/停止
- **连续对话** — VAD 自动检测说话，支持意图打断

---

## 二、ASR 语音识别

### 2.1 可用引擎

| 引擎 | 类型 | 费用 | 说明 |
|------|------|------|------|
| Funasr-local | 本地 | 免费 | **推荐**，中文最佳 |
| qwen3-asr | 云端 | 按量 | 大模型增强，多语言 |
| openai-whisper | 云端 | 按量 | 多语言通用 |
| sherpa-local | 本地 | 免费 | 支持中英日韩粤 |

### 2.2 切换引擎

```yaml
# configs/.config.yaml
selected_module:
  ASR: qwen3-asr
```

### 2.3 FunASR 本地部署

1. 下载模型到 `models/SenseVoiceSmall/`
2. 配置 `.config.yaml`：
```yaml
ASR:
  FunASR:
    type: fun_local
    model_dir: models/SenseVoiceSmall
```

---

## 三、TTS 语音合成

### 3.1 可用引擎

| 引擎 | 类型 | 费用 | 说明 |
|------|------|------|------|
| EdgeTTS | 云端 | **免费** | **推荐**，音色丰富 |
| CosyVoice | 云端 | 按量 | 中文音色最自然 |
| AliyunStream | 云端 | 按量 | 龙系列音色 |

### 3.2 切换引擎

```yaml
# configs/.config.yaml
selected_module:
  TTS: CosyVoice
```

### 3.3 可用音色 (EdgeTTS)

| 音色 ID | 名称 | 性别 |
|---------|------|------|
| zh-CN-XiaoxiaoNeural | 晓晓 | 女 |
| zh-CN-YunxiNeural | 云希 | 男 |
| zh-CN-YunjianNeural | 云健 | 男 |
| zh-CN-XiaoyiNeural | 晓艺 | 女 |
| zh-CN-liaoning-XiaobeiNeural | 晓北（东北） | 女 |
| zh-HK-HiuGaaiNeural | 曉佳（粤语） | 女 |

### 3.4 情绪 TTS

系统会根据用户情绪自动调整 TTS 参数：

| 情绪 | Edge TTS 效果 | CosyVoice 效果 |
|------|-------------|----------------|
| happy | 语速 +10% | style: happy |
| sad | 语速 -10% | style: sad |
| anxious | 语速 +5% | style: gentle |
| angry | 正常 | style: serious |

### 3.5 流式 TTS

支持两种模式：

- **HTTP 整段模式**（默认）：合成完整音频后返回
- **WebSocket 流式模式**：边合成边推送，降低首字延迟

在设置中开启"流式 TTS"即可使用 WebSocket 模式。

---

## 四、VAD 语音活动检测

### 4.1 前端 VAD

基于 Web Audio API 的 RMS 能量检测：

- 采样率：16kHz
- 阈值：0.015（可在设置中调整）
- 静音判定：1500ms

### 4.2 后端 VAD

基于 Silero VAD ONNX 模型：

- 模型：`models/snakers4_silero-vad/silero_vad.onnx`
- 阈值：0.5
- 最短语音：250ms
- 静音判定：200ms

### 4.3 连续对话模式

1. 点击设置 → 语音 Tab
2. VAD 模式选择"连续对话"
3. 系统自动检测说话 → ASR → LLM → TTS → 继续监听

---

## 五、意图打断 (Barge-in)

### 5.1 工作原理

```
TTS 正在播放
    → 用户开始说话
    → VAD 检测到语音
    → AudioManager.onBargeIn()
    → 停止 TTS 播放
    → 开始新的 ASR 识别
```

### 5.2 使用条件

- 需要在"连续对话"模式下
- 前端通过 AudioManager 单例管理音频

---

## 六、WebSocket 语音对话

### 6.1 连接

```javascript
const ws = new WebSocket('ws://host:8000/ws/chat')
```

### 6.2 发送文本

```javascript
ws.send(JSON.stringify({
  type: 'text',
  query: '广东物理600分能上什么',
  session_id: 'my-session',
  role: 'student'
}))
```

### 6.3 发送音频流

```javascript
// 开始音频流
ws.send(JSON.stringify({ type: 'audio_start', session_id: 'my-session' }))

// 发送 PCM chunks
ws.send(pcmChunk)  // binary

// 结束音频流
ws.send(JSON.stringify({ type: 'audio_end' }))
```

### 6.4 接收响应

```javascript
ws.onmessage = (evt) => {
  const msg = JSON.parse(evt.data)
  switch (msg.type) {
    case 'status':  // 状态消息
    case 'token':   // LLM 回复片段
    case 'asr_result': // ASR 识别结果
    case 'profile_update': // 画像更新
    case 'meta':    // 元信息
    case 'done':    // 完成
  }
}
```

---

## 七、API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/voice/asr` | 语音识别 |
| POST | `/voice/tts` | 语音合成（整段） |
| WS | `/voice/tts-stream` | 语音合成（流式） |
| WS | `/ws/chat` | 全双工对话 |
| GET | `/voice/voices` | 可用音色列表 |
| GET | `/voice/status` | 语音模块状态 |
