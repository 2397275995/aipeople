<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import VoiceInput from './VoiceInput.vue'
import RouteRecommendModal from './RouteRecommendModal.vue'

const chatStore = useChatStore()
const { messages, loading, error, sessionId, lastTts } = storeToRefs(chatStore)

const inputText = ref('')
const voiceError = ref<string | null>(null)
const voiceProcessing = ref(false)
const messagesEl = ref<HTMLElement | null>(null)
const showRouteModal = ref(false)
const revealProgress = ref<Record<string, number>>({})
const revealTimers = new Map<string, number>()

const hasConversation = computed(() => messages.value.length > 0)

const QUICK_QUESTIONS = [
  { icon: '🏛️', text: '灵山大佛有什么历史？' },
  { icon: '🗺️', text: '推荐游览路线' },
  { icon: '🌸', text: '拈花湾有什么好玩的？' },
  { icon: '🎫', text: '门票和开放时间' },
] as const

const EMOTION_LABELS: Record<string, string> = {
  friendly: '亲切',
  professional: '专业',
  excited: '热情',
  curious: '好奇',
  surprise: '惊喜',
  happy: '愉快',
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

function clearRevealTimer(messageId: string) {
  const timer = revealTimers.get(messageId)
  if (timer) {
    window.clearTimeout(timer)
    revealTimers.delete(messageId)
  }
}

function startTypewriterReveal(messageId: string, text: string, durationMs = 2800) {
  clearRevealTimer(messageId)
  const total = Math.max(1, text.length)
  const stepMs = Math.max(16, Math.floor(durationMs / total))
  revealProgress.value = { ...revealProgress.value, [messageId]: 0 }

  let index = 0
  const tick = () => {
    index += 1
    revealProgress.value = { ...revealProgress.value, [messageId]: Math.min(text.length, index) }
    if (index < text.length) {
      const timer = window.setTimeout(tick, stepMs)
      revealTimers.set(messageId, timer)
    }
  }

  const timer = window.setTimeout(tick, stepMs)
  revealTimers.set(messageId, timer)
}

watch(lastTts, (tts) => {
  const botMessages = messages.value.filter((m) => m.role === 'bot')
  const latest = botMessages[botMessages.length - 1]
  if (!tts?.audioUrl || !latest) return
  startTypewriterReveal(latest.id, latest.content, tts.durationMs || 2800)
}, { deep: true })

async function handleSend() {
  const text = inputText.value
  if (!text.trim() || loading.value) return
  inputText.value = ''
  await chatStore.sendText(text)
}

function getVisibleText(messageId: string, content: string) {
  const visible = revealProgress.value[messageId] ?? content.length
  return content.slice(0, visible)
}

async function sendQuickQuestion(text: string) {
  if (loading.value) return
  if (text === '推荐游览路线') {
    showRouteModal.value = true
    return
  }
  await chatStore.sendText(text)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void handleSend()
  }
}

function handleVoiceTranscript(text: string) {
  voiceError.value = null
  void chatStore.sendVoice(text)
}

function handleVoiceError(message: string) {
  voiceError.value = message
}

function handleVoiceProcessing(value: boolean) {
  voiceProcessing.value = value
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function emotionLabel(tag?: string): string {
  if (!tag) return ''
  return EMOTION_LABELS[tag] ?? tag
}
</script>

<template>
  <div class="chat-interface mx-auto flex w-full max-w-4xl flex-col" :class="messages.length ? 'h-[calc(100vh-30rem)] min-h-[360px] lg:h-[calc(100vh-28rem)]' : 'h-[calc(100vh-8.5rem)] min-h-[620px]'">
    <div
      ref="messagesEl"
      class="scrollbar-thin flex-1 overflow-y-auto px-1 pb-5 pt-3 sm:px-4"
      :class="messages.length ? 'space-y-6' : 'flex items-center justify-center'"
    >
      <div v-if="!messages.length" class="w-full animate-fade-in text-center">
        <div class="mx-auto mb-7 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#4d6bfe] shadow-[0_18px_40px_rgba(77,107,254,0.28)]">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3 4 8l8 5 8-5-8-5Z" />
            <path d="m4 14 8 5 8-5" />
            <path d="m4 11 8 5 8-5" />
          </svg>
        </div>
        <h1 class="text-3xl font-semibold tracking-tight text-slate-950 sm:text-5xl">有什么可以帮您？</h1>
        <p class="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-500 sm:text-base">
          我是灵山胜景 AI 数字人导游，可以基于官方示范景区资料回答问题、规划路线、介绍景点与服务信息。
        </p>
        <div class="mx-auto mt-8 grid max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            v-for="q in QUICK_QUESTIONS"
            :key="q.text"
            type="button"
            class="group rounded-2xl border border-slate-200/80 bg-white/80 p-4 text-left shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-[#4d6bfe]/30 hover:bg-white hover:shadow-[0_16px_40px_rgba(15,23,42,0.08)]"
            @click="sendQuickQuestion(q.text)"
          >
            <span class="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-base transition group-hover:bg-[#eef2ff]">{{ q.icon }}</span>
            <span class="text-sm font-medium text-slate-700">{{ q.text }}</span>
          </button>
        </div>
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <div class="mx-auto flex w-full max-w-3xl gap-3 animate-slide-up" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
          <div
            v-if="msg.role === 'bot'"
            class="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#4d6bfe] text-xs font-semibold text-white shadow-sm"
          >
            AI
          </div>

          <div class="max-w-[86%] sm:max-w-[78%]">
            <div class="px-4 py-3 text-sm leading-7 shadow-sm" :class="msg.role === 'user' ? 'msg-user-deepseek' : 'msg-bot-deepseek'">
              <p class="whitespace-pre-wrap">{{ msg.role === 'bot' ? getVisibleText(msg.id, msg.content) : msg.content }}</p>

              <div v-if="msg.role === 'bot' && msg.sources?.length" class="mt-4 border-t border-slate-200/80 pt-3">
                <p class="mb-2 text-xs font-medium text-slate-500">参考官方资料</p>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="src in msg.sources"
                    :key="src.docId"
                    class="max-w-full truncate rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-500"
                    :title="src.title"
                  >
                    {{ src.title }}
                  </span>
                </div>
              </div>
            </div>

            <p class="mt-2 flex flex-wrap items-center gap-1 text-xs text-slate-400" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
              <span>{{ formatTime(msg.timestamp) }}</span>
              <span v-if="msg.emotionTag">· {{ emotionLabel(msg.emotionTag) }}</span>
              <span v-if="msg.confidence">· 置信 {{ Math.round(msg.confidence * 100) }}%</span>
            </p>
          </div>
        </div>
      </template>

      <div v-if="loading" class="mx-auto flex w-full max-w-3xl justify-start gap-3 animate-fade-in">
        <div class="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-[#4d6bfe] text-xs font-semibold text-white">AI</div>
        <div class="msg-bot-deepseek px-4 py-3 shadow-sm">
          <div class="flex items-center gap-3 text-sm text-slate-500">
            <span class="flex gap-1">
              <span class="h-1.5 w-1.5 rounded-full bg-[#4d6bfe] animate-bounce" />
              <span class="h-1.5 w-1.5 rounded-full bg-[#4d6bfe] animate-bounce [animation-delay:150ms]" />
              <span class="h-1.5 w-1.5 rounded-full bg-[#4d6bfe] animate-bounce [animation-delay:300ms]" />
            </span>
            正在思考并检索资料…
          </div>
        </div>
      </div>
    </div>

    <div class="mx-auto w-full max-w-3xl pb-2">
      <div v-if="error" class="mb-2 rounded-2xl border border-red-100 bg-red-50 px-4 py-2 text-xs text-red-700">
        {{ error }}
      </div>
      <div v-if="voiceError" class="mb-2 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-700">
        {{ voiceError }}
      </div>

      <div class="rounded-[1.6rem] border border-slate-200/80 bg-white p-2 shadow-[0_18px_60px_rgba(15,23,42,0.10)] transition focus-within:border-[#4d6bfe]/40 focus-within:shadow-[0_18px_70px_rgba(77,107,254,0.16)]">
        <textarea
          v-model="inputText"
          rows="2"
          placeholder="给灵山胜景 AI 发送消息"
          class="max-h-36 min-h-[3rem] w-full resize-none rounded-2xl border-0 bg-transparent px-4 py-3 text-base text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-0"
          :disabled="loading || voiceProcessing"
          @keydown="handleKeydown"
        />

        <div class="flex items-center justify-between gap-3 px-2 pb-1">
          <div class="flex items-center gap-2">
            <VoiceInput
              :disabled="loading || voiceProcessing"
              :session-id="sessionId"
              @transcript="handleVoiceTranscript"
              @error="handleVoiceError"
              @processing="handleVoiceProcessing"
            />
            <button
              type="button"
              class="rounded-full px-3 py-2 text-sm text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
              @click="showRouteModal = true"
            >
              推荐路线
            </button>
            <button
              v-if="messages.length"
              type="button"
              class="rounded-full px-3 py-2 text-sm text-slate-500 transition hover:bg-slate-100 hover:text-red-500"
              @click="chatStore.clearChat()"
            >
              清空
            </button>
          </div>

          <button
            type="button"
            class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[#4d6bfe] text-white shadow-[0_10px_24px_rgba(77,107,254,0.28)] transition hover:bg-[#3f5bef] active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:shadow-none"
            :disabled="loading || voiceProcessing || !inputText.trim()"
            @click="handleSend"
            aria-label="发送"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14" />
              <path d="m13 6 6 6-6 6" />
            </svg>
          </button>
        </div>
      </div>
      <p class="mt-3 text-center text-xs text-slate-400">
        {{ messages.length ? '数字人将在回复时自动播放语音并同步口型。' : '内容由 AI 生成，请结合景区现场公告与工作人员指引确认。' }}
      </p>
    </div>

    <RouteRecommendModal :open="showRouteModal" @close="showRouteModal = false" />
  </div>
</template>
