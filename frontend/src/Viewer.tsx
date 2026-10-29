import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { getJSON } from './api'
import { shortFile, type Target } from './ui'

type Meta = {
  png_url: string
  width: number
  height: number
  bbox?: number[]
  region?: { id: string; title?: string | null; number?: { raw?: string } | null; building?: string | null }
  texts?: { handle: string; text: string; raw: string; at: number[]; layer: string }[]
  lines?: { text: string; bbox: number[] }[]
  number?: string | null
  scanned?: boolean
}

export type Mark = { x: number; y: number; w?: number; h?: number; label?: string }

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
  if (t.kind !== 'dwg' || t.region || !t.handle) return t
  const e = await getJSON<{ region: { id: string } | null }>(`/api/drawing/${t.sha}/entity/${t.handle}`)
  return { ...t, region: e.region?.id ?? null }
}

/** Marker position in image pixels. DWG: model coordinates inside the region box. PDF: points from the top-left. */
function markOf(t: Target, meta: Meta, img: { w: number; h: number }): Mark | null {
  if (t.kind === 'dwg' && t.at && meta.bbox) {
    const [x0, y0, x1, y1] = meta.bbox
    return { x: ((t.at[0] - x0) / (x1 - x0)) * img.w, y: ((y1 - t.at[1]) / (y1 - y0)) * img.h, label: t.label }
  }
  if (t.kind === 'pdf' && t.bbox && meta.width) {
    const k = img.w / meta.width
    const [a, b, c, d] = t.bbox
    return { x: a * k, y: b * k, w: (c - a) * k, h: (d - b) * k, label: t.label }
  }
  return null
}

export function Viewer({ target, onMeta, extraMarks }: { target: Target | null; onMeta?: (m: Meta | null, t: Target | null) => void; extraMarks?: (meta: Meta, img: { w: number; h: number }) => Mark[] }) {
  const box = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<{ meta: Meta | null; t: Target | null; error: string | null; loading: boolean }>({ meta: null, t: null, error: null, loading: false })
  const [img, setImg] = useState<{ w: number; h: number } | null>(null)
  const [view, setView] = useState({ s: 1, x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null)
  const key = target ? JSON.stringify(target) : ''

  useEffect(() => {
    let alive = true
    setImg(null)
    if (!target) {
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
    (focus?: Mark | null) => {
      const el = box.current
      if (!el || !img) return
      const cw = el.clientWidth
      const ch = el.clientHeight
      const s0 = Math.min(cw / img.w, ch / img.h) * 0.96
      if (focus) {
        const s = Math.min(s0 * 3.2, 1.6)
        setView({ s, x: cw / 2 - (focus.x + (focus.w || 0) / 2) * s, y: ch / 2 - (focus.y + (focus.h || 0) / 2) * s })
      } else setView({ s: s0, x: (cw - img.w * s0) / 2, y: (ch - img.h * s0) / 2 })
    },
    [img],
  )

  const mark = state.meta && state.t && img ? markOf(state.t, state.meta, img) : null
  const extras = state.meta && img && extraMarks ? extraMarks(state.meta, img) : []

  useLayoutEffect(() => {
    fit(mark)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [img, key])

  const onWheel = (e: React.WheelEvent) => {
    const el = box.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const px = e.clientX - r.left
    const py = e.clientY - r.top
    const k = Math.exp(-e.deltaY * 0.0015)
    setView((v) => {
      const s = Math.max(0.02, Math.min(8, v.s * k))
      const f = s / v.s
      return { s, x: px - (px - v.x) * f, y: py - (py - v.y) * f }
    })
  }
  const zoom = (k: number) => {
    const el = box.current
    if (!el) return
    const px = el.clientWidth / 2
    const py = el.clientHeight / 2
    setView((v) => {
      const s = Math.max(0.02, Math.min(8, v.s * k))
      const f = s / v.s
      return { s, x: px - (px - v.x) * f, y: py - (py - v.y) * f }
    })
  }

  const foot = state.t
    ? state.t.kind === 'pdf'
      ? `PDF page ${state.t.page + 1}${state.meta?.number ? ` · ${state.meta.number}` : ''}${state.meta?.scanned ? ' · scanned, no text layer' : ''}`
      : `${state.meta?.region?.number?.raw || state.t.region} · ${state.meta?.region?.title || 'sheet'} · rendered from the DWG via ODA`
    : ''

  const transform = `translate(${view.x}px, ${view.y}px) scale(${view.s})`
  const r = 16 / view.s

  return (
    <div className="viewer">
      <div
        className="canvas"
        ref={box}
        onWheel={onWheel}
        onMouseDown={(e) => (drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y })}
        onMouseMove={(e) => {
          const d = drag.current
          if (d) setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }))
        }}
        onMouseUp={() => (drag.current = null)}
        onMouseLeave={() => (drag.current = null)}
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
                  <rect key={i} x={m.x - r * 0.5} y={m.y - r * 0.5} width={(m.w || 0) + r} height={(m.h || 0) + r} fill="#ff6a2a" fillOpacity={0.12} stroke="#ff6a2a" strokeOpacity={0.5} strokeWidth={1.2 / view.s} rx={4 / view.s} />
                ))}
                {mark ? (
                  mark.w ? (
                    <rect x={mark.x - 4 / view.s} y={mark.y - 4 / view.s} width={mark.w + 8 / view.s} height={(mark.h || 0) + 8 / view.s} fill="#ff6a2a" fillOpacity={0.18} stroke="#e8551a" strokeWidth={2.2 / view.s} rx={4 / view.s} />
                  ) : (
                    <g>
                      <circle cx={mark.x} cy={mark.y} r={r * 1.7} fill="#ff6a2a" fillOpacity={0.16} stroke="#e8551a" strokeWidth={2.2 / view.s} />
                      <circle cx={mark.x} cy={mark.y} r={r * 0.25} fill="#e8551a" />
                    </g>
                  )
                ) : null}
              </svg>
            ) : null}
          </>
        ) : null}
      </div>
      {!target ? <div className="empty">Pick something with a source to see it on its sheet.</div> : null}
      {state.loading ? <div className="empty">Opening the sheet… the first open of a large drawing can take a while.</div> : null}
      {state.error ? <div className="empty">This source cannot be shown on a sheet: {state.error}</div> : null}
      {state.meta ? (
        <>
          <div className="foot" title={foot}>{foot}</div>
          <div className="zoom">
            <button onClick={() => zoom(1.4)} title="Zoom in">+</button>
            <button onClick={() => zoom(1 / 1.4)} title="Zoom out">−</button>
            <button onClick={() => fit(null)} title="Whole sheet">⤢</button>
            {mark ? <button onClick={() => fit(mark)} title="Back to the evidence">◎</button> : null}
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
