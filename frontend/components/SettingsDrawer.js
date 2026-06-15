/**
 * SettingsDrawer - 右侧设置抽屉
 * 参考 XiaoZhi voice_chat_ui.py 的设置面板设计
 * Tab: 个性化 | 网络 | AI | 语音 | 情感 | 高级
 */
export default {
  name: 'SettingsDrawer',
  props: {
    visible: { type: Boolean, default: false }
  },
  emits: ['close', 'save', 'switch-theme', 'switch-model'],
  data() {
    return {
      activeTab: 'personal',
      settings: this.loadSettings(),
      presets: { llm: [], asr: [], tts: [], vllm: [] }
    }
  },
  template: `
    <div v-if="visible" class="settings-overlay" @click.self="$emit('close')">
      <div class="settings-drawer">
        <!-- 头部 -->
        <div class="drawer-header">
          <h2><i class="fas fa-cog"></i> 设置</h2>
          <button class="drawer-close" @click="$emit('close')"><i class="fas fa-times"></i></button>
        </div>

        <!-- Tab 栏 -->
        <div class="drawer-tabs">
          <button v-for="tab in tabs" :key="tab.id"
            class="drawer-tab" :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id">
            <i :class="tab.icon"></i> {{ tab.label }}
          </button>
        </div>

        <!-- Tab 内容 -->
        <div class="drawer-body">

          <!-- 🎨 个性化 -->
          <div v-show="activeTab === 'personal'" class="tab-panel">
            <div class="form-group">
              <label>主题颜色</label>
              <div class="theme-grid">
                <button v-for="t in themes" :key="t.id"
                  class="theme-dot" :class="{ active: settings.theme === t.id }"
                  :style="{ background: t.color }"
                  :title="t.name"
                  @click="settings.theme = t.id; $emit('switch-theme', t.id)">
                </button>
              </div>
            </div>
            <div class="form-group">
              <label>回复模式</label>
              <div class="radio-group">
                <label v-for="m in replyModes" :key="m" class="radio-label">
                  <input type="radio" v-model="settings.reply_mode" :value="m" />
                  {{ m }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label>音量 <span class="value-badge">{{ settings.volume }}%</span></label>
              <input type="range" v-model.number="settings.volume" min="0" max="100" step="5" class="slider" />
            </div>
            <div class="form-group">
              <label>音色</label>
              <select v-model="settings.voice" class="select">
                <option v-for="v in voiceOptions" :key="v.id" :value="v.id">
                  {{ v.name }} ({{ v.gender === 'male' ? '男' : '女' }})
                </option>
              </select>
            </div>
          </div>

          <!-- 🌐 网络 -->
          <div v-show="activeTab === 'network'" class="tab-panel">
            <div class="form-group">
              <label>WebSocket 地址</label>
              <input type="text" v-model="settings.ws_address" class="input" placeholder="ws://127.0.0.1:8001" />
            </div>
            <div class="form-group">
              <label>API 地址</label>
              <input type="text" v-model="settings.api_address" class="input" placeholder="http://127.0.0.1:8000" />
            </div>
          </div>

          <!-- 🧠 AI -->
          <div v-show="activeTab === 'ai'" class="tab-panel">
            <div class="form-group">
              <label>LLM 模型</label>
              <select v-model="settings.llm_model" class="select" @change="$emit('switch-model', settings.llm_model)">
                <option v-for="p in presets.llm" :key="p.name" :value="p.name">
                  {{ p.name }} — {{ p.description || p.model }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Temperature <span class="value-badge">{{ settings.temperature }}</span></label>
              <input type="range" v-model.number="settings.temperature" min="0" max="2" step="0.1" class="slider" />
            </div>
            <div class="form-group">
              <label>上下文轮数 <span class="value-badge">{{ settings.context_rounds }}</span></label>
              <input type="range" v-model.number="settings.context_rounds" min="0" max="10" step="1" class="slider" />
            </div>
            <div class="form-group">
              <label>最大 Token <span class="value-badge">{{ settings.max_tokens }}</span></label>
              <input type="range" v-model.number="settings.max_tokens" min="256" max="8192" step="256" class="slider" />
            </div>
            <div class="form-group" v-if="presets.vllm && presets.vllm.length">
              <label>视觉模型 <span class="tag">VLLM</span></label>
              <select v-model="settings.vllm_model" class="select">
                <option v-for="p in presets.vllm" :key="p.name" :value="p.name">
                  {{ p.name }} — {{ p.description || p.model }}
                </option>
              </select>
              <p class="hint">用于图片理解、图文分析</p>
            </div>
          </div>

          <!-- 🎤 语音 -->
          <div v-show="activeTab === 'voice'" class="tab-panel">
            <div class="form-group">
              <label>ASR 引擎</label>
              <select v-model="settings.asr_engine" class="select">
                <option v-for="p in presets.asr" :key="p.name" :value="p.name">
                  {{ p.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>TTS 引擎</label>
              <select v-model="settings.tts_engine" class="select">
                <option v-for="p in presets.tts" :key="p.name" :value="p.name">
                  {{ p.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>VAD 模式</label>
              <div class="radio-group">
                <label class="radio-label"><input type="radio" v-model="settings.vad_mode" value="hold" /> 按住说话</label>
                <label class="radio-label"><input type="radio" v-model="settings.vad_mode" value="click" /> 点击录音</label>
                <label class="radio-label"><input type="radio" v-model="settings.vad_mode" value="continuous" /> 连续对话</label>
              </div>
            </div>
            <div class="form-group">
              <label>流式 TTS <span class="tag">WebSocket</span></label>
              <label class="toggle-label">
                <input type="checkbox" v-model="settings.streaming_tts" class="toggle" />
                <span>启用边合成边推送</span>
              </label>
            </div>
          </div>

          <!-- 🎭 情感 -->
          <div v-show="activeTab === 'emotion'" class="tab-panel">
            <div class="form-group">
              <label>情感分析方案</label>
              <div class="radio-group">
                <label class="radio-label"><input type="radio" v-model="settings.emotion_method" value="keyword" /> 关键词规则（免费）</label>
                <label class="radio-label"><input type="radio" v-model="settings.emotion_method" value="llm" /> LLM 提取（准确）</label>
              </div>
              <p class="hint">关键词规则零成本；LLM 提取更准确但多一次 API 调用</p>
            </div>
            <div class="form-group">
              <label>情绪 TTS</label>
              <label class="toggle-label">
                <input type="checkbox" v-model="settings.emotion_tts_enabled" class="toggle" />
                <span>根据情绪调整语音语调</span>
              </label>
              <p class="hint">需要 TTS 引擎支持（Edge TTS 不支持，推荐阿里 CosyVoice）</p>
            </div>
            <div class="form-group">
              <label>情绪强度 <span class="value-badge">{{ settings.emotion_intensity }}</span></label>
              <input type="range" v-model.number="settings.emotion_intensity" min="0" max="1" step="0.1" class="slider" />
            </div>
          </div>

          <!-- ⚡ 高级 -->
          <div v-show="activeTab === 'advanced'" class="tab-panel">
            <div class="form-group">
              <label>Function Calling 工具</label>
              <div class="checkbox-group">
                <label v-for="tool in fcTools" :key="tool.id" class="checkbox-label">
                  <input type="checkbox" v-model="settings.enabled_tools" :value="tool.id" />
                  {{ tool.name }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label>日限额（元）</label>
              <input type="number" v-model.number="settings.daily_limit" class="input" min="0" step="1" />
            </div>
            <div class="form-group">
              <label>月限额（元）</label>
              <input type="number" v-model.number="settings.monthly_limit" class="input" min="0" step="10" />
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="drawer-footer">
          <button class="btn-save" @click="saveSettings">
            <i class="fas fa-save"></i> 保存设置
          </button>
          <span v-if="saved" class="saved-badge"><i class="fas fa-check"></i> 已保存</span>
        </div>
      </div>
    </div>
  `,
  computed: {
    tabs() {
      return [
        { id: 'personal', label: '个性化', icon: 'fas fa-palette' },
        { id: 'network', label: '网络', icon: 'fas fa-wifi' },
        { id: 'ai', label: 'AI', icon: 'fas fa-brain' },
        { id: 'voice', label: '语音', icon: 'fas fa-microphone' },
        { id: 'emotion', label: '情感', icon: 'fas fa-theater-masks' },
        { id: 'advanced', label: '高级', icon: 'fas fa-sliders-h' },
      ]
    },
    themes() {
      return [
        { id: 'blue', name: '深蓝', color: '#1e3a5f' },
        { id: 'orange', name: '橙色', color: '#c2410c' },
        { id: 'green', name: '绿色', color: '#166534' },
        { id: 'purple', name: '紫色', color: '#6b21a8' },
        { id: 'red', name: '红色', color: '#991b1b' },
        { id: 'cyan', name: '青色', color: '#0e7490' },
      ]
    },
    replyModes() { return ['仅文字', '仅语音', '语音+文字'] },
    voiceOptions() {
      const tts = this.presets.tts.find(t => t.name === this.settings.tts_engine)
      return (tts && tts.voices) || [
        { id: 'zh-CN-XiaoxiaoNeural', name: '晓晓', gender: 'female' }
      ]
    },
    fcTools() {
      return [
        { id: 'query_admission_scores_tool', name: '分数线查询' },
        { id: 'search_experience_tool', name: '经验检索' },
        { id: 'query_news_tool', name: '实时新闻查询' },
        { id: 'query_policy_tool', name: '政策查询' },
      ]
    }
  },
  methods: {
    loadSettings() {
      try {
        const saved = localStorage.getItem('xiaole_settings')
        if (saved) return { ...this.defaults(), ...JSON.parse(saved) }
      } catch (e) {}
      return this.defaults()
    },
    defaults() {
      return {
        theme: 'blue',
        reply_mode: '语音+文字',
        volume: 70,
        voice: 'zh-CN-XiaoxiaoNeural',
        ws_address: 'ws://127.0.0.1:8001',
        api_address: 'http://127.0.0.1:8000',
        llm_model: '',
        temperature: 0.7,
        context_rounds: 3,
        max_tokens: 4096,
        vllm_model: '',
        asr_engine: '',
        tts_engine: '',
        vad_mode: 'click',
        streaming_tts: false,
        emotion_method: 'keyword',
        emotion_tts_enabled: false,
        emotion_intensity: 0.5,
        enabled_tools: ['query_admission_scores_tool', 'search_experience_tool', 'query_news_tool', 'query_policy_tool'],
        daily_limit: 10,
        monthly_limit: 200,
      }
    },
    async loadPresets() {
      try {
        const resp = await fetch(window.API_BASE + '/settings/models')
        if (resp.ok) {
          const data = await resp.json()
          this.presets = data
        }
      } catch (e) {
        console.warn('加载预设失败:', e)
      }
    },
    async saveSettings() {
      localStorage.setItem('xiaole_settings', JSON.stringify(this.settings))
      // 同步到后端
      try {
        await fetch(window.API_BASE + '/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.settings)
        })
      } catch (e) {
        console.warn('同步设置到后端失败:', e)
      }
      this.$emit('save', this.settings)
      this.saved = true
      setTimeout(() => { this.saved = false }, 2000)
    }
  },
  watch: {
    visible(v) {
      if (v) this.loadPresets()
    }
  }
}
