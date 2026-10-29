import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { postJSON } from './api'

export type Lang = 'en' | 'az' | 'both'
type Entry = { text: string | null; origin: string; checks?: Record<string, unknown> }

const LangCtx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: 'en', setLang: () => {} })
const store = new Map<string, Entry>()
const waiting = new Set<string>()
const listeners = new Set<() => void>()
let timer: number | null = null

function flush() {
  timer = null
  const batch = [...waiting].slice(0, 800)
  batch.forEach((t) => waiting.delete(t))
  if (!batch.length) return
  postJSON<Record<string, Entry>>('/api/translations', batch)
    .then((res) => {
      Object.entries(res).forEach(([k, v]) => store.set(k, v))
      listeners.forEach((l) => l())
      if (waiting.size) timer = window.setTimeout(flush, 30)
    })
    .catch(() => batch.forEach((t) => store.set(t, { text: null, origin: 'error' })))
}

function request(text: string) {
  if (store.has(text) || waiting.has(text)) return
  waiting.add(text)
  if (timer === null) timer = window.setTimeout(flush, 40)
}

export function setTranslation(text: string, entry: Entry) {
  store.set(text, entry)
  listeners.forEach((l) => l())
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem('azboq.lang') as Lang) || 'both')
  const setLang = (l: Lang) => {
    localStorage.setItem('azboq.lang', l)
    setLangState(l)
  }
  return <LangCtx.Provider value={{ lang, setLang }}>{children}</LangCtx.Provider>
}

export function useLang() {
  return useContext(LangCtx)
}

function useTranslation(text: string | null | undefined): Entry | undefined {
  const [, force] = useState(0)
  useEffect(() => {
    if (!text) return
    const l = () => force((n) => n + 1)
    listeners.add(l)
    request(text)
    return () => {
      listeners.delete(l)
    }
  }, [text])
  return text ? store.get(text) : undefined
}

/** Azerbaijani source text shown in the chosen language. The source is always one hover away. */
const HAS_LETTER = /\p{L}{2}/u

export function T({ az, className }: { az: string | null | undefined; className?: string }) {
  const { lang } = useLang()
  const wordy = !!az && HAS_LETTER.test(az)
  const entry = useTranslation(lang === 'az' || !wordy ? null : az)
  const en = entry?.text ?? null
  const origin = entry?.origin
  const title = useMemo(() => {
    if (!az) return undefined
    if (origin === 'pending' || !en) return `Azerbaijani original (translation pending)\n${az}`
    return `Azerbaijani original · ${origin === 'human' ? 'corrected by a person' : origin === 'glossary' ? 'glossary translation' : 'machine translation'}\n${az}`
  }, [az, en, origin])
  if (!az) return <span className={className}>—</span>
  if (!wordy || (en && en.trim() === az.trim())) return <span className={className}>{az}</span>
  if (lang === 'az' || !en) {
    return (
      <span className={className} lang="az" title={lang !== 'az' ? title : undefined}>
        {az}
        {lang !== 'az' && origin === 'pending' ? <i className="pending" title="Translation pending"> ·</i> : null}
      </span>
    )
  }
  if (lang === 'en') {
    return (
      <span className={className} title={title}>
        {en}
      </span>
    )
  }
  return (
    <span className={className} title={title}>
      <span lang="az">{az}</span>
      <span className="en-under">{en}</span>
    </span>
  )
}
