const TOKEN_KEY = 'admin_token'

/** 硬编码 Token（与后端 ADMIN_API_TOKEN 一致，开发简化） */
export const HARDCODED_ADMIN_TOKEN = 'scenic-admin-token-2026'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || HARDCODED_ADMIN_TOKEN
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
