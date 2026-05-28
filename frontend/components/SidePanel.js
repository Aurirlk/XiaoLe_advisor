export default {
  name: 'SidePanel',
  props: {
    status: {
      type: Object,
      default: () => ({})
    },
    profile: {
      type: Object,
      default: () => ({})
    },
    messageCount: {
      type: Number,
      default: 0
    }
  },
  emits: ['clear-chat'],
  template: `
    <aside class="side-panel">
      <!-- Service Status -->
      <div class="section">
        <h4><i class="fas fa-chart-line"></i> 服务状态</h4>
        <div class="status-grid">
          <div class="status-row">
            <div class="status-info">
              <div class="status-icon" :class="status.graph_ready ? 'green' : 'red'">
                <i class="fas fa-project-diagram"></i>
              </div>
              <span>Graph 引擎</span>
            </div>
            <span class="ind" :class="status.graph_ready ? 'green' : 'red'"></span>
          </div>
          
          <div class="status-row">
            <div class="status-info">
              <div class="status-icon" :class="status.db_ready ? 'green' : 'red'">
                <i class="fas fa-database"></i>
              </div>
              <span>数据库</span>
            </div>
            <span class="ind" :class="status.db_ready ? 'green' : 'red'"></span>
          </div>
          
          <div class="status-row">
            <div class="status-info">
              <div class="status-icon" :class="status.redis_ready ? 'green' : 'red'">
                <i class="fas fa-server"></i>
              </div>
              <span>Redis</span>
            </div>
            <span class="ind" :class="status.redis_ready ? 'green' : 'red'"></span>
          </div>
          
          <div class="status-row">
            <div class="status-info">
              <div class="status-icon" :class="status.vector_ready ? 'green' : 'red'">
                <i class="fas fa-cube"></i>
              </div>
              <span>向量库</span>
            </div>
            <span class="ind" :class="status.vector_ready ? 'green' : 'red'"></span>
          </div>
          
          <div class="status-row">
            <div class="status-info">
              <div class="status-icon" :class="status.rag_index_exists ? 'green' : 'red'">
                <i class="fas fa-search"></i>
              </div>
              <span>RAG 索引</span>
            </div>
            <span class="ind" :class="status.rag_index_exists ? 'green' : 'red'"></span>
          </div>
        </div>
        
        <div style="margin-top: 12px; font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
          <i class="fas fa-clock"></i>
          运行时间: {{ formatUptime(status.uptime_seconds) }}
        </div>
      </div>

      <!-- User Profile -->
      <div class="section">
        <h4><i class="fas fa-user-circle"></i> 用户画像</h4>
        <profile-card :profile="profile"></profile-card>
      </div>

      <!-- Session Info -->
      <div class="section">
        <h4><i class="fas fa-comments"></i> 会话</h4>
        <div class="session-counter">
          已交换 <strong>{{ messageCount }}</strong> 条消息
        </div>
        <button class="reset-btn" @click="$emit('clear-chat')">
          <i class="fas fa-trash-alt"></i>
          清空对话
        </button>
      </div>

      <!-- Tips -->
      <div class="section">
        <div class="tip-box">
          <strong><i class="fas fa-lightbulb"></i> 提示：</strong>
          <span>提供省份、选科、分数/位次、目标专业，可获得更精准的报考建议。</span>
        </div>
      </div>
    </aside>
  `,
  methods: {
    formatUptime(seconds) {
      if (!seconds) return '刚刚启动';
      const mins = Math.floor(seconds / 60);
      if (mins < 1) return '刚刚启动';
      if (mins < 60) return `${mins}分钟`;
      const hours = Math.floor(mins / 60);
      const remainingMins = mins % 60;
      return `${hours}小时${remainingMins}分钟`;
    }
  }
}