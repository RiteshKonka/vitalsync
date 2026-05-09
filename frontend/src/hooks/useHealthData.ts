import { useEffect } from 'react'
import { useHealthStore } from '../store/healthStore'

export function useHealthData() {
  const { data, weekly, loading, error, loadAll, loadWeekly } = useHealthStore()

  useEffect(() => {
    if (Object.keys(data).length === 0) loadAll()
  }, [])

  return { data, weekly, loading, error, loadWeekly }
}