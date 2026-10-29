import type { ReactNode } from 'react'
import { useLang } from './i18n'

export type Source = {
  file_id: string
  file_name: string
  locator: Record<string, any>
  raw_text: string | null
  decoded_text: string | null
  sheet?: string | null
  row_label?: string | null
  keywords?: string[] | null
}

export type Value = {
  value: number | null
  unit: string
  method: string
  status: string
  sources: Source[]
  formula: string | null
  inputs: Record<string, Value>
  missing: string[]
  note: string
  searched: string[]
  rejected: any[]
  conflicts: any[]
}

export type Target =
  | { kind: 'dwg'; sha: string; region: string | null; at?: number[] | null; handle?: string | null; label?: string }
  | { kind: 'pdf'; sha: string; page: number; bbox?: number[] | null; label?: string }

export const LINE_STATUS: Record<string, { label: string; cls: string; dot: string; hint: string }> = {
  matched: { label: 'Matches', cls: 'ok', dot: 'ok', hint: 'Equals a quantity measured from the drawings' },
  printed: { label: 'Printed on drawing', cls: 'ok', dot: 'ok', hint: 'The same number is written on a drawing of this building' },
  derived: { label: 'Derived', cls: 'info', dot: 'info', hint: 'Follows from a checked line (repeat, same quantity or density)' },
  different: { label: 'Different', cls: 'bad', dot: 'bad', hint: 'The drawings give another quantity' },
  review: { label: 'Needs review', cls: 'warn', dot: 'warn', hint: 'Only weak candidates were found' },
  blocked: { label: 'Blocked', cls: 'warn', dot: 'warn', hint: 'An input the measurement needs is missing' },
  not_found: { label: 'Not on drawings', cls: 'muted', dot: '', hint: 'No measured item and the number is not printed on any drawing of this building' },
}

export const VALUE_STATUS: Record<string, { label: string; cls: string }> = {
  verified: { label: 'Verified', cls: 'ok' },
  extracted: { label: 'Extracted', cls: 'info' },
  review: { label: 'Review', cls: 'warn' },
  blocked: { label: 'Blocked', cls: 'bad' },
}

export const METHOD: Record<string, string> = {
  geometry: 'Measured from geometry',
  stated: 'Printed on a drawing',
  schedule: 'Read from a schedule',
  derived: 'Calculated from other values',
  rule: 'Project rule',
  vision: 'Read from a scan',
}

const BUILDINGS: Record<string, [string, string]> = {
  depot: ['Depot', 'Depo'],
  tower: ['Tower', 'Qüllə'],
  fence: ['Fence and retaining wall', 'Hasar və istinad divarı'],
  site: ['Site works', 'Ərazi işləri'],
  toilet: ['Toilet block', 'Ayaqyolu'],
  heating_point: ['Heating point', 'İstilik məntəqəsi'],
  pump_station: ['Pump station', 'Nasos stansiyası'],
  substation: ['Substation', 'Yarımstansiya'],
  generator: ['Generator', 'Generator'],
  checkpoint: ['Checkpoint', 'Nəzarət-buraxılış məntəqəsi'],
  canopy: ['Canopy', 'Talvar'],
  smoking_area: ['Smoking area', 'Siqaret çəkmə yeri'],
  drinking_tanks: ['Drinking water tanks', 'İçməli su çənləri'],
  fire_tanks: ['Fire water tanks', 'Yanğın su çənləri'],
  drinking_tank_5: ['Drinking water tank 5 m³', 'İçməli su çəni 5 m³'],
  roads: ['Roads', 'Yollar'],
  grading: ['Grading', 'Vertikal planlaşdırma'],
  networks: ['External networks', 'Xarici şəbəkələr'],
  unknown: ['Not assigned', 'Təyin edilməyib'],
}

function titleCase(code: string) {
  const s = code.replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function useBuildingName() {
  const { lang } = useLang()
  return (code: string | null | undefined) => {
    if (!code) return '—'
    const pair = BUILDINGS[code]
    if (!pair) return titleCase(code)
    return lang === 'az' ? pair[1] : pair[0]
  }
}

export function tradeName(code: string | null | undefined) {
  return code ? titleCase(code) : '—'
}

/** A label that exists in both languages already (from the rule files), so it is never machine-translated. */
export function Label({ en, az }: { en: string; az: string }) {
  const { lang } = useLang()
  if (lang === 'en') return <span title={az}>{en}</span>
  if (lang === 'az') return <span lang="az" title={en}>{az}</span>
  return (
    <span>
      <span lang="az">{az}</span>
      <span className="en-under">{en}</span>
    </span>
  )
}

export function StatusTag({ status }: { status: string }) {
  const s = LINE_STATUS[status] || { label: status, cls: 'muted', hint: '' }
  return (
    <span className={`tag ${s.cls}`} title={s.hint}>
      {s.label}
    </span>
  )
}

export function ValueTag({ status }: { status: string }) {
  const s = VALUE_STATUS[status] || { label: status, cls: 'muted' }
  return <span className={`tag ${s.cls}`}>{s.label}</span>
}

export function shortFile(name: string | null | undefined) {
  if (!name) return '—'
  return name.split('/').pop() || name
}

export function targetOf(src: Source): Target | null {
  const loc = src.locator || {}
  if (!src.file_id || src.file_id === 'rule') return null
  const sha = src.file_id.slice(0, 12)
  if (String(loc.kind).startsWith('pdf')) return { kind: 'pdf', sha, page: loc.page ?? 0, bbox: loc.bbox, label: src.decoded_text || '' }
  return { kind: 'dwg', sha, region: loc.region ?? null, at: loc.at, handle: loc.handle, label: src.decoded_text || '' }
}

export function where(src: Source) {
  const loc = src.locator || {}
  if (loc.kind === 'rule') return `Project rule ${loc.rule_id} · ${loc.citation ?? ''}`
  if (String(loc.kind).startsWith('pdf')) return `${shortFile(src.file_name)} · page ${(loc.page ?? 0) + 1}`
  const what = loc.kind === 'dxf_dimension' ? 'dimension' : 'text'
  return `${shortFile(src.file_name)} · ${src.sheet || loc.sheet || loc.region || 'model space'} · ${what} ${loc.handle ?? ''}`
}

export function SourceCard({ src, onOpen, active }: { src: Source; onOpen?: (t: Target) => void; active?: boolean }) {
  const t = targetOf(src)
  const loc = src.locator || {}
  return (
    <button
      className="src"
      style={active ? { borderColor: 'var(--accent)' } : undefined}
      onClick={() => t && onOpen?.(t)}
      disabled={!t}
      title={src.file_name}
    >
      <small>{where(src)}</small>
      <span lang="az">{src.decoded_text || '—'}</span>
      {src.raw_text && src.raw_text !== src.decoded_text ? (
        <span className="faint" style={{ display: 'block', fontSize: 11.5 }}>
          stored as: {src.raw_text.slice(0, 80)}
        </span>
      ) : null}
      {src.row_label ? <span className="muted" style={{ display: 'block', fontSize: 11.5 }}>row: {src.row_label}</span> : null}
      {loc.kind === 'dxf_dimension' && loc.measurement ? (
        <span className="muted" style={{ display: 'block', fontSize: 11.5 }}>
          measured {Number(loc.measurement).toFixed(1)}
          {loc.override ? ` · text override “${loc.override}”` : ''}
        </span>
      ) : null}
    </button>
  )
}

export function Loading({ what }: { what?: string }) {
  return <div className="loading">Loading {what || ''}…</div>
}

export function ErrorBox({ error }: { error: string }) {
  return <div className="err">Could not load: {error}</div>
}

export function Card({ title, right, children, className, style }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div className={`card ${className || ''}`} style={style}>
      {title || right ? (
        <div className="card-h">
          {title}
          {right ? <div className="right">{right}</div> : null}
        </div>
      ) : null}
      {children}
    </div>
  )
}
