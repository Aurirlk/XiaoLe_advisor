/**
 * DataSync - 数据同步管理组件
 * 管理API数据同步和手动触发
 */
const DataSync = {
    name: 'DataSync',
    template: `
        <div class="data-sync">
            <div class="section-header">
                <h4>数据同步</h4>
            </div>

            <div class="sync-cards">
                <div class="sync-card">
                    <div class="card-icon"><i class="fas fa-university"></i></div>
                    <h5>院校信息同步</h5>
                    <p>从咕咕数据API同步院校基础信息（985/211/双一流）</p>
                    <button class="btn" @click="syncData('college_info', { college_name: '清华大学' })">
                        同步院校信息
                    </button>
                </div>

                <div class="sync-card">
                    <div class="card-icon"><i class="fas fa-chart-line"></i></div>
                    <h5>院校分数线同步</h5>
                    <p>同步院校录取分数线数据</p>
                    <form @submit.prevent="syncCollegeLine" class="sync-form">
                        <input v-model="collegeLineForm.college_name" placeholder="院校名称" required />
                        <input v-model="collegeLineForm.province" placeholder="省份" required />
                        <button type="submit" class="btn" :disabled="syncing">
                            {{ syncing ? '同步中...' : '同步分数线' }}
                        </button>
                    </form>
                </div>

                <div class="sync-card">
                    <div class="card-icon"><i class="fas fa-graduation-cap"></i></div>
                    <h5>专业分数线同步</h5>
                    <p>同步专业录取分数线数据</p>
                    <form @submit.prevent="syncMajorLine" class="sync-form">
                        <input v-model="majorLineForm.major_name" placeholder="专业名称" required />
                        <input v-model="majorLineForm.province" placeholder="省份" required />
                        <button type="submit" class="btn" :disabled="syncing">
                            {{ syncing ? '同步中...' : '同步分数线' }}
                        </button>
                    </form>
                </div>

                <div class="sync-card">
                    <div class="card-icon"><i class="fas fa-map-marker-alt"></i></div>
                    <h5>批次线同步</h5>
                    <p>同步各省批次线数据</p>
                    <form @submit.prevent="syncProvinceCutoff" class="sync-form">
                        <input v-model="cutoffForm.province" placeholder="省份" required />
                        <button type="submit" class="btn" :disabled="syncing">
                            {{ syncing ? '同步中...' : '同步批次线' }}
                        </button>
                    </form>
                </div>
            </div>

            <div v-if="syncResult" class="sync-result" :class="syncResult.ok ? 'success' : 'error'">
                <pre>{{ JSON.stringify(syncResult, null, 2) }}</pre>
            </div>
        </div>
    `,
    data() {
        return {
            syncing: false,
            syncResult: null,
            collegeLineForm: { college_name: '', province: '', year: 2025 },
            majorLineForm: { major_name: '', province: '', year: 2025 },
            cutoffForm: { province: '', year: 2025 },
        };
    },
    methods: {
        async syncData(apiType, params) {
            this.syncing = true;
            this.syncResult = null;
            try {
                const response = await fetch('/admin/knowledge/sync-api', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Key': localStorage.getItem('admin_key') || '',
                    },
                    body: JSON.stringify({ api_type: apiType, params }),
                });
                this.syncResult = await response.json();
            } catch (error) {
                this.syncResult = { ok: false, message: error.message };
            } finally {
                this.syncing = false;
            }
        },
        syncCollegeLine() {
            this.syncData('college_line', this.collegeLineForm);
        },
        syncMajorLine() {
            this.syncData('major_line', this.majorLineForm);
        },
        syncProvinceCutoff() {
            this.syncData('province_cutoff', this.cutoffForm);
        },
    },
};
