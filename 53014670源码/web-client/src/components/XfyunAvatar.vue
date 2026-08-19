<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { http } from '@/services/api'

const props = defineProps<{
  answerText?: string
  compact?: boolean
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const speaking = ref(false)
const localTalking = ref(false)
const statusText = ref('待命中')
const videoUrl = ref('')
const spokenText = ref('')
const spokenIndex = ref(0)
const mouthShape = ref<'closed' | 'small' | 'wide' | 'round' | 'flat'>('closed')
let utterance: SpeechSynthesisUtterance | null = null
let lipTimer: number | null = null

const currentMouthPath = computed(() => {
  const paths = {
    closed: 'M 132 170 Q 150 176 168 170',
    small: 'M 135 168 Q 150 180 165 168 Q 150 187 135 168',
    wide: 'M 128 167 Q 150 190 172 167 Q 150 199 128 167',
    round: 'M 139 165 Q 150 154 161 165 Q 166 180 150 189 Q 134 180 139 165',
    flat: 'M 126 170 Q 150 179 174 170 Q 150 184 126 170',
  }
  return paths[mouthShape.value]
})

function getMouthShape(char: string): 'closed' | 'small' | 'wide' | 'round' | 'flat' {
  if (!char || /[，。！？、；：,.!?;:\s]/.test(char)) return 'closed'
  if (/[我佛国说活过若所口游周中宗容融荣哦喔噢]/.test(char)) return 'round'
  if (/[大山法华塔马达啊家驾化话花霞]/.test(char)) return 'wide'
  if (/[一历史可以灵里地西其七起体]/.test(char)) return 'flat'
  return 'small'
}

function updateLipByIndex(index: number) {
  spokenIndex.value = Math.max(0, Math.min(index, spokenText.value.length))
  mouthShape.value = getMouthShape(spokenText.value[spokenIndex.value] || '')
}

function startEstimatedLipSync(text: string) {
  if (lipTimer !== null) window.clearInterval(lipTimer)
  const total = Math.max(text.length, 1)
  const msPerChar = 210
  const startTime = performance.now()
  lipTimer = window.setInterval(() => {
    if (!localTalking.value) return
    const nextIndex = Math.min(Math.floor((performance.now() - startTime) / msPerChar), total)
    updateLipByIndex(nextIndex)
    if (nextIndex >= total) {
      mouthShape.value = 'closed'
      window.clearInterval(lipTimer!)
      lipTimer = null
    }
  }, 80)
}

function stopLocalSpeech() {
  localTalking.value = false
  mouthShape.value = 'closed'
  spokenIndex.value = 0
  if (lipTimer !== null) {
    window.clearInterval(lipTimer)
    lipTimer = null
  }
  utterance = null
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

function startLocalSpeech(text: string) {
  stopLocalSpeech()
  spokenText.value = text.slice(0, 180)
  updateLipByIndex(0)
  if (!('speechSynthesis' in window)) {
    localTalking.value = true
    startEstimatedLipSync(spokenText.value)
    return
  }

  utterance = new SpeechSynthesisUtterance(spokenText.value)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.95
  utterance.pitch = 1.08
  utterance.volume = 1
  utterance.onstart = () => {
    localTalking.value = true
    statusText.value = '正在讲解...'
    startEstimatedLipSync(spokenText.value)
  }
  utterance.onboundary = (event) => {
    updateLipByIndex(event.charIndex || 0)
  }
  utterance.onend = () => {
    localTalking.value = false
    if (!videoUrl.value) statusText.value = '生成视频中...'
  }
  utterance.onerror = () => {
    localTalking.value = false
  }
  window.speechSynthesis.speak(utterance)
}

async function generateVideo(text: string) {
  if (!text || !containerRef.value) return

  speaking.value = true
  statusText.value = '生成视频中...'
  videoUrl.value = ''
  startLocalSpeech(text)

  try {
    const prompt = text.slice(0, 90)
    const resp = await http.post('/api/v1/avatar/video/generate-sync', {
      prompt,
      word_count: Math.max(Math.min(prompt.length, 80), 50),
    })
    
    const result = resp.data.data
    const finalVideoUrl = result?.video_url || result?.payload?.video || result?.payload?.video_url
    if (finalVideoUrl) {
      stopLocalSpeech()
      videoUrl.value = finalVideoUrl
      statusText.value = '播放中'
      await nextTick()
      try {
        await videoRef.value?.play()
      } catch (playError) {
        console.warn('视频自动播放被浏览器拦截:', playError)
      }
    } else {
      statusText.value = '未返回视频'
    }
  } catch (error: any) {
    console.error('视频生成失败:', error)
    statusText.value = '待命中'
  }
}

function onVideoEnded() {
  stopLocalSpeech()
  speaking.value = false
  statusText.value = '待命中'
  videoUrl.value = ''
}

watch(
  () => props.answerText,
  (text) => {
    if (!text) return
    speaking.value = true
    statusText.value = '正在回答...'
    void generateVideo(text)
  },
)

onMounted(() => {
  void nextTick(() => {
    statusText.value = '待命中'
  })
})

onUnmounted(() => {
  stopLocalSpeech()
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.src = ''
  }
})
</script>

<template>
  <div class="xfyun-avatar flex w-full flex-col items-center">
    <div
      class="relative w-full overflow-hidden rounded-[1.8rem] bg-white/90 transition-all duration-500"
      :class="[
        compact ? 'max-w-[220px] sm:max-w-[260px] aspect-square' : 'max-w-[320px] sm:max-w-[360px] aspect-square',
        speaking ? 'shadow-[0_24px_70px_rgba(77,107,254,0.22)] ring-2 ring-[#4d6bfe]/35' : 'shadow-[0_18px_50px_rgba(15,23,42,0.12)] ring-1 ring-slate-200/80',
      ]"
    >
      <div
        ref="containerRef"
        class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100"
      >
        <video
          v-if="videoUrl"
          ref="videoRef"
          :src="videoUrl"
          autoplay
          playsinline
          controls
          class="h-full w-full bg-black object-contain"
          @loadeddata="statusText = '播放中'"
          @ended="onVideoEnded"
          @error="statusText = '视频加载失败'"
        />
        
        <div
          v-else
          class="relative h-full w-full overflow-hidden bg-gradient-to-b from-[#f7f9ff] via-[#eef4ff] to-[#dfe8ff]"
          :class="localTalking ? 'avatar-live' : ''"
        >
          <svg class="drawn-avatar" viewBox="0 0 300 300" role="img" aria-label="AI数字人">
            <defs>
              <linearGradient id="skin" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#ffd9c7" />
                <stop offset="1" stop-color="#f0a98f" />
              </linearGradient>
              <linearGradient id="hair" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#6b463b" />
                <stop offset="1" stop-color="#2d2025" />
              </linearGradient>
              <linearGradient id="suit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#4b5a75" />
                <stop offset="1" stop-color="#1f2937" />
              </linearGradient>
              <filter id="softShadow" x="-20%" y="-20%" width="140%" height="150%">
                <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#6371a5" flood-opacity="0.22" />
              </filter>
            </defs>

            <ellipse cx="150" cy="285" rx="86" ry="14" fill="#b8c7ee" opacity="0.35" />
            <g class="avatar-body" filter="url(#softShadow)">
              <path d="M 78 292 C 84 238 111 210 150 210 C 189 210 216 238 222 292 Z" fill="url(#suit)" />
              <path d="M 124 214 L 150 286 L 176 214 C 169 210 160 207 150 207 C 140 207 131 210 124 214 Z" fill="#f8fafc" />
              <path d="M 139 222 L 150 286 L 161 222 L 151 214 Z" fill="#4d6bfe" opacity="0.9" />
              <path d="M 82 292 C 91 246 113 220 139 212 L 126 292 Z" fill="#354258" />
              <path d="M 218 292 C 209 246 187 220 161 212 L 174 292 Z" fill="#354258" />
            </g>

            <g class="avatar-head" :class="localTalking ? 'head-speaking' : ''" filter="url(#softShadow)">
              <path d="M 87 126 C 86 64 125 30 166 35 C 211 40 230 80 218 133 C 211 102 193 74 161 64 C 128 53 101 75 87 126 Z" fill="url(#hair)" />
              <path d="M 87 121 C 77 152 84 194 119 210 C 92 203 70 175 70 137 C 70 91 102 51 147 43 C 118 63 96 91 87 121 Z" fill="#3a2728" />
              <path d="M 211 118 C 224 154 214 193 181 210 C 205 203 228 176 229 139 C 230 102 209 65 174 49 C 197 75 209 96 211 118 Z" fill="#2b2024" />
              <ellipse cx="150" cy="132" rx="63" ry="76" fill="url(#skin)" />
              <path d="M 92 123 C 107 76 135 58 171 65 C 148 87 121 102 92 123 Z" fill="url(#hair)" opacity="0.95" />
              <path d="M 113 121 Q 126 114 139 121" stroke="#4d2e32" stroke-width="4" stroke-linecap="round" fill="none" />
              <path d="M 162 121 Q 175 114 188 121" stroke="#4d2e32" stroke-width="4" stroke-linecap="round" fill="none" />
              <g class="avatar-open-eyes">
                <ellipse cx="126" cy="132" rx="6" ry="8" fill="#2f2327" />
                <ellipse cx="174" cy="132" rx="6" ry="8" fill="#2f2327" />
                <circle cx="128" cy="129" r="2" fill="#fff" opacity="0.9" />
                <circle cx="176" cy="129" r="2" fill="#fff" opacity="0.9" />
              </g>
              <g class="avatar-closed-eyes">
                <path d="M 119 132 Q 126 137 134 132" stroke="#2f2327" stroke-width="3" stroke-linecap="round" fill="none" />
                <path d="M 166 132 Q 174 137 181 132" stroke="#2f2327" stroke-width="3" stroke-linecap="round" fill="none" />
              </g>
              <path d="M 150 136 Q 145 151 153 154" stroke="#c47f72" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.7" />
              <ellipse cx="111" cy="151" rx="13" ry="7" fill="#ff9fa6" opacity="0.3" />
              <ellipse cx="188" cy="151" rx="13" ry="7" fill="#ff9fa6" opacity="0.3" />
              <path class="avatar-mouth-shape" :d="currentMouthPath" fill="#5d1f28" stroke="#9d4d58" stroke-width="2" stroke-linejoin="round" />
              <path v-if="mouthShape !== 'closed'" class="avatar-tongue" d="M 141 180 Q 150 187 160 180 Q 153 193 141 180" fill="#f39aa5" opacity="0.85" />
            </g>
          </svg>
        </div>
      </div>

      <div class="absolute inset-0 bg-gradient-to-b from-white/20 via-white/0 to-white/30 pointer-events-none" />

      <div
        class="absolute right-4 top-4 rounded-full bg-white/90 px-3 py-1 text-[11px] font-medium shadow-sm backdrop-blur z-10 flex items-center gap-1.5"
        :class="speaking ? 'text-[#4d6bfe]' : 'text-slate-600'"
      >
        <span
          class="w-1.5 h-1.5 rounded-full"
          :class="speaking ? 'bg-[#4d6bfe] animate-pulse' : 'bg-emerald-500'"
        />
        {{ statusText }}
      </div>

    </div>

    <div class="mt-3 w-full text-center">
      <h2 class="text-base font-semibold tracking-tight text-slate-900 sm:text-lg">灵山胜景 · AI 数字人</h2>
      <div v-if="!compact" class="mt-3 flex flex-wrap justify-center gap-2">
        <span class="rounded-full border border-[#dfe6ff] bg-[#eef2ff] px-2.5 py-1 text-[10px] text-[#4d6bfe]">视频生成</span>
        <span class="rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[10px] text-emerald-700">口型同步</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawn-avatar {
  width: 100%;
  height: 100%;
}

.avatar-head {
  transform-origin: 150px 150px;
}

.head-speaking {
  animation: avatar-breathe 2.4s ease-in-out infinite, avatar-nod 3.2s ease-in-out infinite;
}

.avatar-mouth-shape {
  transition: d 90ms linear, transform 90ms linear;
  transform-origin: 150px 146px;
}

.avatar-tongue {
  transition: opacity 90ms linear;
}

.avatar-open-eyes {
  animation: avatar-open-eye-blink 4.5s ease-in-out infinite;
}

.avatar-closed-eyes {
  animation: avatar-closed-eye-blink 4.5s ease-in-out infinite;
  opacity: 0;
}

@keyframes avatar-breathe {
  0%, 100% {
    transform: translateY(0) scale(1);
    filter: saturate(1.02);
  }
  50% {
    transform: translateY(-2px) scale(1.012);
    filter: saturate(1.08);
  }
}

@keyframes avatar-nod {
  0%, 100% {
    rotate: 0deg;
  }
  45% {
    rotate: -0.6deg;
  }
  70% {
    rotate: 0.55deg;
  }
}

@keyframes avatar-open-eye-blink {
  0%, 88%, 100% {
    opacity: 1;
  }
  91%, 94% {
    opacity: 0;
  }
}

@keyframes avatar-closed-eye-blink {
  0%, 88%, 100% {
    opacity: 0;
  }
  91%, 94% {
    opacity: 1;
  }
}
</style>
