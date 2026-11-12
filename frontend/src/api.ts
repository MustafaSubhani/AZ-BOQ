import { useEffect, useState } from 'react'

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  return sendJSON<T>('POST', path, body)
}

export async function delJSON<T>(path: string, body: unknown): Promise<T> {
  return sendJSON<T>('DELETE', path, body)
}

async function sendJSON<T>(method: string, path: string, body: unknown): Promise<T> {
  const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

const cache = new Map<string, Promise<unknown>>()
const resolvedCache = new Map<string, unknown>()
const listeners = new Set<(prefix?: string) => void>()

/** Clears cached endpoints and triggers smooth background revalidation across all mounted views (zero page reload). */
export function clearCache(prefix?: string) {
  if (!prefix) {
    cache.clear()
  } else {
    for (const key of [...cache.keys()]) {
      if (key.startsWith(prefix)) cache.delete(key)
    }
  }
  for (const fn of listeners) fn(prefix)
}

export function revalidateAll() {
  clearCache()
}

export function useData<T>(path: string | null): { data: T | null; error: string | null; loading: boolean; revalidating: boolean } {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean; revalidating: boolean }>(() => {
    const warm = path ? (resolvedCache.get(path) as T | undefined) : undefined
    return {
      data: warm ?? null,
      error: null,
      loading: !!path && warm === undefined,
      revalidating: false,
    }
  })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!path) return
    const onInvalidate = (prefix?: string) => {
      if (!prefix || path.startsWith(prefix)) {
        setTick((t) => t + 1)
      }
    }
    listeners.add(onInvalidate)
    return () => {
      listeners.delete(onInvalidate)
    }
  }, [path])

  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false, revalidating: false })
      return
    }
    let alive = true
    const hasWarm = resolvedCache.has(path)
    if (!cache.has(path)) {
      const p = getJSON<T>(path).then((res) => {
        resolvedCache.set(path, res)
        return res
      })
      cache.set(path, p)
    }
    setState((s) => ({
      data: s.data ?? ((resolvedCache.get(path) as T | undefined) ?? null),
      error: null,
      loading: !hasWarm && !s.data,
      revalidating: hasWarm || !!s.data,
    }))
    ;(cache.get(path) as Promise<T>)
      .then((data) => {
        if (alive) setState({ data, error: null, loading: false, revalidating: false })
      })
      .catch((e) => {
        cache.delete(path)
        if (alive) setState((s) => ({ data: s.data, error: String(e.message || e), loading: false, revalidating: false }))
      })
    return () => {
      alive = false
    }
  }, [path, tick])

  return state
}
