import { useCallback, useEffect, useRef, useState } from 'react'

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  resetDeps: any[] = [],
) {
  const [data, setData]       = useState<T | null>(null)
  const [error, setError]     = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef            = useRef(fetcher)
  fetcherRef.current          = fetcher

  const run = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  // When resetDeps change: clear stale data, show loading, fetch immediately
  useEffect(() => {
    setData(null)
    setLoading(true)
    run()
  // resetDeps spread intentionally — caller controls identity
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, resetDeps)

  // Polling interval (independent of filter changes)
  useEffect(() => {
    const id = setInterval(run, intervalMs)
    return () => clearInterval(id)
  }, [run, intervalMs])

  return { data, error, loading, refetch: run }
}
