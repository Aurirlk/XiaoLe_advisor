<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="login-logo">🎓</div>
        <h1>小乐AI</h1>
        <p>高考志愿填报助手</p>
      </div>
      <div class="login-tabs">
        <button
          :class="['tab-btn', { active: mode === 'login' }]"
          @click="mode = 'login'; error = ''"
        >登录</button>
        <button
          :class="['tab-btn', { active: mode === 'register' }]"
          @click="mode = 'register'; error = ''"
        >注册</button>
      </div>
      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label><i class="fas fa-phone"></i> 手机号</label>
          <input type="tel" v-model="phone" placeholder="请输入手机号" maxlength="11" required />
        </div>
        <div class="form-group">
          <label><i class="fas fa-lock"></i> 密码</label>
          <input type="password" v-model="password" placeholder="请输入密码" required />
        </div>
        <div v-if="mode === 'register'" class="form-group">
          <label><i class="fas fa-user-tag"></i> 身份选择</label>
          <div class="role-select">
            <label v-for="r in roles" :key="r.value" :class="['role-option', { active: role === r.value }]">
              <input type="radio" v-model="role" :value="r.value" />
              <span class="role-icon">{{ r.icon }}</span>
              <span class="role-label">{{ r.label }}</span>
            </label>
          </div>
        </div>
        <transition name="fade">
          <div v-if="error" class="error-message">
            <i class="fas fa-exclamation-circle"></i> {{ error }}
          </div>
        </transition>
        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading" class="loading-spinner"></span>
          <span v-else>{{ mode === 'login' ? '登 录' : '注 册' }}</span>
        </button>
      </form>
      <div class="login-footer">
        <p>登录即表示同意《用户协议》和《隐私政策》</p>
      </div>
    </div>
  </div>
</template>

<script>
import apiClient from '../utils/apiClient.js'

export default {
  name: 'LoginView',
  data() {
    return {
      mode: 'login',
      phone: '',
      password: '',
      role: 'student',
      loading: false,
      error: '',
      roles: [
        { value: 'student', label: '学生', icon: '👤' },
        { value: 'parent', label: '家长', icon: '👨‍👩‍👧' },
        { value: 'admin', label: '管理员', icon: '🔧' }
      ]
    }
  },
  methods: {
    async handleSubmit() {
      this.error = ''
      this.loading = true
      try {
        const url = this.mode === 'login' ? '/auth/login' : '/auth/register'
        const body = { phone_number: this.phone, password: this.password }
        if (this.mode === 'register') body.role = this.role
        const data = await apiClient.post(url, body)
        if (data.token) {
          apiClient.setToken(data.token)
          localStorage.setItem('user_info', JSON.stringify(data.user))
          const roleMap = { admin: '/admin', parent: '/parent', student: '/student' }
          this.$router.push(roleMap[data.user.role] || '/student')
        }
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    }
  },
  mounted() {
    const token = localStorage.getItem('auth_token')
    const userInfo = localStorage.getItem('user_info')
    if (token && userInfo) {
      try {
        const user = JSON.parse(userInfo)
        const roleMap = { admin: '/admin', parent: '/parent', student: '/student' }
        this.$router.push(roleMap[user.role] || '/student')
      } catch {}
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--bg) 0%, var(--bg-light) 100%);
  padding: 20px;
}
.login-container {
  background: var(--card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  animation: slideUp 0.4s ease;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
.login-header { text-align: center; margin-bottom: 32px; }
.login-logo { font-size: 56px; margin-bottom: 12px; }
.login-header h1 { font-size: 28px; font-weight: 700; color: var(--primary); margin-bottom: 4px; }
.login-header p { color: var(--text-muted); font-size: 14px; }
.login-tabs { display: flex; gap: 0; margin-bottom: 24px; background: var(--bg); border-radius: var(--radius-sm); padding: 4px; }
.tab-btn { flex: 1; padding: 10px; border: none; background: transparent; color: var(--text-muted); font-size: 14px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: var(--transition); }
.tab-btn.active { background: var(--card); color: var(--primary); box-shadow: var(--shadow); }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; color: var(--text-muted); font-weight: 500; display: flex; align-items: center; gap: 6px; }
.form-group input { padding: 12px 14px; border: 1px solid var(--input-border); border-radius: var(--radius-sm); font-size: 14px; background: var(--input-bg); transition: var(--transition); outline: none; color: var(--text); }
.form-group input:focus { border-color: var(--input-focus-border); box-shadow: var(--input-focus-shadow); }
.role-select { display: flex; gap: 8px; }
.role-option { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 12px 8px; border: 2px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition); }
.role-option.active { border-color: var(--primary); background: rgba(30,58,95,0.05); }
.role-option input { display: none; }
.role-icon { font-size: 24px; }
.role-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.error-message { padding: 10px 14px; background: rgba(231,76,60,0.08); border: 1px solid var(--danger-light); border-radius: var(--radius-sm); color: var(--danger); font-size: 13px; display: flex; align-items: center; gap: 8px; }
.submit-btn { padding: 14px; border: none; border-radius: var(--radius-sm); background: var(--btn-primary-bg); color: var(--btn-primary-text); font-size: 16px; font-weight: 700; cursor: pointer; transition: var(--transition); box-shadow: var(--btn-primary-shadow); }
.submit-btn:hover { box-shadow: var(--btn-primary-hover-shadow); transform: translateY(-1px); }
.submit-btn:disabled { opacity: 0.7; cursor: not-allowed; transform: none; }
.login-footer { text-align: center; margin-top: 20px; font-size: 12px; color: var(--text-light); }
.loading-spinner { display: inline-block; width: 20px; height: 20px; border: 2px solid rgba(255,255,255,.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
