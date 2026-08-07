<template>
  <div style="max-width:800px;margin:0 auto;padding:24px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h2 style="margin:0">通知中心</h2>
      <el-button size="small" @click="markAllRead">全部标记已读</el-button>
    </div>
    <div v-if="!items.length" style="text-align:center;padding:60px;color:#718096">暂无通知</div>
    <el-card v-for="n in items" :key="n.id" :class="['notif-card',n.is_read?'':'unread']" shadow="hover" style="margin-bottom:8px;cursor:pointer" @click="markRead(n.id)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><span v-if="!n.is_read" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--el-color-danger);margin-right:8px"></span>
          <strong>{{ n.title }}</strong></div>
        <el-tag size="small" v-if="n.type==='announcement'">公告</el-tag>
      </div>
      <p v-if="n.content" style="margin:8px 0 0;font-size:13px;color:#718096">{{ n.content }}</p>
      <div style="font-size:12px;color:#a0aec0;margin-top:8px">{{ n.created_at }}</div>
    </el-card>
    <el-pagination v-if="total>size" background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
  </div>
</template>
<script>
export default {
  name:'NotificationsView', data(){return{items:[],total:0,page:1,size:20}},
  methods:{
    async loadData(){try{const r=await fetch(`/api/notifications?page=${this.page}&size=${this.size}`,{headers:{'Authorization':'Bearer '+localStorage.getItem('auth_token')}});const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}},
    async markRead(id){await fetch(`/api/notifications/${id}/read`,{method:'PUT',headers:{'Authorization':'Bearer '+localStorage.getItem('auth_token')}});this.loadData()},
    async markAllRead(){await fetch('/api/notifications/read-all',{method:'PUT',headers:{'Authorization':'Bearer '+localStorage.getItem('auth_token')}});this.loadData()}
  },
  mounted(){this.loadData()}
}
</script>
<style scoped>
.notif-card.unread { border-left: 3px solid var(--el-color-primary); }
</style>