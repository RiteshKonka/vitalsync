const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

export const api = {
  health:        () => get<{ status: string }>('/health').catch(() => ({ status: 'offline' })),
  domains:       () => get<{ domains: { id: string; label: string; color: string; key_metric: string }[] }>('/domains'),
  allData:       () => get<Record<string, { recent: unknown[]; summary: unknown; color: string }>>('/data'),
  domainData:    (domain: string) => get<{ records: unknown[]; count: number }>(`/data/${domain}`),
  weeklyPattern: (domain: string, metric: string) =>
    get<{ pattern: Record<string, number> }>(`/data/${domain}/weekly?metric=${metric}`),
  initSession:   (sid: string) => post<{ session_id: string; history_count: number }>(`/session/${sid}/init`),
  getSession:    (sid: string) => get<{ history: unknown[]; count: number }>(`/session/${sid}`),
}