export interface PoiItem {
  id: string
  name: string
  lat: number
  lng: number
  description: string
  tags: string[]
  visitMinutes: number
}

export interface RouteItem {
  routeId: string
  name: string
  description: string
  pois: PoiItem[]
  estimatedDuration: number
  highlights: string[]
  matchScore: number
}

export interface RecommendRoutesData {
  routes: RouteItem[]
  preferences: string[]
}

export interface RecommendRoutesRequest {
  preference: string[]
}

export interface PreferenceOption {
  id: string
  label: string
  icon: string
}

export const PREFERENCE_OPTIONS: PreferenceOption[] = [
  { id: 'history', label: '历史', icon: '🏛️' },
  { id: 'culture', label: '文化', icon: '📜' },
  { id: 'nature', label: '自然', icon: '🌿' },
  { id: 'photo', label: '摄影', icon: '📷' },
  { id: 'family', label: '亲子', icon: '👨‍👩‍👧' },
  { id: 'adventure', label: '探险', icon: '🥾' },
]

export const TAG_LABELS: Record<string, string> = {
  history: '历史',
  culture: '文化',
  nature: '自然',
  photo: '摄影',
  family: '亲子',
  adventure: '探险',
}
