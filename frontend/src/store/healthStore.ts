import { create } from 'zustand'
import { api } from '../lib/api'

interface HealthStore {
  data:       Record<string, unknown[]>
  weekly:     Record<string, Record<string, number>>
  loading:    boolean
  error:      string | null
  loadAll:    () => Promise<void>
  loadWeekly: (domain: string, metric: string) => Promise<void>
}

export const useHealthStore = create<HealthStore>((set, get) => ({
  data:    {},
  weekly:  {},
  loading: false,
  error:   null,

  async loadAll() {
    set({ loading: true, error: null })
    try {
      const res = await api.allData()
      const data: Record<string, unknown[]> = {}
      for (const [domain, val] of Object.entries(res)) {
        data[domain] = (val as { recent: unknown[] }).recent
      }
      set({ data, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  async loadWeekly(domain, metric) {
    const key = `${domain}.${metric}`
    if (get().weekly[key]) return
    try {
      const res = await api.weeklyPattern(domain, metric)
      set(s => ({ weekly: { ...s.weekly, [key]: res.pattern } }))
    } catch { /* silent */ }
  },
}))