<script setup lang="ts">
defineProps<{
  emotion?: string
  speaking?: boolean
}>()

/** 占位图：后续替换为 Live2D 数字人 */
const avatarPlaceholder =
  'https://images.unsplash.com/photo-1578632767112-351597cf2477?w=400&h=500&fit=crop&q=80'
</script>

<template>
  <div class="avatar-display flex flex-col items-center">
    <div
      class="relative w-full max-w-[280px] aspect-[4/5] rounded-2xl overflow-hidden shadow-scenic ring-2 ring-scenic-200/60 bg-gradient-to-b from-scenic-100 to-white"
    >
      <!-- 装饰背景 -->
      <div
        class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-scenic-200/40 via-transparent to-transparent"
      />

      <!-- 数字人占位图 -->
      <img
        :src="avatarPlaceholder"
        alt="AI 数字人导游"
        class="relative z-10 w-full h-full object-cover object-top transition-transform duration-500"
        :class="{ 'scale-[1.02]': speaking }"
      />

      <!-- 说话状态指示 -->
      <div
        v-if="speaking"
        class="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm shadow-card"
      >
        <span class="w-1.5 h-1.5 rounded-full bg-scenic-500 animate-bounce [animation-delay:0ms]" />
        <span class="w-1.5 h-1.5 rounded-full bg-scenic-500 animate-bounce [animation-delay:150ms]" />
        <span class="w-1.5 h-1.5 rounded-full bg-scenic-500 animate-bounce [animation-delay:300ms]" />
      </div>

      <!-- Live2D 占位标签 -->
      <div
        class="absolute top-3 right-3 z-20 px-2 py-0.5 text-[10px] font-medium text-scenic-700 bg-white/80 backdrop-blur rounded-md border border-scenic-200"
      >
        Live2D 占位
      </div>
    </div>

    <div class="mt-4 text-center">
      <h2 class="text-lg font-semibold text-scenic-800">小导 · AI 数字人</h2>
      <p class="text-sm text-mountain-600 mt-0.5">
        您的专属景区智能导游
        <span v-if="emotion" class="text-scenic-600"> · {{ emotion }}</span>
      </p>
    </div>
  </div>
</template>
