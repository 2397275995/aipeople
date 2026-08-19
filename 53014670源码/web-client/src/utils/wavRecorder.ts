/**
 * WAV 录音工具 — 输出 16kHz / mono / PCM16
 *
 * 说明：浏览器原生 MediaRecorder 普遍不支持直接录制 WAV，
 * 因此采用「getUserMedia + AudioContext 采集 PCM → 重采样 → 编码 WAV」方案，
 * 以满足 Whisper ASR 对 16kHz 单声道 WAV 的输入要求。
 */

const TARGET_SAMPLE_RATE = 16000
const MIN_RECORDING_MS = 500

export class VoiceRecorderError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'VoiceRecorderError'
  }
}

export interface RecordResult {
  blob: Blob
  durationMs: number
}

export class WavRecorder {
  private stream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private chunks: Float32Array[] = []
  private startedAt = 0

  get isRecording(): boolean {
    return this.stream !== null
  }

  /** 请求麦克风并开始录音 */
  async start(): Promise<void> {
    if (this.isRecording) return

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
    } catch (err) {
      const dom = err as DOMException
      if (dom.name === 'NotAllowedError' || dom.name === 'PermissionDeniedError') {
        throw new VoiceRecorderError('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风')
      }
      if (dom.name === 'NotFoundError') {
        throw new VoiceRecorderError('未检测到麦克风设备')
      }
      throw new VoiceRecorderError('无法访问麦克风，请检查设备与权限')
    }

    this.audioContext = new AudioContext()
    this.sourceNode = this.audioContext.createMediaStreamSource(this.stream)
    // bufferSize=4096，单声道输入
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1)
    this.chunks = []
    this.startedAt = Date.now()

    this.processorNode.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0)
      this.chunks.push(new Float32Array(input))
    }

    this.sourceNode.connect(this.processorNode)
    this.processorNode.connect(this.audioContext.destination)
  }

  /** 停止录音并返回 16kHz mono WAV Blob */
  async stop(): Promise<RecordResult> {
    if (!this.isRecording || !this.audioContext) {
      throw new VoiceRecorderError('当前未在录音')
    }

    const durationMs = Date.now() - this.startedAt
    const inputSampleRate = this.audioContext.sampleRate

    this._teardownCapture()

    if (durationMs < MIN_RECORDING_MS) {
      throw new VoiceRecorderError(`录音时间过短，请至少按住 ${MIN_RECORDING_MS / 1000} 秒`)
    }

    if (this.chunks.length === 0) {
      throw new VoiceRecorderError('未采集到有效音频数据')
    }

    const merged = mergeFloat32(this.chunks)
    const resampled = await resampleTo16k(merged, inputSampleRate)
    const wavBuffer = encodeWav(resampled, TARGET_SAMPLE_RATE)
    const blob = new Blob([wavBuffer], { type: 'audio/wav' })

    return { blob, durationMs }
  }

  /** 取消录音并释放资源 */
  cancel(): void {
    this._teardownCapture()
    this.chunks = []
  }

  private _teardownCapture(): void {
    this.processorNode?.disconnect()
    this.sourceNode?.disconnect()
    this.processorNode = null
    this.sourceNode = null

    this.stream?.getTracks().forEach((t) => t.stop())
    this.stream = null

    if (this.audioContext) {
      void this.audioContext.close()
      this.audioContext = null
    }
  }
}

/** 合并 Float32 片段 */
function mergeFloat32(chunks: Float32Array[]): Float32Array {
  const total = chunks.reduce((sum, c) => sum + c.length, 0)
  const result = new Float32Array(total)
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.length
  }
  return result
}

/** 使用 OfflineAudioContext 重采样到 16kHz */
async function resampleTo16k(
  samples: Float32Array,
  inputSampleRate: number,
): Promise<Float32Array> {
  if (inputSampleRate === TARGET_SAMPLE_RATE) {
    return samples
  }

  const durationSec = samples.length / inputSampleRate
  const outputLength = Math.ceil(durationSec * TARGET_SAMPLE_RATE)
  const offline = new OfflineAudioContext(1, outputLength, TARGET_SAMPLE_RATE)
  const buffer = offline.createBuffer(1, samples.length, inputSampleRate)
  buffer.copyToChannel(samples, 0)

  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start(0)

  const rendered = await offline.startRendering()
  return rendered.getChannelData(0)
}

/** 将 Float32 PCM 编码为标准 WAV (PCM16, mono) */
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const numChannels = 1
  const bitsPerSample = 16
  const bytesPerSample = bitsPerSample / 8
  const blockAlign = numChannels * bytesPerSample
  const dataLength = samples.length * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bitsPerSample, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataLength, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }

  return buffer
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

export { MIN_RECORDING_MS, TARGET_SAMPLE_RATE }
