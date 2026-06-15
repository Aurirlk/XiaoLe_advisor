import AudioManager from '../utils/AudioManager.js'

/**
 * VoiceInput - 语音录入组件
 * 支持两种模式：
 * 1. 按住说话（默认，无需 VAD 模型）
 * 2. 点击录音 + VAD 自动端点检测（需要 Silero VAD ONNX 模型）
 */
export default {
  name: 'VoiceInput',
  emits: ['voice-result', 'barge-in'],
  data() {
    return {
      isRecording: false,
      isProcessing: false,
      isListening: false,
      mediaRecorder: null,
      audioChunks: [],
      recordingTime: 0,
      timer: null,
      error: '',
      continuousMode: false,
      audioContext: null,
      analyser: null,
      silenceStart: 0,
      vadThreshold: 0.015,
      silenceDuration: 1500,
      animFrame: null,
    }
  },
  template: `
    <div class="voice-input">
      <button
        class="voice-btn"
        :class="{
          recording: isRecording,
          processing: isProcessing,
          listening: isListening,
          continuous: continuousMode
        }"
        @click="handleClick"
        @mousedown="startHoldRecording"
        @mouseup="stopHoldRecording"
        @mouseleave="stopHoldRecording"
        @touchstart.prevent="startHoldRecording"
        @touchend.prevent="stopHoldRecording"
        :disabled="isProcessing"
        :title="buttonTitle"
      >
        <i :class="iconClass"></i>
      </button>
      <span v-if="isRecording" class="voice-timer">{{ formatTime(recordingTime) }}</span>
      <span v-if="isListening" class="voice-listening">聆听中...</span>
      <span v-if="error" class="voice-error">{{ error }}</span>
    </div>
  `,
  computed: {
    iconClass() {
      if (this.isProcessing) return 'fas fa-spinner fa-spin'
      if (this.isRecording || this.isListening) return 'fas fa-stop'
      return 'fas fa-microphone'
    },
    buttonTitle() {
      if (this.continuousMode) return '点击停止连续对话'
      if (this.isRecording) return '松开结束录音'
      return '点击录音（或按住说话）'
    }
  },
  methods: {
    handleClick(e) {
      if (e.detail > 1) return
      if (this.continuousMode) {
        this.stopContinuousMode()
        return
      }
      if (this.isHoldActive) return
      this.toggleRecording()
    },

    startHoldRecording(e) {
      if (this.continuousMode) return
      this.isHoldActive = true
      this.holdTimer = setTimeout(() => {
        if (this.isHoldActive && !this.isRecording && !this.isProcessing) {
          this.startRecording()
        }
      }, 200)
    },

    stopHoldRecording() {
      if (this.continuousMode) return
      clearTimeout(this.holdTimer)
      if (this.isHoldActive && this.isRecording) {
        this.stopRecording()
      }
      setTimeout(() => { this.isHoldActive = false }, 50)
    },

    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording()
      } else {
        await this.startRecording()
      }
    },

    async startRecording() {
      if (this.isRecording || this.isProcessing) return
      this.error = ''
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        })
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
        this.mediaRecorder = new MediaRecorder(stream, { mimeType })
        this.audioChunks = []
        this.mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) this.audioChunks.push(e.data) }
        this.mediaRecorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop())
          this.processAudio()
        }
        this.mediaRecorder.start()
        this.isRecording = true
        this.recordingTime = 0
        this.timer = setInterval(() => { this.recordingTime++ }, 1000)

        if (this.continuousMode) {
          this.initVAD(stream)
        }
        setTimeout(() => { if (this.isRecording) this.stopRecording() }, 60000)
      } catch (err) {
        this.handleMediaError(err)
      }
    },

    stopRecording() {
      if (!this.isRecording) return
      this.isRecording = false
      clearInterval(this.timer)
      this.stopVAD()
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop()
      }
    },

    initVAD(stream) {
      try {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
        const source = this.audioContext.createMediaStreamSource(stream)
        this.analyser = this.audioContext.createAnalyser()
        this.analyser.fftSize = 2048
        source.connect(this.analyser)
        this.silenceStart = Date.now()
        this.monitorVAD()
      } catch (e) {
        console.warn('VAD init failed:', e)
      }
    },

    monitorVAD() {
      if (!this.isRecording || !this.analyser) return
      const data = new Float32Array(this.analyser.fftSize)
      this.analyser.getFloatTimeDomainData(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i]
      const rms = Math.sqrt(sum / data.length)
      if (rms < this.vadThreshold) {
        if (Date.now() - this.silenceStart > this.silenceDuration) {
          this.stopRecording()
          return
        }
      } else {
        this.silenceStart = Date.now()
      }
      this.animFrame = requestAnimationFrame(() => this.monitorVAD())
    },

    stopVAD() {
      if (this.animFrame) cancelAnimationFrame(this.animFrame)
      if (this.audioContext && this.audioContext.state !== 'closed') {
        this.audioContext.close().catch(() => {})
      }
      this.audioContext = null
      this.analyser = null
    },

    async startContinuousMode() {
      this.continuousMode = true
      const audioManager = AudioManager.getInstance()
      audioManager.registerBargeInCallback(() => {
        if (!this.isRecording) this.startRecording()
      })
      await this.startRecording()
    },

    stopContinuousMode() {
      this.continuousMode = false
      this.stopRecording()
      AudioManager.getInstance().unregisterBargeInCallback()
    },

    async processAudio() {
      if (this.audioChunks.length === 0) return
      this.isProcessing = true
      try {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('audio', blob, 'recording.webm')
        const resp = await fetch(window.API_BASE + '/voice/asr', { method: 'POST', body: formData })
        if (!resp.ok) throw new Error('ASR 请求失败 ' + resp.status)
        const data = await resp.json()
        if (data.ok && data.text) {
          this.$emit('voice-result', data.text)
        } else {
          this.error = data.detail || '未识别到语音内容'
        }
      } catch (err) {
        this.error = '语音识别失败: ' + err.message
      } finally {
        this.isProcessing = false
        this.recordingTime = 0
        if (this.continuousMode && !this.isRecording) {
          setTimeout(() => { if (this.continuousMode) this.startRecording() }, 500)
        }
      }
    },

    handleMediaError(err) {
      if (err.name === 'NotAllowedError') this.error = '请允许麦克风权限'
      else if (err.name === 'NotFoundError') this.error = '未检测到麦克风'
      else this.error = '录音失败: ' + err.message
    },

    formatTime(sec) {
      const m = Math.floor(sec / 60)
      const s = sec % 60
      return `${m}:${String(s).padStart(2, '0')}`
    }
  },

  beforeUnmount() {
    clearInterval(this.timer)
    this.stopVAD()
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop()
    }
    if (this.continuousMode) AudioManager.getInstance().unregisterBargeInCallback()
  }
}
