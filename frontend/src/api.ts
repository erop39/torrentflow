import type { AuditEvent, Category, DownloadItem, Feed, FeedCheckResult, HealthResponse, IntegrationStatus, Release, Rule } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal, credentials: 'include' })
  if (!response.ok) throw new Error(`Request failed with ${response.status}`)
  return response.json() as Promise<T>
}

async function sendJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  if (!response.ok) throw new Error(`Request failed with ${response.status}`)
  return response.json() as Promise<T>
}

async function deleteJson(path: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, { method: 'DELETE', credentials: 'include' })
  if (!response.ok) throw new Error(`Request failed with ${response.status}`)
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) throw new Error(`Request failed with ${response.status}`)
  return response.json() as Promise<T>
}

export const api = {
  health: (signal?: AbortSignal) => getJson<HealthResponse>('/api/health', signal),
  releases: (signal?: AbortSignal) => getJson<Release[]>('/api/releases', signal),
  feeds: (signal?: AbortSignal) => getJson<Feed[]>('/api/feeds', signal),
  me: (signal?: AbortSignal) => getJson<{ authenticated: boolean }>('/api/auth/me', signal),
  login: (password: string) => sendJson<{ authenticated: boolean }>('/api/auth/login', { password }),
  createFeed: (payload: Pick<Feed, 'name' | 'url' | 'adapter_type' | 'interval_minutes'>) => sendJson<Feed>('/api/feeds', payload),
  deleteFeed: (feedId: number) => deleteJson(`/api/feeds/${feedId}`),
  rules: (signal?: AbortSignal) => getJson<Rule[]>('/api/rules', signal),
  createRule: (payload: Omit<Rule, 'id' | 'enabled' | 'category'> & { category?: string }) => sendJson<Rule>('/api/rules', payload),
  categories: () => getJson<Category[]>('/api/categories'),
  createCategory: (payload: Pick<Category, 'name' | 'color' | 'is_interesting'>) => sendJson<Category>('/api/categories', payload),
  updateCategory: (categoryId: number, payload: Partial<Pick<Category, 'color' | 'is_interesting'>>) => patchJson<Category>(`/api/categories/${categoryId}`, payload),
  checkFeed: (feedId: number) => sendJson<FeedCheckResult>(`/api/feeds/${feedId}/check`),
  downloads: () => getJson<DownloadItem[]>('/api/downloads'),
  audit: () => getJson<AuditEvent[]>('/api/audit'),
  integrationStatus: () => getJson<IntegrationStatus>('/api/integrations/status'),
  testQbit: () => sendJson<{ ok: boolean }>('/api/integrations/qbittorrent/test'),
  testTelegram: () => sendJson<{ ok: boolean }>('/api/integrations/telegram/test'),
}
