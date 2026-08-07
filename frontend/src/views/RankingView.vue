<template>
  <div class="ranking-view" style="flex:1;overflow:auto;padding:24px">
    <h2 style="margin-bottom:16px">院校排名</h2>
    <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
      <el-select v-model="source" @change="loadRanking" style="width:180px">
        <el-option v-for="s in sources" :key="s.key" :label="s.label" :value="s.key" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索院校..." style="flex:1;min-width:200px" @keyup.enter="loadRanking" clearable />
      <el-button type="primary" @click="loadRanking">查询</el-button>
    </div>
    <el-card shadow="never" style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-size:13px;color:#718096;font-weight:600">显示数量</span>
        <span style="font-size:14px;font-weight:700;color:var(--el-color-primary)">{{ pageSize }} 条/页</span>
      </div>
      <el-slider v-model="pageSize" :min="5" :max="100" :step="5" show-stops @change="currentPage=1;loadRanking()" />
    </el-card>
    <div v-if="loading" style="text-align:center;padding:40px;color:#718096">加载中...</div>
    <div v-else-if="error" style="text-align:center;padding:40px;color:var(--el-color-danger)">
      {{ error }} <el-button size="small" @click="loadRanking" style="margin-left:8px">重试</el-button>
    </div>
    <el-table v-else-if="pagedData.length" :data="pagedData" stripe style="width:100%">
      <el-table-column label="排名" width="80">
        <template #default="{_,$i}">{{ (currentPage-1)*pageSize+$i+1 }}</template>
      </el-table-column>
      <el-table-column prop="name" label="院校" min-width="180" />
      <el-table-column label="地区" width="120"><template #default="{row}">{{ row.province||row.location||'-' }}</template></el-table-column>
      <el-table-column label="类型" width="100"><template #default="{row}">{{ row.type||row.level||'-' }}</template></el-table-column>
      <el-table-column label="评分" width="100"><template #default="{row}"><span style="font-weight:600;color:var(--el-color-primary)">{{ row.score||row.overall_score||'-' }}</span></template></el-table-column>
    </el-table>
    <div v-else style="text-align:center;padding:40px;color:#718096">选择排名来源并搜索院校</div>
    <div v-if="totalPages>1" style="display:flex;justify-content:center;margin-top:16px">
      <el-pagination background layout="prev,pager,next" :total="totalCount" :page-size="pageSize" v-model:current-page="currentPage" />
    </div>
    <el-card shadow="never" style="margin-top:24px">
      <div style="padding:4px 0">
        <zhihu-search-panel />
      </div>
    </el-card>
  </div>
</template>
<script>
import ZhihuSearchPanel from '../components/ZhihuSearchPanel.vue'
export default {
  name:'RankingView',
  components:{ ZhihuSearchPanel },
  data(){return {source:'qs',keyword:'',rankingData:[],loading:false,error:'',currentPage:1,pageSize:20,
    sources:[{key:'qs',label:'QS 世界排名'},{key:'usnews',label:'US News'},{key:'times',label:'泰晤士 (THE)'},{key:'nature',label:'自然指数'},{key:'arwu',label:'软科 (ARWU)'},{key:'cuhk',label:'校友会'}]
  }},
  computed:{totalCount(){return this.rankingData.length},totalPages(){return Math.max(1,Math.ceil(this.totalCount/this.pageSize))},pagedData(){const s=(this.currentPage-1)*this.pageSize;return this.rankingData.slice(s,s+this.pageSize)}},
  methods:{
    async loadRanking(){this.loading=true;this.error='';this.currentPage=1;try{const p=new URLSearchParams();if(this.keyword)p.set('keyword',this.keyword);p.set('limit','200');const r=await fetch((window.API_BASE||'')+'/api/ranking/'+this.source+'?'+p);if(!r.ok)throw Error('加载失败');const d=await r.json();this.rankingData=d.data||d.ranking||d.universities||[]}catch(e){this.error=e.message;try{const r=await fetch((window.API_BASE||'')+'/assets/ranking_data.json');if(r.ok){const d=await r.json();this.rankingData=(d[this.source]||d||[]).slice(0,200);this.error=''}}catch{}}finally{this.loading=false}}
  },
  mounted(){this.loadRanking()}
}
</script>
