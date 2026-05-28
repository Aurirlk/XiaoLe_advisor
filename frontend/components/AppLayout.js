export default {
  name: 'AppLayout',
  template: `
    <div style="display:flex;flex-direction:column;height:100vh;overflow:hidden">
      <header class="header">
        <div class="brand">
          <div class="icon">🎓</div>
          <span>ZX AI Advisor</span>
        </div>
        <div class="service-dots" id="service-dots">
          <span class="dot" :class="{ off: !status.graph_ready }">
            <i class="fas fa-project-diagram"></i> Graph
          </span>
          <span class="dot" :class="{ off: !status.db_ready }">
            <i class="fas fa-database"></i> DB
          </span>
          <span class="dot" :class="{ off: !status.redis_ready }">
            <i class="fas fa-server"></i> Redis
          </span>
          <span class="dot" :class="{ off: !status.vector_ready }">
            <i class="fas fa-cube"></i> Vector
          </span>
        </div>
      </header>

      <div class="app-layout" style="flex:1;min-height:0">
        <chat-container 
          :messages="messages" 
          :is-sending="isSending"
          @send-message="sendMessage"
          @clear-chat="clearChat"
        ></chat-container>
        
        <side-panel 
          :status="status"
          :profile="profile"
          :message-count="messages.length"
          @clear-chat="clearChat"
        ></side-panel>
      </div>
    </div>
  `,
  data() {
    return {
      messages: [],
      isSending: false,
      profile: {},
      status: {
        graph_ready: false,
        db_ready: false,
        redis_ready: false,
        vector_ready: false,
        rag_index_exists: false,
        uptime_seconds: 0
      },
      sessionId: this.generateSessionId()
    }
  },
  methods: {
    generateSessionId() {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },
    
    lastAssistantMsg() {
      const msgs = this.messages;
      return msgs[msgs.length - 1];
    },
    
    async refreshStatus() {
      try {
        const response = await fetch(window.API_BASE + '/status');
        const data = await response.json();
        this.status = data;
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    },
    
    async sendMessage(query) {
      if (!query.trim() || this.isSending) return;
      
      this.isSending = true;
      
      // 添加用户消息
      this.messages.push({
        id: Date.now(),
        role: 'user',
        content: query,
        timestamp: new Date()
      });
      
      // 添加助手消息占位
      this.messages.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        status: '',
        timestamp: new Date(),
        isLoading: true
      });
      
      try {
        const response = await fetch(window.API_BASE + '/stream/advice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            query: query,
            session_id: this.sessionId
          })
        });
        
        if (!response.ok || !response.body) {
          this.lastAssistantMsg().content = `请求失败 (HTTP ${response.status})，请确认后端服务已启动。`;
          this.lastAssistantMsg().isLoading = false;
          return;
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          buffer = buffer.replace(/\r\n/g, '\n');
          const blocks = buffer.split('\n\n');
          buffer = blocks.pop() || '';
          
          for (const block of blocks) {
            const payload = this.tryParseSSE(block);
            if (!payload) continue;
            
            try {
              const data = JSON.parse(payload);
              
              if (data.type === 'token') {
                this.lastAssistantMsg().content += data.msg;
              }
              
              if (data.type === 'status') {
                this.lastAssistantMsg().status = data.msg;
              }
              
              if (data.type === 'profile_update' && data.profile) {
                this.profile = data.profile;
              }
            } catch (e) {
              this.lastAssistantMsg().content += payload;
            }
          }
        }
        
        if (buffer.trim()) {
          const payload = this.tryParseSSE(buffer);
          if (payload) {
            try {
              const data = JSON.parse(payload);
              if (data.type === 'token') {
                this.lastAssistantMsg().content += data.msg;
              }
            } catch (e) {}
          }
        }
        
      } catch (error) {
        this.lastAssistantMsg().content = `连接异常: ${error.message}`;
      } finally {
        this.lastAssistantMsg().isLoading = false;
        this.isSending = false;
        this.refreshStatus();
      }
    },
    
    tryParseSSE(block) {
      const lines = block.split('\n');
      for (const line of lines) {
        if (line.startsWith('data:')) {
          return line.slice(5).trim();
        }
      }
      return null;
    },
    
    clearChat() {
      this.messages = [];
      this.profile = {};
      this.sessionId = this.generateSessionId();
    }
  },
  
  mounted() {
    this.refreshStatus();
    // 每30秒刷新状态
    setInterval(() => this.refreshStatus(), 30000);
  }
}