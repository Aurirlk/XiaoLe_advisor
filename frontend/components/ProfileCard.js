export default {
  name: 'ProfileCard',
  props: {
    profile: { type: Object, default: () => ({}) },
    parentProfile: { type: Object, default: () => ({}) },
    familyContext: { type: Object, default: () => ({}) },
    subjectScores: { type: Object, default: () => ({}) }
  },
  template: `
    <div class="profile-card">
      <div v-if="!hasAnyProfile" class="empty">
        <i class="fas fa-user-plus" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
        对话开始后自动采集...
      </div>

      <template v-else>
        <!-- 学生画像 -->
        <div class="profile-section">
          <div class="section-title"><i class="fas fa-user-graduate"></i> 学生画像</div>
          <div class="field" v-for="f in studentFields" :key="f.key">
            <span class="k"><i :class="f.icon"></i> {{ f.label }}</span>
            <span class="v">{{ formatValue(f.key, profile[f.key]) }}</span>
          </div>
          <div class="field" v-if="interestsText">
            <span class="k"><i class="fas fa-heart"></i> 兴趣</span>
            <span class="v">{{ interestsText }}</span>
          </div>
          <div class="field" v-if="universitiesText">
            <span class="k"><i class="fas fa-university"></i> 目标院校</span>
            <span class="v">{{ universitiesText }}</span>
          </div>
        </div>

        <!-- 学科评分 -->
        <div class="profile-section" v-if="hasSubjectScores">
          <div class="section-title"><i class="fas fa-chart-bar"></i> 学科评分</div>
          <div class="subject-grid">
            <div v-for="(s, i) in subjectNames" :key="s" class="subject-item" :class="subjectClass(i)">
              <span class="subj-name">{{ s }}</span>
              <span class="subj-score">{{ subjectDisplay(i) }}</span>
            </div>
          </div>
          <div class="field" v-if="strongText">
            <span class="k"><i class="fas fa-arrow-up"></i> 强势</span>
            <span class="v strong">{{ strongText }}</span>
          </div>
          <div class="field" v-if="weakText">
            <span class="k"><i class="fas fa-arrow-down"></i> 弱势</span>
            <span class="v weak">{{ weakText }}</span>
          </div>
        </div>

        <!-- 家长画像 -->
        <div class="profile-section" v-if="hasParentProfile">
          <div class="section-title"><i class="fas fa-user-tie"></i> 家长画像</div>
          <div class="field" v-for="f in parentFields" :key="f.key">
            <span class="k"><i :class="f.icon"></i> {{ f.label }}</span>
            <span class="v">{{ formatParentValue(f.key, parentProfile[f.key]) }}</span>
          </div>
        </div>

        <!-- 家庭背景 -->
        <div class="profile-section" v-if="hasFamilyContext">
          <div class="section-title"><i class="fas fa-home"></i> 家庭背景</div>
          <div class="field" v-for="f in familyFields" :key="f.key">
            <span class="k"><i :class="f.icon"></i> {{ f.label }}</span>
            <span class="v">{{ formatFamilyValue(f.key, familyContext[f.key]) }}</span>
          </div>
        </div>
      </template>
    </div>
  `,
  data() {
    return {
      subjectNames: ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理']
    }
  },
  computed: {
    studentFields() {
      return [
        { key: 'province', label: '省份', icon: 'fas fa-map-marker-alt' },
        { key: 'subject_type', label: '选科', icon: 'fas fa-book' },
        { key: 'gender', label: '性别', icon: 'fas fa-venus-mars' },
        { key: 'score', label: '分数', icon: 'fas fa-star' },
        { key: 'rank', label: '位次', icon: 'fas fa-trophy' },
        { key: 'major_name', label: '专业', icon: 'fas fa-graduation-cap' },
        { key: 'target_city', label: '目标城市', icon: 'fas fa-city' },
        { key: 'budget', label: '预算', icon: 'fas fa-coins' },
        { key: 'postgraduate_plan', label: '读研', icon: 'fas fa-book-reader' },
        { key: 'risk_tolerance', label: '风险偏好', icon: 'fas fa-balance-scale' },
      ]
    },
    parentFields() {
      return [
        { key: 'role', label: '角色', icon: 'fas fa-user' },
        { key: 'industry', label: '行业', icon: 'fas fa-briefcase' },
        { key: 'education', label: '学历', icon: 'fas fa-graduation-cap' },
        { key: 'expectation', label: '期望', icon: 'fas fa-star' },
        { key: 'decision_weight', label: '决策风格', icon: 'fas fa-balance-scale' },
      ]
    },
    familyFields() {
      return [
        { key: 'income_level', label: '收入水平', icon: 'fas fa-money-bill' },
        { key: 'annual_budget', label: '年预算', icon: 'fas fa-coins' },
        { key: 'is_only_child', label: '独生子女', icon: 'fas fa-child' },
        { key: 'decision_maker', label: '决策人', icon: 'fas fa-user-shield' },
        { key: 'location_preference', label: '出省意愿', icon: 'fas fa-plane' },
        { key: 'parent_consensus', label: '家校一致', icon: 'fas fa-handshake' },
      ]
    },
    hasAnyProfile() {
      return this.hasStudentProfile || this.hasParentProfile || this.hasFamilyContext
    },
    hasStudentProfile() {
      return this.studentFields.some(f => this.profile[f.key])
    },
    hasParentProfile() {
      return this.parentFields.some(f => this.parentProfile[f.key])
    },
    hasFamilyContext() {
      return this.familyFields.some(f => this.familyContext[f.key])
    },
    hasSubjectScores() {
      const ss = this.subjectScores
      return ss && (ss.strong_subjects?.length || ss.weak_subjects?.length || ss.gaokao_scores?.some(s => s != null))
    },
    interestsText() {
      return (this.profile.interests || []).join('、')
    },
    universitiesText() {
      return (this.profile.target_universities || []).join('、')
    },
    strongText() {
      return (this.subjectScores.strong_subjects || []).join('、')
    },
    weakText() {
      return (this.subjectScores.weak_subjects || []).join('、')
    }
  },
  methods: {
    formatValue(key, value) {
      if (!value) return '-'
      if (key === 'budget') return (value / 10000).toFixed(1) + '万'
      if (key === 'gender') return value === 'male' ? '男' : value === 'female' ? '女' : value
      if (key === 'postgraduate_plan') return value === 'yes' ? '是' : value === 'no' ? '否' : value
      if (key === 'risk_tolerance') {
        return { aggressive: '激进冲高', balanced: '均衡', conservative: '保守求稳' }[value] || value
      }
      return value
    },
    formatParentValue(key, value) {
      if (!value) return '-'
      if (key === 'role') {
        return { father: '父亲', mother: '母亲', grandfather: '祖父', grandmother: '祖母', other: '其他' }[value] || value
      }
      if (key === 'decision_weight') {
        return { dominant: '主导型', consultative: '协商型', independent: '放手型' }[value] || value
      }
      return value
    },
    formatFamilyValue(key, value) {
      if (value === '' || value === null || value === undefined || value === -1) return '-'
      if (key === 'income_level') return { low: '较低', medium: '中等', high: '较高' }[value] || value
      if (key === 'annual_budget') return value ? (value / 10000).toFixed(1) + '万' : '-'
      if (key === 'is_only_child') return value === true || value === 1 ? '是' : value === false || value === 0 ? '否' : '-'
      if (key === 'decision_maker') return { student: '学生自主', parent: '家长主导', joint: '共同决策' }[value] || value
      if (key === 'location_preference') return { local: '留本省', nearby: '就近', anywhere: '无所谓' }[value] || value
      if (key === 'parent_consensus') return { agree: '一致', partial: '部分一致', disagree: '有分歧', unknown: '待了解' }[value] || value
      return value
    },
    subjectClass(index) {
      const gaokao = this.subjectScores.gaokao_scores || []
      const rank = this.subjectScores.self_rank || []
      if (gaokao[index] != null) return 'has-score'
      if (rank[index] === 'excellent') return 'strong'
      if (rank[index] === 'weak') return 'weak'
      return 'empty'
    },
    subjectDisplay(index) {
      const gaokao = this.subjectScores.gaokao_scores || []
      const rank = this.subjectScores.self_rank || []
      if (gaokao[index] != null) return gaokao[index]
      if (rank[index] === 'excellent') return '强'
      if (rank[index] === 'weak') return '弱'
      return '-'
    }
  }
}
