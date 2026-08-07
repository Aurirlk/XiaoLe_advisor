<template>
  <div id="app-root">
    <router-view />
    <!-- 暗色模式开关（全局） -->
    <div class="dark-mode-toggle-wrapper" @click="toggleDark" title="切换暗色模式">
      <span class="dark-mode-icon">{{ isDark ? '☀️' : '🌙' }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return { isDark: localStorage.getItem('xiaole_dark_mode') === '1' }
  },
  methods: {
    toggleDark() {
      this.isDark = !this.isDark
      if (this.isDark) document.documentElement.classList.add('dark')
      else document.documentElement.classList.remove('dark')
      localStorage.setItem('xiaole_dark_mode', this.isDark ? '1' : '0')
    }
  },
  created() {
    if (this.isDark) document.documentElement.classList.add('dark')
  }
}
</script>

<style>
.dark-mode-toggle-wrapper {
  position: fixed !important;
  bottom: 20px; left: 20px;
  z-index: 9999;
  background: var(--card, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 50%;
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,.15);
  font-size: 20px;
  pointer-events: auto;
  user-select: none;
  transition: transform 0.2s;
}
.dark-mode-toggle-wrapper:hover { transform: scale(1.1); }
</style>
