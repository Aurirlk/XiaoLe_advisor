<template>
  <div class="image-analyzer"><button class="analyze-btn" @click="selectImage" :disabled="loading"><i :class="loading?'fas fa-spinner fa-spin':'fas fa-image'" /> {{ loading?'分析中...':'上传图片分析' }}</button><input type="file" ref="fileInput" @change="handleFile" accept="image/*" style="display:none" /><div v-if="result" class="result" v-html="safeResult" /></div>
</template>
<script>
import { renderMarkdown } from '@/utils/sanitize'
export default {
  name: 'ImageAnalyzer', emits: ['analysis-result'],
  data() { return { loading: false, result: '' } },
  computed: { safeResult() { return renderMarkdown(this.result) } },
  methods: {
    selectImage() { this.$refs.fileInput.click() },
    async handleFile(e) {
      const f = e.target.files[0]; if (!f) return; this.loading = true
      try {
        const fd = new FormData(); fd.append('file', f)
        const r = await fetch(`${window.API_BASE||''}/vision/analyze`, { method:'POST', body:fd })
        if (r.ok) { const d = await r.json(); this.result = d.result || d.analysis || ''; this.$emit('analysis-result', d) }
      } catch {} finally { this.loading = false }
    }
  }
}
</script>
<style scoped>.analyze-btn{padding:8px 16px;border:1px solid var(--border);border-radius:8px;background:var(--card);cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px}.analyze-btn:hover{border-color:var(--primary);color:var(--primary)}.result{margin-top:8px;padding:12px;background:var(--card);border-radius:8px;border:1px solid var(--border);font-size:13px;line-height:1.6}</style>
