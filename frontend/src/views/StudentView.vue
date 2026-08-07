<template>
  <div style="display:flex;flex:1;overflow:hidden">
    <chat-container :messages="messages" :is-sending="sending"
      @send-message="send" @clear-chat="messages=[]" style="flex:1" />
    <side-panel :status="status" :user="user" :messages="messages" />
  </div>
</template>

<script>
import ChatContainer from '../components/ChatContainer.vue'
import SidePanel from '../components/SidePanel.vue'

export default {
  name: 'StudentView',
  components: { ChatContainer, SidePanel },
  data() {
    return { sending: false, user: {}, messages: [], status: { graph_ready: false, db_ready: false, redis_ready: false, vector_ready: false, rag_index_exists: true } }
  },
  methods: {
    send(q) {
      if (!q.trim() || this.sending) return
      this.messages.push({ id: Date.now(), role: 'user', content: q, timestamp: new Date() })
      this.sending = true
      ;(async () => {
        try {
          const r = await fetch(`${window.API_BASE || ''}/stream/advice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` },
            body: JSON.stringify({ query: q, domain: localStorage.getItem('xiaole_domain') || 'gaokao' })
          })
          if (!r.ok) throw Error('请求失败')
          const m = { id: Date.now() + 1, role: 'assistant', content: '', timestamp: new Date() }
          this.messages.push(m)
          const rd = r.body.getReader(); const d = new TextDecoder()
          while (true) {
            const { done, v } = await rd.read(); if (done) break
            for (const l of d.decode(v).split('\n')) {
              if (l.startsWith('data: ')) {
                try { const j = JSON.parse(l.slice(6)); if (j.type === 'token') m.content += j.msg } catch {}
              }
            }
          }
        } catch (e) {
          this.messages.push({ id: Date.now() + 2, role: 'assistant', content: '错误: ' + e.message, timestamp: new Date() })
        } finally { this.sending = false }
      })()
    },
    async refreshStatus() {
      try {
        const r = await fetch(`${window.API_BASE || ''}/status`)
        if (r.ok) this.status = await r.json()
      } catch {}
    }
  },
  mounted() {
    const u = localStorage.getItem('user_info'); if (u) try { this.user = JSON.parse(u) } catch {}
    this.refreshStatus(); setInterval(() => this.refreshStatus(), 30000)
  }
}
</script>
