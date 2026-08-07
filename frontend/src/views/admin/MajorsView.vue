<template>
  <div class="admin-page"><h3>专业管理</h3>
    <el-input v-model="keyword" placeholder="搜索专业名" style="width:300px;margin-bottom:16px" clearable @keyup.enter="loadData"/>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="name" label="专业名" min-width="200"/>
      <el-table-column prop="code" label="代码" width="100"/>
      <el-table-column prop="category" label="门类" width="120"/>
      <el-table-column prop="subcategory" label="子类" width="120"/>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{row}"><el-button size="small" @click="editItem=row;showEditor=true">编辑</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
    <el-dialog v-model="showEditor" title="编辑专业" width="500px">
      <el-form label-position="top">
        <el-form-item label="专业名"><el-input v-model="form.name"/></el-form-item>
        <el-form-item label="门类"><el-input v-model="form.category"/></el-form-item>
      </el-form>
      <template #footer><el-button @click="showEditor=false">取消</el-button><el-button type="primary" @click="save" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script>
export default {
  name:'AdminMajors', data(){return{items:[],total:0,page:1,size:20,keyword:'',loading:false,saving:false,showEditor:false,editItem:null,form:{name:'',category:''}}},
  methods:{
    async loadData(){this.loading=true;try{let url=`/api/admin/majors?page=${this.page}&size=${this.size}`;if(this.keyword)url+=`&keyword=${encodeURIComponent(this.keyword)}`;const r=await fetch(url);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}},
    async save(){this.saving=true;await fetch(`/api/admin/majors/${this.editItem.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});this.saving=false;this.showEditor=false;this.loadData()}
  },
  watch:{showEditor(v){if(v&&this.editItem)this.form={name:this.editItem.name,category:this.editItem.category}}},
  mounted(){this.loadData()}
}
</script>