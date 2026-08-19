/**
 * Rhubarb 风格口型同步播放器
 *
 * 通过 TTS 音素/时长分析，生成更明显的口型开合序列。
 */

import type { PhonemeItem } from '@/types/chat'
import { resolveMediaUrl } from '@/utils/mediaUrl'

export type MouthShape = 'rest' | 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G'

export interface MouthFrame {
  shape: MouthShape
  startMs: number
  endMs: number
  openness: number
}

const DEFAULT_AUDIO_CONTEXT_RATE = 16000

export function mouthOpenForPhone(phone: string): number {
  if (!phone || phone === 'sil') return 0.03

  const openVowels = /[aoueāáǎàōóǒòēéěèīíǐìūúǔùü]/i
  const wideOpen = /[ahou啊哈喔哦呵嘿]/i
  const closed = /[mnbszcsMNBSZC]/

  let value = 0.28
  for (const ch of phone) {
    if (wideOpen.test(ch)) value = Math.max(value, 0.95)
    else if (openVowels.test(ch)) value = Math.max(value, 0.78)
    else if (closed.test(ch)) value = Math.max(value, 0.12)
    else value = Math.max(value, 0.46)
  }
  return Math.min(1, Math.max(0, value))
}

export function mouthShapeFromOpen(open: number): MouthShape {
  if (open <= 0.08) return 'rest'
  if (open <= 0.18) return 'B'
  if (open <= 0.34) return 'C'
  if (open <= 0.5) return 'D'
  if (open <= 0.68) return 'E'
  if (open <= 0.84) return 'F'
  return 'G'
}

export function buildMouthFrames(phonemes: PhonemeItem[], durationMs: number): MouthFrame[] {
  if (!phonemes.length) {
    return [{ shape: 'rest', startMs: 0, endMs: durationMs, openness: 0.08 }]
  }

  const frames: MouthFrame[] = []
  for (let i = 0; i < phonemes.length; i++) {
    const p = phonemes[i]
    const next = phonemes[i + 1]
    const start = Math.max(0, p.startMs)
    const end = Math.max(start + 40, p.endMs || (next ? next.startMs : durationMs))
    const openness = mouthOpenForPhone(p.phone)
    const shape = mouthShapeFromOpen(openness)
    frames.push({ shape, startMs: start, endMs: end, openness })
  }

  return frames
}

export function findFrameAtTime(frames: MouthFrame[], timeMs: number): MouthFrame {
  for (const frame of frames) {
    if (timeMs >= frame.startMs && timeMs < frame.endMs) return frame
  }
  return frames[frames.length - 1] ?? { shape: 'rest', startMs: 0, endMs: 0, openness: 0.08 }
}

function estimateFromSpectrum(data: Uint8Array): number {
  if (!data.length) return 0.08
  let sum = 0
  let count = 0
  for (let i = 0; i < data.length; i += 8) {
    sum += data[i]
    count += 1
  }
  const avg = sum / Math.max(1, count)
  return Math.max(0.05, Math.min(1, (avg - 18) / 72))
}

export class LipSyncPlayer {
  private audio: HTMLAudioElement | null = null
  private frames: MouthFrame[] = []
  private rafId = 0
  private onMouthOpen: ((value: number) => void) | null = null
  private onShape: ((shape: MouthShape, openness: number) => void) | null = null
  private onEnded: (() => void) | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private sourceNode: MediaElementAudioSourceNode | null = null
  private frequencyData: Uint8Array | null = null

  async play(
    audioUrl: string,
    phonemes: PhonemeItem[],
    onMouthOpen: (value: number) => void,
    onEnded?: () => void,
    onShape?: (shape: MouthShape, openness: number) => void,
  ): Promise<void> {
    this.stop()
    this.onMouthOpen = onMouthOpen
    this.onEnded = onEnded ?? null
    this.onShape = onShape ?? null

    const audio = new Audio(resolveMediaUrl(audioUrl))
    audio.preload = 'auto'
    audio.crossOrigin = 'anonymous'
    this.audio = audio

    this.audioContext = new AudioContext({ sampleRate: DEFAULT_AUDIO_CONTEXT_RATE })
    this.analyser = this.audioContext.createAnalyser()
    this.analyser.fftSize = 2048
    this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount)

    this.sourceNode = this.audioContext.createMediaElementSource(audio)
    this.sourceNode.connect(this.analyser)
    this.analyser.connect(this.audioContext.destination)

    return new Promise((resolve, reject) => {
      audio.addEventListener('ended', () => {
        this.onMouthOpen?.(0)
        this.onShape?.('rest', 0)
        this.onEnded?.()
        this.stop()
        resolve()
      })
      audio.addEventListener('error', () => {
        reject(new Error('音频播放失败'))
      })

      audio
        .play()
        .then(() => {
          void this.audioContext?.resume()
          this.frames = buildMouthFrames(phonemes, Math.max(audio.duration * 1000, phonemes.at(-1)?.endMs ?? 0))
          this.tick()
        })
        .catch(reject)
    })
  }

  stop(): void {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId)
      this.rafId = 0
    }
    if (this.audio) {
      this.audio.pause()
      this.audio.src = ''
      this.audio = null
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect()
      this.sourceNode = null
    }
    if (this.analyser) {
      this.analyser.disconnect()
      this.analyser = null
    }
    if (this.audioContext) {
      void this.audioContext.close()
      this.audioContext = null
    }
    this.frequencyData = null
    this.onMouthOpen?.(0)
    this.onShape?.('rest', 0)
  }

  private tick = (): void => {
    if (!this.audio) return

    const timeMs = this.audio.currentTime * 1000
    const frame = findFrameAtTime(this.frames, timeMs)

    let spectrum = 0.08
    if (this.analyser && this.frequencyData) {
      this.analyser.getByteFrequencyData(this.frequencyData)
      spectrum = estimateFromSpectrum(this.frequencyData)
    }

    const openness = Math.min(1, Math.max(frame.openness, spectrum))
    this.onMouthOpen?.(openness)
    this.onShape?.(frame.shape, openness)

    if (!this.audio.paused && !this.audio.ended) {
      this.rafId = requestAnimationFrame(this.tick)
    }
  }
}
