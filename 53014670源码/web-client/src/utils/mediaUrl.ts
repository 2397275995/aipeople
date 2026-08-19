/**
 * 解析后端返回的媒体 URL（支持相对路径 /static/tts/...）
 */
export function resolveMediaUrl(url: string): string {
  if (!url) return url
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url
  }
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
  return `${base}${url.startsWith('/') ? url : `/${url}`}`
}
