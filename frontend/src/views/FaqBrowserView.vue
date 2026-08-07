<template>
  <div style="max-width:800px;margin:0 auto;padding:24px">
    <h2 style="margin-bottom:20px">常见问题</h2>
    <el-collapse v-model="activeNames">
      <el-collapse-item v-for="faq in items" :key="faq.id" :title="faq.question" :name="faq.id">
        <div style="white-space:pre-wrap;line-height:1.8">{{ faq.answer }}</div>
      </el-collapse-item>
    </el-collapse>
    <div v-if="!items.length" style="text-align:center;padding:60px;color:#718096">暂无常见问题</div>
  </div>
</template>
<script>
export default {
  name:'FaqBrowserView', data(){return{items:[],activeNames:[]}},
  methods:{
    async loadData(){try{const r=await fetch('/api/faqs?size=50');const d=await r.json();if(d.ok)this.items=d.data.items}catch{}}
  },
  mounted(){this.loadData()}
}
</script>