<template>
  <div class="quick-chips" style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">
    <button v-for="q in chips" :key="q" @click="$emit('send-query',q)" class="chip-btn">{{ q }}</button>
  </div>
</template>
<script>
export default {
  name: 'QuickChips', emits: ['send-query'],
  data() { return { chips: ['计算机就业前景','广东省物理类580分推荐','金融和计算机怎么选','985和211的区别','医学类院校推荐','师范类院校推荐'] } }
}
</script>
<style scoped>.chip-btn{padding:8px 16px;border:1px solid var(--border);border-radius:20px;background:var(--card);font-size:13px;cursor:pointer;color:var(--primary);transition:all .2s}.chip-btn:hover{background:var(--primary);color:#fff;border-color:var(--primary)}</style>
