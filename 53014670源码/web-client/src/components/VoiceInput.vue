<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { asrRecognize } from '@/services/api'
import { WavRecorder, VoiceRecorderError } from '@/utils/wavRecorder'

const props = defineProps<{
  disabled?: boolean
  sessionId: string
}>()

const emit = defineEmits<{
  transcript: [text: string]
  error: [message: string]
  /** 识别进行中，父组件可禁用输入区 */
  processing: [value: boolean]
}>()

const isRecording = ref(false)
const isProcessing = ref(false)
const recorder = new WavRecorder()

async function startRecording() {
  if (isRecording.value || isProcessing.value || props.disabled) return

  try {
    await recorder.start()
    isRecording.value = true
  } catch (err) {
    const msg =
      err instanceof VoiceRecorderError
        ? err.message
        : '无法开始录音，请检查麦克风权限'
    emit('error', msg)
  }
}

async function stopRecording() {
  if (!isRecording.value) return
  isRecording.value = false
  isProcessing.value = true
  emit('processing', true)

  try {
    const { blob, durationMs } = await recorder.stop()

    const result = await asrRecognize({
      audio: blob,
      sessionId: props.sessionId,
      lang: 'zh',
    })

    if (!result.text?.trim()) {
      emit('error', '未识别到有效内容，请重新录制')
      return
    }

    console.log('[VoiceInput] ASR 成功', {
      text: result.text,
      confidence: result.confidence,
      durationMs,
      uploadSize: blob.size,
    })

    emit('transcript', result.text.trim())
  } catch (err) {
    recorder.cancel()
    const msg =
      err instanceof VoiceRecorderError
        ? err.message
        : err instanceof Error
          ? err.message
          : '语音识别失败'
    emit('error', msg)
  } finally {
    isProcessing.value = false
    emit('processing', false)
  }
}

function handlePointerDown() {
  void startRecording()
}

function handlePointerUp() {
  void stopRecording()
}

function handlePointerLeave() {
  if (isRecording.value) {
    void stopRecording()
  }
}

onUnmounted(() => {
  recorder.cancel()
})
</script>

<template>
  <button
    type="button"
    class="voice-btn flex-shrink-0 w-11 h-11 rounded-full flex items-center justify-center transition-all duration-200 select-none touch-none shadow-sm"
    :class="
      isRecording
        ? 'bg-red-500 text-white shadow-lg scale-110 ring-4 ring-red-200/80'
        : isProcessing
          ? 'bg-scenic-100 text-scenic-600 cursor-wait ring-2 ring-scenic-200'
          : 'bg-white text-scenic-700 border border-scenic-200 hover:bg-scenic-50 hover:border-scenic-300 hover:shadow-md'
    "
    :disabled="disabled || isProcessing"
    :title="isProcessing ? '识别中…' : isRecording ? '松手发送' : '按住说话'"
    @pointerdown.prevent="handlePointerDown"
    @pointerup.prevent="handlePointerUp"
    @pointerleave="handlePointerLeave"
    @contextmenu.prevent
  >
    <!-- 识别中 -->
    <svg
      v-if="isProcessing"
      class="animate-spin w-5 h-5"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
    <!-- 录音中 -->
    <svg
      v-else-if="isRecording"
      xmlns="http://www.w3.org/2000/svg"
      class="w-5 h-5 animate-pulse"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
    <!-- 默认麦克风 -->
    <svg
      v-else
      xmlns="http://www.w3.org/2000/svg"
      class="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="22" />
    </svg>
  </button>
</template>

<style scoped>
.voice-btn:disabled {
  @apply opacity-50 cursor-not-allowed;
}
</style>
