export default {
  name: 'ProfileCard',
  props: {
    profile: {
      type: Object,
      default: () => ({})
    }
  },
  template: `
    <div class="profile-card">
      <div v-if="!hasAnyProfile" class="empty">
        <i class="fas fa-user-plus" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
        对话开始后自动采集...
      </div>
      <template v-else>
        <div class="field" v-for="field in profileFields" :key="field.key">
          <span class="k">
            <i :class="field.icon"></i>
            {{ field.label }}
          </span>
          <span class="v">{{ formatValue(field.key, profile[field.key]) }}</span>
        </div>
      </template>
    </div>
  `,
  computed: {
    profileFields() {
      return [
        { key: 'province', label: '省份', icon: 'fas fa-map-marker-alt' },
        { key: 'subject_type', label: '选科', icon: 'fas fa-book' },
        { key: 'major_name', label: '专业', icon: 'fas fa-graduation-cap' },
        { key: 'score', label: '分数', icon: 'fas fa-star' },
        { key: 'rank', label: '位次', icon: 'fas fa-trophy' },
        { key: 'target_city', label: '目标城市', icon: 'fas fa-city' },
        { key: 'budget', label: '预算', icon: 'fas fa-coins' }
      ];
    },
    
    hasAnyProfile() {
      return this.profileFields.some(field => this.profile[field.key]);
    }
  },
  methods: {
    formatValue(key, value) {
      if (!value) return '';
      if (key === 'budget') {
        return (value / 10000).toFixed(1) + '万';
      }
      return value;
    }
  }
}