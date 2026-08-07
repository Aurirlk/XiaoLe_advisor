<template>
  <div class="voice-input">
    <button class="voice-btn" :class="{ recording, unsupported: !supported }" @click="toggleRecord"
      :disabled="!supported" :title="supported ? (recording ? '点击停止录音' : '语音输入') : '浏览器不支持麦克风'">
      <i v-if="!supported" class="fas fa-microphone-slash"></i>
      <i v-else-if="recording" class="fas fa-microphone-alt"></i>
      <i v-else class="fas fa-microphone"></i>
    </button>
    <span v-if="recording" class="recording-hint">🎤 录音中...</span>
    <span v-if="error" class="error-hint">{{ error }}</span>
  </div>
</template>
<script>
export default {
  name: 'VoiceInput',
  emits: ['voice-result'],
  data() {
    return {
      recording: false,
      error: '',
      supported: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    }
  },
  methods: {
    async toggleRecord() {
      if (this.recording) { this.recording = false; this.error = ''; return }
      this.recording = true; this.error = ''
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav' })
        const chunks = []
        recorder.ondataavailable = e => chunks.push(e.data)
        recorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop())
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
          try {
            const fd = new FormData(); fd.append('audio', blob, 'recording.webm')
            const r = await fetch(`${window.API_BASE||''}/voice/asr`, { method:'POST', body:fd })
            if (r.ok) {
              const d = await r.json()
              this.$emit('voice-result', d.text || d.result || '')
            } else {
              this.error = '语音识别失败'
            }
          } catch { this.error = '网络错误' }
          this.recording = false
        }
        recorder.onerror = () => { this.error = '录音出错'; this.recording = false }
        recorder.start()
        // Auto-stop after 15 seconds
        setTimeout(() => { if (recorder.state === 'recording') { recorder.stop() } }, 15000)
      } catch (e) {
        if (e.name === 'NotAllowedError') {
          this.error = '麦克风权限被拒绝'
        } else if (e.name === 'NotFoundError') {
          this.error = '未找到麦克风设备'
        } else {
          this.error = '录音启动失败'
        }
        this.recording = false
      }
    }
  }
}
</script>
<style scoped>
.voice-input {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.voice-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid var(--primary-light, #2d5a8e);
  background: var(--bg-light, #f8fafc);
  color: var(--primary, #1e3a5f);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}
.voice-btn:hover:not(:disabled) {
  background: var(--primary, #1e3a5f);
  color: #fff;
  transform: scale(1.05);
}
.voice-btn.recording {
  border-color: var(--danger, #e74c3c);
  color: var(--danger, #e74c3c);
  background: rgba(231,76,60,.08);
  animation: pulse 1.5s infinite;
}
.voice-btn.unsupported {
  border-color: var(--border, #e2e8f0);
  color: var(--text-light, #a0aec0);
  opacity: 0.5;
  cursor: not-allowed;
}
.recording-hint {
  font-size: 12px;
  color: var(--danger, #e74c3c);
  white-space: nowrap;
  animation: blink 1s infinite;
}
.error-hint {
  font-size: 11px;
  color: var(--text-muted, #718096);
  white-space: nowrap;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(231,76,60,.4); }
  50% { box-shadow: 0 0 0 10px rgba(231,76,60,0); }
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
