import { useEffect, useState } from 'react'

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

const cache = new Map<string, Promise<unknown>>()

export function useData<T>(path: string | null): { data: T | null; error: string | null; loading: boolean } {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({ data: null, error: null, loading: !!path })
  useEffect(() => {
    if (!path) return
    let alive = true
    if (!cache.has(path)) cache.set(path, getJSON<T>(path))
    setState((s) => ({ ...s, loading: true }))
    ;(cache.get(path) as Promise<T>)
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((e) => {
        cache.delete(path)
        if (alive) setState({ data: null, error: String(e.message || e), loading: false })
      })
    return () => {
      alive = false
    }
  }, [path])
  return state
}
