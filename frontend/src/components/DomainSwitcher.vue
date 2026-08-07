<template>
  <div class="domain-switcher">
    <el-dropdown trigger="click" @command="switchDomain">
      <span class="domain-trigger">
        <span class="domain-icon">{{ current.icon }}</span>
        <span class="domain-name">{{ current.name }}</span>
        <el-icon><ArrowDown /></el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="d in enabledDomains"
            :key="d.key"
            :command="d.key"
            :class="{ active: activeDomain === d.key }"
          >
            <span class="domain-icon">{{ d.icon }}</span>
            {{ d.name }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue'

const DOMAINS = {
  gaokao:               { icon: '🎓', name: '高考志愿' },
  postgraduate:         { icon: '📚', name: '考研' },
  civil_service:        { icon: '🏛', name: '考公' },
  public_institution:   { icon: '🏢', name: '考编' },
  associate_bachelor:   { icon: '📖', name: '专升本' },
  career:               { icon: '💼', name: '职业规划' },
}

export default {
  name: 'DomainSwitcher',
  data() {
    return {
      activeDomain: localStorage.getItem('xiaole_domain') || 'gaokao',
    }
  },
  computed: {
    current() {
      return DOMAINS[this.activeDomain] || DOMAINS.gaokao
    },
    enabledDomains() {
      return Object.entries(DOMAINS).map(([k, v]) => ({ key: k, ...v }))
    },
  },
  methods: {
    switchDomain(key) {
      this.activeDomain = key
      localStorage.setItem('xiaole_domain', key)
      // 通知全局切换领域
      window.dispatchEvent(new CustomEvent('domain-changed', { detail: key }))
    },
  },
}
</script>

<style scoped>
.domain-switcher {
  padding: 8px 16px;
  border-bottom: 1px solid var(--border, #e2e8f0);
}
.domain-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(30, 58, 95, 0.08);
  font-size: 13px;
  font-weight: 600;
  color: var(--primary, #1e3a5f);
  transition: background 0.2s;
  user-select: none;
}
.domain-trigger:hover {
  background: rgba(30, 58, 95, 0.15);
}
.domain-icon {
  font-size: 16px;
}
.domain-name {
  flex: 1;
}
</style>
