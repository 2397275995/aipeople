export const SDKEvents = {
  connected: 'connected',
  disconnected: 'disconnected',
  stream_start: 'stream_start',
  frame_start: 'frame_start',
  frame_stop: 'frame_stop',
  action_start: 'action_start',
  action_stop: 'action_stop',
  tts_duration: 'tts_duration',
  asr: 'asr',
  nlp: 'nlp',
  subtitle_info: 'subtitle_info',
  error: 'error',
}

export const PlayerEvents = {
  play: 'play',
  waiting: 'waiting',
  playing: 'playing',
  playNotAllowed: 'playNotAllowed',
  error: 'error',
}

class Player {
  constructor(wrapper) {
    this.wrapper = wrapper
    this.listeners = {}
  }
  
  on(event, handler) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(handler)
    return this
  }
  
  emit(event, ...args) {
    const handlers = this.listeners[event] || []
    handlers.forEach(h => h(...args))
  }
  
  resume() {
    console.log('Player resumed')
  }
  
  resize() {
    console.log('Player resized')
  }
  
  setSinkId() {
    return Promise.resolve()
  }
  
  get muted() { return this._muted || false }
  set muted(v) { this._muted = v }
  get volume() { return this._volume || 1 }
  set volume(v) { this._volume = v }
}

async function _generateSignedUrl(serverUrl, apiKey, apiSecret) {
  const urlObj = new URL(serverUrl)
  const host = urlObj.host
  const path = urlObj.pathname
  const date = new Date().toUTCString()
  const signatureOrigin = `host: ${host}\ndate: ${date}\nGET ${path} HTTP/1.1`
  
  const key = await crypto.subtle.importKey(
    'raw', 
    new TextEncoder().encode(apiSecret), 
    { name: 'HMAC', hash: 'SHA-256' }, 
    false, 
    ['sign']
  )
  
  const signature = await window.crypto.subtle.sign(
    { name: 'HMAC', hash: 'SHA-256' },
    key,
    new TextEncoder().encode(signatureOrigin)
  )
  
  const signatureB64 = btoa(String.fromCharCode(...new Uint8Array(signature)))
  const authOrigin = `api_key="${apiKey}", algorithm="hmac-sha256", headers="host date request-line", signature="${signatureB64}"`
  const authorization = btoa(authOrigin)
  return `${serverUrl}?authorization=${encodeURIComponent(authorization)}&date=${encodeURIComponent(date)}&host=${encodeURIComponent(host)}`
}

class AvatarPlatform {
  constructor() {
    this.listeners = {}
    this.player = null
    this.websocket = null
    this.apiInfo = null
    this.globalParams = null
    this.isConnected = false
  }
  
  on(event, handler) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(handler)
    return this
  }
  
  off(event, handler) {
    const handlers = this.listeners[event] || []
    this.listeners[event] = handlers.filter(h => h !== handler)
    return this
  }
  
  emit(event, ...args) {
    const handlers = this.listeners[event] || []
    handlers.forEach(h => h(...args))
  }
  
  removeAllListeners() {
    this.listeners = {}
    return this
  }
  
  setApiInfo(info) {
    this.apiInfo = info
    return this
  }
  
  setGlobalParams(config) {
    this.globalParams = config
    return this
  }
  
  createPlayer() {
    return new Player()
  }
  
  async start({ wrapper }) {
    if (!this.apiInfo) {
      throw new Error('apiInfo not set')
    }
    
    this.player = new Player(wrapper)
    
    try {
      let url = this.apiInfo.signedUrl
      if (!url && this.apiInfo.serverUrl && this.apiInfo.apiKey && this.apiInfo.apiSecret) {
        url = await _generateSignedUrl(this.apiInfo.serverUrl, this.apiInfo.apiKey, this.apiInfo.apiSecret)
      }
      if (!url) {
        url = this.apiInfo.serverUrl
      }
      this.websocket = new WebSocket(url)
      
      return new Promise((resolve, reject) => {
        this.websocket.onopen = () => {
          console.log('WebSocket connected')
          
          const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
          
          const initMsg = {
            header: {
              app_id: this.apiInfo.appId,
              uid: '',
              request_id: requestId,
              ctrl: 'start',
            },
            parameter: {
              avatar: {
                avatar_id: this.globalParams?.avatar?.avatar_id || '',
                width: this.globalParams?.avatar?.width || 720,
                height: this.globalParams?.avatar?.height || 1280,
                stream: this.globalParams?.stream || { protocol: 'xrtc' },
              },
              tts: this.globalParams?.tts || {},
              ...(this.globalParams?.air && { air: this.globalParams.air }),
              ...(this.globalParams?.subtitle && { subtitle: this.globalParams.subtitle }),
              ...(this.globalParams?.background && { background: this.globalParams.background }),
            },
            payload: {
              session_id: '',
            },
          }
          
          this.websocket.send(JSON.stringify(initMsg))
        }
        
        this.websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('WebSocket message:', data)
            
            if (data.header?.code === 0 || data.code === 0) {
              this.isConnected = true
              this.emit(SDKEvents.connected, data)
              
              if (data.payload?.stream_url) {
                this.emit(SDKEvents.stream_start)
                this._setupPlayer(wrapper, data.payload)
              }
              
              if (data.payload?.data) {
                const result = JSON.parse(data.payload.data)
                if (result.vmr_status === 1) {
                  this.emit(SDKEvents.frame_start)
                } else if (result.vmr_status === 2) {
                  this.emit(SDKEvents.frame_stop)
                }
                if (result.nlp) {
                  this.emit(SDKEvents.nlp, result)
                }
                if (result.subtitle) {
                  this.emit(SDKEvents.subtitle_info, result)
                }
              }
              
              resolve()
            } else {
              const error = {
                code: data.header?.code || data.code || -1,
                message: data.header?.message || data.message || 'Unknown error',
              }
              this.emit(SDKEvents.error, error)
              reject(new Error(`${error.code}: ${error.message}`))
            }
          } catch (e) {
            console.error('Parse message error:', e)
          }
        }
        
        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.emit(SDKEvents.error, { code: -1, message: 'Connection error' })
          reject(error)
        }
        
        this.websocket.onclose = (event) => {
          console.log('WebSocket closed:', event)
          this.isConnected = false
          if (event.code !== 1000) {
            this.emit(SDKEvents.disconnected, { code: event.code, reason: event.reason })
          } else {
            this.emit(SDKEvents.disconnected)
          }
        }
        
        setTimeout(() => {
          if (!this.isConnected) {
            this.websocket?.close()
            reject(new Error('Connection timeout'))
          }
        }, 15000)
      })
    } catch (e) {
      this.emit(SDKEvents.error, { code: -1, message: e.message })
      throw e
    }
  }
  
  _setupPlayer(wrapper, payload) {
    if (!wrapper) return
    
    const streamUrl = payload.stream_url
    if (streamUrl) {
      const video = document.createElement('video')
      video.autoplay = true
      video.muted = false
      video.playsInline = true
      video.style.width = '100%'
      video.style.height = '100%'
      video.style.objectFit = 'contain'
      video.style.backgroundColor = '#000'
      
      video.addEventListener('play', () => {
        this.player?.emit(PlayerEvents.play)
      })
      
      video.addEventListener('waiting', () => {
        this.player?.emit(PlayerEvents.waiting)
      })
      
      video.addEventListener('playing', () => {
        this.player?.emit(PlayerEvents.playing)
      })
      
      video.addEventListener('error', (e) => {
        this.player?.emit(PlayerEvents.error, e)
      })
      
      video.addEventListener('play', () => {
        if (video.paused && video.readyState >= 2) {
          this.player?.emit(PlayerEvents.playNotAllowed)
        }
      })
      
      wrapper.innerHTML = ''
      wrapper.appendChild(video)
      
      if (streamUrl.startsWith('http')) {
        video.src = streamUrl
      } else if (streamUrl.startsWith('rtmp')) {
        console.warn('RTMP not supported in browser')
      }
    }
  }
  
  async writeText(text, extend = {}) {
    if (!this.websocket || !this.isConnected) {
      throw new Error('Not connected')
    }
    
    const msg = {
      header: {
        app_id: this.apiInfo.appId,
        uid: '',
      },
      parameter: {
        vmr: {
          tts: {
            vcn: extend?.tts?.vcn || this.globalParams?.tts?.vcn || 'x4_xiaoxuan',
            ...(extend?.tts || {}),
          },
          ...(extend?.avatar_dispatch && { avatar_dispatch: extend.avatar_dispatch }),
          ...(this.globalParams?.air && { air: this.globalParams.air }),
        },
      },
      payload: {
        data: JSON.stringify({
          text: text,
          nlp: extend.nlp || false,
        }),
      },
    }
    
    return new Promise((resolve, reject) => {
      this.websocket.send(JSON.stringify(msg))
      const timeout = setTimeout(() => {
        reject(new Error('Write timeout'))
      }, 30000)
      
      const handler = (data) => {
        if (data?.payload?.data) {
          const result = JSON.parse(data.payload.data)
          if (result.request_id) {
            clearTimeout(timeout)
            this.off(SDKEvents.nlp, handler)
            resolve(result.request_id)
          }
        }
      }
      
      this.on(SDKEvents.nlp, handler)
      
      this.once(SDKEvents.error, (e) => {
        clearTimeout(timeout)
        reject(e)
      })
    })
  }
  
  once(event, handler) {
    const onceHandler = (...args) => {
      handler(...args)
      this.off(event, onceHandler)
    }
    return this.on(event, onceHandler)
  }
  
  async writeAudio(buf, status, extend) {
    console.log('writeAudio not implemented')
    return ''
  }
  
  async writeCmd(type, value) {
    if (!this.websocket || !this.isConnected) {
      throw new Error('Not connected')
    }
    
    const msg = {
      header: {
        app_id: this.apiInfo.appId,
        uid: '',
      },
      parameter: {
        vmr: {},
      },
      payload: {
        data: JSON.stringify({
          cmd: type,
          value: value,
        }),
      },
    }
    
    this.websocket.send(JSON.stringify(msg))
    return ''
  }
  
  async interrupt() {
    if (!this.websocket || !this.isConnected) {
      throw new Error('Not connected')
    }
    
    const msg = {
      header: {
        app_id: this.apiInfo.appId,
        uid: '',
      },
      parameter: {
        vmr: {},
      },
      payload: {
        data: JSON.stringify({
          cmd: 'interrupt',
        }),
      },
    }
    
    this.websocket.send(JSON.stringify(msg))
  }
  
  stop() {
    if (this.websocket) {
      try {
        this.websocket.close(1000)
      } catch {}
      this.websocket = null
    }
    this.isConnected = false
  }
  
  destroy() {
    this.stop()
    this.player = null
    this.listeners = {}
  }
  
  createRecorder() {
    console.log('Recorder not implemented')
    return {
      startRecord: () => {},
      stopRecord: () => {},
    }
  }
  
  static getVersion() {
    return '3.2.3.1002'
  }
  
  static setLogLevel() {
    console.log('Log level not implemented')
  }
}

export default AvatarPlatform
