/**
 * ImageAnalyzer - 图片分析组件
 * 支持拖拽上传、粘贴、点击选择图片，发送到 /vision/analyze 分析
 */
export default {
  name: 'ImageAnalyzer',
  emits: ['analysis-result'],
  data() {
    return {
      isAnalyzing: false,
      previewUrl: null,
      fileName: '',
      error: '',
      dragOver: false
    }
  },
  template: `
    <div class="image-analyzer">
      <!-- 上传区域 -->
      <div
        class="upload-zone"
        :class="{ 'drag-over': dragOver, 'has-image': previewUrl }"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="handleDrop"
        @click="triggerUpload"
        @paste="handlePaste"
        tabindex="0"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display:none"
          @change="handleFileSelect"
        />

        <div v-if="!previewUrl" class="upload-placeholder">
          <i class="fas fa-image"></i>
          <p>拖拽/粘贴/点击上传图片</p>
          <span class="hint">支持 JPEG、PNG、WebP，最大 20MB</span>
        </div>

        <div v-else class="preview-area">
          <img :src="previewUrl" class="preview-image" />
          <button class="remove-btn" @click.stop="clearImage">
            <i class="fas fa-times"></i>
          </button>
          <span class="file-name">{{ fileName }}</span>
        </div>
      </div>

      <!-- 分析按钮 -->
      <div v-if="previewUrl" class="action-row">
        <input
          v-model="customPrompt"
          class="prompt-input"
          placeholder="分析指令（默认：请详细描述这张图片）"
          @keydown.enter="analyze"
        />
        <button class="analyze-btn" @click="analyze" :disabled="isAnalyzing">
          <i :class="isAnalyzing ? 'fas fa-spinner fa-spin' : 'fas fa-search'"></i>
          {{ isAnalyzing ? '分析中...' : '分析' }}
        </button>
      </div>

      <!-- 错误提示 -->
      <span v-if="error" class="error-text">{{ error }}</span>
    </div>
  `,
  methods: {
    triggerUpload() {
      this.$refs.fileInput.click()
    },

    handleFileSelect(e) {
      const file = e.target.files[0]
      if (file) this.processFile(file)
    },

    handleDrop(e) {
      this.dragOver = false
      const file = e.dataTransfer.files[0]
      if (file && file.type.startsWith('image/')) {
        this.processFile(file)
      }
    },

    handlePaste(e) {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) this.processFile(file)
          break
        }
      }
    },

    processFile(file) {
      if (file.size > 20 * 1024 * 1024) {
        this.error = '图片大小不能超过 20MB'
        return
      }
      this.error = ''
      this.fileName = file.name
      this.previewUrl = URL.createObjectURL(file)
      this._file = file
    },

    clearImage() {
      if (this.previewUrl) URL.revokeObjectURL(this.previewUrl)
      this.previewUrl = null
      this.fileName = ''
      this._file = null
      this.error = ''
    },

    async analyze() {
      if (!this._file || this.isAnalyzing) return
      this.isAnalyzing = true
      this.error = ''

      try {
        const formData = new FormData()
        formData.append('image', this._file)
        formData.append('prompt', this.customPrompt || '请详细描述这张图片的内容')

        const resp = await fetch(window.API_BASE + '/vision/analyze', {
          method: 'POST',
          body: formData
        })

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || '分析失败')
        }

        const data = await resp.json()
        this.$emit('analysis-result', {
          result: data.result,
          model: data.model,
          fileName: this.fileName
        })
      } catch (e) {
        this.error = e.message
      } finally {
        this.isAnalyzing = false
      }
    }
  },

  beforeUnmount() {
    this.clearImage()
  }
}
