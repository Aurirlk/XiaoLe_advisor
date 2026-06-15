/**
 * SystemManagement - 系统管理组件
 * 模型配置、成本监控、服务状态
 */
const SystemManagement = {
    name: 'SystemManagement',
    template: `
        <div class="system-management">
            <div class="section-header">
                <h4>系统管理</h4>
            </div>

            <div class="system-sections">
                <div class="system-section">
                    <h5>模型配置</h5>
                    <div class="config-card">
                        <p>当前模型: {{ currentModel }}</p>
                        <div class="model-presets">
                            <button 
                                v-for="preset in modelPresets" 
                                :key="preset"
                                class="btn btn-sm"
                                :class="{ active: preset === currentModel }"
                                @click="switchModel(preset)"
                            >
                                {{ preset }}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="system-section">
                    <h5>服务状态</h5>
                    <div class="status-grid">
                        <div class="status-item">
                            <span class="status-label">数据库</span>
                            <span :class="['status-indicator', serviceStatus.db_ready ? 'online' : 'offline']">
                                {{ serviceStatus.db_ready ? '正常' : '离线' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Redis</span>
                            <span :class="['status-indicator', serviceStatus.redis_ready ? 'online' : 'offline']">
                                {{ serviceStatus.redis_ready ? '正常' : '离线' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">LangGraph</span>
                            <span :class="['status-indicator', serviceStatus.graph_ready ? 'online' : 'offline']">
                                {{ serviceStatus.graph_ready ? '正常' : '离线' }}
                            </span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">向量库</span>
                            <span :class="['status-indicator', serviceStatus.vector_ready ? 'online' : 'offline']">
                                {{ serviceStatus.vector_ready ? '正常' : '离线' }}
                            </span>
                        </div>
                    </div>
                </div>

                <div class="system-section">
                    <h5>运行信息</h5>
                    <div class="info-card">
                        <p>运行时间: {{ formatUptime(serviceStatus.uptime_seconds) }}</p>
                        <p>启动时间: {{ formatDate(serviceStatus.started_at) }}</p>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            currentModel: '',
            modelPresets: [],
            serviceStatus: {},
        };
    },
    mounted() {
        this.loadModelPresets();
        this.loadServiceStatus();
    },
    methods: {
        async loadModelPresets() {
            try {
                const response = await fetch('/admin/model-presets');
                const data = await response.json();
                if (data.ok) {
                    this.modelPresets = data.presets;
                }
            } catch (error) {
                console.error('加载模型预设失败:', error);
            }
        },
        async loadServiceStatus() {
            try {
                const response = await fetch('/status');
                this.serviceStatus = await response.json();
            } catch (error) {
                console.error('加载服务状态失败:', error);
            }
        },
        async switchModel(preset) {
            try {
                const response = await fetch('/admin/switch-model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ preset }),
                });
                const data = await response.json();
                if (data.ok) {
                    this.currentModel = preset;
                    alert('模型切换成功');
                }
            } catch (error) {
                console.error('切换模型失败:', error);
            }
        },
        formatUptime(seconds) {
            if (!seconds) return '--';
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return hours > 0 ? hours + '小时' + minutes + '分钟' : minutes + '分钟';
        },
        formatDate(timestamp) {
            if (!timestamp) return '--';
            return new Date(timestamp * 1000).toLocaleString('zh-CN');
        },
    },
};
