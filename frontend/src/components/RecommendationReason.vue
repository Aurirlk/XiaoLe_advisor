<template>
  <div v-if="reasons && reasons.length" class="recommendation-reason" style="padding:12px 16px;margin:8px 0;background:rgba(39,174,96,.06);border:1px solid rgba(39,174,96,.2);border-radius:12px">
    <div style="font-size:12px;font-weight:600;color:var(--success,#27ae60);margin-bottom:8px"><i class="fas fa-check-circle"></i> 推荐理由</div>
    <div v-for="(r,i) in reasons" :key="i" style="font-size:13px;color:var(--text);margin-bottom:4px">• {{ r }}</div>
  </div>
</template>
<script>export default { name: 'RecommendationReason', props: { reasons: Array } }</script>
