import { onUnmounted, ref, watch, type Ref } from 'vue'
import {
  createLive2DModel,
  EMOTION_MOTIONS,
  MOUTH_PARAM,
  type Live2DModelHandle,
} from '@/live2d/live2dBridge'
import { LipSyncPlayer } from '@/utils/lipSync'
import type { TtsPayload } from '@/types/chat'

export function useLive2D(canvasRef: Ref<HTMLCanvasElement | null>) {
  const ready = ref(false)
  const loadError = ref<string | null>(null)
  const speaking = ref(false)

  let model: Live2DModelHandle | null = null
  let rafId = 0
  let lastFrame = 0
  const lipSync = new LipSyncPlayer()

  async function init(modelPath?: string) {
    if (!canvasRef.value) return
    try {
      model = await createLive2DModel(canvasRef.value, modelPath)
      ready.value = true
      loadError.value = null
      lastFrame = performance.now()
      loop()
    } catch (e) {
      ready.value = false
      loadError.value = e instanceof Error ? e.message : 'Live2D 初始化失败，请检查 SDK 是否已放置'
    }
  }

  function loop() {
    const now = performance.now()
    const delta = now - lastFrame
    lastFrame = now
    model?.update(delta)
    rafId = requestAnimationFrame(loop)
  }

  function setMouthOpen(value: number) {
    model?.setParameterValueById(MOUTH_PARAM, value)
  }

  function playEmotion(emotionTag: string) {
    const cfg = EMOTION_MOTIONS[emotionTag] ?? EMOTION_MOTIONS.friendly
    model?.startMotion(cfg.group, cfg.index, 2)
  }

  async function playSpeech(tts: TtsPayload) {
    speaking.value = true
    try {
      await lipSync.play(tts.audioUrl, tts.phonemes, setMouthOpen, () => {
        setMouthOpen(0)
        speaking.value = false
      })
    } catch {
      speaking.value = false
      setMouthOpen(0)
    }
  }

  function stopSpeech() {
    lipSync.stop()
    setMouthOpen(0)
    speaking.value = false
  }

  onUnmounted(() => {
    stopSpeech()
    if (rafId) cancelAnimationFrame(rafId)
    model?.destroy()
    model = null
  })

  return {
    ready,
    loadError,
    speaking,
    init,
    playEmotion,
    playSpeech,
    stopSpeech,
    setMouthOpen,
  }
}

export function useAutoSpeech(
  ttsRef: Ref<TtsPayload | null | undefined>,
  emotionRef: Ref<string | undefined>,
  live2d: ReturnType<typeof useLive2D>,
) {
  watch(
    ttsRef,
    async (tts) => {
      if (!tts?.audioUrl) return
      if (emotionRef.value) {
        live2d.playEmotion(emotionRef.value)
      }
      await live2d.playSpeech(tts)
    },
    { deep: true },
  )
}
