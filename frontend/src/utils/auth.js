/**
 * auth.js - 统一认证模块
 * 管理 token、登录态检查、角色判断
 */
const AUTH_TOKEN_KEY = 'auth_token'
const USER_INFO_KEY = 'user_info'

const auth = {
  /**
   * 获取 token
   */
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  },

  /**
   * 设置 token
   */
  setToken(token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  },

  /**
   * 移除 token
   */
  removeToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(USER_INFO_KEY)
  },

  /**
   * 是否已登录
   */
  isLoggedIn() {
    return !!this.getToken()
  },

  /**
   * 获取用户信息
   */
  getUserInfo() {
    const info = localStorage.getItem(USER_INFO_KEY)
    return info ? JSON.parse(info) : null
  },

  /**
   * 设置用户信息
   */
  setUserInfo(user) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
  },

  /**
   * 获取当前用户角色
   */
  getRole() {
    const user = this.getUserInfo()
    return user ? user.role : null
  },

  /**
   * 是否是学生
   */
  isStudent() {
    return this.getRole() === 'student'
  },

  /**
   * 是否是家长
   */
  isParent() {
    return this.getRole() === 'parent'
  },

  /**
   * 是否是管理员
   */
  isAdmin() {
    return this.getRole() === 'admin'
  },

  /**
   * 登出
   */
  logout() {
    this.removeToken()
    window.dispatchEvent(new CustomEvent('auth:expired'))
  },

  /**
   * 登录成功处理
   */
  onLoginSuccess(token, user) {
    this.setToken(token)
    this.setUserInfo(user)
    window.dispatchEvent(new CustomEvent('auth:login', { detail: user }))
  },

  /**
   * 检查 token 是否即将过期（可选，需要后端支持）
   */
  async refreshToken() {
    try {
      const token = this.getToken()
      if (!token) return false

      const response = await fetch(`${window.API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        if (data.token) {
          this.setToken(data.token)
          return true
        }
      }
      return false
    } catch (e) {
      return false
    }
  }
}

export default auth
