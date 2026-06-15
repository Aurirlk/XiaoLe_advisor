/**
 * AdminLayout - 管理后台布局组件
 * 包含左侧导航栏和右侧内容区
 */
const AdminLayout = {
    name: 'AdminLayout',
    template: `
        <div class="admin-layout">
            <aside class="admin-sidebar">
                <div class="sidebar-header">
                    <h2>🎓 小乐AI 管理后台</h2>
                </div>
                <nav class="sidebar-nav">
                    <a 
                        v-for="item in navItems" 
                        :key="item.key"
                        :class="['nav-item', { active: currentView === item.key }]"
                        @click="currentView = item.key"
                    >
                        <i :class="item.icon"></i>
                        <span>{{ item.label }}</span>
                    </a>
                </nav>
                <div class="sidebar-footer">
                    <button class="logout-btn" @click="handleLogout">
                        <i class="fas fa-sign-out-alt"></i>
                        退出登录
                    </button>
                </div>
            </aside>
            <main class="admin-main">
                <header class="admin-header">
                    <h3>{{ currentTitle }}</h3>
                    <div class="header-actions">
                        <span class="user-info">
                            <i class="fas fa-user-shield"></i>
                            {{ userInfo?.username || '管理员' }}
                        </span>
                    </div>
                </header>
                <div class="admin-content">
                    <knowledge-management v-if="currentView === 'knowledge'"></knowledge-management>
                    <data-sync v-else-if="currentView === 'sync'"></data-sync>
                    <system-management v-else-if="currentView === 'system'"></system-management>
                    <data-statistics v-else-if="currentView === 'stats'"></data-statistics>
                </div>
            </main>
        </div>
    `,
    data() {
        return {
            currentView: 'knowledge',
            navItems: [
                { key: 'knowledge', label: '知识库管理', icon: 'fas fa-database' },
                { key: 'sync', label: '数据同步', icon: 'fas fa-sync-alt' },
                { key: 'system', label: '系统管理', icon: 'fas fa-cog' },
                { key: 'stats', label: '数据统计', icon: 'fas fa-chart-bar' },
            ],
            userInfo: null,
        };
    },
    computed: {
        currentTitle() {
            const item = this.navItems.find(i => i.key === this.currentView);
            return item ? item.label : '';
        },
    },
    mounted() {
        this.userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    },
    methods: {
        handleLogout() {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
            window.location.reload();
        },
    },
};
