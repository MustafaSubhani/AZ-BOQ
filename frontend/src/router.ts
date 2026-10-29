import { useEffect, useState } from 'react'

export type Route = { parts: string[]; query: URLSearchParams }

function parse(): Route {
  const raw = window.location.hash.replace(/^#\/?/, '')
  const [path, qs] = raw.split('?')
  return { parts: path ? path.split('/').map(decodeURIComponent) : ['home'], query: new URLSearchParams(qs || '') }
}

export function useRoute(): Route {
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const on = () => setRoute(parse())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return route
}

export function go(path: string, query?: Record<string, string | number | null | undefined>) {
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  window.location.hash = `#/${path}${qs ? `?${qs}` : ''}`
}

export function href(path: string, query?: Record<string, string | number | null | undefined>): string {
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  return `#/${path}${qs ? `?${qs}` : ''}`
}
