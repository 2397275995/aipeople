<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchRecommendRoutes } from '@/services/api'
import type { RouteItem } from '@/types/recommend'
import { PREFERENCE_OPTIONS, TAG_LABELS } from '@/types/recommend'

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const selectedPrefs = ref<string[]>(['history', 'nature'])
const routes = ref<RouteItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const activeRouteIndex = ref(0)
const viewMode = ref<'list' | 'map'>('list')

const mapContainer = ref<HTMLElement | null>(null)
let mapInstance: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let routeLine: L.Polyline | null = null

function togglePref(id: string) {
  const idx = selectedPrefs.value.indexOf(id)
  if (idx >= 0) {
    if (selectedPrefs.value.length > 1) {
      selectedPrefs.value.splice(idx, 1)
    }
  } else {
    selectedPrefs.value.push(id)
  }
}

async function loadRoutes() {
  loading.value = true
  error.value = null
  try {
    const data = await fetchRecommendRoutes({ preference: selectedPrefs.value })
    routes.value = data.routes
    activeRouteIndex.value = 0
    if (viewMode.value === 'map') {
      await nextTick()
      renderMap()
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
    routes.value = []
  } finally {
    loading.value = false
  }
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markersLayer = null
    routeLine = null
  }
}

function renderMap() {
  const route = routes.value[activeRouteIndex.value]
  if (!route?.pois.length || !mapContainer.value) return

  destroyMap()

  const pois = route.pois
  mapInstance = L.map(mapContainer.value, { zoomControl: true })
  markersLayer = L.layerGroup().addTo(mapInstance)

  const latLngs: L.LatLngExpression[] = pois.map((p) => [p.lat, p.lng])

  pois.forEach((poi, index) => {
    const marker = L.marker([poi.lat, poi.lng]).bindPopup(
      `<strong>${index + 1}. ${poi.name}</strong><br/>${poi.description}`,
    )
    markersLayer!.addLayer(marker)
  })

  routeLine = L.polyline(latLngs, {
    color: '#0d9488',
    weight: 4,
    opacity: 0.85,
    dashArray: '8 6',
  }).addTo(mapInstance)

  mapInstance.fitBounds(routeLine.getBounds(), { padding: [40, 40] })
  setTimeout(() => mapInstance?.invalidateSize(), 100)
}

function selectRoute(index: number) {
  activeRouteIndex.value = index
  if (viewMode.value === 'map') {
    nextTick(() => renderMap())
  }
}

function switchView(mode: 'list' | 'map') {
  viewMode.value = mode
  if (mode === 'map') {
    nextTick(() => renderMap())
  }
}

function handleClose() {
  emit('close')
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `约 ${minutes} 分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m > 0 ? `约 ${h} 小时 ${m} 分钟` : `约 ${h} 小时`
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      void loadRoutes()
    } else {
      destroyMap()
      viewMode.value = 'list'
    }
  },
)

onBeforeUnmount(() => {
  destroyMap()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex items-center justify-center p-4"
    >
      <div
        class="absolute inset-0 bg-mountain-900/40 backdrop-blur-sm"
        @click="handleClose"
      />

      <div
        class="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl border border-scenic-100 overflow-hidden"
      >
        <!-- 头部 -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-scenic-100 bg-gradient-to-r from-scenic-50 via-white to-emerald-50/40">
          <div>
            <h2 class="scenic-title text-lg">灵山胜景 · 推荐路线</h2>
            <p class="text-xs text-mountain-600 mt-0.5">基于官方 POI 数据 · 选择兴趣获取个性化路线</p>
          </div>
          <button
            type="button"
            class="w-8 h-8 rounded-lg hover:bg-scenic-100 text-mountain-600 flex items-center justify-center transition-colors"
            @click="handleClose"
          >
            ✕
          </button>
        </div>

        <!-- 兴趣选择 -->
        <div class="px-5 py-3 border-b border-scenic-50">
          <p class="text-xs text-mountain-600 mb-2">我的兴趣（可多选）</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in PREFERENCE_OPTIONS"
              :key="opt.id"
              type="button"
              class="px-3 py-1.5 text-xs rounded-full border transition-all"
              :class="
                selectedPrefs.includes(opt.id)
                  ? 'bg-scenic-500 text-white border-scenic-500 shadow-sm'
                  : 'bg-white text-mountain-700 border-scenic-200 hover:border-scenic-400'
              "
              @click="togglePref(opt.id)"
            >
              {{ opt.icon }} {{ opt.label }}
            </button>
          </div>
          <button
            type="button"
            class="mt-3 text-xs text-scenic-600 hover:text-scenic-800 font-medium disabled:opacity-50"
            :disabled="loading"
            @click="loadRoutes"
          >
            {{ loading ? '生成中…' : '🔄 重新推荐' }}
          </button>
        </div>

        <!-- 视图切换 -->
        <div class="px-5 pt-3 flex gap-2">
          <button
            type="button"
            class="px-3 py-1.5 text-xs rounded-lg transition-colors"
            :class="viewMode === 'list' ? 'bg-scenic-100 text-scenic-800 font-medium' : 'text-mountain-600 hover:bg-scenic-50'"
            @click="switchView('list')"
          >
            📋 路线列表
          </button>
          <button
            type="button"
            class="px-3 py-1.5 text-xs rounded-lg transition-colors"
            :class="viewMode === 'map' ? 'bg-scenic-100 text-scenic-800 font-medium' : 'text-mountain-600 hover:bg-scenic-50'"
            :disabled="!routes.length"
            @click="switchView('map')"
          >
            🗺️ 地图展示
          </button>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 overflow-y-auto px-5 py-3 min-h-0">
          <div
            v-if="error"
            class="mb-3 px-3 py-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg"
          >
            {{ error }}
          </div>

          <div v-if="loading" class="flex items-center justify-center py-16 text-scenic-600 text-sm gap-2">
            <svg class="animate-spin w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            正在规划路线…
          </div>

          <!-- 列表视图 -->
          <div v-else-if="viewMode === 'list'" class="space-y-3 pb-2">
            <article
              v-for="(route, idx) in routes"
              :key="route.routeId"
              class="rounded-xl border transition-all cursor-pointer"
              :class="
                activeRouteIndex === idx
                  ? 'border-scenic-400 bg-scenic-50/50 shadow-sm'
                  : 'border-scenic-100 hover:border-scenic-200'
              "
              @click="selectRoute(idx)"
            >
              <div class="px-4 py-3">
                <div class="flex items-start justify-between gap-2">
                  <div>
                    <h3 class="font-semibold text-scenic-800">{{ route.name }}</h3>
                    <p class="text-xs text-mountain-600 mt-1">{{ route.description }}</p>
                  </div>
                  <span class="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                    匹配 {{ Math.round(route.matchScore * 100) }}%
                  </span>
                </div>

                <p class="text-xs text-scenic-600 mt-2">
                  ⏱ {{ formatDuration(route.estimatedDuration) }}
                  · {{ route.pois.length }} 个景点
                </p>

                <ol class="mt-3 space-y-2">
                  <li
                    v-for="(poi, poiIdx) in route.pois"
                    :key="poi.id"
                    class="flex gap-2 text-sm"
                  >
                    <span class="flex-shrink-0 w-5 h-5 rounded-full bg-scenic-500 text-white text-[10px] flex items-center justify-center font-bold">
                      {{ poiIdx + 1 }}
                    </span>
                    <div class="min-w-0">
                      <p class="font-medium text-mountain-800">{{ poi.name }}</p>
                      <p class="text-xs text-mountain-600 line-clamp-2">{{ poi.description }}</p>
                      <div class="flex flex-wrap gap-1 mt-1">
                        <span
                          v-for="tag in poi.tags"
                          :key="tag"
                          class="text-[10px] px-1.5 py-0.5 rounded bg-scenic-50 text-scenic-700"
                        >
                          {{ TAG_LABELS[tag] || tag }}
                        </span>
                      </div>
                    </div>
                  </li>
                </ol>
              </div>
            </article>
          </div>

          <!-- 地图视图 -->
          <div v-else class="pb-2">
            <div v-if="routes.length" class="flex gap-2 mb-2">
              <button
                v-for="(route, idx) in routes"
                :key="route.routeId"
                type="button"
                class="px-3 py-1 text-xs rounded-lg border transition-colors"
                :class="
                  activeRouteIndex === idx
                    ? 'bg-scenic-500 text-white border-scenic-500'
                    : 'bg-white text-mountain-700 border-scenic-200 hover:border-scenic-400'
                "
                @click="selectRoute(idx)"
              >
                {{ route.name }}
              </button>
            </div>
            <div
              ref="mapContainer"
              class="w-full h-[360px] rounded-xl border border-scenic-200 overflow-hidden z-0"
            />
            <p v-if="routes[activeRouteIndex]" class="text-xs text-mountain-600 mt-2 text-center">
              点击标记查看景点详情 · 虚线为推荐游览顺序
            </p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
:deep(.leaflet-container) {
  font-family: inherit;
}
</style>
