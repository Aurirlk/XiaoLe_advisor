<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <div class="brand">🎓 小乐AI · 管理后台</div>
      </div>
      <div class="header-right">
        <el-button text @click="logout">
          <el-icon><SwitchButton /></el-icon>
          退出
        </el-button>
      </div>
    </el-header>
    <el-container class="app-body">
      <el-aside width="220px" class="app-aside">
        <el-menu :default-active="activeMenu" router>
          <el-menu-item-group title="核心">
            <el-menu-item index="/admin">
              <el-icon><Monitor /></el-icon><span>系统监控</span>
            </el-menu-item>
            <el-menu-item index="/admin/users">
              <el-icon><User /></el-icon><span>用户管理</span>
            </el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="内容">
            <el-menu-item index="/admin/announcements">
              <el-icon><Message /></el-icon><span>公告管理</span>
            </el-menu-item>
            <el-menu-item index="/admin/faqs">
              <el-icon><QuestionFilled /></el-icon><span>FAQ 管理</span>
            </el-menu-item>
            <el-menu-item index="/admin/guides">
              <el-icon><Document /></el-icon><span>报考指南</span>
            </el-menu-item>
            <el-menu-item index="/admin/keywords">
              <el-icon><Edit /></el-icon><span>快捷提问词</span>
            </el-menu-item>
            <el-menu-item index="/admin/knowledge">
              <el-icon><Collection /></el-icon><span>知识库管理</span>
            </el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="数据">
            <el-menu-item index="/admin/feedback">
              <el-icon><ChatDotSquare /></el-icon><span>用户反馈</span>
            </el-menu-item>
            <el-menu-item index="/admin/universities">
              <el-icon><School /></el-icon><span>院校管理</span>
            </el-menu-item>
            <el-menu-item index="/admin/majors">
              <el-icon><Reading /></el-icon><span>专业管理</span>
            </el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="系统">
            <el-menu-item index="/admin/sync">
              <el-icon><Refresh /></el-icon><span>数据同步</span>
            </el-menu-item>
            <el-menu-item index="/admin/stats">
              <el-icon><DataAnalysis /></el-icon><span>数据统计</span>
            </el-menu-item>
            <el-menu-item index="/admin/config">
              <el-icon><Setting /></el-icon><span>系统配置</span>
            </el-menu-item>
          </el-menu-item-group>
        </el-menu>
      </el-aside>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { Monitor, User, Message, QuestionFilled, Document, Edit, Collection, ChatDotSquare, School, Reading, Refresh, DataAnalysis, Setting, SwitchButton } from '@element-plus/icons-vue'

export default {
  name: 'AdminLayout',
  computed: {
    activeMenu() {
      const path = this.$route.path
      if (path === '/admin') return '/admin'
      return path
    }
  },
  methods: {
    logout() {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.app-container { height: 100vh; }
.app-header { display: flex; align-items: center; justify-content: space-between; background: var(--primary-dark, #152a45); color: #fff; padding: 0 20px; height: 56px; }
.header-left { display: flex; align-items: center; }
.header-right { display: flex; align-items: center; gap: 8px; }
.header-right .el-button { color: rgba(255,255,255,.7); }
.header-right .el-button:hover { color: #fff; }
.brand { font-size: 18px; font-weight: 700; }
.app-body { flex: 1; overflow: hidden; }
.app-aside { background: var(--primary-dark, #152a45); overflow-y: auto; }
.app-aside .el-menu { background: transparent; border-right: none; }
.app-aside .el-menu-item { color: rgba(255,255,255,.65); height: 40px; line-height: 40px; }
.app-aside .el-menu-item:hover { background: rgba(255,255,255,.12); color: #fff; }
.app-aside .el-menu-item.is-active { color: #fff; background: rgba(255,255,255,.12); border-left: 3px solid var(--gold, #f0a500); }
.app-aside .el-menu-item-group__title { color: rgba(255,255,255,.35); font-size: 11px; padding: 16px 20px 4px; text-transform: uppercase; letter-spacing: 1px; }
.app-main { background: var(--bg, #f0f4f8); padding: 0; overflow: auto; display: flex; flex-direction: column; }
</style>
