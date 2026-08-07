<template>
  <div class="admin-page"><h3>公告管理</h3>
    <el-button type="primary" @click="showEditor=true;editItem=null" style="margin-bottom:16px">新建公告</el-button>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="title" label="标题" min-width="200"/>
      <el-table-column label="发送范围" width="100"><template #default="{row}">{{ {all:'全部',student:'学生',parent:'家长'}[row.target_role]||row.target_role }}</template></el-table-column>
      <el-table-column label="置顶" width="60"><template #default="{row}">{{ row.is_pinned?'📌':'' }}</template></el-table-column>
      <el-table-column label="状态" width="80"><template #default="{row}">{{ {draft:'草稿',published:'已发布',archived:'归档'}[row.status]||row.status }}</template></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160"/>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="editItem=row;showEditor=true">编辑</el-button>
          <el-button size="small" @click="deleteItem(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>

    <el-dialog v-model="showEditor" :title="editItem?'编辑公告':'新建公告'" width="600px">
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="form.title"/></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.content" type="textarea" :rows="6"/></el-form-item>
        <el-form-item label="发送范围"><el-select v-model="form.target_role"><el-option label="全部" value="all"/><el-option label="学生" value="student"/><el-option label="家长" value="parent"/></el-select></el-form-item>
        <el-form-item label="置顶"><el-switch v-model="form.is_pinned"/></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditor=false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">{{ editItem?'更新':'创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script>
export default {
  name:'AdminAnnouncements', data(){return{items:[],total:0,page:1,size:20,loading:false,saving:false,showEditor:false,editItem:null,form:{title:'',content:'',target_role:'all',is_pinned:false}}},
  methods:{
    async loadData(){this.loading=true;try{const r=await fetch(`/api/admin/announcements?page=${this.page}&size=${this.size}`);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}},
    async save(){this.saving=true;try{const r=await fetch(`/api/admin/announcements${this.editItem?'/'+this.editItem.id:''}`,{method:this.editItem?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});const d=await r.json();if(d.ok){this.showEditor=false;this.loadData()}}catch{}finally{this.saving=false}},
    async deleteItem(id){if(!confirm('确定删除？'))return;await fetch(`/api/admin/announcements/${id}`,{method:'DELETE'});this.loadData()}
  },
  watch:{showEditor(v){if(v&&!this.editItem)this.form={title:'',content:'',target_role:'all',is_pinned:false};if(v&&this.editItem)this.form={...this.editItem}}},
  mounted(){this.loadData()}
}
</script>