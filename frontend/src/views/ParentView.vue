<template>
  <div class="parent-view" style="display:flex;flex:1;overflow:hidden">
    <div class="main-area" style="flex:1;display:flex;flex-direction:column;background:var(--bg-light)">
      <div class="chat-container" style="flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:20px">
        <div v-if="messages.length === 0" class="chat-welcome" style="text-align:center;padding:60px 20px 40px">
          <h2>家长端 - 小乐AI</h2>
          <p style="color:var(--text-muted)">为家长提供专业的报考咨询和家庭调解建议</p>
        </div>
        <div v-for="msg in messages" :key="msg.id" class="msg-row" :class="msg.role">
          <div class="msg-avatar"><i :class="msg.role === 'user' ? 'fas fa-user' : 'fas fa-graduation-cap'"></i></div>
          <div class="msg-content">
            <div class="msg-bubble" v-html="renderContent(msg.content)"></div>
            <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>
      </div>
      <div class="input-area" style="display:flex;align-items:center;gap:12px;padding:16px 24px;border-top:1px solid var(--border);background:var(--card)">
        <textarea v-model="inputQuery" @keydown.enter.exact.prevent="sendMessage(inputQuery)"
          placeholder="输入你的问题..." rows="2"
          style="flex:1;padding:12px 16px;border:1px solid var(--border);border-radius:12px;resize:none;font-size:14px;outline:none"
          :disabled="isSending"></textarea>
        <button @click="sendMessage(inputQuery)" :disabled="isSending || !inputQuery.trim()"
          style="padding:12px 24px;background:var(--btn-primary-bg);color:#fff;border:none;border-radius:12px;font-weight:600;cursor:pointer">
          {{ isSending ? '分析中' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { renderMarkdown } from '@/utils/sanitize'
export default {
  name: 'ParentView',
  data() { return { inputQuery: '', user: {}, messages: [], isSending: false } },
  methods: {
    async sendMessage(query) {
      if (!query.trim() || this.isSending) return
      this.messages.push({ id: Date.now(), role: 'user', content: query, timestamp: new Date() })
      this.isSending = true; this.inputQuery = ''
      try {
        const resp = await fetch(`${window.API_BASE||'http://127.0.0.1:8000'}/stream/advice`, {
          method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${localStorage.getItem('auth_token')}`},body:JSON.stringify({query, domain: localStorage.getItem('xiaole_domain') || 'gaokao'})
        })
        if(!resp.ok) throw new Error('请求失败')
        const m = { id: Date.now()+1, role: 'assistant', content: '', timestamp: new Date() }; this.messages.push(m)
        const reader = resp.body.getReader(); const decoder = new TextDecoder()
        while(true) { const {done,value}=await reader.read(); if(done) break
          for(const l of decoder.decode(value).split('\n')) { if(l.startsWith('data: ')) { try{ const d=JSON.parse(l.slice(6)); if(d.type==='token') m.content+=d.msg }catch{} } }
        }
      } catch(err) { this.messages.push({ id:Date.now()+2,role:'assistant',content:`错误: ${err.message}`,timestamp:new Date() }) }
      finally { this.isSending = false }
    },
    renderContent(c) { return renderMarkdown(c) },
    formatTime(t) { if(!t) return ''; return new Date(t).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) }
  },
  mounted() { const ui=localStorage.getItem('user_info'); if(ui) try{this.user=JSON.parse(ui)}catch{} }
}
</script>
