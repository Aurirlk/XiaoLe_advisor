<template>
  <div class="admin-page"><h3>知识库管理</h3>
    <el-button type="primary" @click="showEditor=true;editItem=null" style="margin-bottom:16px">新建文档</el-button>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="title" label="文档名" min-width="250"/>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="editItem=row;showEditor=true">编辑</el-button>
          <el-button size="small" @click="deleteItem(row.path)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showEditor" :title="editItem?'编辑文档':'新建文档'" width="700px">
      <el-form label-position="top">
        <el-form-item label="文档名"><el-input v-model="form.title"/></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.content" type="textarea" :rows="15"/></el-form-item>
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
  name:'AdminKnowledge', data(){return{items:[],total:0,loading:false,saving:false,showEditor:false,editItem:null,form:{title:'',content:''}}},
  methods:{
    async loadData(){this.loading=true;try{const r=await fetch('/api/admin/knowledge');const d=await r.json();if(d.ok)this.items=d.data.items}catch{}finally{this.loading=false}},
    async save(){this.saving=true;try{const r=await fetch('/api/admin/knowledge'+(this.editItem?'/'+this.editItem.path:''),{method:this.editItem?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});const d=await r.json();if(d.ok){this.showEditor=false;this.loadData()}}catch{}finally{this.saving=false}},
    async deleteItem(path){if(!confirm('确定删除？'))return;await fetch(`/api/admin/knowledge/${encodeURIComponent(path)}`,{method:'DELETE'});this.loadData()}
  },
  watch:{showEditor(v){if(v&&!this.editItem)this.form={title:'',content:''}}},
  mounted(){this.loadData()}
}
</script>