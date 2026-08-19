import axios from 'axios'
import type { ApiResponse, AsrRecognizeData, AvatarStreamPayload, ChatAskData, ChatAskRequest } from '@/types/chat'
import type { RecommendRoutesData, RecommendRoutesRequest } from '@/types/recommend'

const baseURL = import.meta.env.VITE_API_BASE_URL || ''

const http = axios.create({
  baseURL,
  timeout: 120000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '网络请求失败，请稍后重试'
    const message = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg || String(d)).join('; ')
      : String(detail)
    return Promise.reject(new Error(message))
  },
)

export async function chatAsk(payload: ChatAskRequest): Promise<ChatAskData> {
  const { data } = await http.post<ApiResponse<ChatAskData>>(
    '/api/v1/chat/ask',
    payload,
    { headers: { 'Content-Type': 'application/json' } },
  )
  if (data.code !== 0 || !data.data) {
    throw new Error(data.message || '问答请求失败')
  }
  return data.data
}

export interface AsrRecognizeParams {
  audio: Blob
  sessionId: string
  lang?: string
}

export async function asrRecognize(params: AsrRecognizeParams): Promise<AsrRecognizeData> {
  const formData = new FormData()
  formData.append('audio', params.audio, 'recording.wav')
  formData.append('sessionId', params.sessionId)
  formData.append('lang', params.lang ?? 'zh')

  const { data } = await http.post<ApiResponse<AsrRecognizeData>>(
    '/api/v1/asr/recognize',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )

  if (data.code !== 0 || !data.data) {
    throw new Error(data.message || '语音识别失败')
  }
  return data.data
}

export async function healthCheck(): Promise<boolean> {
  try {
    const { data } = await http.get('/health')
    return data?.status === 'ok'
  } catch {
    return false
  }
}

export async function fetchRecommendRoutes(
  payload: RecommendRoutesRequest,
): Promise<RecommendRoutesData> {
  const { data } = await http.post<ApiResponse<RecommendRoutesData>>(
    '/api/v1/recommend/routes',
    payload,
    { headers: { 'Content-Type': 'application/json' } },
  )
  if (data.code !== 0 || !data.data) {
    throw new Error(data.message || '路线推荐失败')
  }
  return data.data
}

export async function startAvatarSession(): Promise<AvatarStreamPayload> {
  const { data } = await http.post<ApiResponse<AvatarStreamPayload>>('/api/v1/avatar/start', {}, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (data.code !== 0 || !data.data) {
    throw new Error(data.message || '虚拟人启动失败')
  }
  return data.data
}

export async function stopAvatarSession(sessionId: string): Promise<void> {
  const { data } = await http.post<ApiResponse<{ stopped: boolean }>>('/api/v1/avatar/stop', { sessionId }, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (data.code !== 0) {
    throw new Error(data.message || '虚拟人停止失败')
  }
}

export async function talkAvatarSession(sessionId: string, text: string, mode: 'interact' | 'driver' = 'interact'): Promise<string> {
  const { data } = await http.post<ApiResponse<{ reply: string }>>(
    '/api/v1/avatar/talk',
    { sessionId, text, mode },
    { headers: { 'Content-Type': 'application/json' } },
  )
  if (data.code !== 0 || !data.data) {
    throw new Error(data.message || '虚拟人交互失败')
  }
  return data.data.reply || ''
}

export { http }
