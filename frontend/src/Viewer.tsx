import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { getJSON } from './api'
import { CornersOut, Crosshair, FileText, Minus, Plus, Scan } from './icons'
import { shortFile, Skeleton, type Target } from './ui'

type Meta = {
  png_url: string
  width: number
  height: number
  bbox?: number[]
  region?: { id: string; title?: string | null; number?: { raw?: string } | null; building?: string | null }
  texts?: { handle: string; text: string; raw: string; at: number[]; layer: string }[]
  lines?: { text: string; bbox: number[] }[]
  number?: string | { raw?: string } | null
  scanned?: boolean
  transform?: { kind: string; scale: number; offset?: number[]; bbox?: number[]; dpi?: number }
}

export type Mark = { x: number; y: number; w?: number; h?: number; label?: string }

export type SheetShape = {
  id: string
  kind: string
  points: number[][]
  label: string
  area_m2: number | null
  status?: string | null
  lines?: string[]
  room?: string | null
  schedule_m2?: number | null
}

const SHAPE_COLOR: Record<string, string> = {
  room: '#2563eb',
  area_unlinked: '#71717a',
  area_conflict: '#e11d48',
}

const metaCache = new Map<string, Promise<Meta>>()

function metaUrl(t: Target) {
  return t.kind === 'pdf' ? `/api/pdf/${t.sha}/page/${t.page}/meta` : `/api/drawing/${t.sha}/region/${t.region}/meta`
}

export function loadMeta(t: Target): Promise<Meta> {
  const url = metaUrl(t)
  if (!metaCache.has(url)) {
    const p = getJSON<Meta>(url)
    p.catch(() => metaCache.delete(url))
    metaCache.set(url, p)
  }
  return metaCache.get(url)!
}

async function resolveRegion(t: Target): Promise<Target> {
  if (t.kind !== 'dwg' || !t.handle || (t.region && t.at)) return t
  try {
    const e = await getJSON<{ region: { id: string } | null; entity: { at?: number[]; pts?: number[][] } }>(`/api/drawing/${t.sha}/entity/${t.handle}`)
    return { ...t, region: t.region || e.region?.id || null, at: t.at || e.entity?.at || e.entity?.pts?.[0] || null }
  } catch (err) {
    if (t.region) return t
    throw err
  }
}

function sheetNo(n: Meta['number']): string {
  if (!n) return ''
  if (typeof n === 'string') return n
  return n.raw || ''
}

function markOf(t: Target, meta: Meta, img: { w: number; h: number }): Mark | null {
  const tr = meta.transform
  if (t.kind === 'dwg' && t.at && tr?.kind === 'dxf' && tr.bbox && tr.offset) {
    const [x0, , , y1] = tr.bbox
    const [ox, oy] = tr.offset
    return { x: ox + (t.at[0] - x0) * tr.scale, y: oy + (y1 - t.at[1]) * tr.scale, label: t.label }
  }
  if (t.kind === 'dwg' && t.at && meta.bbox) {
    const [x0, y0, x1, y1] = meta.bbox
    return { x: ((t.at[0] - x0) / (x1 - x0)) * img.w, y: ((y1 - t.at[1]) / (y1 - y0)) * img.h, label: t.label }
  }
  if (t.kind === 'pdf' && t.bbox && tr?.kind === 'pdf') {
    const s = tr.scale
    const [a, b, c, d] = t.bbox
    return { x: a * s, y: b * s, w: (c - a) * s, h: (d - b) * s, label: t.label }
  }
  if (t.kind === 'pdf' && t.bbox && meta.width) {
    const k = img.w / meta.width
    const [a, b, c, d] = t.bbox
    return { x: a * k, y: b * k, w: (c - a) * k, h: (d - b) * k, label: t.label }
  }
  return null
}

export function Viewer({
  target,
  onMeta,
  extraMarks,
  emptyText,
  shapes,
  selectedShape,
  onShape,
}: {
  target: Target | null
  onMeta?: (m: Meta | null, t: Target | null) => void
  extraMarks?: (meta: Meta, img: { w: number; h: number }) => Mark[]
  emptyText?: string
  shapes?: SheetShape[]
  selectedShape?: string | null
  onShape?: (id: string | null) => void
}) {
  const box = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<{ meta: Meta | null; t: Target | null; error: string | null; loading: boolean }>({
    meta: null,
    t: null,
    error: null,
    loading: false,
  })
  const [img, setImg] = useState<{ w: number; h: number } | null>(null)
  const [view, setView] = useState({ s: 1, x: 0, y: 0 })
  const viewRef = useRef(view)
  viewRef.current = view

  const rafRef = useRef<number | null>(null)
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null)
  const shownUrl = useRef<string | null>(null)
  const prevUrl = useRef<string | null>(null)
  const key = target ? JSON.stringify(target) : ''

  const cancelAnim = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [])

  const flyTo = useCallback(
    (dest: { s: number; x: number; y: number }, animate: boolean) => {
      cancelAnim()
      const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      if (!animate || prefersReduced) {
        setView(dest)
        return
      }
      const start = viewRef.current
      const t0 = performance.now()
      const dur = 260
      const step = (now: number) => {
        const p = Math.min(1, (now - t0) / dur)
        const ease = 1 - Math.pow(1 - p, 3)
        setView({
          s: start.s + (dest.s - start.s) * ease,
          x: start.x + (dest.x - start.x) * ease,
          y: start.y + (dest.y - start.y) * ease,
        })
        if (p < 1) rafRef.current = requestAnimationFrame(step)
        else rafRef.current = null
      }
      rafRef.current = requestAnimationFrame(step)
    },
    [cancelAnim],
  )

  useEffect(() => () => cancelAnim(), [cancelAnim])

  useEffect(() => {
    let alive = true
    if (!target) {
      shownUrl.current = null
      prevUrl.current = null
      setImg(null)
      setState({ meta: null, t: null, error: null, loading: false })
      onMeta?.(null, null)
      return
    }
    setState((s) => ({ ...s, loading: true, error: null }))
    resolveRegion(target)
      .then((t) => {
        if (t.kind === 'dwg' && !t.region) throw new Error('this entity is outside every detected sheet')
        return loadMeta(t).then((meta) => ({ t, meta }))
      })
      .then(({ t, meta }) => {
        if (!alive) return
        if (shownUrl.current !== meta.png_url) {
          shownUrl.current = meta.png_url
          setImg(null)
        }
        setState({ meta, t, error: null, loading: false })
        onMeta?.(meta, t)
      })
      .catch((e) => alive && setState({ meta: null, t: null, error: String(e.message || e), loading: false }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const fit = useCallback(
    (focus?: Mark | null, animate = false) => {
      const el = box.current
      if (!el || !img) return
      const cw = el.clientWidth
      const ch = el.clientHeight
      const s0 = Math.min(cw / img.w, ch / img.h) * 0.95
      if (focus) {
        const s = focus.w ? Math.min(s0 * 3.2, 1.6) : Math.min(Math.max(s0 * 6, 1.2), 3.2)
        flyTo({ s, x: cw / 2 - (focus.x + (focus.w || 0) / 2) * s, y: ch / 2 - (focus.y + (focus.h || 0) / 2) * s }, animate)
      } else {
        flyTo({ s: s0, x: (cw - img.w * s0) / 2, y: (ch - img.h * s0) / 2 }, animate)
      }
    },
    [img, flyTo],
  )

  const mark = state.meta && state.t && img ? markOf(state.t, state.meta, img) : null
  const extras = state.meta && img && extraMarks ? extraMarks(state.meta, img) : []

  useLayoutEffect(() => {
    if (!img || !state.meta) return
    const sameSheet = prevUrl.current === state.meta.png_url
    prevUrl.current = state.meta.png_url
    fit(mark, sameSheet)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [img, key])

  useEffect(() => {
    const el = box.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      cancelAnim()
      const r = el.getBoundingClientRect()
      const px = e.clientX - r.left
      const py = e.clientY - r.top
      const k = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015))
      setView((v) => {
        const s = Math.max(0.02, Math.min(8, v.s * k))
        const f = s / v.s
        return { s, x: px - (px - v.x) * f, y: py - (py - v.y) * f }
      })
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [cancelAnim])

  const zoom = (k: number) => {
    const el = box.current
    if (!el) return
    const px = el.clientWidth / 2
    const py = el.clientHeight / 2
    const v = viewRef.current
    const s = Math.max(0.02, Math.min(8, v.s * k))
    const f = s / v.s
    flyTo({ s, x: px - (px - v.x) * f, y: py - (py - v.y) * f }, true)
  }

  const foot = state.t
    ? state.t.kind === 'pdf'
      ? `PDF page ${state.t.page + 1}${sheetNo(state.meta?.number) ? ` · ${sheetNo(state.meta?.number)}` : ''}${state.meta?.scanned ? ' · scan (review only)' : ''}`
      : `${state.meta?.region?.number?.raw || state.t.region} · ${state.meta?.region?.title || 'sheet'} · DWG via ODA`
    : ''

  const transform = `translate(${view.x}px, ${view.y}px) scale(${view.s})`
  const r = 16 / view.s

  return (
    <div className="viewer">
      <div
        className="canvas"
        ref={box}
        onPointerDown={(e) => {
          if (e.button !== 0) return
          cancelAnim()
          e.currentTarget.setPointerCapture(e.pointerId)
          drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }
        }}
        onPointerMove={(e) => {
          const d = drag.current
          if (d) setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }))
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
        onDoubleClick={() => zoom(1.6)}
      >
        {state.meta ? (
          <>
            <img
              src={state.meta.png_url}
              alt="sheet"
              draggable={false}
              style={{ transform, width: img?.w, height: img?.h }}
              onLoad={(e) => setImg({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
            />
            {img ? (
              <svg className="overlay" width={img.w} height={img.h} style={{ transform }}>
                {extras.map((m, i) => (
                  <rect
                    key={i}
                    x={m.x - r * 0.5}
                    y={m.y - r * 0.5}
                    width={(m.w || 0) + r}
                    height={(m.h || 0) + r}
                    fill="#2563eb"
                    fillOpacity={0.12}
                    stroke="#2563eb"
                    strokeOpacity={0.55}
                    strokeWidth={1.3 / view.s}
                    rx={4 / view.s}
                  />
                ))}
                {mark ? (
                  mark.w ? (
                    <rect
                      x={mark.x - 4 / view.s}
                      y={mark.y - 4 / view.s}
                      width={mark.w + 8 / view.s}
                      height={(mark.h || 0) + 8 / view.s}
                      fill="#2563eb"
                      fillOpacity={0.16}
                      stroke="#1d4ed8"
                      strokeWidth={2.2 / view.s}
                      rx={4 / view.s}
                    />
                  ) : (
                    <g>
                      <circle className="pulse" cx={mark.x} cy={mark.y} r={r * 1.7} fill="none" stroke="#2563eb" strokeWidth={2 / view.s} />
                      <circle cx={mark.x} cy={mark.y} r={r * 1.7} fill="#2563eb" fillOpacity={0.15} stroke="#1d4ed8" strokeWidth={2.2 / view.s} />
                      <circle cx={mark.x} cy={mark.y} r={r * 0.28} fill="#1d4ed8" />
                    </g>
                  )
                ) : null}
              </svg>
            ) : null}
            {img && shapes?.length ? (
              <svg className="shapes" width={img.w} height={img.h} style={{ transform }}>
                {shapes.map((shape) => (
                  <polygon
                    key={shape.id}
                    points={shape.points.map((p) => p.join(',')).join(' ')}
                    className={[
                      'shape',
                      shape.id === selectedShape ? 'selected' : '',
                      shape.status === 'different' || shape.kind === 'area_conflict' ? 'bad' : '',
                    ].join(' ')}
                    style={{ ['--c' as string]: SHAPE_COLOR[shape.kind] || SHAPE_COLOR.area_unlinked }}
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation()
                      onShape?.(shape.id)
                    }}
                  >
                    <title>{`${shape.label}${shape.area_m2 != null ? ` · ${shape.area_m2.toFixed(2)} m²` : ''}`}</title>
                  </polygon>
                ))}
              </svg>
            ) : null}
          </>
        ) : null}
      </div>

      {!target ? (
        <div className="empty">
          <span className="well idle sm"><FileText size={18} /></span>
          <span>{emptyText || 'Select a source citation to inspect it on the drawing sheet.'}</span>
        </div>
      ) : null}

      {state.loading && !state.meta ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 bg-[var(--paper-3)]/85 backdrop-blur-[1px]">
          <Skeleton className="h-[68%] w-[78%] rounded-xl border border-[var(--line-2)] shadow-sm" />
          <span className="text-[12px] text-[var(--muted)]">Rendering drawing sheet…</span>
        </div>
      ) : null}

      {state.error ? (
        <div className="empty">
          <span className="well warn sm"><Scan size={18} /></span>
          <span>Cannot display sheet region: {state.error}</span>
        </div>
      ) : null}

      {state.meta ? (
        <>
          <div className="foot" title={foot}>
            {state.t?.kind === 'pdf' ? <FileText size={13} /> : <Scan size={13} />}
            <span>{foot}</span>
          </div>
          <div className="zoom">
            <button type="button" onClick={() => zoom(1.4)} title="Zoom in" aria-label="Zoom in"><Plus size={14} /></button>
            <button type="button" onClick={() => zoom(1 / 1.4)} title="Zoom out" aria-label="Zoom out"><Minus size={14} /></button>
            <button type="button" onClick={() => fit(null, true)} title="Fit whole sheet" aria-label="Fit whole sheet"><CornersOut size={14} /></button>
            {mark ? (
              <button type="button" onClick={() => fit(mark, true)} title="Fly to citation marker" aria-label="Fly to citation marker">
                <Crosshair size={14} />
              </button>
            ) : null}
            <div className="pct">{Math.round(view.s * 100)}%</div>
          </div>
        </>
      ) : null}
    </div>
  )
}

export function fileLabel(t: Target | null, name?: string) {
  if (!t) return ''
  return `${shortFile(name)}${t.kind === 'pdf' ? ` · page ${t.page + 1}` : ` · ${t.region}`}`
}
