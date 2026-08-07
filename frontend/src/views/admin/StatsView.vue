<template>
  <div class="admin-page"><h3>数据统计</h3>
    <el-row :gutter="16">
      <el-col :span="6" v-for="st in stats" :key="st.label">
        <el-card shadow="hover"><div style="text-align:center;padding:12px">
          <div style="font-size:28px;font-weight:700;color:var(--el-color-primary)">{{ st.value }}</div>
          <div style="font-size:13px;color:#718096;margin-top:8px">{{ st.label }}</div>
        </div></el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script>
export default {
  name:'AdminStats', data(){return{stats:[{label:'注册用户',value:'—'},{label:'院校收录',value:'2,817'},{label:'录取数据',value:'283,653'},{label:'RAG 文档',value:'1,998'}]}}
}
</script>