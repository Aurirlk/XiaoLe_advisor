/**
 * API Client - 带Token认证的HTTP请求拦截器
 * 自动在请求头中注入Authorization: Bearer <token>
 */

const API_BASE = window.API_BASE || 'http://127.0.0.1:8000';

class ApiClient {
    constructor() {
        this.baseURL = API_BASE;
    }

    getToken() {
        return localStorage.getItem('auth_token');
    }

    setToken(token) {
        localStorage.setItem('auth_token', token);
    }

    removeToken() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
    }

    isLoggedIn() {
        return !!this.getToken();
    }

    getUserInfo() {
        const info = localStorage.getItem('user_info');
        return info ? JSON.parse(info) : null;
    }

    async refreshToken() {
        try {
            const token = this.getToken();
            if (!token) return false;
            const response = await fetch(`${this.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.token) {
                    this.setToken(data.token);
                    return true;
                }
            }
            return false;
        } catch (e) {
            return false;
        }
    }

    async request(url, options = {}) {
        const fullURL = url.startsWith('http') ? url : `${this.baseURL}${url}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            let response = await fetch(fullURL, {
                ...options,
                headers,
            });

            if (response.status === 401) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    headers['Authorization'] = `Bearer ${this.getToken()}`;
                    response = await fetch(fullURL, { ...options, headers });
                } else {
                    this.removeToken();
                    window.dispatchEvent(new CustomEvent('auth:expired'));
                    throw new Error('登录已过期，请重新登录');
                }
            }

            let data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `请求失败: ${response.status}`);
            }

            // 统一响应格式：{code: 0, data: ..., message: "success"}
            // 自动解包，保持前端代码兼容
            if (data && typeof data === 'object' && 'code' in data) {
                if (data.code !== 0) {
                    throw new Error(data.message || '请求失败');
                }
                return data.data !== undefined ? data.data : data;
            }

            return data;
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('网络连接失败，请检查网络');
            }
            throw error;
        }
    }

    get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    }

    post(url, body, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    put(url, body, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(body),
        });
    }

    delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
}

const apiClient = new ApiClient();

export default apiClient;
