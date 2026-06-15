/**
 * UniversityRanking - 院校排名页面
 * 包含QS、US News、泰晤士、自然指数等主流排名方案
 */
const UniversityRanking = {
    name: 'UniversityRanking',
    template: `
        <div class="university-ranking">
            <!-- 页面标题 -->
            <div class="ranking-header">
                <h2>🏆 院校排名查询</h2>
                <p>汇集全球主流院校排名，助你全面了解院校实力</p>
            </div>

            <!-- 排名来源选择 -->
            <div class="ranking-tabs">
                <button 
                    v-for="source in rankingSources" 
                    :key="source.id"
                    :class="['tab-btn', { active: currentSource === source.id }]"
                    @click="currentSource = source.id"
                >
                    <span class="tab-icon">{{ source.icon }}</span>
                    <span class="tab-name">{{ source.name }}</span>
                </button>
            </div>

            <!-- 当前排名说明 -->
            <div class="ranking-info">
                <div class="info-card">
                    <h3>{{ currentSourceInfo.name }}</h3>
                    <p>{{ currentSourceInfo.description }}</p>
                    <a :href="currentSourceInfo.url" target="_blank" class="source-link">
                        🔗 访问官网查看更多
                    </a>
                </div>
            </div>

            <!-- 搜索和筛选 -->
            <div class="ranking-filter">
                <input 
                    type="text" 
                    v-model="searchKeyword" 
                    placeholder="🔍 搜索院校名称..."
                    class="search-input"
                />
                <select v-model="filterCountry" class="filter-select">
                    <option value="">全部国家/地区</option>
                    <option value="china">中国</option>
                    <option value="usa">美国</option>
                    <option value="uk">英国</option>
                    <option value="japan">日本</option>
                    <option value="korea">韩国</option>
                    <option value="other">其他</option>
                </select>
            </div>

            <!-- 排名表格 -->
            <div class="ranking-table-wrapper">
                <table class="ranking-table">
                    <thead>
                        <tr>
                            <th class="rank-col">排名</th>
                            <th class="name-col">院校名称</th>
                            <th class="country-col">国家/地区</th>
                            <th class="score-col">综合得分</th>
                            <th class="detail-col">详情</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="uni in filteredUniversities" :key="uni.rank" class="ranking-row">
                            <td class="rank-col">
                                <span :class="['rank-badge', getRankClass(uni.rank)]">
                                    {{ uni.rank }}
                                </span>
                            </td>
                            <td class="name-col">
                                <div class="uni-name">
                                    <span class="name">{{ uni.name }}</span>
                                    <span class="name-en">{{ uni.nameEn }}</span>
                                </div>
                            </td>
                            <td class="country-col">
                                <span class="country-flag">{{ uni.flag }}</span>
                                {{ uni.country }}
                            </td>
                            <td class="score-col">
                                <div class="score-bar">
                                    <div class="score-fill" :style="{ width: uni.score + '%' }"></div>
                                    <span class="score-text">{{ uni.score }}</span>
                                </div>
                            </td>
                            <td class="detail-col">
                                <button class="btn-detail" @click="showDetail(uni)">查看详情</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- 详情弹窗 -->
            <div v-if="selectedUni" class="modal-overlay" @click.self="selectedUni = null">
                <div class="modal">
                    <div class="modal-header">
                        <h3>{{ selectedUni.name }}</h3>
                        <button class="btn-close" @click="selectedUni = null">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="detail-grid">
                            <div class="detail-item">
                                <span class="label">综合排名</span>
                                <span class="value">#{{ selectedUni.rank }}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">综合得分</span>
                                <span class="value">{{ selectedUni.score }}/100</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">国家/地区</span>
                                <span class="value">{{ selectedUni.flag }} {{ selectedUni.country }}</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">院校类型</span>
                                <span class="value">{{ selectedUni.type || '综合' }}</span>
                            </div>
                        </div>
                        <div class="detail-section">
                            <h4>📊 各项指标</h4>
                            <div class="indicators">
                                <div v-for="(value, key) in selectedUni.indicators" :key="key" class="indicator">
                                    <span class="indicator-name">{{ key }}</span>
                                    <div class="indicator-bar">
                                        <div class="indicator-fill" :style="{ width: value + '%' }"></div>
                                    </div>
                                    <span class="indicator-value">{{ value }}</span>
                                </div>
                            </div>
                        </div>
                        <div class="detail-section">
                            <h4>🔗 相关链接</h4>
                            <div class="links">
                                <a :href="selectedUni.website" target="_blank" class="link-item">
                                    🏫 官网
                                </a>
                                <a :href="currentSourceInfo.url" target="_blank" class="link-item">
                                    📊 排名详情
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 排名对比说明 -->
            <div class="ranking-comparison">
                <h3>📊 各排名体系对比</h3>
                <div class="comparison-grid">
                    <div v-for="source in rankingSources" :key="source.id" class="comparison-card">
                        <h4>{{ source.icon }} {{ source.name }}</h4>
                        <p>{{ source.focus }}</p>
                        <div class="metrics">
                            <span v-for="metric in source.metrics" :key="metric" class="metric-tag">
                                {{ metric }}
                            </span>
                        </div>
                        <a :href="source.url" target="_blank" class="source-url">
                            {{ source.url }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            currentSource: 'qs',
            searchKeyword: '',
            filterCountry: '',
            selectedUni: null,
            rankingSources: [
                {
                    id: 'qs',
                    name: 'QS世界大学排名',
                    icon: '🌍',
                    description: 'QS世界大学排名是由英国Quacquarelli Symonds公司发布的年度世界大学排名，是历史第二悠久的全球大学排名。',
                    url: 'https://www.topuniversities.com/world-university-rankings',
                    focus: '学术声誉、雇主声誉、师生比、引用率',
                    metrics: ['学术声誉', '雇主声誉', '师生比', '教师引用', '国际教师', '国际学生']
                },
                {
                    id: 'usnews',
                    name: 'US News世界大学排名',
                    icon: '🇺🇸',
                    description: 'US News世界大学排名由美国《美国新闻与世界报道》发布，侧重于学术研究和全球声誉。',
                    url: 'https://www.usnews.com/education/best-global-universities',
                    focus: '学术研究、全球声誉、出版物、引用',
                    metrics: ['全球研究声誉', '区域研究声誉', '出版物', '引用', '国际合作']
                },
                {
                    id: 'times',
                    name: '泰晤士高等教育排名',
                    icon: '📰',
                    description: '泰晤士高等教育世界大学排名是全球最具影响力的大学排名之一，由英国《泰晤士高等教育》发布。',
                    url: 'https://www.timeshighereducation.com/world-university-rankings',
                    focus: '教学、研究、引用、国际化、产业收入',
                    metrics: ['教学', '研究', '引用', '国际化', '产业收入']
                },
                {
                    id: 'nature',
                    name: '自然指数排名',
                    icon: '🔬',
                    description: '自然指数由《自然》杂志发布，追踪全球高校和科研机构在顶级自然科学期刊上的论文发表情况。',
                    url: 'https://www.nature.com/nature-index',
                    focus: '顶级期刊论文发表、科研产出质量',
                    metrics: ['论文数量', '贡献份额', '高质量论文']
                },
                {
                    id: 'arwu',
                    name: '软科世界大学学术排名',
                    icon: '🎓',
                    description: '软科世界大学学术排名（ARWU）由上海交通大学发布，是全球首个综合性世界大学排名。',
                    url: 'https://www.shanghairanking.com',
                    focus: '校友获奖、教师获奖、高被引学者、论文',
                    metrics: ['校友获奖', '教师获奖', '高被引学者', '论文', '人均绩效']
                },
                {
                    id: 'cuhk',
                    name: '中国大学排名',
                    icon: '🇨🇳',
                    description: '中国大学排名由国内权威机构发布，针对中国内地高校进行综合评价。',
                    url: 'https://www.shanghairanking.cn',
                    focus: '人才培养、科学研究、服务社会',
                    metrics: ['生源质量', '培养成果', '科研规模', '科研质量', '高端人才']
                }
            ],
            // 示例数据：QS排名前20
            universities: [
                { rank: 1, name: '麻省理工学院', nameEn: 'MIT', country: '美国', flag: '🇺🇸', score: 100, type: '理工', website: 'https://www.mit.edu' },
                { rank: 2, name: '剑桥大学', nameEn: 'Cambridge', country: '英国', flag: '🇬🇧', score: 99.5, type: '综合', website: 'https://www.cam.ac.uk' },
                { rank: 3, name: '牛津大学', nameEn: 'Oxford', country: '英国', flag: '🇬🇧', score: 99.2, type: '综合', website: 'https://www.ox.ac.uk' },
                { rank: 4, name: '哈佛大学', nameEn: 'Harvard', country: '美国', flag: '🇺🇸', score: 99.0, type: '综合', website: 'https://www.harvard.edu' },
                { rank: 5, name: '斯坦福大学', nameEn: 'Stanford', country: '美国', flag: '🇺🇸', score: 98.8, type: '综合', website: 'https://www.stanford.edu' },
                { rank: 6, name: '帝国理工学院', nameEn: 'Imperial College', country: '英国', flag: '🇬🇧', score: 98.5, type: '理工', website: 'https://www.imperial.ac.uk' },
                { rank: 7, name: '苏黎世联邦理工', nameEn: 'ETH Zurich', country: '瑞士', flag: '🇨🇭', score: 98.2, type: '理工', website: 'https://ethz.ch' },
                { rank: 8, name: '新加坡国立大学', nameEn: 'NUS', country: '新加坡', flag: '🇸🇬', score: 98.0, type: '综合', website: 'https://www.nus.edu.sg' },
                { rank: 9, name: '伦敦大学学院', nameEn: 'UCL', country: '英国', flag: '🇬🇧', score: 97.8, type: '综合', website: 'https://www.ucl.ac.uk' },
                { rank: 10, name: '加州大学伯克利', nameEn: 'UC Berkeley', country: '美国', flag: '🇺🇸', score: 97.5, type: '综合', website: 'https://www.berkeley.edu' },
                { rank: 11, name: '清华大学', nameEn: 'Tsinghua', country: '中国', flag: '🇨🇳', score: 97.2, type: '综合', website: 'https://www.tsinghua.edu.cn' },
                { rank: 12, name: '北京大学', nameEn: 'Peking', country: '中国', flag: '🇨🇳', score: 97.0, type: '综合', website: 'https://www.pku.edu.cn' },
                { rank: 13, name: '复旦大学', nameEn: 'Fudan', country: '中国', flag: '🇨🇳', score: 96.5, type: '综合', website: 'https://www.fudan.edu.cn' },
                { rank: 14, name: '浙江大学', nameEn: 'Zhejiang', country: '中国', flag: '🇨🇳', score: 96.2, type: '综合', website: 'https://www.zju.edu.cn' },
                { rank: 15, name: '上海交通大学', nameEn: 'SJTU', country: '中国', flag: '🇨🇳', score: 96.0, type: '综合', website: 'https://www.sjtu.edu.cn' },
                { rank: 16, name: '中国科学技术大学', nameEn: 'USTC', country: '中国', flag: '🇨🇳', score: 95.8, type: '理工', website: 'https://www.ustc.edu.cn' },
                { rank: 17, name: '南京大学', nameEn: 'Nanjing', country: '中国', flag: '🇨🇳', score: 95.5, type: '综合', website: 'https://www.nju.edu.cn' },
                { rank: 18, name: '武汉大学', nameEn: 'Wuhan', country: '中国', flag: '🇨🇳', score: 95.2, type: '综合', website: 'https://www.whu.edu.cn' },
                { rank: 19, name: '中山大学', nameEn: 'Sun Yat-sen', country: '中国', flag: '🇨🇳', score: 95.0, type: '综合', website: 'https://www.sysu.edu.cn' },
                { rank: 20, name: '华中科技大学', nameEn: 'HUST', country: '中国', flag: '🇨🇳', score: 94.8, type: '理工', website: 'https://www.hust.edu.cn' },
            ],
        };
    },
    computed: {
        currentSourceInfo() {
            return this.rankingSources.find(s => s.id === this.currentSource) || this.rankingSources[0];
        },
        filteredUniversities() {
            let result = this.universities;
            
            // 关键词搜索
            if (this.searchKeyword) {
                const keyword = this.searchKeyword.toLowerCase();
                result = result.filter(u => 
                    u.name.toLowerCase().includes(keyword) || 
                    u.nameEn.toLowerCase().includes(keyword)
                );
            }
            
            // 国家筛选
            if (this.filterCountry) {
                const countryMap = {
                    'china': '中国',
                    'usa': '美国',
                    'uk': '英国',
                    'japan': '日本',
                    'korea': '韩国',
                };
                const country = countryMap[this.filterCountry];
                if (country) {
                    result = result.filter(u => u.country === country);
                }
            }
            
            return result;
        },
    },
    methods: {
        getRankClass(rank) {
            if (rank <= 3) return 'top-3';
            if (rank <= 10) return 'top-10';
            if (rank <= 20) return 'top-20';
            return '';
        },
        showDetail(uni) {
            this.selectedUni = {
                ...uni,
                indicators: {
                    '学术声誉': Math.round(uni.score * 0.95),
                    '雇主声誉': Math.round(uni.score * 0.92),
                    '师生比': Math.round(uni.score * 0.88),
                    '引用率': Math.round(uni.score * 0.90),
                    '国际化': Math.round(uni.score * 0.85),
                }
            };
        },
    },
};
