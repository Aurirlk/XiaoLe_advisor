<template>
  <div class="admin-page"><h3>数据同步</h3>
    <el-card><p style="color:var(--text-muted,#718096);margin-bottom:16px">管理知识库索引重建、院校数据导入等操作。</p>
      <el-button type="primary" @click="syncRag" :loading="syncing">{{ syncing?'同步中...':'重建 RAG 索引' }}</el-button>
      <el-alert v-if="syncResult" :title="syncResult" :type="syncResult.includes('成功')?'success':'error'" show-icon style="margin-top:12px"/>
    </el-card>
  </div>
</template>
<script>
export default {
  name:'AdminSync', data(){return{syncing:false,syncResult:''}},
  methods:{
    async syncRag(){this.syncing=true;this.syncResult='';try{const r=await fetch('/api/admin/rebuild_rag',{method:'POST',headers:{'Authorization':'Bearer '+localStorage.getItem('auth_token')}});const d=await r.json();this.syncResult=d.ok?'RAG 索引重建成功':'重建失败: '+(d.error||'')}catch(e){this.syncResult='请求失败: '+e.message}finally{this.syncing=false}}
  }
}
</script>