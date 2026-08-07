<template>
  <div class="main-area">
    <div class="chat-container" ref="chatContainer">
      <div class="chat-welcome" v-if="messages.length === 0">
        <div class="big-icon">🎓</div>
        <h2>你好，我是张雪峰风格的报考顾问</h2>
        <p>基于十万级录取数据 + AI 智能分析，为你提供个性化志愿填报建议</p>
        <quick-chips @send-query="handleQuickQuery"></quick-chips>
      </div>
      <template v-else>
        <message-bubble v-for="msg in messages" :key="msg.id" :message="msg"
          :current-emotion="currentEmotion" @submit-feedback="$emit('submit-feedback', $event)" />
      </template>
      <intent-indicator :scene="sceneType" :scene-confidence="sceneConfidence"
        :path="pathType" :path-confidence="pathConfidence" :decision="decisionState" />
      <progressive-questions :questions="progressiveQuestions" @answer="handleQuestionAnswer" />
      <fallback-card :response="fallbackResponse" :decision-state="decisionState"
        @accept="handleFallbackAccept" @dismiss="handleFallbackDismiss" />
      <recommendation-reason :reasons="recommendationReasons" />
      <div v-if="showUploader" class="upload-prompt">
        <div class="upload-prompt-header">
          <span>📤 上传数据</span>
          <button class="close-btn" @click="showUploader = false">✕</button>
        </div>
        <file-uploader :scenario="uploadScenario" :province="uploadProvince"
          :year="uploadYear" :subject-type="uploadSubjectType"
          @upload-success="handleUploadSuccess" @upload-error="handleUploadError" />
      </div>
    </div>
    <div class="input-area">
      <voice-input @voice-result="handleVoiceResult" />
      <button class="upload-btn" @click="showUploader = !showUploader" title="上传数据">
        <i class="fas fa-upload"></i>
      </button>
      <div class="input-wrapper">
        <textarea ref="inputTextarea" v-model="inputQuery"
          @keydown.enter.exact.prevent="sendMessage" @input="autoResize"
          placeholder="输入你的问题，如：广东省物理类580分，想去江浙沪读计算机..."
          rows="1" :disabled="isSending" />
      </div>
      <button class="send-btn" @click="sendMessage" :disabled="isSending || !inputQuery.trim()">
        <i :class="isSending ? 'fas fa-spinner fa-spin' : 'fas fa-paper-plane'" />
        <span>{{ isSending ? '分析中...' : '发送' }}</span>
      </button>
    </div>
  </div>
</template>

<script>
import MessageBubble from './MessageBubble.vue'
import QuickChips from './QuickChips.vue'
import IntentIndicator from './IntentIndicator.vue'
import ProgressiveQuestions from './ProgressiveQuestions.vue'
import FallbackCard from './FallbackCard.vue'
import RecommendationReason from './RecommendationReason.vue'
import FileUploader from './FileUploader.vue'
import VoiceInput from './VoiceInput.vue'

export default {
  name: 'ChatContainer',
  components: { MessageBubble, QuickChips, IntentIndicator, ProgressiveQuestions, FallbackCard, RecommendationReason, FileUploader, VoiceInput },
  props: {
    messages: { type: Array, default: () => [] },
    isSending: { type: Boolean, default: false },
    currentEmotion: { type: Object, default: () => ({ label: 'neutral', intensity: 0.5 }) }
  },
  emits: ['send-message', 'clear-chat', 'submit-feedback'],
  data() {
    return {
      inputQuery: '', showUploader: false,
      uploadScenario: 'generic', uploadProvince: '', uploadYear: 2025, uploadSubjectType: '',
      sceneType: '', sceneConfidence: 0, pathType: '', pathConfidence: 0,
      decisionState: 'firm', progressiveQuestions: [], fallbackResponse: '', recommendationReasons: [],
    }
  },
  methods: {
    sendMessage() {
      if (!this.inputQuery.trim() || this.isSending) return
      this.$emit('send-message', this.inputQuery); this.inputQuery = ''; this.autoResize()
    },
    handleQuickQuery(q) { this.inputQuery = q; this.sendMessage() },
    handleVoiceResult(t) { this.inputQuery = t; this.sendMessage() },
    autoResize() {
      const ta = this.$refs.inputTextarea; if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 150) + 'px' }
    },
    scrollToBottom() {
      this.$nextTick(() => { const c = this.$refs.chatContainer; if (c) c.scrollTop = c.scrollHeight })
    },
    handleUploadSuccess(d) {
      this.$emit('send-message', '已上传数据：' + (d.message || '') + '，共' + (d.parsed_count || 0) + '条记录。请分析。')
      this.showUploader = false
    },
    handleUploadError(d) { console.error('Upload error:', d) },
    handleQuestionAnswer(field, value) {
      this.$emit('send-message', value)
      this.progressiveQuestions = this.progressiveQuestions.filter(q => q.field !== field)
    },
    handleFallbackAccept() { this.fallbackResponse = '' },
    handleFallbackDismiss() { this.fallbackResponse = '' },
  },
  watch: { messages: { handler() { this.scrollToBottom() }, deep: true } },
  mounted() { this.scrollToBottom() }
}
</script>

<style scoped>
.main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; background: linear-gradient(180deg, var(--bg-light) 0%, var(--bg) 100%); }
.chat-container { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; scroll-behavior: smooth; }
.input-area { display: flex; align-items: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid var(--border); background: var(--card); }
.input-wrapper { flex: 1; position: relative; }
.input-wrapper textarea { width: 100%; padding: 12px 16px; border: 1px solid var(--border); border-radius: 12px; resize: none; font-size: 14px; outline: none; background: var(--bg-light); color: var(--text); font-family: inherit; }
.send-btn { padding: 12px 24px; background: var(--btn-primary-bg); color: #fff; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 14px; white-space: nowrap; }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-btn { width: 44px; height: 44px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-light); color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.upload-prompt { margin: 12px 0; padding: 16px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; }
.upload-prompt-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-weight: 600; }
.close-btn { background: none; border: none; cursor: pointer; font-size: 18px; color: var(--text-muted); }
</style>
