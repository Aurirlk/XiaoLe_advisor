<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <div class="brand">🎓 小乐AI · 家长端</div>
      </div>
      <div class="header-right">
        <el-badge :value="unreadCount" :hidden="unreadCount===0" class="notif-badge">
          <el-button text circle @click="$router.push('/notifications')">
            <el-icon><Bell /></el-icon>
          </el-button>
        </el-badge>
        <el-button text circle @click="showSettings = true">
          <el-icon><Setting /></el-icon>
        </el-button>
        <el-button text @click="logout">
          <el-icon><SwitchButton /></el-icon>
          退出
        </el-button>
      </div>
    </el-header>
    <el-container class="app-body">
      <el-aside width="200px" class="app-aside">
        <domain-switcher />
        <el-menu :default-active="activeMenu" router>
          <el-menu-item index="/parent/chat">
            <el-icon><ChatDotSquare /></el-icon>
            <span>对话</span>
          </el-menu-item>
          <el-menu-item index="/parent/questionnaire">
            <el-icon><Document /></el-icon>
            <span>问卷</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
    <SettingsDrawer :visible="showSettings" @close="showSettings = false" />
  </el-container>
</template>

<script>
import { ChatDotSquare, Document, Setting, SwitchButton, Bell } from '@element-plus/icons-vue'
import SettingsDrawer from '../components/SettingsDrawer.vue'
import DomainSwitcher from '../components/DomainSwitcher.vue'

export default {
  name: 'ParentLayout',
  components: { SettingsDrawer, DomainSwitcher },
  data() {
    return { showSettings: false, unreadCount: 0 }
  },
  computed: {
    activeMenu() { return this.$route.path }
  },
  methods: {
    async fetchUnread() {
      try {
        const r = await fetch('/api/notifications/unread-count', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('auth_token') } })
        const d = await r.json()
        if (d.ok) this.unreadCount = d.data.count
      } catch {}
    },
    logout() {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      this.$router.push('/login')
    }
  },
  mounted() {
    this.fetchUnread()
    setInterval(() => this.fetchUnread(), 30000)
  }
}
</script>

<style scoped>
.app-container { height: 100vh; }
.app-header { display: flex; align-items: center; justify-content: space-between; background: var(--header-bg, #1e3a5f); color: #fff; padding: 0 20px; height: 56px; }
.header-left { display: flex; align-items: center; }
.header-right { display: flex; align-items: center; gap: 8px; }
.header-right .el-button { color: rgba(255,255,255,.8); }
.header-right .el-button:hover { color: #fff; }
.brand { font-size: 18px; font-weight: 700; letter-spacing: .5px; }
.app-body { flex: 1; overflow: hidden; }
.app-aside { background: var(--sidebar-bg, #fff); border-right: 1px solid var(--border, #e2e8f0); }
.app-main { background: var(--bg, #f0f4f8); padding: 0; overflow: auto; display: flex; flex-direction: column; }
.el-menu { border-right: none; }
</style>
