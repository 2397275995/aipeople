import axios from 'axios'
import { getToken } from '../utils/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || ''

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface KbDocumentItem {
  docId: string
  title: string
  filename: string
  category: string
  scenicAreaId: string
  status: string
  progress: number
  chunkCount: number
  createdAt: string
  errorMessage?: string | null
}

export interface DashboardOverviewData {
  sessionCount: number
  messageCount: number
  visitorCount: number
  avgSatisfaction: number
  hotQA: { question: string; count: number }[]
  satisfactionTrend: { date: string; avgSatisfaction: number }[]
  sentimentTrend?: {
    date: string
    positive: number
    neutral: number
    negative: number
    total?: number
  }[]
}

export interface SentimentTrendItem {
  date: string
  positive: number
  neutral: number
  negative: number
  total: number
}

export interface HotTopicWord {
  word: string
  count: number
  weight: number
}

export interface SentimentSummary {
  totalMessages: number
  positiveRate: number
  neutralRate: number
  negativeRate: number
}

export interface SentimentTrendData {
  trend: SentimentTrendItem[]
  hotTopics: HotTopicWord[]
  summary: SentimentSummary
}

export interface KbDocumentUploadData {
  docId: string
  status: string
  chunkCount: number
  progress: number
}

export interface KbDocumentStatusData {
  docId: string
  status: string
  progress: number
  chunkCount: number
  errorMessage?: string | null
}

const http = axios.create({ baseURL, timeout: 120000 })

http.interceptors.request.use((config) => {
  config.headers.Authorization = `Bearer ${getToken()}`
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail || err.message
    return Promise.reject(new Error(typeof detail === 'string' ? detail : '请求失败'))
  },
)

export async function adminLogin(username: string, password: string): Promise<string> {
  const { data } = await http.post<ApiResponse<{ token: string }>>(
    '/api/v1/admin/auth/login',
    { username, password },
  )
  if (data.code !== 0 || !data.data?.token) {
    throw new Error(data.message || '登录失败')
  }
  return data.data.token
}

export async function uploadKbDocument(
  file: File,
  category: string,
  scenicAreaId: string,
): Promise<KbDocumentUploadData> {
  const form = new FormData()
  form.append('file', file)
  form.append('category', category)
  form.append('scenicAreaId', scenicAreaId)

  const { data } = await http.post<ApiResponse<KbDocumentUploadData>>(
    '/api/v1/admin/kb/documents',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  if (data.code !== 0 || !data.data) throw new Error(data.message || '上传失败')
  return data.data
}

export async function listKbDocuments(limit = 20): Promise<KbDocumentItem[]> {
  const { data } = await http.get<ApiResponse<{ documents: KbDocumentItem[] }>>(
    '/api/v1/admin/kb/documents',
    { params: { limit } },
  )
  if (data.code !== 0 || !data.data) throw new Error(data.message || '加载失败')
  return data.data.documents
}

export async function getDashboardOverview(): Promise<DashboardOverviewData> {
  const { data } = await http.get<ApiResponse<DashboardOverviewData>>(
    '/api/v1/admin/dashboard/overview',
  )
  if (data.code !== 0 || !data.data) throw new Error(data.message || '加载大屏数据失败')
  return data.data
}

export async function getSentimentTrend(days = 7): Promise<SentimentTrendData> {
  const { data } = await http.get<ApiResponse<SentimentTrendData>>(
    '/api/v1/admin/analytics/sentiment-trend',
    { params: { days } },
  )
  if (data.code !== 0 || !data.data) throw new Error(data.message || '加载感受度数据失败')
  return data.data
}

export async function getKbDocumentStatus(docId: string): Promise<KbDocumentStatusData> {
  const { data } = await http.get<ApiResponse<KbDocumentStatusData>>(
    `/api/v1/admin/kb/documents/${docId}`,
  )
  if (data.code !== 0 || !data.data) throw new Error(data.message || '查询失败')
  return data.data
}
