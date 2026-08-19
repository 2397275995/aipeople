import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatAsk } from '@/services/api'
import type { ChatMessage, TtsPayload } from '@/types/chat'

function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(generateId('sess'))
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastEmotion = ref('friendly')
  const lastEmotionTag = ref('friendly')
  const lastAnswer = ref('')
  const lastTts = ref<TtsPayload | null>(null)

  const hasMessages = computed(() => messages.value.length > 0)

  function addMessage(role: ChatMessage['role'], content: string, extra?: Partial<ChatMessage>) {
    messages.value.push({
      id: generateId('msg'),
      role,
      content,
      timestamp: Date.now(),
      ...extra,
    })
  }

  async function sendMessage(text: string, inputType: 'text' | 'voice' = 'text') {
    const trimmed = text.trim()
    if (!trimmed || loading.value) return

    error.value = null
    addMessage('user', trimmed)
    loading.value = true

    try {
      const data = await chatAsk({
        sessionId: sessionId.value,
        text: trimmed,
        inputType,
      })

      lastAnswer.value = data.answerText
      lastEmotion.value = data.avatar.expression
      lastEmotionTag.value = data.emotionTag
      lastTts.value = data.tts

      addMessage('bot', data.answerText, {
        emotionTag: data.emotionTag,
        confidence: data.confidence,
        sources: data.sources,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '发送失败'
      error.value = msg
      addMessage('bot', `抱歉，暂时无法回答您的问题：${msg}`)
    } finally {
      loading.value = false
    }
  }

  async function sendText(text: string) {
    return sendMessage(text, 'text')
  }

  async function sendVoice(text: string) {
    return sendMessage(text, 'voice')
  }

  async function clearChat() {
    messages.value = []
    error.value = null
    lastAnswer.value = ''
    lastTts.value = null
    sessionId.value = generateId('sess')
  }

  return {
    sessionId,
    messages,
    loading,
    error,
    lastEmotion,
    lastEmotionTag,
    lastAnswer,
    lastTts,
    hasMessages,
    sendText,
    sendVoice,
    clearChat,
  }
})
