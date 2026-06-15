export default {
  name: 'AppLayout',
  template: `
    <div style="display:flex;flex-direction:column;height:100vh;overflow:hidden">
      <header class="header">
        <div class="brand">
          <div class="icon">🎓</div>
          <span>小乐AI · 高考志愿填报助手</span>
        </div>
        <div class="nav-buttons">
          <button 
            class="nav-btn" 
            :class="{ active: currentView === 'chat' }"
            @click="currentView = 'chat'"
          >
            <i class="fas fa-comments"></i> 对话
          </button>
          <button 
            class="nav-btn" 
            :class="{ active: currentView === 'ranking' }"
            @click="currentView = 'ranking'"
          >
            <i class="fas fa-trophy"></i> 院校排名
          </button>
          <button 
            class="nav-btn" 
            :class="{ active: currentView === 'graph' }"
            @click="currentView = 'graph'"
          >
            <i class="fas fa-project-diagram"></i> 知识图谱
          </button>
        </div>
        <div class="role-switcher">
          <button 
            class="role-btn" 
            :class="{ active: conversationRole === 'student' }"
            @click="switchRole('student')"
          >
            <i class="fas fa-user-graduate"></i> 学生
          </button>
          <button 
            class="role-btn" 
            :class="{ active: conversationRole === 'parent' }"
            @click="switchRole('parent')"
          >
            <i class="fas fa-user-tie"></i> 家长
          </button>
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
          <button class="settings-trigger" @click="showSettings = true">
            <i class="fas fa-cog"></i> 设置
          </button>
        </div>
      </header>

      <!-- 设置抽屉 -->
      <settings-drawer
        :visible="showSettings"
        @close="showSettings = false"
        @save="onSettingsSave"
        @switch-theme="applyTheme"
        @switch-model="switchModel"
      ></settings-drawer>

      <div class="app-layout" style="flex:1;min-height:0">
        <!-- 对话视图 -->
        <template v-if="currentView === 'chat'">
          <chat-container 
            :messages="messages" 
            :is-sending="isSending"
            :current-emotion="currentEmotion"
            @send-message="sendMessage"
            @clear-chat="clearChat"
            @submit-feedback="submitFeedback"
          ></chat-container>
          
          <side-panel 
            :status="status"
            :profile="profile"
            :parent-profile="parentProfile"
            :family-context="familyContext"
            :subject-scores="subjectScores"
            :message-count="messages.length"
            @clear-chat="clearChat"
            @image-analysis="onImageAnalysis"
          ></side-panel>
        </template>

        <!-- 院校排名视图 -->
        <template v-else-if="currentView === 'ranking'">
          <university-ranking style="flex:1;overflow:auto;padding:20px"></university-ranking>
        </template>

        <!-- 知识图谱视图 -->
        <template v-else-if="currentView === 'graph'">
          <knowledge-graph style="flex:1;overflow:auto;padding:20px"></knowledge-graph>
        </template>
      </div>
    </div>
  `,
  data() {
    return {
      messages: [],
      isSending: false,
      profile: {},
      parentProfile: {},
      familyContext: {},
      subjectScores: {},
      currentEmotion: { label: 'neutral', intensity: 0.5 },
      status: {
        graph_ready: false,
        db_ready: false,
        redis_ready: false,
        vector_ready: false,
        rag_index_exists: false,
        uptime_seconds: 0
      },
      sessionId: this.generateSessionId(),
      conversationRole: 'student',
      showSettings: false,
      currentView: 'chat'
    }
  },
  methods: {
    generateSessionId() {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    switchRole(role) {
      this.conversationRole = role;
      this.clearChat();
    },

    applyTheme(themeId) {
      document.documentElement.dataset.theme = themeId;
      localStorage.setItem('xiaole_theme', themeId);
    },

    async switchModel(preset) {
      try {
        const resp = await fetch(window.API_BASE + '/settings/switch-model', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ preset })
        });
        if (resp.ok) {
          console.log('模型已切换到:', preset);
        }
      } catch (e) {
        console.warn('切换模型失败:', e);
      }
    },

    onSettingsSave(settings) {
      if (settings.theme) this.applyTheme(settings.theme);
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
        isLoading: true,
        turnId: null
      });
      
      try {
        const response = await fetch(window.API_BASE + '/stream/advice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            query: query,
            session_id: this.sessionId,
            conversation_role: this.conversationRole
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
              if (data.type === 'profile_update' && data.parent_profile) {
                this.parentProfile = data.parent_profile;
              }
              if (data.type === 'profile_update' && data.family_context) {
                this.familyContext = data.family_context;
              }
              if (data.type === 'profile_update' && data.subject_scores) {
                this.subjectScores = data.subject_scores;
              }
              if (data.type === 'profile_update' && data.emotion) {
                this.currentEmotion = data.emotion;
              }

              if (data.type === 'meta') {
                if (data.session_id) {
                  this.sessionId = data.session_id;
                }
                if (data.turn_id) {
                  this.lastAssistantMsg().turnId = data.turn_id;
                }
              }
            } catch (e) {
              // JSON 解析失败时不暴露原始数据到用户界面
              console.warn('SSE payload parse error:', e, payload);
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
      this.parentProfile = {};
      this.familyContext = {};
      this.subjectScores = {};
      this.currentEmotion = { label: 'neutral', intensity: 0.5 };
      this.sessionId = this.generateSessionId();
    },

    async submitFeedback(payload) {
      if (!payload.turnId) return;
      try {
        await fetch(window.API_BASE + '/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            turn_id: payload.turnId,
            rating: payload.rating,
            tags: payload.tags || [],
            comment: payload.comment || ''
          })
        });
      } catch (error) {
        console.error('Feedback submit failed:', error);
      }
    },

    onImageAnalysis(data) {
      // 将图片分析结果添加为助手消息
      this.messages.push({
        id: Date.now(),
        role: 'assistant',
        content: `📷 **图片分析** (${data.model})\n\n${data.result}`,
        timestamp: new Date(),
        isLoading: false,
        turnId: null
      });
    }
  },
  
  mounted() {
    this.refreshStatus();
    this._statusInterval = setInterval(() => this.refreshStatus(), 30000);
    // 初始化主题
    const savedTheme = localStorage.getItem('xiaole_theme') || 'blue';
    this.applyTheme(savedTheme);
  },

  beforeUnmount() {
    if (this._statusInterval) {
      clearInterval(this._statusInterval);
      this._statusInterval = null;
    }
  }
}