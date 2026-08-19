<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { TtsPayload } from '@/types/chat'
import { LipSyncPlayer, type MouthShape } from '@/utils/lipSync'
import flvjs from 'flv.js'

const props = defineProps<{
  tts?: TtsPayload | null
  emotionTag?: string
  streamUrl?: string
  compact?: boolean
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const speaking = ref(false)
const mouthShape = ref<MouthShape>('rest')
const mouthOpen = ref(0)
const prevAudioUrl = ref('')
const lipSync = new LipSyncPlayer()
let settleTimer = 0

const EMOTION_LABELS: Record<string, string> = {
  friendly: '亲切',
  professional: '专业',
  excited: '热情',
  curious: '好奇',
}

const emotionLabel = computed(() =>
  props.emotionTag ? (EMOTION_LABELS[props.emotionTag] ?? props.emotionTag) : '',
)

function clearSettle() {
  if (settleTimer) window.clearTimeout(settleTimer)
  settleTimer = 0
}

async function playVideo(tts?: TtsPayload | null) {
  const video = videoRef.value
  if (!video || !tts?.audioUrl) return
  try {
    video.currentTime = 0
    speaking.value = true
    clearSettle()
    await lipSync.play(
      tts.audioUrl,
      tts.phonemes,
      (value) => {
        mouthOpen.value = Math.max(mouthOpen.value, value)
      },
      () => {
        speaking.value = false
        mouthShape.value = 'rest'
        mouthOpen.value = 0
        clearSettle()
        settleTimer = window.setTimeout(() => {
          mouthShape.value = 'rest'
        }, 120)
      },
      (shape, openness) => {
        mouthShape.value = shape
        mouthOpen.value = openness
      },
    )
    if (video.paused) await video.play().catch(() => undefined)
  } catch {
    speaking.value = false
    mouthShape.value = 'rest'
    mouthOpen.value = 0
    clearSettle()
  }
}

function ensureFlvStream(streamUrl: string) {
  const video = videoRef.value
  if (!video) return
  if ((window as any).__xfyunFlvPlayer) {
    try {
      ;(window as any).__xfyunFlvPlayer.destroy()
    } catch {}
    ;(window as any).__xfyunFlvPlayer = null
  }
  if (flvjs.isSupported()) {
    const player = flvjs.createPlayer({ type: 'flv', url: streamUrl, isLive: true, enableWorker: false, enableStashBuffer: false })
    player.attachMediaElement(video)
    player.load()
    player.play().catch(() => undefined)
    ;(window as any).__xfyunFlvPlayer = player
  } else {
    video.src = streamUrl
    video.play().catch(() => undefined)
  }
}

watch(
  () => props.streamUrl,
  (url) => {
    if (!url) return
    ensureFlvStream(url)
  },
  { immediate: true },
)

watch(
  () => props.tts?.audioUrl,
  (url) => {
    if (!url || url === prevAudioUrl.value) return
    prevAudioUrl.value = url
    void playVideo(props.tts)
  },
  { immediate: true },
)

onMounted(() => {
  const video = videoRef.value
  if (!video) return
  video.loop = false
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'
  video.pause()
})

onUnmounted(() => {
  clearSettle()
  lipSync.stop()
  const player = (window as any).__xfyunFlvPlayer
  if (player) {
    try { player.destroy() } catch {}
    ;(window as any).__xfyunFlvPlayer = null
  }
})

const mouthClass = computed(() => `mouth-rh-${mouthShape.value}`)
const mouthStyle = computed(() => ({
  transform: `translateX(-50%) scale(${1 + mouthOpen.value * 0.32})`,
  opacity: speaking.value ? 1 : 0,
}))
</script>

<template>
  <div class="live2d-avatar flex w-full flex-col items-center">
    <div
      class="relative w-full overflow-hidden rounded-[1.8rem] bg-white/90 transition-all duration-500"
      :class="[
        compact ? 'max-w-[220px] sm:max-w-[260px] aspect-square' : 'max-w-[320px] sm:max-w-[360px] aspect-square',
        speaking ? 'shadow-[0_24px_70px_rgba(77,107,254,0.22)] ring-2 ring-[#4d6bfe]/35' : 'shadow-[0_18px_50px_rgba(15,23,42,0.12)] ring-1 ring-slate-200/80',
      ]"
    >
      <video
        ref="videoRef"
        class="absolute inset-0 h-full w-full object-cover"
        autoplay
        muted
        playsinline
        preload="auto"
      />

      <div class="absolute inset-0 bg-gradient-to-b from-white/0 via-white/0 to-white/10" />

      <div class="mouth-overlay-wrap absolute inset-x-0 bottom-0 h-[48%]" :class="speaking ? 'opacity-100' : 'opacity-0'">
        <div class="mouth-overlay-shine" />
        <div class="mouth-overlay-mouth" :class="mouthClass" :style="mouthStyle" />
        <div class="mouth-overlay-beam" :style="{ opacity: speaking ? 0.65 : 0 }" />
      </div>

      <div
        v-if="speaking"
        class="absolute right-4 top-4 rounded-full bg-white/85 px-3 py-1 text-[11px] font-medium text-[#4d6bfe] shadow-sm backdrop-blur"
      >
        讲解中
      </div>
      <div
        v-else
        class="absolute right-4 top-4 rounded-full bg-white/85 px-3 py-1 text-[11px] font-medium text-slate-600 shadow-sm backdrop-blur"
      >
        待命中
      </div>

      <div
        v-if="!streamUrl"
        class="absolute inset-0 flex items-center justify-center bg-slate-100/80 backdrop-blur"
      >
        <div class="text-center">
          <div class="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#4d6bfe]/10 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-[#4d6bfe]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="4" />
              <path d="m8 12 2 2 4-4" />
            </svg>
          </div>
          <p class="text-xs text-slate-500">数字人连接中...</p>
        </div>
      </div>
    </div>

    <div class="mt-3 w-full text-center">
      <h2 class="text-base font-semibold tracking-tight text-slate-900 sm:text-lg">灵山胜景 · AI 数字人</h2>
      <p class="mt-1 text-xs text-slate-500 sm:text-sm">
        讯飞虚拟人 / Rhubarb 风格口型同步
        <span v-if="emotionLabel" class="text-[#4d6bfe]"> · {{ emotionLabel }}</span>
      </p>
      <div v-if="!compact" class="mt-3 flex flex-wrap justify-center gap-2">
        <span class="rounded-full border border-[#dfe6ff] bg-[#eef2ff] px-2.5 py-1 text-[10px] text-[#4d6bfe]">虚拟人流</span>
        <span class="rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[10px] text-emerald-700">音素驱动口型</span>
        <span class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] text-slate-500">同步播放</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mouth-overlay-wrap {
  transition: opacity 0.25s ease;
  pointer-events: none;
}

.mouth-overlay-shine {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60%;
  background: linear-gradient(to top, rgba(255, 255, 255, 0.35) 0%, transparent 70%);
}

.mouth-overlay-mouth {
  position: absolute;
  bottom: 28%;
  left: 50%;
  width: 32px;
  height: 16px;
  background: radial-gradient(ellipse at center, #2a1a10 0%, #1a0a00 100%);
  border-radius: 50%;
  transition: transform 0.08s ease, opacity 0.25s ease;
}

.mouth-overlay-mouth.mouth-rh-rest {
  height: 4px;
  width: 24px;
  border-radius: 2px;
}

.mouth-overlay-mouth.mouth-rh-B {
  height: 6px;
  width: 26px;
  border-radius: 3px;
}

.mouth-overlay-mouth.mouth-rh-C {
  height: 8px;
  width: 28px;
  border-radius: 4px;
}

.mouth-overlay-mouth.mouth-rh-D {
  height: 10px;
  width: 30px;
  border-radius: 5px;
}

.mouth-overlay-mouth.mouth-rh-E {
  height: 12px;
  width: 32px;
  border-radius: 6px;
}

.mouth-overlay-mouth.mouth-rh-F {
  height: 14px;
  width: 34px;
  border-radius: 7px;
}

.mouth-overlay-mouth.mouth-rh-G {
  height: 16px;
  width: 36px;
  border-radius: 8px;
}

.mouth-overlay-mouth.mouth-rh-A {
  height: 18px;
  width: 38px;
  border-radius: 9px;
}

.mouth-overlay-beam {
  position: absolute;
  bottom: 30%;
  left: 50%;
  width: 40px;
  height: 20px;
  background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  transform: translateX(-50%);
  transition: opacity 0.25s ease;
}
</style>
