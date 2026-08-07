<template>
  <div class="path-panel">
    <div class="path-header" @click="expanded = !expanded">
      <span>🗺 学习路径</span>
      <el-icon :class="['arrow', expanded ? 'up' : '']"><ArrowDown /></el-icon>
    </div>
    <el-collapse-transition>
      <div v-show="expanded" class="path-body">
        <div v-if="!paths.length" style="text-align:center;padding:12px;color:#718096;font-size:12px">加载中...</div>
        <el-timeline v-else>
          <el-timeline-item
            v-for="path in paths"
            :key="path.id"
            :timestamp="path.for"
            placement="top"
          >
            <div class="path-card" @click="selectPath(path)">
              <div class="path-name">{{ path.name }}</div>
              <div class="path-steps">{{ path.steps.length }} 步规划</div>
            </div>
          </el-timeline-item>
        </el-timeline>

        <!-- 步骤详情弹窗 -->
        <el-dialog v-model="showDetail" :title="selectedPath?.name" width="500px">
          <el-steps direction="vertical" v-if="selectedPath">
            <el-step
              v-for="step in selectedPath.steps"
              :key="step.order"
              :title="step.title"
              :description="step.desc"
              status="process"
            />
          </el-steps>
          <template #footer>
            <el-button @click="showDetail=false">关闭</el-button>
          </template>
        </el-dialog>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'CareerPathPanel',
  data() {
    return {
      expanded: false,
      paths: [],
      selectedPath: null,
      showDetail: false,
    }
  },
  methods: {
    async loadPaths() {
      try {
        const r = await fetch('/api/career/paths')
        const d = await r.json()
        if (d.code === 0) this.paths = d.data.paths
      } catch {}
    },
    selectPath(p) {
      this.selectedPath = p
      this.showDetail = true
    }
  },
  mounted() {
    this.loadPaths()
  }
}
</script>

<style scoped>
.path-panel { font-size: 13px; }
.path-header { display: flex; align-items: center; gap: 8px; padding: 12px 20px; cursor: pointer; color: var(--text-muted, #718096); user-select: none; }
.path-header:hover { color: var(--primary, #1e3a5f); }
.arrow { font-size: 12px; margin-left: auto; transition: transform 0.2s; }
.arrow.up { transform: rotate(180deg); }
.path-body { padding: 0 12px 12px; }
.path-card { padding: 6px 10px; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
.path-card:hover { background: var(--bg-light, #f8fafc); }
.path-name { font-weight: 600; color: var(--text, #1a202c); }
.path-steps { font-size: 11px; color: var(--text-light, #a0aec0); margin-top: 2px; }
</style>
