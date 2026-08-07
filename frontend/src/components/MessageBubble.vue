<template>
  <div class="msg-row" :class="[message.role]">
    <div class="msg-avatar"><i :class="message.role==='user'?'fas fa-user':'fas fa-graduation-cap'" /></div>
    <div class="msg-content">
      <div class="msg-bubble"><markdown-renderer :content="message.content" /></div>
      <div class="msg-time">{{ formatTime(message.timestamp) }}</div>
    </div>
  </div>
</template>
<script>
import MarkdownRenderer from './core/MarkdownRenderer.vue'
export default {
  name: 'MessageBubble', components: { MarkdownRenderer },
  props: { message: { type: Object, required: true }, currentEmotion: { type: Object, default: () => ({ label:'neutral',intensity:0.5 }) } },
  emits: ['submit-feedback'],
  methods: { formatTime(t) { if(!t)return''; const d=new Date(t),n=new Date(); const df=n-d; if(df<60000)return'刚刚'; if(df<3600000)return Math.floor(df/60000)+'分钟前'; return d.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) } }
}
</script>
<style scoped>
.msg-row{display:flex;gap:12px;align-items:flex-start}.msg-row.user{flex-direction:row-reverse}.msg-avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}.msg-row.user .msg-avatar{background:var(--avatar-user-bg,linear-gradient(135deg,#1e3a5f,#2d5a8e));color:#fff}.msg-row.assistant .msg-avatar{background:var(--avatar-assistant-bg,linear-gradient(135deg,#f0a500,#ffc940));color:var(--accent-text,#1e3a5f)}.msg-content{max-width:70%}.msg-bubble{padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.7}.msg-row.user .msg-bubble{background:var(--bubble-user-bg);color:var(--bubble-user-text,#fff)}.msg-row.assistant .msg-bubble{background:var(--bubble-assistant-bg,#fff);border:1px solid var(--bubble-assistant-border,#e2e8f0);color:var(--text)}.msg-time{font-size:11px;color:var(--text-light);margin-top:4px;padding:0 4px}
</style>
