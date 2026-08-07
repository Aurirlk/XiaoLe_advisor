<template>
  <div v-if="questions && questions.length" class="progressive-questions" style="padding:16px;margin:8px 0;background:var(--card);border-radius:12px;border:1px solid var(--border)">
    <p style="font-size:13px;color:var(--text-muted);margin-bottom:8px">选填以下信息，获得更精准的建议：</p>
    <div v-for="q in questions" :key="q.field" style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
      <label style="font-size:13px;color:var(--text);min-width:80px">{{ q.label }}</label>
      <input v-model="answers[q.field]" style="flex:1;padding:6px 12px;border:1px solid var(--border);border-radius:8px;font-size:13px" :placeholder="q.placeholder" />
      <button @click="$emit('answer', q.field, answers[q.field])" style="padding:6px 12px;border:none;border-radius:8px;background:var(--primary);color:#fff;font-size:12px;cursor:pointer">确定</button>
    </div>
  </div>
</template>
<script>export default { name: 'ProgressiveQuestions', props: { questions: Array }, emits: ['answer'], data() { return { answers: {} } } }</script>
