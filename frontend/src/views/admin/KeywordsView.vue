<template>
  <div class="admin-page"><h3>快捷提问词管理</h3>
    <el-button type="primary" @click="showEditor=true;editItem=null" style="margin-bottom:16px">新建提问词</el-button>
    <el-table :data="items" stripe v-loading="loading">
      <el-table-column prop="text" label="提问词" min-width="250"/>
      <el-table-column prop="group_name" label="分组" width="120"/>
      <el-table-column prop="sort_order" label="排序" width="60"/>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="editItem=row;showEditor=true">编辑</el-button>
          <el-button size="small" @click="deleteItem(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination background layout="prev,pager,next" :total="total" :page-size="size" v-model:current-page="page" @current-change="loadData" style="margin-top:16px"/>
    <el-dialog v-model="showEditor" :title="editItem?'编辑提问词':'新建提问词'" width="500px">
      <el-form label-position="top">
        <el-form-item label="提问词"><el-input v-model="form.text"/></el-form-item>
        <el-form-item label="分组"><el-input v-model="form.group_name" placeholder="默认"/></el-form-item>
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
  name:'AdminKeywords', data(){return{items:[],total:0,page:1,size:20,loading:false,saving:false,showEditor:false,editItem:null,form:{text:'',group_name:'默认'}}},
  methods:{
    async loadData(){this.loading=true;try{const r=await fetch(`/api/admin/keywords?page=${this.page}&size=${this.size}`);const d=await r.json();if(d.ok){this.items=d.data.items;this.total=d.data.total}}catch{}finally{this.loading=false}},
    async save(){this.saving=true;try{const r=await fetch(`/api/admin/keywords${this.editItem?'/'+this.editItem.id:''}`,{method:this.editItem?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});const d=await r.json();if(d.ok){this.showEditor=false;this.loadData()}}catch{}finally{this.saving=false}},
    async deleteItem(id){if(!confirm('确定删除？'))return;await fetch(`/api/admin/keywords/${id}`,{method:'DELETE'});this.loadData()}
  },
  watch:{showEditor(v){if(v&&!this.editItem)this.form={text:'',group_name:'默认'}}},
  mounted(){this.loadData()}
}
</script>