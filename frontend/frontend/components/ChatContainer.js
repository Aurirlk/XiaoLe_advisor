export default {
  name: 'ChatContainer',
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    isSending: {
      type: Boolean,
      default: false
    }
  },
  emits: ['send-message', 'clear-chat', 'submit-feedback'],
  template: `
    <div class="main-area">
      <div class="chat-container" ref="chatContainer">
        <!-- Welcome Screen -->
        <div class="chat-welcome" v-if="messages.length === 0">
          <div class="big-icon">📚</div>
          <h2>你好，我是张雪峰风格的报考顾问</h2>
          <p>基于十万级录取数据 + AI 智能分析，为你提供个性化志愿填报建议</p>
          <quick-chips @send-query="handleQuickQuery"></quick-chips>
        </div>
        
        <!-- Messages -->
        <template v-else>
          <message-bubble 
            v-for="msg in messages" 
            :key="msg.id" 
            :message="msg"
            @submit-feedback="$emit('submit-feedback', $event)"
          ></message-bubble>
        </template>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-wrapper">
          <textarea 
            ref="inputTextarea"
            v-model="inputQuery"
            @keydown.enter.exact.prevent="sendMessage"
            @input="autoResize"
            placeholder="输入你的问题，如：广东省物理类580分，想去江浙沪读计算机..."
            rows="1"
            :disabled="isSending"
          ></textarea>
        </div>
        <button 
          class="send-btn" 
          @click="sendMessage"
          :disabled="isSending || !inputQuery.trim()"
        >
          <i :class="isSending ? 'fas fa-spinner fa-spin' : 'fas fa-paper-plane'"></i>
          <span>{{ isSending ? '分析中...' : '发送' }}</span>
        </button>
      </div>
    </div>
  `,
  data() {
    return {
      inputQuery: ''
    }
  },
  methods: {
    sendMessage() {
      if (!this.inputQuery.trim() || this.isSending) return;
      this.$emit('send-message', this.inputQuery);
      this.inputQuery = '';
      this.autoResize();
    },
    
    handleQuickQuery(query) {
      this.inputQuery = query;
      this.sendMessage();
    },
    
    autoResize() {
      const textarea = this.$refs.inputTextarea;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
      }
    },
    
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.chatContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  },
  
  watch: {
    messages: {
      handler() {
        this.scrollToBottom();
      },
      deep: true
    }
  },
  
  mounted() {
    this.scrollToBottom();
  }
}