<template>
  <div class="admin-page"><h3>用户反馈管理</h3>
    <el-select v-model="statusFilter" clearable placeholder="筛选状态" style="width:150px;margin-bottom:16px" @change="loadData">
      <el-option label="待处理" value="pending"/><el-option label="已处理" value="processed"/><el-option label="已忽略" value="dismissed"/>
    </el-select>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="user_id" label="用户ID" width="80"/>
      <el-table-column label="评价" width="80"><template #default="{row}">{{ ['','👎','','','👍'][row.rating]||row.rating }}</template></el-table-column>
      <el-table-column prop="comment" label="反馈内容" min-width="250"/>
      <el-table-column label="状态" width="80"><template #default="{row}">{{ {pending:'待处理',processed:'已处理',dismissed:'已忽略'}[row.status]||row.status }}</template></el-table-column>
      <el-table-column prop="created_at" label="时间" width="160"/>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button size="small" type="success" @click="updateStatus(row.id,'processed')">已处理</el-button>
          <el-button size="small" @click="updateStatus(row.id,'dismissed')">忽略</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
  </div>
</template>
<script>
export default {
  name:'AdminFeedback', data(){return{items:[],total:0,page:1,size:20,loading:false,statusFilter:''}},
  methods:{
    async loadData(){this.loading=true;try{let url=`/api/admin/feedback?page=${this.page}&size=${this.size}`;if(this.statusFilter)url+=`&status=${this.statusFilter}`;const r=await fetch(url);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}},
    async updateStatus(id,status){await fetch(`/api/admin/feedback/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});this.loadData()}
  },
  mounted(){this.loadData()}
}
</script>