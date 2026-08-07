<template>
  <div class="admin-view" style="display:flex;flex:1;overflow:hidden">
    <aside style="width:240px;background:var(--primary-dark,#152a45);color:#fff;display:flex;flex-direction:column;flex-shrink:0">
      <div style="padding:24px 20px;border-bottom:1px solid rgba(255,255,255,.1)"><h2 style="font-size:16px;margin:0">🎓 管理后台</h2></div>
      <nav style="flex:1;padding:12px 0">
        <a v-for="item in navItems" :key="item.key" @click="currentView=item.key" :style="{display:'flex',alignItems:'center',gap:'10px',padding:'12px 20px',color:currentView===item.key?'#fff':'rgba(255,255,255,.6)',fontSize:'14px',cursor:'pointer',borderLeft:currentView===item.key?'3px solid var(--gold,#f0a500)':'3px solid transparent',background:currentView===item.key?'rgba(255,255,255,.12)':'transparent'}">
          <i :class="item.icon"></i><span>{{ item.label }}</span>
        </a>
      </nav>
      <div style="padding:16px;border-top:1px solid rgba(255,255,255,.1)">
        <button @click="logout" style="width:100%;padding:10px;border:1px solid rgba(255,255,255,.2);background:transparent;color:rgba(255,255,255,.7);border-radius:8px;cursor:pointer;font-size:13px"><i class="fas fa-sign-out-alt"></i> 退出登录</button>
      </div>
    </aside>
    <main style="flex:1;background:var(--bg);display:flex;flex-direction:column">
      <header style="display:flex;justify-content:space-between;padding:16px 24px;background:var(--card);border-bottom:1px solid var(--border)">
        <h3 style="margin:0">{{ currentTitle }}</h3>
        <span style="color:var(--text-muted)">{{ userInfo?.username || '管理员' }}</span>
      </header>
      <div style="flex:1;overflow-y:auto;padding:24px">

        <!-- 系统监控 -->
        <div v-if="currentView==='status'" style="display:flex;flex-direction:column;gap:20px">
          <div class="stat-cards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px">
            <div v-for="s in statusList" :key="s.key" class="stat-card" :style="{background:'var(--card)',borderRadius:'12px',padding:'20px',boxShadow:'var(--shadow)',borderLeft:'4px solid '+(s.ok?'var(--success)':'var(--danger)')}">
              <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px"><i :class="s.icon"></i> {{ s.label }}</div>
              <div style="font-size:24px;font-weight:700" :style="{color:s.ok?'var(--success)':'var(--danger)'}">{{ s.ok ? '✅ 正常' : '❌ 异常' }}</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:4px">{{ s.detail }}</div>
            </div>
          </div>
        </div>

        <!-- 知识库管理 -->
        <div v-else-if="currentView==='knowledge'" class="panel-card" style="background:var(--card);border-radius:12px;padding:24px;box-shadow:var(--shadow)">
          <h4 style="margin:0 0 16px"><i class="fas fa-database"></i> 知识库索引</h4>
          <div v-if="loading" style="text-align:center;padding:20px;color:var(--text-muted)"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>
          <table v-else style="width:100%;border-collapse:collapse;font-size:14px">
            <tr v-for="k in knowledgeStats" :key="k.label" style="border-bottom:1px solid var(--border-light)">
              <td style="padding:12px 16px;color:var(--text-muted)">{{ k.label }}</td>
              <td style="padding:12px 16px;font-weight:600">{{ k.value }}</td>
            </tr>
          </table>
        </div>

        <!-- 数据同步 -->
        <div v-else-if="currentView==='sync'" class="panel-card" style="background:var(--card);border-radius:12px;padding:24px;box-shadow:var(--shadow)">
          <h4 style="margin:0 0 16px"><i class="fas fa-sync-alt"></i> 数据同步</h4>
          <p style="color:var(--text-muted);margin-bottom:20px">管理知识库索引重建、院校数据导入等操作。</p>
          <button @click="syncRag" :disabled="syncing" class="action-btn">{{ syncing ? '同步中...' : '🔄 重建 RAG 索引' }}</button>
          <div v-if="syncResult" :style="{marginTop:'12px',padding:'12px',borderRadius:'8px',background:syncResult.includes('成功')?'rgba(39,174,96,.08)':'rgba(231,76,60,.08)',color:syncResult.includes('成功')?'var(--success)':'var(--danger)',fontSize:'13px'}">{{ syncResult }}</div>
        </div>

        <!-- 数据统计 -->
        <div v-else-if="currentView==='stats'" class="panel-card" style="background:var(--card);border-radius:12px;padding:24px;box-shadow:var(--shadow)">
          <h4 style="margin:0 0 16px"><i class="fas fa-chart-bar"></i> 数据统计</h4>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px">
            <div v-for="st in statsData" :key="st.label" style="text-align:center;padding:24px;background:var(--bg);border-radius:12px">
              <div style="font-size:28px;font-weight:700;color:var(--primary)">{{ st.value }}</div>
              <div style="font-size:13px;color:var(--text-muted);margin-top:8px">{{ st.label }}</div>
            </div>
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script>
import apiClient from '../utils/apiClient.js'

export default {
  name: 'AdminView',
  data() {
    return {
      currentView: 'status',
      userInfo: null,
      loading: false,
      syncing: false,
      syncResult: '',
      statusList: [
        { key: 'db', label: 'SQLite 数据库', icon: 'fas fa-database', ok: true, detail: '本地嵌入式数据库' },
        { key: 'rag', label: '向量数据库 (ChromaDB)', icon: 'fas fa-brain', ok: false, detail: 'RAG 语义检索' },
        { key: 'graph', label: '知识图谱 (Neo4j)', icon: 'fas fa-project-diagram', ok: false, detail: '院校-专业-职业图谱' },
        { key: 'redis', label: 'Redis 缓存', icon: 'fas fa-memory', ok: false, detail: '会话缓存服务' },
      ],
      knowledgeStats: [
        { label: '院校数据', value: '2,817 条' },
        { label: '专业数据', value: '883 条' },
        { label: 'RAG 文档', value: '1,998 条' },
        { label: '录取数据', value: '283,653 条' },
        { label: '用户画像', value: '—' },
      ],
      statsData: [
        { label: '注册用户', value: '—' },
        { label: '今日对话', value: '—' },
        { label: '院校收录', value: '2,817' },
        { label: '录取数据', value: '283,653' },
      ],
      navItems: [
        { key: 'status', label: '系统监控', icon: 'fas fa-heartbeat' },
        { key: 'knowledge', label: '知识库管理', icon: 'fas fa-database' },
        { key: 'sync', label: '数据同步', icon: 'fas fa-sync-alt' },
        { key: 'stats', label: '数据统计', icon: 'fas fa-chart-bar' },
      ]
    }
  },
  computed: {
    currentTitle() {
      return this.navItems.find(i => i.key === this.currentView)?.label || ''
    }
  },
  methods: {
    logout() {
      apiClient.removeToken()
      this.$router.push('/login')
    },
    async fetchStatus() {
      try {
        const r = await fetch(`${window.API_BASE||''}/status`)
        if (r.ok) {
          const d = await r.json()
          this.statusList = this.statusList.map(s => ({
            ...s,
            ok: d[s.key + '_ready'] ?? s.ok,
            detail: d[s.key + '_ready'] ? '运行中' : (d[s.key + '_error'] || '未启动')
          }))
        }
      } catch {}
    },
    async syncRag() {
      this.syncing = true; this.syncResult = ''
      try {
        const r = await fetch(`${window.API_BASE||''}/api/admin/rebuild_rag`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
        })
        const d = await r.json()
        this.syncResult = d.ok ? '✅ RAG 索引重建成功' : '❌ 重建失败: ' + (d.error || '')
      } catch (e) {
        this.syncResult = '❌ 请求失败: ' + e.message
      } finally { this.syncing = false }
    }
  },
  mounted() {
    this.userInfo = apiClient.getUserInfo()
    if (!this.userInfo) { this.$router.push('/login'); return }
    this.fetchStatus()
  }
}
</script>

<style scoped>
.action-btn {
  padding: 12px 24px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--btn-primary-bg);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}
.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.panel-card h4 {
  font-size: 16px;
  color: var(--text);
}
</style>
