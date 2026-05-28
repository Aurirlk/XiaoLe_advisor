export default {
  name: 'MessageBubble',
  props: {
    message: {
      type: Object,
      required: true
    }
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
            <div v-if="message.status" class="status-tag">
              <i class="fas fa-cog fa-spin"></i>
              {{ message.status }}
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
      // 简单的Markdown渲染
      let html = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
      return html;
    }
  }
}