import NumberFlow from '@number-flow/react'
import { clsx, type ClassValue } from 'clsx'
import { motion } from 'motion/react'
import type { CSSProperties, ReactNode } from 'react'
import { twMerge } from 'tailwind-merge'
import { WarningCircle } from './icons'
import { useLang } from './i18n'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

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
  different: { label: 'Contradicts', cls: 'bad', dot: 'bad', hint: 'The drawings give another quantity' },
  review: { label: 'Needs review', cls: 'warn', dot: 'warn', hint: 'Only weak candidates were found' },
  blocked: { label: 'Blocked', cls: 'warn', dot: 'warn', hint: 'An input the measurement needs is missing' },
  not_found: { label: 'Not on drawings', cls: 'muted', dot: '', hint: 'No measured item and the number is not printed on any drawing of this building' },
}

export const STATUS_ORDER = ['matched', 'printed', 'derived', 'different', 'review', 'blocked', 'not_found']
export const STATUS_COLOR: Record<string, string> = {
  matched: '#059669',
  printed: '#34d399',
  derived: '#2563eb',
  different: '#e11d48',
  review: '#d97706',
  blocked: '#f59e0b',
  not_found: '#d4d4d8',
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
  depot: ['4-Bay Fire Depot', '4 çıxışlı Yanğın Deposu'],
  tower: ['Drill Tower', 'Təlim Qülləsi'],
  fence: ['Fence & Retaining Wall', 'Hasar və İstinad Divarı'],
  site: ['Site Works', 'Ərazi işləri'],
  toilet: ['Toilet Block', 'Ayaqyolu'],
  heating_point: ['Heating Point', 'İstilik məntəqəsi'],
  pump_station: ['Pump Station', 'Su nasos stansiyası'],
  substation: ['Substation', 'Yarımstansiya'],
  generator: ['Diesel Generator', 'Dizel Generatoru'],
  checkpoint: ['Guard Room', 'Nəzarətçi otağı'],
  canopy: ['Canopy / Wash', 'Avtoyuma / Talvar'],
  smoking_area: ['Gazebo / Shelter', 'Söhbətgah'],
  drinking_tanks: ['Drinking Water Tanks', 'İçməli su çənləri'],
  fire_tanks: ['Fire Water Tanks', 'Yanğın su çənləri'],
  drinking_tank_5: ['Drinking Tank 5 m³', 'İçməli su çəni 5 m³'],
  sand_pit: ['Sand Training Pit', 'Qum meydançası'],
  roads: ['Roads & Pavements', 'Yollar və səkilər'],
  grading: ['Vertical Grading', 'Şaquli planlaşdırma'],
  networks: ['External Networks', 'Xarici şəbəkələr'],
  unknown: ['Unassigned', 'Təyin edilməyib'],
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

export function readableRow(label: string) {
  return label.replace(/\bfloor_2\b/g, '2nd floor').replace(/\bfloor_1\b/g, '1st floor')
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
      className={`src ${active ? 'on' : ''}`}
      onClick={() => t && onOpen?.(t)}
      disabled={!t}
      title={src.file_name}
    >
      <small>{where(src)}</small>
      <span lang="az" className="font-medium text-[var(--ink)]">{src.decoded_text || '—'}</span>
      {src.raw_text && src.raw_text !== src.decoded_text ? (
        <span className="faint" style={{ display: 'block', fontSize: 11.5 }}>
          stored as: <span className="mono">{src.raw_text.slice(0, 80)}</span>
        </span>
      ) : null}
      {src.row_label ? <span className="muted" style={{ display: 'block', fontSize: 11.5 }}>row: {readableRow(src.row_label)}</span> : null}
      {loc.kind === 'dxf_dimension' && loc.measurement ? (
        <span className="muted" style={{ display: 'block', fontSize: 11.5 }}>
          measured {Number(loc.measurement).toFixed(1)}
          {loc.override ? ` · text override “${loc.override}”` : ''}
        </span>
      ) : null}
    </button>
  )
}

/** Animated tabular numeral powered by @number-flow/react */
export function AnimatedNumber({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}: {
  value: number
  decimals?: number
  prefix?: string
  suffix?: string
  className?: string
}) {
  return (
    <span className={cn('num inline-flex items-baseline', className)}>
      {prefix ? <span className="mr-0.5">{prefix}</span> : null}
      <NumberFlow
        value={Number.isFinite(value) ? value : 0}
        format={{ minimumFractionDigits: decimals, maximumFractionDigits: decimals }}
        transformTiming={{ duration: 380, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }}
      />
      {suffix ? <span className="ml-1 text-[0.72em] font-normal text-[var(--muted)]">{suffix}</span> : null}
    </span>
  )
}

/** Shared-layout sliding segmented control (Motion spring physics) */
export function SegmentedTabs<T extends string>({
  id,
  options,
  value,
  onChange,
  size = 'md',
}: {
  id: string
  options: { value: T; label: ReactNode; count?: number | string; tone?: 'bad' | 'warn' | 'ok' | 'default' }[]
  value: T
  onChange: (val: T) => void
  size?: 'sm' | 'md'
}) {
  return (
    <div className={cn('chips relative', size === 'sm' && 'p-[2px]')}>
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              'chip relative z-10 transition-colors',
              size === 'sm' ? 'h-6 px-2.5 text-[11.5px]' : 'h-7 px-3 text-[12px]',
              active ? 'text-[var(--ink)]' : 'text-[var(--muted)] hover:text-[var(--ink-2)]',
            )}
          >
            {active ? (
              <motion.span
                layoutId={`seg-${id}`}
                transition={{ type: 'spring', stiffness: 460, damping: 36 }}
                className="pointer-events-none absolute inset-0 -z-10 rounded-[6px] bg-[var(--paper)] shadow-[0_1px_2px_rgba(9,9,11,0.06),0_0_0_1px_var(--line-2)]"
              />
            ) : null}
            <span>{opt.label}</span>
            {opt.count !== undefined ? (
              <b
                className={cn(
                  'ml-1 font-mono text-[11px]',
                  active
                    ? opt.tone === 'bad'
                      ? 'text-[var(--bad-text)]'
                      : opt.tone === 'warn'
                        ? 'text-[var(--warn-text)]'
                        : 'text-[var(--ink)]'
                    : 'text-[var(--faint)]',
                )}
              >
                {opt.count}
              </b>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}

/** Shimmer skeleton building block */
export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div className={cn('shimmer rounded-md', className)} style={style} aria-hidden />
}

/** Geometry-matched shimmer skeleton states (zero bare spinners) */
export function Loading({ what }: { what?: string }) {
  const kind = (what || '').toLowerCase()

  if (kind.includes('summary') || kind.includes('overview')) {
    return (
      <div className="flex flex-col gap-4" role="status" aria-label={`Loading ${what || 'screen'}`}>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card p-4 gap-3">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-7 w-36" />
              <Skeleton className="h-3 w-44" />
            </div>
          ))}
        </div>
        <div className="card p-5 gap-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-28" />
          </div>
          <Skeleton className="h-3 w-full rounded-full" />
          <div className="flex gap-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-7 w-24 rounded-lg" />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="card p-5 gap-3 lg:col-span-7">
            <Skeleton className="h-4 w-40 mb-2" />
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-7 w-full" />
            ))}
          </div>
          <div className="card p-5 gap-3 lg:col-span-5">
            <Skeleton className="h-4 w-36 mb-2" />
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 w-full" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (kind.includes('takeoff')) {
    return (
      <div className="work" role="status" aria-label="Loading takeoff workspace">
        <div className="card p-3 gap-2.5">
          <Skeleton className="h-8 w-full rounded-lg" />
          <Skeleton className="h-8 w-full rounded-lg" />
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
        <div className="card p-4 gap-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="flex-1 min-h-[380px] w-full rounded-xl" />
        </div>
        <div className="card p-4 gap-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-16 w-full rounded-lg" />
        </div>
      </div>
    )
  }

  // Default dense register / bill table skeleton
  return (
    <div className="flex flex-col gap-3" role="status" aria-label={`Loading ${what || 'data'}`}>
      <div className="card overflow-hidden">
        <div className="flex items-center gap-2 border-b border-[var(--line)] p-3">
          <Skeleton className="h-8 w-64 rounded-lg" />
          <Skeleton className="h-8 w-36 rounded-lg" />
          <Skeleton className="ml-auto h-8 w-52 rounded-lg" />
        </div>
        <div className="divide-y divide-[var(--line)]">
          {Array.from({ length: 11 }).map((_, idx) => (
            <div key={idx} className="flex items-center gap-4 px-4 py-3">
              <Skeleton className="h-3.5 w-14" />
              <Skeleton className="h-3.5 flex-1 max-w-[440px]" />
              <Skeleton className="h-3.5 w-12" />
              <Skeleton className="h-3.5 w-20 ml-auto" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function ErrorBox({ error }: { error: string }) {
  return (
    <div className="err" role="alert">
      <WarningCircle size={18} className="mt-0.5 shrink-0" />
      <div>
        <b>Could not load this screen.</b>
        <div style={{ fontSize: 12.5, marginTop: 2 }}>{error.slice(0, 400)}</div>
      </div>
    </div>
  )
}

export function Card({ title, sub, right, children, className, style }: { title?: ReactNode; sub?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <div className={cn('card', className)} style={style}>
      {title || right ? (
        <div className="card-h">
          <div style={{ minWidth: 0 }}>
            <div className="card-title">{title}</div>
            {sub ? <span className="sub">{sub}</span> : null}
          </div>
          {right ? <div className="right">{right}</div> : null}
        </div>
      ) : null}
      {children}
    </div>
  )
}

export function Ring({ value, size = 44, stroke = 4.5, label, color }: { value: number; size?: number; stroke?: number; label?: ReactNode; color?: string }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(1, value || 0))
  return (
    <span className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden>
        <circle className="track" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} />
        <circle className="arc" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} strokeDasharray={`${Math.max(v * c, v ? 2 : 0)} ${c}`} style={color ? { stroke: color } : undefined} />
      </svg>
      {label !== undefined ? <i>{label}</i> : null}
    </span>
  )
}

export function Empty({ icon, title, children, action }: { icon?: ReactNode; title?: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty-state">
      {icon ? <span className="well idle sm">{icon}</span> : null}
      {title ? <b>{title}</b> : null}
      {children ? <p>{children}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}

export function pct(part: number, whole: number, digits = 1) {
  if (!whole) return '0%'
  return `${((part / whole) * 100).toFixed(digits)}%`
}
