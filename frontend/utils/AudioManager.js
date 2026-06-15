/**
 * 全局音频管理器（单例）
 * 统一管理 TTS 播放，支持意图打断（barge-in）
 */
class AudioManager {
  static instance = null

  static getInstance() {
    if (!AudioManager.instance) {
      AudioManager.instance = new AudioManager()
    }
    return AudioManager.instance
  }

  constructor() {
    this.currentAudio = null
    this.isPlaying = false
    this.onBargeInCallbacks = []
    this.currentUrl = null
  }

  /**
   * 播放音频 blob（自动停止旧的）
   * @param {Blob} blob - 音频数据
   * @returns {Promise<void>}
   */
  async play(blob) {
    this.stop()
    return new Promise((resolve, reject) => {
      this.currentUrl = URL.createObjectURL(blob)
      this.currentAudio = new Audio(this.currentUrl)
      this.isPlaying = true

      this.currentAudio.onended = () => {
        this.isPlaying = false
        this._cleanup()
        resolve()
      }
      this.currentAudio.onerror = (e) => {
        this.isPlaying = false
        this._cleanup()
        reject(e)
      }
      this.currentAudio.play().catch(reject)
    })
  }

  /**
   * 停止当前播放
   */
  stop() {
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
    }
    this.isPlaying = false
    this._cleanup()
  }

  /**
   * 意图打断：用户开始说话时调用
   */
  onBargeIn() {
    if (this.isPlaying) {
      this.stop()
      this.onBargeInCallbacks.forEach(cb => {
        try { cb() } catch (e) { console.warn('barge-in callback error:', e) }
      })
    }
  }

  /**
   * 注册打断回调
   * @param {Function} callback
   */
  registerBargeInCallback(callback) {
    this.onBargeInCallbacks.push(callback)
  }

  /**
   * 注销打断回调
   * @param {Function} callback - 不传则清空所有回调
   */
  unregisterBargeInCallback(callback) {
    if (callback) {
      this.onBargeInCallbacks = this.onBargeInCallbacks.filter(cb => cb !== callback)
    } else {
      this.onBargeInCallbacks = []
    }
  }

  _cleanup() {
    if (this.currentUrl) {
      URL.revokeObjectURL(this.currentUrl)
      this.currentUrl = null
    }
    this.currentAudio = null
  }
}

export default AudioManager
