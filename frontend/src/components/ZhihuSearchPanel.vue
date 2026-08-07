<template>
  <div class="zhihu-search">
    <div class="search-header" @click="expanded = !expanded">
      <el-icon><Search /></el-icon>
      <span>全网查风评</span>
      <el-icon :class="['arrow', expanded ? 'up' : '']"><ArrowDown /></el-icon>
    </div>
    <el-collapse-transition>
      <div v-show="expanded" class="search-body">
        <el-radio-group v-model="source" size="small" style="margin-bottom:8px">
          <el-radio-button value="zhihu">知乎</el-radio-button>
          <el-radio-button value="weibo">微博</el-radio-button>
          <el-radio-button value="tieba">贴吧</el-radio-button>
          <el-radio-button value="xhs">小红书</el-radio-button>
          <el-radio-button value="web">全网</el-radio-button>
        </el-radio-group>
        <div class="search-input-row">
          <el-input v-model="query" :placeholder="placeholderText" size="small"
            @keyup.enter="search" :disabled="loading" clearable />
          <el-button type="primary" size="small" @click="search" :loading="loading" :disabled="!query.trim()">
            搜索
          </el-button>
        </div>
        <div v-if="error" class="search-error">{{ error }}</div>

        <!-- 知乎搜索结果 -->
        <div v-if="results.length && source==='zhihu'" class="search-results">
          <div v-for="(item, i) in results" :key="i" class="result-item">
            <a :href="item.url" target="_blank" rel="noopener" class="result-title">{{ item.title }}</a>
            <div class="result-meta" v-if="item.author">@{{ item.author }}</div>
            <div class="result-summary">{{ item.summary }}</div>
          </div>
          <div class="result-footer">— 结果来自知乎，仅供参考 —</div>
        </div>

        <!-- 站内搜索/全网搜索结果 -->
        <div v-if="results.length && source!=='zhihu'" class="search-results">
          <div v-for="(item, i) in results" :key="i" class="result-item">
            <a :href="item.url" target="_blank" rel="noopener" class="result-title">{{ item.title }}</a>
            <div class="result-meta" v-if="item.author">@{{ item.author }}</div>
            <div class="result-summary">{{ item.summary }}</div>
          </div>
          <div class="result-footer">— 结果来自搜索引擎，仅供参考，请自行判断 —</div>
        </div>

        <div v-if="searched && !results.length && !loading" class="search-empty">无结果，换个关键词试试</div>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script>
import { Search, ArrowDown } from '@element-plus/icons-vue'

const SITE_MAP = {
  weibo: 'site:weibo.com',
  tieba: 'site:tieba.baidu.com',
  xhs: 'site:xiaohongshu.com',
}

export default {
  name: 'ZhihuSearchPanel',
  data() {
    return {
      expanded: false,
      query: '',
      source: 'zhihu',
      results: [],
      loading: false,
      error: '',
      searched: false,
    }
  },
  computed: {
    placeholderText() {
      const map = { zhihu: '知乎', weibo: '微博', tieba: '贴吧', xhs: '小红书', web: '全网' }
      return `搜${map[this.source]}上关于「院校/专业」的评价`
    }
  },
  methods: {
    async search() {
      if (!this.query.trim()) return
      this.loading = true
      this.error = ''
      this.searched = true
      this.results = []
      try {
        let url
        if (this.source === 'zhihu') {
          url = `/api/zhihu/search?query=${encodeURIComponent(this.query.trim())}&count=8`
        } else {
          let searchQuery = this.query.trim()
          const site = SITE_MAP[this.source]
          if (site) searchQuery = `${this.query.trim()} ${site}`
          url = `/api/web/search?query=${encodeURIComponent(searchQuery)}&count=8`
        }
        const r = await fetch(url)
        const d = await r.json()
        if (d.code === 0 && d.data?.items?.length) {
          this.results = d.data.items
        } else {
          this.error = d.message || '无结果'
        }
      } catch (e) {
        this.error = '网络错误: ' + e.message
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.zhihu-search { border-top: 1px solid var(--border, #e2e8f0); font-size: 13px; }
.search-header { display: flex; align-items: center; gap: 8px; padding: 12px 20px; cursor: pointer; color: var(--text-muted, #718096); transition: color 0.2s; user-select: none; }
.search-header:hover { color: var(--primary, #1e3a5f); }
.arrow { transition: transform 0.2s; font-size: 12px; margin-left: auto; }
.arrow.up { transform: rotate(180deg); }
.search-body { padding: 0 20px 16px; }
.search-input-row { display: flex; gap: 8px; }
.search-results { margin-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.result-item { padding: 8px 10px; border-radius: 6px; background: var(--bg-light, #f8fafc); }
.result-title { font-weight: 600; color: var(--primary, #1e3a5f); text-decoration: none; font-size: 13px; display: block; }
.result-title:hover { text-decoration: underline; }
.result-meta { font-size: 11px; color: var(--text-light, #a0aec0); margin-top: 2px; }
.result-summary { font-size: 12px; color: var(--text-muted, #718096); margin-top: 4px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.result-footer { text-align: center; font-size: 11px; color: var(--text-light, #a0aec0); margin-top: 8px; }
.search-error { color: var(--danger, #e74c3c); font-size: 12px; margin-top: 8px; }
.search-empty { text-align: center; color: var(--text-light, #a0aec0); margin-top: 12px; font-size: 12px; }
</style>
