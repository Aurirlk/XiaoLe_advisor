<template>
  <div v-if="scene" class="intent-indicator" style="padding:8px 16px;font-size:12px;color:var(--text-muted);display:flex;gap:12px;align-items:center;border-bottom:1px solid var(--border)">
    <span v-if="scene">场景: {{ scene }} ({{ (sceneConfidence*100).toFixed(0) }}%)</span>
    <span v-if="path">路径: {{ path }}</span>
    <span v-if="decision">决策: {{ decision }}</span>
  </div>
</template>
<script>export default { name: 'IntentIndicator', props: { scene: String, sceneConfidence: Number, path: String, pathConfidence: Number, decision: String } }</script>
