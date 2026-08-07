<template>
  <div class="profile-card">
    <div v-if="!hasProfile" class="empty">暂无画像信息，开始对话后将自动提取</div>
    <div v-else class="field" v-for="(v,k) in fields" :key="k"><span class="k">{{ k }}</span><span class="v">{{ v }}</span></div>
    <div v-if="messages.length" style="margin-top:12px;font-size:12px;color:var(--text-muted)">已对话 {{ messages.length }} 轮</div>
  </div>
</template>
<script>
export default {
  name: 'ProfileCard', props: { user: Object, messages: Array },
  computed: {
    hasProfile() { return this.user && (this.user.province || this.user.score || this.user.subject_type) },
    fields() { const f = {}; const u = this.user || {}; if(u.username)f['姓名']=u.username; if(u.province)f['省份']=u.province; if(u.score)f['分数']=u.score; if(u.subject_type)f['选科']=u.subject_type; if(u.rank)f['位次']=u.rank; return f }
  }
}
</script>
<style scoped>
.profile-card{padding:18px;background:linear-gradient(135deg,var(--bg-light),var(--bg));border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow)}.field{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-light);font-size:13px}.field:last-child{border-bottom:none}.k{color:var(--text-muted)}.v{font-weight:600;color:var(--text);background:var(--card);padding:4px 10px;border-radius:20px;font-size:12px}.empty{color:var(--text-muted);font-size:13px;font-style:italic;text-align:center;padding:20px}
</style>
