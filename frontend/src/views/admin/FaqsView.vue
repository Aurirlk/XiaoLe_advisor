<template>
  <div class="admin-page"><h3>FAQ 管理</h3>
    <el-button type="primary" @click="showEditor=true;editItem=null" style="margin-bottom:16px">新建 FAQ</el-button>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="question" label="问题" min-width="250"/>
      <el-table-column prop="category" label="分类" width="100"/>
      <el-table-column label="置顶" width="60"><template #default="{row}">{{ row.is_pinned?'📌':'' }}</template></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160"/>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="editItem=row;showEditor=true">编辑</el-button>
          <el-button size="small" @click="deleteItem(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
    <el-dialog v-model="showEditor" :title="editItem?'编辑FAQ':'新建FAQ'" width="600px">
      <el-form label-position="top">
        <el-form-item label="问题"><el-input v-model="form.question"/></el-form-item>
        <el-form-item label="答案"><el-input v-model="form.answer" type="textarea" :rows="6"/></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" placeholder="通用"/></el-form-item>
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
  name:'AdminFaqs', data(){return{items:[],total:0,page:1,size:20,loading:false,saving:false,showEditor:false,editItem:null,form:{question:'',answer:'',category:'通用'}}},
  methods:{
    async loadData(){this.loading=true;try{const r=await fetch(`/api/admin/faqs?page=${this.page}&size=${this.size}`);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}},
    async save(){this.saving=true;try{const r=await fetch(`/api/admin/faqs${this.editItem?'/'+this.editItem.id:''}`,{method:this.editItem?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});const d=await r.json();if(d.ok){this.showEditor=false;this.loadData()}}catch{}finally{this.saving=false}},
    async deleteItem(id){if(!confirm('确定删除？'))return;await fetch(`/api/admin/faqs/${id}`,{method:'DELETE'});this.loadData()}
  },
  watch:{showEditor(v){if(v&&!this.editItem)this.form={question:'',answer:'',category:'通用'};if(v&&this.editItem)this.form={...this.editItem}}},
  mounted(){this.loadData()}
}
</script>