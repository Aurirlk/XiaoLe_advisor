import AudioManager from '../utils/AudioManager.js'

/**
 * VoiceOutput - 语音播放组件
 * 支持两种模式：
 * 1. HTTP 整段模式（默认）
 * 2. WebSocket 流式模式（settings.streaming_tts 启用时）
 */
export default {
  name: 'VoiceOutput',
  props: {
    text: { type: String, default: '' },
    autoPlay: { type: Boolean, default: true },
    emotion: { type: String, default: '' },
    emotionIntensity: { type: Number, default: 0.5 }
  },
  data() {
    return {
      isPlaying: false,
      isLoading: false,
      audioUrl: null,
      audio: null,
      error: ''
    }
  },
  template: `
    <div class="voice-output" v-if="text">
      <button
        class="tts-btn"
        :class="{ playing: isPlaying, loading: isLoading }"
        @click="togglePlay"
        :disabled="isLoading"
        :title="isPlaying ? '停止播放' : '朗读回复'"
      >
        <i :class="iconClass"></i>
      </button>
      <div v-if="isPlaying" class="audio-wave">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
      <span v-if="error" class="voice-error">{{ error }}</span>
    </div>
  `,
  computed: {
    iconClass() {
      if (this.isLoading) return 'fas fa-spinner fa-spin'
      if (this.isPlaying) return 'fas fa-stop'
      return 'fas fa-volume-up'
    },
    useStreaming() {
      try {
        const s = JSON.parse(localStorage.getItem('xiaole_settings') || '{}')
        return s.streaming_tts === true
      } catch { return false }
    }
  },
  watch: {
    text(newText) {
      if (newText && this.autoPlay) {
        this.$nextTick(() => this.speak())
      }
    }
  },
  methods: {
    async togglePlay() {
      if (this.isPlaying) {
        this.stop()
      } else {
        await this.speak()
      }
    },

    async speak() {
      if (!this.text || this.isLoading) return
      this.error = ''
      this.isLoading = true

      try {
        if (this.useStreaming) {
          await this.speakStream()
        } else {
          await this.speakHttp()
        }
      } catch (err) {
        this.error = '语音合成失败: ' + err.message
      } finally {
        this.isLoading = false
      }
    },

    async speakHttp() {
      const body = { text: this.text }
      if (this.emotion) {
        body.emotion = this.emotion
        body.emotion_intensity = this.emotionIntensity
      }
      const resp = await fetch(window.API_BASE + '/voice/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!resp.ok) throw new Error('HTTP ' + resp.status)
      const blob = await resp.blob()
      this.playBlob(blob)
    },

    async speakStream() {
      const wsUrl = (window.API_BASE || '').replace(/^http/, 'ws') + '/voice/tts-stream'
      const ws = new WebSocket(wsUrl)

      const chunks = []
      let done = false

      ws.onopen = () => {
        ws.send(JSON.stringify({
          text: this.text,
          emotion: this.emotion || '',
          emotion_intensity: this.emotionIntensity
        }))
      }

      ws.onmessage = (evt) => {
        if (evt.data instanceof Blob) {
          chunks.push(evt.data)
        } else {
          try {
            const msg = JSON.parse(evt.data)
            if (msg.type === 'done') {
              done = true
              ws.close()
              const blob = new Blob(chunks, { type: 'audio/mpeg' })
              this.playBlob(blob)
            } else if (msg.type === 'error') {
              this.error = msg.msg
              ws.close()
            }
          } catch {}
        }
      }

      ws.onerror = () => {
        this.error = 'WebSocket 连接失败'
        ws.close()
      }

      ws.onclose = () => {
        if (!done && chunks.length > 0) {
          const blob = new Blob(chunks, { type: 'audio/mpeg' })
          this.playBlob(blob)
        }
      }
    },

    playBlob(blob) {
      if (this.audioUrl) URL.revokeObjectURL(this.audioUrl)
      this.audioUrl = URL.createObjectURL(blob)
      this.audio = new Audio(this.audioUrl)
      this.audio.onended = () => { this.isPlaying = false }
      this.audio.onerror = () => {
        this.isPlaying = false
        this.error = '音频播放失败'
      }
      this.isPlaying = true
      this.audio.play()
    },

    stop() {
      if (this.audio) {
        this.audio.pause()
        this.audio.currentTime = 0
      }
      this.isPlaying = false
    }
  },

  beforeUnmount() {
    this.stop()
    if (this.audioUrl) URL.revokeObjectURL(this.audioUrl)
  }
}
