<template>
  <div class="voice-output" v-if="text">
    <button class="tts-btn" :class="{playing:isPlaying}" @click="toggle" :disabled="loading" title="朗读回复">
      <i :class="loading?'fas fa-spinner fa-spin':isPlaying?'fas fa-pause':'fas fa-volume-up'" />
    </button>
  </div>
</template>
<script>
export default {
  name: 'VoiceOutput', props: { text: { type: String, default: '' }, autoPlay: { type: Boolean, default: false }, emotion: String, emotionIntensity: Number },
  data() { return { isPlaying: false, loading: false, audio: null } },
  methods: {
    toggle() { if (this.isPlaying) { this.stop() } else { this.speak() } },
    async speak() {
      if (!this.text || this.loading) return; this.loading = true
      try {
        const r = await fetch(`${window.API_BASE||''}/voice/tts`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:this.text,emotion:this.emotion||'',emotion_intensity:this.emotionIntensity||0.5}) })
        if (!r.ok) throw Error('TTS failed')
        const blob = await r.blob(); const url = URL.createObjectURL(blob)
        this.audio = new Audio(url); this.audio.onended = () => { this.isPlaying = false; URL.revokeObjectURL(url) }
        this.audio.play(); this.isPlaying = true
      } catch {} finally { this.loading = false }
    },
    stop() { if (this.audio) { this.audio.pause(); this.audio.currentTime = 0 }; this.isPlaying = false }
  },
  beforeUnmount() { this.stop() }
}
</script>
<style scoped>.voice-output{display:inline-flex;align-items:center;margin-top:8px}.tts-btn{width:36px;height:36px;border-radius:50%;border:1px solid var(--border);background:var(--bg-light);color:var(--primary);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:var(--transition)}.tts-btn:hover{border-color:var(--primary);background:rgba(30,58,95,.05)}.tts-btn.playing{background:var(--primary);color:#fff}.tts-btn:disabled{opacity:.5;cursor:not-allowed}</style>
