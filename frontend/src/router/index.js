import { createRouter, createWebHashHistory } from 'vue-router'

import StudentLayout from '../layouts/StudentLayout.vue'
import ParentLayout from '../layouts/ParentLayout.vue'
import AdminLayout from '../layouts/AdminLayout.vue'

const routes = [
  { path: '/', redirect: '/student' },

  // 登录（不使用 Layout）
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue'), meta: { guest: true } },

  // 学生端
  {
    path: '/student',
    component: StudentLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/student/chat' },
      { path: 'chat', name: 'StudentChat', component: () => import('../views/StudentView.vue') },
      { path: 'ranking', name: 'StudentRanking', component: () => import('../views/RankingView.vue') },
      { path: 'graph', name: 'StudentGraph', component: () => import('../views/GraphView.vue') },
    ]
  },

  // 家长端
  {
    path: '/parent',
    component: ParentLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/parent/chat' },
      { path: 'chat', name: 'ParentChat', component: () => import('../views/ParentView.vue') },
      { path: 'questionnaire', name: 'ParentQuestionnaire', component: () => import('../views/QuestionnaireView.vue') },
    ]
  },

  // 用户端辅助页面
  { path: '/notifications', name: 'Notifications', component: () => import('../views/NotificationsView.vue'), meta: { requiresAuth: true } },
  { path: '/faq', name: 'FaqBrowser', component: () => import('../views/FaqBrowserView.vue'), meta: { requiresAuth: true } },

  // 管理端
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      { path: '', name: 'Admin', component: () => import('../views/AdminView.vue') },
      { path: 'users', name: 'AdminUsers', component: () => import('../views/admin/UsersView.vue') },
      { path: 'announcements', name: 'AdminAnnouncements', component: () => import('../views/admin/AnnouncementsView.vue') },
      { path: 'faqs', name: 'AdminFaqs', component: () => import('../views/admin/FaqsView.vue') },
      { path: 'guides', name: 'AdminGuides', component: () => import('../views/admin/GuidesView.vue') },
      { path: 'keywords', name: 'AdminKeywords', component: () => import('../views/admin/KeywordsView.vue') },
      { path: 'knowledge', name: 'AdminKnowledge', component: () => import('../views/admin/KnowledgeView.vue') },
      { path: 'feedback', name: 'AdminFeedback', component: () => import('../views/admin/FeedbackView.vue') },
      { path: 'universities', name: 'AdminUniversities', component: () => import('../views/admin/UniversitiesView.vue') },
      { path: 'majors', name: 'AdminMajors', component: () => import('../views/admin/MajorsView.vue') },
      { path: 'sync', name: 'AdminSync', component: () => import('../views/admin/SyncView.vue') },
      { path: 'stats', name: 'AdminStats', component: () => import('../views/admin/StatsView.vue') },
      { path: 'config', name: 'AdminConfig', component: () => import('../views/admin/ConfigView.vue') },
    ]
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')
  const userInfo = localStorage.getItem('user_info')

  if (to.meta.requiresAuth && !token) return next('/login')

  // 管理员角色检查
  if (to.meta.requiresAuth && to.meta.roles?.includes('admin')) {
    try {
      const u = JSON.parse(userInfo)
      if (u.role !== 'admin') return next('/student/chat')
    } catch { return next('/login') }
  }

  // 已登录用户访问登录页时跳转到对应角色首页
  if (to.meta.guest && token) {
    try {
      const u = JSON.parse(userInfo)
      const m = { admin: '/admin', parent: '/parent/chat', student: '/student/chat' }
      return next(m[u.role] || '/student/chat')
    } catch { return next('/student/chat') }
  }

  next()
})

export default router
