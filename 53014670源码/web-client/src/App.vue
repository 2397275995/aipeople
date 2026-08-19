<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import XfyunAvatar from '@/components/XfyunAvatar.vue'
import ChatInterface from '@/components/ChatInterface.vue'
import { healthCheck } from '@/services/api'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const { messages, lastAnswer } = storeToRefs(chatStore)

const backendOnline = ref<boolean | null>(null)
const showAvatar = computed(() => messages.value.length > 0 || Boolean(lastAnswer.value))
const adminUrl = import.meta.env.VITE_ADMIN_URL || 'http://localhost:5174'

onMounted(async () => {
  backendOnline.value = await healthCheck()
})
</script>

<template>
  <div class="app min-h-screen flex flex-col relative overflow-hidden bg-[#f7f8fb] text-slate-900">
    <div class="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <div class="absolute left-1/2 top-[-18rem] h-[34rem] w-[54rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(77,125,255,0.18),rgba(247,248,251,0)_68%)]" />
      <div class="absolute bottom-[-16rem] right-[-10rem] h-[32rem] w-[32rem] rounded-full bg-[radial-gradient(circle,rgba(78,205,196,0.14),rgba(247,248,251,0)_70%)]" />
    </div>

    <header class="relative z-20 flex items-center justify-between px-5 py-4 sm:px-8">
      <div class="flex items-center gap-2.5">
        <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-[#4d6bfe] shadow-[0_10px_24px_rgba(77,107,254,0.25)]">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3 4 8l8 5 8-5-8-5Z" />
            <path d="m4 14 8 5 8-5" />
            <path d="m4 11 8 5 8-5" />
          </svg>
        </div>
        <div class="leading-tight">
          <p class="text-sm font-semibold tracking-tight text-slate-900">灵山胜景 AI</p>
          <p class="hidden text-xs text-slate-500 sm:block">Scenic Guide Assistant</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <a :href="adminUrl" target="_blank" rel="noreferrer" class="hidden rounded-full px-4 py-2 text-sm text-slate-600 transition hover:bg-white hover:text-slate-900 hover:shadow-sm sm:inline-flex">管理后台</a>
        <span
          class="inline-flex items-center gap-2 rounded-full border bg-white/80 px-3 py-1.5 text-xs font-medium shadow-sm backdrop-blur"
          :class="
            backendOnline === true
              ? 'border-emerald-100 text-emerald-700'
              : backendOnline === false
                ? 'border-amber-100 text-amber-700'
                : 'border-slate-100 text-slate-500'
          "
        >
          <span
            class="h-2 w-2 rounded-full"
            :class="
              backendOnline === true
                ? 'bg-emerald-500'
                : backendOnline === false
                  ? 'bg-amber-500'
                  : 'bg-slate-300 animate-pulse'
            "
          />
          {{ backendOnline === true ? '在线' : backendOnline === false ? '离线' : '检测中' }}
        </span>
      </div>
    </header>

    <main class="relative z-10 flex flex-1 flex-col px-4 pb-6 sm:px-6">
      <section class="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center gap-6 pt-4">
        <Transition name="avatar-drop">
          <div v-if="showAvatar" class="w-full animate-fade-in">
            <div class="mx-auto max-w-[420px] rounded-[2rem] border border-white/80 bg-white/70 p-3 shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur-xl">
              <XfyunAvatar :answer-text="lastAnswer" compact />
            </div>
          </div>
        </Transition>

        <div class="w-full animate-fade-in">
          <ChatInterface />
        </div>
      </section>
    </main>
  </div>
</template>
