<template>
  <div class="side-panel">
    <div class="section"><h4><i class="fas fa-server"></i> 服务状态</h4>
      <status-indicator :status="status" />
    </div>
    <div class="section"><h4><i class="fas fa-user"></i> 用户画像</h4>
      <profile-card :user="user" :messages="messages" />
    </div>
    <div class="section"><button class="reset-btn" @click="$emit('reset')"><i class="fas fa-refresh"></i> 重置对话</button></div>
  </div>
</template>
<script>
import StatusIndicator from './StatusIndicator.vue'
import ProfileCard from './ProfileCard.vue'
export default { name: 'SidePanel', components: { StatusIndicator, ProfileCard }, props: { status: Object, user: Object, messages: Array }, emits: ['reset'] }
</script>
<style scoped>
.side-panel{width:360px;border-left:1px solid var(--sidebar-border,#e2e8f0);background:var(--sidebar-bg,#fff);overflow-y:auto;flex-shrink:0}.section{padding:20px;border-bottom:1px solid var(--border)}.section h4{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);margin-bottom:16px;display:flex;align-items:center;gap:8px}.reset-btn{width:100%;padding:12px;border:2px dashed var(--border);border-radius:8px;background:none;color:var(--text-muted);cursor:pointer;font-size:13px}.reset-btn:hover{border-color:var(--danger);color:var(--danger)}
</style>
