<template>
  <div v-if="response" class="fallback-card" style="padding:16px;margin:8px 0;background:var(--tip-bg,linear-gradient(135deg,#fffbeb,#fef3c7));border:1px solid var(--tip-border,#fde68a);border-radius:12px">
    <div style="font-size:13px;color:var(--tip-text,#92400e);line-height:1.6" v-html="safeResponse"></div>
    <div style="margin-top:8px;display:flex;gap:8px">
      <button @click="$emit('accept')" style="padding:6px 16px;border:none;border-radius:8px;background:var(--primary);color:#fff;font-size:12px;cursor:pointer">接受建议</button>
      <button @click="$emit('dismiss')" style="padding:6px 16px;border:1px solid var(--border);border-radius:8px;background:transparent;font-size:12px;cursor:pointer">跳过</button>
    </div>
  </div>
</template>
<script>import { sanitizeHtml } from '@/utils/sanitize'; export default { name: 'FallbackCard', props: { response: String, decisionState: String }, emits: ['accept','dismiss'], computed: { safeResponse() { return sanitizeHtml(this.response) } } }</script>
