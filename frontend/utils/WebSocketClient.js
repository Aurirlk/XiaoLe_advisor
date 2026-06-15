/**
 * WebSocketClient - 标准化 WebSocket 客户端 SDK
 * 支持自动重连、消息分发、音频流发送
 */
class WebSocketClient {
  constructor(url, options = {}) {
    this.url = url
    this.options = {
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      ...options
    }
    this.ws = null
    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.isConnecting = false
    this.isClosed = false
    this.listeners = {}
    this.audioMode = false
  }

  connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) return
    this.isConnecting = true
    this.isClosed = false

    try {
      this.ws = new WebSocket(this.url)
    } catch (e) {
      this.isConnecting = false
      this._emit('error', e)
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.isConnecting = false
      this.reconnectAttempts = 0
      this._emit('open')
      this._startHeartbeat()
    }

    this.ws.onmessage = (evt) => {
      if (evt.data instanceof Blob) {
        this._emit('audio_chunk', evt.data)
        return
      }
      try {
        const msg = JSON.parse(evt.data)
        this._emit(msg.type, msg)
        this._emit('message', msg)
      } catch {
        this._emit('raw', evt.data)
      }
    }

    this.ws.onclose = (evt) => {
      this.isConnecting = false
      this._stopHeartbeat()
      this._emit('close', evt)
      if (!this.isClosed && this.options.autoReconnect) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = (evt) => {
      this._emit('error', evt)
    }
  }

  send(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket 未连接')
      return false
    }
    if (typeof data === 'object') {
      this.ws.send(JSON.stringify(data))
    } else {
      this.ws.send(data)
    }
    return true
  }

  sendText(query, sessionId, role = 'student') {
    return this.send({
      type: 'text',
      query,
      session_id: sessionId,
      role
    })
  }

  startAudioStream(sessionId, role = 'student') {
    this.audioMode = true
    return this.send({
      type: 'audio_start',
      session_id: sessionId,
      role
    })
  }

  sendAudioChunk(pcmChunk) {
    if (!this.audioMode) return false
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(pcmChunk)
      return true
    }
    return false
  }

  endAudioStream() {
    this.audioMode = false
    return this.send({ type: 'audio_end' })
  }

  on(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = []
    this.listeners[event].push(callback)
    return () => this.off(event, callback)
  }

  off(event, callback) {
    if (!this.listeners[event]) return
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
  }

  close() {
    this.isClosed = true
    this._stopHeartbeat()
    clearTimeout(this.reconnectTimer)
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }

  _emit(event, data) {
    const cbs = this.listeners[event] || []
    cbs.forEach(cb => {
      try { cb(data) } catch (e) { console.error('WebSocket event handler error:', e) }
    })
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this._emit('reconnect_failed')
      return
    }
    this.reconnectAttempts++
    const delay = this.options.reconnectInterval * Math.min(this.reconnectAttempts, 5)
    this.reconnectTimer = setTimeout(() => {
      this._emit('reconnecting', { attempt: this.reconnectAttempts })
      this.connect()
    }, delay)
  }

  _startHeartbeat() {
    if (this.options.heartbeatInterval > 0) {
      this.heartbeatTimer = setInterval(() => {
        this.send({ type: 'ping' })
      }, this.options.heartbeatInterval)
    }
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

export default WebSocketClient
