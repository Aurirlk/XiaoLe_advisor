export default {
  name: 'StatusIndicator',
  props: {
    status: {
      type: Object,
      required: true
    }
  },
  template: `
    <div class="status-indicator">
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
  `
}