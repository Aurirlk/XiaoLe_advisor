/**
 * DataStatistics - 数据统计组件
 * 显示成本监控、数据统计等信息
 */
const DataStatistics = {
    name: 'DataStatistics',
    template: `
        <div class="data-statistics">
            <div class="section-header">
                <h4>数据统计</h4>
            </div>

            <div class="stats-grid">
                <div class="stats-card">
                    <h5>数据概览</h5>
                    <div class="stats-items">
                        <div class="stat-item">
                            <span class="stat-value">{{ dataStats.universities || 0 }}</span>
                            <span class="stat-label">院校数量</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{{ dataStats.scores || 0 }}</span>
                            <span class="stat-label">分数线记录</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{{ dataStats.majors || 0 }}</span>
                            <span class="stat-label">专业数量</span>
                        </div>
                    </div>
                </div>

                <div class="stats-card">
                    <h5>成本统计</h5>
                    <div class="stats-items">
                        <div class="stat-item">
                            <span class="stat-value">{{ costStats.monthly?.total_cost || 0 }}</span>
                            <span class="stat-label">本月成本(元)</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{{ costStats.monthly?.total_tokens || 0 }}</span>
                            <span class="stat-label">本月Token数</span>
                        </div>
                    </div>
                </div>

                <div class="stats-card full-width">
                    <h5>每日成本趋势</h5>
                    <div class="cost-chart">
                        <div v-if="dailyCosts.length === 0" class="empty">暂无数据</div>
                        <div v-else class="chart-bars">
                            <div 
                                v-for="item in dailyCosts" 
                                :key="item.date"
                                class="chart-bar"
                                :style="{ height: getBarHeight(item.cost) + '%' }"
                                :title="item.date + ': ¥' + item.cost"
                            >
                                <span class="bar-label">{{ item.date.slice(-5) }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            dataStats: {},
            costStats: {},
            dailyCosts: [],
        };
    },
    mounted() {
        this.loadDataStats();
        this.loadCostStats();
    },
    methods: {
        async loadDataStats() {
            try {
                const response = await fetch('/admin/data/stats', {
                    headers: { 'X-Admin-Key': localStorage.getItem('admin_key') || '' },
                });
                const data = await response.json();
                if (data.ok) {
                    this.dataStats = data;
                }
            } catch (error) {
                console.error('加载数据统计失败:', error);
            }
        },
        async loadCostStats() {
            try {
                const response = await fetch('/admin/cost-stats');
                const data = await response.json();
                if (data.ok) {
                    this.costStats = data;
                    this.dailyCosts = data.daily || [];
                }
            } catch (error) {
                console.error('加载成本统计失败:', error);
            }
        },
        getBarHeight(cost) {
            if (!this.dailyCosts.length) return 0;
            const maxCost = Math.max(...this.dailyCosts.map(d => d.cost || 0));
            return maxCost > 0 ? (cost / maxCost) * 100 : 0;
        },
    },
};
