<template>
  <el-drawer v-model="show" title="设置" size="380px" @close="$emit('close')">
    <div class="setting-group">
      <label>深色模式</label>
      <el-switch v-model="isDark" active-text="深色" inactive-text="浅色" @change="toggleDark" />
    </div>
    <div class="setting-group">
      <label>主题颜色</label>
      <div style="display:flex;gap:8px">
        <div v-for="t in themes" :key="t.value"
          @click="setTheme(t.value)"
          :style="{width:32,height:32,borderRadius:'50%',background:t.color,cursor:'pointer',border:theme===t.value?'3px solid var(--el-color-primary)':'3px solid transparent'}" />
      </div>
    </div>
    <div class="setting-group">
      <label>语音合成</label>
      <el-checkbox v-model="streamTTS" @change="save">流式推送</el-checkbox>
    </div>
  </el-drawer>
</template>
<script>
export default {
  name: 'SettingsDrawer',
  props: { visible: Boolean },
  emits: ['close'],
  data() {
    const s = (() => { try { return JSON.parse(localStorage.getItem('xiaole_settings')||'{}') } catch { return {} } })()
    return {
      isDark: document.documentElement.classList.contains('dark'),
      theme: 'blue',
      streamTTS: s.streaming_tts||false,
      themes: [
        { value:'blue', color:'#1e3a5f' },
        { value:'orange', color:'#c2410c' },
        { value:'green', color:'#059669' },
        { value:'purple', color:'#7c3aed' },
        { value:'red', color:'#dc2626' },
        { value:'cyan', color:'#0891b2' },
      ]
    }
  },
  computed: {
    show: {
      get() { return this.visible },
      set(v) { if(!v) this.$emit('close') }
    }
  },
  methods: {
    toggleDark(v) {
      if(v) document.documentElement.classList.add('dark')
      else document.documentElement.classList.remove('dark')
      localStorage.setItem('xiaole_dark_mode', v ? '1' : '0')
    },
    setTheme(t) { this.theme=t; document.body.setAttribute('data-theme', t) },
    save() { localStorage.setItem('xiaole_settings', JSON.stringify({streaming_tts:this.streamTTS})) }
  }
}
</script>
<style scoped>
.setting-group { margin-bottom: 24px; }
.setting-group label { display: block; margin-bottom: 8px; font-size: 14px; font-weight: 600; color: var(--el-text-color-primary); }
</style>
