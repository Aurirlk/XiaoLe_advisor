/**
 * LoginPage - 登录/注册页面组件
 * 支持手机号+密码登录，角色选择（学生/家长/管理员）
 */
const LoginPage = {
    name: 'LoginPage',
    template: `
        <div class="login-page">
            <div class="login-container">
                <div class="login-header">
                    <h1>🎓 小乐AI</h1>
                    <p>高考志愿填报助手</p>
                </div>

                <div class="login-tabs">
                    <button 
                        :class="['tab-btn', { active: mode === 'login' }]"
                        @click="mode = 'login'"
                    >
                        登录
                    </button>
                    <button 
                        :class="['tab-btn', { active: mode === 'register' }]"
                        @click="mode = 'register'"
                    >
                        注册
                    </button>
                </div>

                <form class="login-form" @submit.prevent="handleSubmit">
                    <div class="form-group">
                        <label>手机号</label>
                        <input 
                            type="tel" 
                            v-model="phone" 
                            placeholder="请输入手机号"
                            maxlength="11"
                            required
                        />
                    </div>

                    <div class="form-group">
                        <label>密码</label>
                        <input 
                            type="password" 
                            v-model="password" 
                            placeholder="请输入密码"
                            required
                        />
                    </div>

                    <div v-if="mode === 'register'" class="form-group">
                        <label>身份选择</label>
                        <div class="role-select">
                            <label class="role-option">
                                <input type="radio" v-model="role" value="student" />
                                <span class="role-label">👤 学生</span>
                            </label>
                            <label class="role-option">
                                <input type="radio" v-model="role" value="parent" />
                                <span class="role-label">👨‍👩‍👧 家长</span>
                            </label>
                            <label class="role-option">
                                <input type="radio" v-model="role" value="admin" />
                                <span class="role-label">🔧 管理员</span>
                            </label>
                        </div>
                    </div>

                    <div v-if="error" class="error-message">
                        {{ error }}
                    </div>

                    <button type="submit" class="submit-btn" :disabled="loading">
                        {{ loading ? '处理中...' : (mode === 'login' ? '登 录' : '注 册') }}
                    </button>
                </form>

                <div class="login-footer">
                    <p>登录即表示同意《用户协议》和《隐私政策》</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            mode: 'login',
            phone: '',
            password: '',
            role: 'student',
            loading: false,
            error: '',
        };
    },
    methods: {
        async handleSubmit() {
            this.error = '';
            this.loading = true;

            try {
                const url = this.mode === 'login' ? '/auth/login' : '/auth/register';
                const body = {
                    phone_number: this.phone,
                    password: this.password,
                };

                if (this.mode === 'register') {
                    body.role = this.role;
                }

                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || '操作失败');
                }

                if (data.token) {
                    localStorage.setItem('auth_token', data.token);
                    localStorage.setItem('user_info', JSON.stringify(data.user));
                    this.$emit('login-success', data.user);
                }
            } catch (err) {
                this.error = err.message;
            } finally {
                this.loading = false;
            }
        },
    },
};
