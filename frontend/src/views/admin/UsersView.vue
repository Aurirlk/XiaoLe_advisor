<template>
  <div class="admin-page"><h3>用户管理</h3>
    <el-card><el-input v-model="keyword" placeholder="搜索用户名/手机号" clearable style="width:300px;margin-bottom:16px" @keyup.enter="loadData" />
      <el-table :data="items" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60"/>
        <el-table-column prop="username" label="用户名" min-width="120"/>
        <el-table-column prop="phone_number" label="手机号" width="140"/>
        <el-table-column prop="role" label="角色" width="80"/>
        <el-table-column prop="province" label="省份" width="100"/>
        <el-table-column prop="score" label="分数" width="80"/>
        <el-table-column label="注册时间" width="160"><template #default="{row}">{{ row.created_at }}</template></el-table-column>
      </el-table>
      <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
    </el-card>
  </div>
</template>
<script>
export default {
  name:'AdminUsers', data(){return{items:[],total:0,page:1,size:20,keyword:'',loading:false}},
  methods:{
    async loadData(){this.loading=true;try{const p=new URLSearchParams({page:this.page,size:this.size});if(this.keyword)p.set('keyword',this.keyword);const r=await fetch(`/api/admin/users?${p}`);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}}
  },
  mounted(){this.loadData()}
}
</script>