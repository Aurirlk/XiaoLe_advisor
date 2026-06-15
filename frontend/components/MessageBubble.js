export default {
  name: 'MessageBubble',
  props: {
    message: {
      type: Object,
      required: true
    },
    currentEmotion: {
      type: Object,
      default: () => ({ label: 'neutral', intensity: 0.5 })
    }
  },
  emits: ['submit-feedback'],
  data() {
    return {
      showTagPicker: false,
      selectedTags: [],
      comment: '',
      feedbackSubmitted: false,
      feedbackTags: ['数据不准', '建议没用', '太端水', '没回答我的问题', '路由错了']
    };
  },
  template: `
    <div class="msg-row" :class="message.role">
      <div class="msg-avatar">
        <i :class="message.role === 'user' ? 'fas fa-user' : 'fas fa-graduation-cap'"></i>
      </div>
      <div class="msg-content">
        <div class="msg-bubble">
          <div v-if="message.isLoading" class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <template v-else>
            <div v-html="renderContent(message.content)"></div>
            <voice-output
              v-if="message.role === 'assistant' && message.content && !message.isLoading"
              :text="message.content"
              :auto-play="false"
              :emotion="currentEmotion.label"
              :emotion-intensity="currentEmotion.intensity"
            ></voice-output>
            <div v-if="message.status" class="status-tag">
              <i class="fas fa-cog fa-spin"></i>
              {{ message.status }}
            </div>
            <div
              v-if="message.role === 'assistant' && message.turnId && !message.isLoading"
              class="feedback-bar"
            >
              <button
                class="feedback-btn"
                :disabled="feedbackSubmitted"
                @click="submitPositive"
                title="有帮助"
              >
                <i class="fas fa-thumbs-up"></i>
              </button>
              <button
                class="feedback-btn"
                :disabled="feedbackSubmitted"
                @click="toggleNegative"
                title="没帮助"
              >
                <i class="fas fa-thumbs-down"></i>
              </button>
              <span v-if="feedbackSubmitted" class="feedback-done">已反馈</span>
            </div>
            <div v-if="showTagPicker && !feedbackSubmitted" class="feedback-tags">
              <label
                v-for="tag in feedbackTags"
                :key="tag"
                class="feedback-tag"
              >
                <input type="checkbox" :value="tag" v-model="selectedTags" />
                {{ tag }}
              </label>
              <input
                v-model="comment"
                class="feedback-comment"
                placeholder="可选备注..."
                maxlength="200"
              />
              <button class="feedback-submit" @click="submitNegative">提交反馈</button>
            </div>
          </template>
        </div>
        <div class="msg-time">
          <i class="far fa-clock"></i>
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
    </div>
  `,
  methods: {
    formatTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    renderContent(content) {
      if (!content) return '';
      // 先转义 HTML 实体，防止 XSS（必须在 markdown 转换之前）
      let html = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
      return html;
    },

    submitPositive() {
      if (this.feedbackSubmitted || !this.message.turnId) return;
      this.$emit('submit-feedback', {
        turnId: this.message.turnId,
        rating: 1,
        tags: [],
        comment: ''
      });
      this.feedbackSubmitted = true;
      this.showTagPicker = false;
    },

    toggleNegative() {
      if (this.feedbackSubmitted) return;
      this.showTagPicker = !this.showTagPicker;
    },

    submitNegative() {
      if (this.feedbackSubmitted || !this.message.turnId) return;
      this.$emit('submit-feedback', {
        turnId: this.message.turnId,
        rating: -1,
        tags: [...this.selectedTags],
        comment: this.comment.trim()
      });
      this.feedbackSubmitted = true;
      this.showTagPicker = false;
    }
  }
}
