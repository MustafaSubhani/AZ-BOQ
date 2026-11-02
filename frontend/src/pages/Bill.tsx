import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, Search, X } from '../icons'
import { clearCache, delJSON, postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, Empty, ErrorBox, LINE_STATUS, Loading, SourceCard, StatusTag, targetOf, tradeName, useBuildingName, type Source, type Target } from '../ui'
import { Viewer } from '../Viewer'
import { reasonText } from '../reasons'

type Line = {
  id: string
  row: number
  section: string
  item: number | string | null
  description: string
  unit_raw: string | null
  unit: string
  unit_known: boolean
  qty: number
  rate: number | null
  amount: number | null
  building: string
  trade: string
  comment: string | null
  check: {
    status: string
    reason: string
    our_qty: number | null
    gap?: number | null
    gap_pct?: number | null
    item?: string
    sources?: Source[]
    candidates?: Source[]
    derived_from?: string
    reviewer?: { kind?: string; delta?: number; value?: number }
    method?: string
    group_total?: number
    engine_qty?: number | null
    engine_reason?: string
    override?: { id: number; expression: string; author: string; reason: string }
    review_reasons?: { code: string; link?: string; citation?: string; rule?: string; note?: string; accepted_by?: string; file?: string }[]
  } | null
}
type Explain = {
  item?: { label_en?: string; formula?: string | null; substituted?: string | null; citation?: string } | null
  inputs: { label: string; value: number | null; unit: string; sources: { file?: string; page?: number | null; row?: string | null; col?: string | null; printed?: string | null; is_rule?: boolean; citation?: string | null }[] }[]
  printed: { file?: string; page?: number | null; row?: string | null; col?: string | null; printed?: string | null; is_rule?: boolean }[]
}
type Section = { code: string; stored_code: any; row: number; title: string; trade: string; building: string; code_repaired: boolean }
type BillData = { sections: Section[]; lines: Line[]; totals: Record<string, number>; chain: Record<string, any>; line_sum: number; unknown_units: any[]; external_links: any }

const CHECKED = new Set(['matched', 'printed', 'derived'])
const EDITABLE = new Set(['review', 'different', 'not_found'])

function cleanNum(n: number): string {
  return n.toFixed(6).replace(/\.?0+$/, '')
}

function QuantityForm({ line, expr, setExpr, who, setWho, qtyWhy, setQtyWhy, editErr, setEditErr, saving, setSaving }: {
  line: Line
  expr: string
  setExpr: (value: string) => void
  who: string
  setWho: (value: string) => void
  qtyWhy: string
  setQtyWhy: (value: string) => void
  editErr: string
  setEditErr: (value: string) => void
  saving: boolean
  setSaving: (value: boolean) => void
}) {
  return (
    <form id="qty-editor" className="box edit" onSubmit={async (e) => {
      e.preventDefault()
      if (saving) return
      if (!expr.trim() || !who.trim() || !qtyWhy.trim()) {
        setEditErr('Enter a quantity, your name, and why you are changing it.')
        return
      }
      setSaving(true)
      setEditErr('')
      try {
        try { localStorage.setItem('azboq.author', who.trim()) } catch { /* keep going */ }
        await postJSON('/api/review', {
          target_kind: 'line',
          target_id: line.id,
          action: 'override',
          reason: qtyWhy.trim(),
          author: who.trim(),
          payload: { expression: expr.trim(), unit: line.unit },
        })
        clearCache()
        window.location.reload()
      } catch (err) {
        setEditErr(errText(err))
        setSaving(false)
      }
    }}>
      <small>{line.check?.override ? 'Edited quantity' : 'Set the quantity'}</small>
      <div className="faint">{quantityHint(line)}</div>
      <input aria-label="Quantity or formula" inputMode="decimal" value={expr} onChange={(e) => setExpr(e.target.value)} placeholder="12.4 or 3 × 4.2" />
      <input aria-label="Your name" placeholder="Your name" value={who} onChange={(e) => setWho(e.target.value)} />
      <input aria-label="Why you are changing it" placeholder="Why this figure is right" value={qtyWhy} onChange={(e) => setQtyWhy(e.target.value)} />
      {editErr ? <div className="err">{editErr}</div> : null}
      <div className="acts">
        <button className="btn" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save quantity'}</button>
        {line.check?.override ? (
          <button className="quiet" type="button" disabled={saving} onClick={async () => {
            if (!who.trim()) {
              setEditErr('Enter your name before putting the measured figure back.')
              return
            }
            setSaving(true)
            setEditErr('')
            try {
              try { localStorage.setItem('azboq.author', who.trim()) } catch { /* keep going */ }
              await delJSON(`/api/review/${line.check!.override!.id}`, {
                author: who.trim(),
                reason: qtyWhy.trim() || 'the measured figure stands',
              })
              clearCache()
              window.location.reload()
            } catch (err) {
              setEditErr(errText(err))
              setSaving(false)
            }
          }}>Use the measured figure</button>
        ) : null}
      </div>
    </form>
  )
}

function quantityHint(line: Line): string {
  const measured = line.check?.override ? line.check.engine_qty : line.check?.our_qty
  const figure = measured != null ? `${fmt(measured, 3)} ${line.unit}` : ''
  if (line.check?.override) {
    return figure ? `The check measured ${figure}. The bill is using your figure.` : 'The check had no figure. The bill is using your figure.'
  }
  return figure ? `The check measured ${figure}. Enter the figure the bill should use.` : 'The check has no figure yet. Enter the figure the bill should use.'
}

function errText(err: unknown): string {
  const raw = String((err as Error).message || err)
  const body = raw.replace(/^\d+\s+/, '')
  let detail = raw
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string') detail = parsed.detail
  } catch { /* the server sent plain text */ }
  if (detail.startsWith('unknown name') || detail.startsWith('cannot read') || detail.startsWith('unexpected')) {
    return 'Use a number or a sum, for example 12.4 or 3 × 4.2.'
  }
  if (detail === 'division by zero') return 'That divides by zero.'
  if (detail === 'the expression is empty') return 'Enter a quantity.'
  return detail
}

export function Bill({ route }: { route: Route }) {
  const { data, error } = useData<BillData>('/api/bill')
  const take = useData<{ items: { id: string; value: { sources: Source[] }; viewer?: Source | null }[] }>('/api/takeoff')
  const [q, setQ] = useState(route.query.get('q') || '')
  const [target, setTarget] = useState<Target | null>(null)
  const [who, setWho] = useState(() => { try { return localStorage.getItem('azboq.author') || '' } catch { return '' } })
  const [why, setWhy] = useState('')
  const [expr, setExpr] = useState('')
  const [qtyWhy, setQtyWhy] = useState('')
  const [editErr, setEditErr] = useState('')
  const [saving, setSaving] = useState(false)
  const bname = useBuildingName()
  const status = route.query.get('status') || 'all'
  const building = route.query.get('building') || ''
  const selId = route.query.get('line')
  const explained = useData<Explain>(selId ? `/api/line/${selId}/explain` : null)
  const table = useRef<HTMLDivElement>(null)
  const nav = (patch: Record<string, string | null>) => {
    const cur: Record<string, string | null> = { status: status === 'all' ? null : status, building: building || null, line: selId }
    go('bill', { ...cur, ...patch })
  }

  const counts = useMemo(() => {
    const m: Record<string, number> = {}
    for (const l of data?.lines || []) {
      const s = l.check?.status || 'none'
      m[s] = (m[s] || 0) + 1
    }
    m.checked = (m.matched || 0) + (m.printed || 0) + (m.derived || 0)
    return m
  }, [data])
  const buildings = useMemo(() => [...new Set((data?.lines || []).map((l) => l.building))], [data])

  const { bySection, visible } = useMemo(() => {
    const bySection = new Map<string, Line[]>()
    const visible: Line[] = []
    if (!data) return { bySection, visible }
    const titleHit = new Set(q ? data.sections.filter((s) => matches(q, s.code, s.title)).map((s) => s.code) : [])
    for (const l of data.lines) {
      const s = l.check?.status || ''
      if (status === 'checked' ? !CHECKED.has(s) : status !== 'all' && s !== status) continue
      if (building && l.building !== building) continue
      if (!(titleHit.has(l.section) || matches(q, l.id, l.description, l.comment))) continue
      bySection.set(l.section, [...(bySection.get(l.section) || []), l])
    }
    for (const s of data.sections) visible.push(...(bySection.get(s.code) || []))
    return { bySection, visible }
  }, [data, q, status, building])

  // Bring the chosen line into view, also when it was opened from another screen.
  useEffect(() => {
    if (!selId) return
    const el = table.current?.querySelector<HTMLElement>(`tr[data-line="${CSS.escape(selId)}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [selId, data])

  // ↑/↓ walk the visible lines, Esc closes the line.
  const visibleRef = useRef(visible)
  visibleRef.current = visible
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const list = visibleRef.current
      if (!list.length) return
      const at = list.findIndex((l) => l.id === selId)
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setTarget(null)
        nav({ line: list[Math.min(at + 1, list.length - 1)].id })
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault()
        setTarget(null)
        nav({ line: list[Math.max(at - 1, 0)].id })
      } else if (e.key === 'Escape' && selId) nav({ line: null })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selId, status, building])

  const selected = data?.lines.find((l) => l.id === selId) || null
  const overrideId = selected?.check?.override?.id
  const overrideExpr = selected?.check?.override?.expression
  useEffect(() => {
    const figure = selected?.check?.our_qty
    setExpr(overrideExpr ?? (figure != null ? cleanNum(figure) : ''))
    setQtyWhy('')
    setEditErr('')
    setSaving(false)
  }, [selected?.id, overrideId, overrideExpr, selected?.check?.our_qty])

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the bill" />

  const sel = data.lines.find((l) => l.id === selId) || null
  const item = sel?.check?.item ? take.data?.items.find((i) => i.id === sel.check!.item) : undefined
  const itemSources = item ? [...(item.viewer ? [item.viewer] : []), ...item.value.sources.filter((s) => s !== item.viewer)].slice(0, 6) : []
  const selSources = sel?.check?.sources || (itemSources.length ? itemSources : sel?.check?.candidates) || []
  const shown = target || (selSources[0] ? targetOf(selSources[0]) : null)
  const chips: [string, string][] = [
    ['all', 'All'],
    ['different', 'Different'],
    ['checked', 'Backed by a drawing'],
    ['review', 'Needs review'],
    ['blocked', 'Blocked'],
    ['not_found', 'Not on drawings'],
  ]
  const head = data.totals.contract_price_c5
  const selIdx = sel ? visible.findIndex((l) => l.id === sel.id) : -1
  const different = sel?.check?.status === 'different'
  const editing = !!(sel?.check && (EDITABLE.has(sel.check.status) || sel.check.override))
  const step = (d: number) => {
    const next = selIdx >= 0 ? visible[selIdx + d] : undefined
    if (!next) return
    setTarget(null)
    nav({ line: next.id })
  }

  return (
    <div className={`fill-row ${sel ? 'with-insp' : ''}`}>
      <Card style={{ overflow: 'hidden' }}>
        <div className="toolbar">
          <div className="chips">
            {chips.map(([k, label]) => (
              <button key={k} className={`chip ${status === k ? 'on' : ''}`} onClick={() => nav({ status: k === 'all' ? null : k })} title={LINE_STATUS[k]?.hint}>
                {label} <b>{fmt(k === 'all' ? data.lines.length : counts[k] || 0)}</b>
              </button>
            ))}
          </div>
          <select className="search" style={{ minWidth: 150 }} value={building} onChange={(e) => nav({ building: e.target.value || null })} aria-label="Building">
            <option value="">All buildings</option>
            {buildings.map((b) => <option key={b} value={b}>{bname(b)}</option>)}
          </select>
          <label className="field grow">
            <Search size={14} />
            <input placeholder="Search code or words (ə = e, ı = i…)" value={q} onChange={(e) => setQ(e.target.value)} />
            {q ? <button onClick={() => setQ('')} aria-label="Clear search" style={{ display: 'grid', color: 'var(--faint)' }}><X size={14} /></button> : null}
          </label>
          <span className="muted" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
            <span className="mono" style={{ color: 'var(--ink)' }}>{fmt(visible.length)}</span> lines shown · header <span className="mono">{money(head)}</span>
          </span>
        </div>
        <div className="scroll" style={{ flex: 1 }} ref={table}>
          <table>
            <thead>
              <tr>
                <th>Code</th><th>Description</th><th>Unit</th><th className="r">Bill qty</th><th className="r">From drawings</th><th className="r">Amount</th><th>Check</th>
              </tr>
            </thead>
            <tbody>
              {data.sections.map((s) => {
                const ls = bySection.get(s.code)
                if (!ls) return null
                return [
                  <tr key={s.code + s.row} className="sec">
                    <td className="code">
                      {s.code}
                      {s.code_repaired ? <span className="note warn" title={`Stored in the workbook as ${s.stored_code}; repaired from its position`}> *</span> : null}
                    </td>
                    <td colSpan={6}>
                      <T az={s.title} /> <span className="muted" style={{ fontWeight: 400 }}>· {bname(s.building)} · {tradeName(s.trade)} · {ls.length} {ls.length === 1 ? 'line' : 'lines'}</span>
                    </td>
                  </tr>,
                  ...ls.map((l) => (
                    <tr key={l.id} data-line={l.id} tabIndex={0} className={`click ${sel?.id === l.id ? 'sel' : ''}`} onClick={() => { setTarget(null); nav({ line: l.id }) }} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); setTarget(null); nav({ line: l.id }) } }}>
                      <td className="code">{l.id}</td>
                      <td className="desc"><T az={l.description} />{l.comment ? <span className="pill" style={{ marginLeft: 6 }} title={l.comment}>reviewer note</span> : null}</td>
                      <td>{l.unit_known ? l.unit_raw : <span className="note warn" title="Unit not recognised">{l.unit_raw}</span>}</td>
                      <td className="r num">{fmt(l.qty, 3)}</td>
                      <td className={`r num ${l.check?.status === 'different' ? 'bad-fig' : ''}`}>
                        {l.check?.our_qty === null || l.check?.our_qty === undefined ? <span className="faint">—</span> : fmt(l.check.our_qty, 3)}
                        {l.check?.override ? <span className="pill" style={{ marginLeft: 6 }} title={`${l.check.override.author}: ${l.check.override.reason}`}>edited</span> : null}
                      </td>
                      <td className="r num">{money(l.amount)}</td>
                      <td>{l.check ? <StatusTag status={l.check.status} /> : null}</td>
                    </tr>
                  )),
                ]
              })}
            </tbody>
          </table>
          {!bySection.size ? <Empty icon={<Search size={20} />} title="No line matches these filters">Clear the search or choose another status or building.</Empty> : null}
        </div>
      </Card>

      {sel ? (
        <Card
          title={<span>Line <span className="mono">{sel.id}</span></span>}
          sub={selIdx >= 0 ? `${selIdx + 1} of ${fmt(visible.length)} shown · ↑ ↓ to move` : 'Not in the current filter'}
          right={
            <>
              <button className="icon" style={{ width: 30, height: 30 }} title="Previous line (↑)" disabled={selIdx <= 0} onClick={() => step(-1)}><ArrowUp size={14} /></button>
              <button className="icon" style={{ width: 30, height: 30 }} title="Next line (↓)" disabled={selIdx < 0 || selIdx >= visible.length - 1} onClick={() => step(1)}><ArrowDown size={14} /></button>
              <button className="icon" style={{ width: 30, height: 30 }} title="Close (Esc)" onClick={() => nav({ line: null })}><X size={14} /></button>
            </>
          }
          className="inspector"
          style={{ overflow: 'hidden' }}
        >
          <div className="insp" style={editing ? { flex: '1 1 auto', minHeight: 0 } : { flex: '0 1 auto', maxHeight: '58%' }}>
            <div className="eyebrow accent">{bname(sel.building)} · {tradeName(sel.trade)} · workbook row {sel.row}</div>
            <h1><T az={sel.description} /></h1>
            <div className="vs">
              <div>
                <small>Bill says</small>
                <b>{fmt(sel.qty, 3)} <span>{sel.unit}</span></b>
                <span className="mono">× {money(sel.rate)} = {money(sel.amount)}</span>
              </div>
              <div className={different ? 'bad' : sel.check && LINE_STATUS[sel.check.status]?.cls === 'ok' ? 'ok' : ''}>
                <small>Drawings say</small>
                <b>{sel.check?.our_qty === null || sel.check?.our_qty === undefined ? '—' : fmt(sel.check.our_qty, 3)} <span>{sel.check?.our_qty != null ? sel.unit : ''}</span></b>
                {sel.check ? <StatusTag status={sel.check.status} /> : <span>Not checked</span>}
                {(sel.check?.review_reasons || []).map((reason) => (
                  <div key={reason.code + (reason.link || reason.rule || '')} className="faint" style={{ marginTop: 4 }}>
                    {reasonText(reason)}
                  </div>
                ))}
                {(sel.check?.review_reasons || []).some((reason) => !reason.accepted_by) ? (
                  <form className="box" onSubmit={async (e) => {
                    e.preventDefault()
                    const open = (sel.check?.review_reasons || []).find((reason) => !reason.accepted_by)
                    if (!open || !who.trim() || !why.trim()) return
                    try { localStorage.setItem('azboq.author', who.trim()) } catch { /* keep going */ }
                    await postJSON('/api/review', { target_kind: 'reason', target_id: `reason:${sel.id}:${open.code}`, action: 'accept', reason: why.trim(), author: who.trim(), payload: {} })
                    clearCache()
                    window.location.reload()
                  }}>
                    <small>Accept a review reason</small>
                    <input placeholder="Your name" value={who} onChange={(e) => setWho(e.target.value)} />
                    <input placeholder="Why you accept it" value={why} onChange={(e) => setWhy(e.target.value)} />
                    <button className="btn" type="submit">Accept</button>
                  </form>
                ) : null}
              </div>
            </div>
            {sel.check && (EDITABLE.has(sel.check.status) || sel.check.override) ? (
              <QuantityForm
                line={sel}
                expr={expr}
                setExpr={setExpr}
                who={who}
                setWho={setWho}
                qtyWhy={qtyWhy}
                setQtyWhy={setQtyWhy}
                editErr={editErr}
                setEditErr={setEditErr}
                saving={saving}
                setSaving={setSaving}
              />
            ) : null}
            {sel.check ? (
              <>
                <div className={`box ${LINE_STATUS[sel.check.status]?.cls === 'bad' ? 'bad' : LINE_STATUS[sel.check.status]?.cls === 'ok' ? 'ok' : ''}`}>
                  <small>Reason</small>
                  {sel.check.reason}
                  {sel.check.override && sel.check.engine_reason ? <div className="faint" style={{ marginTop: 4 }}>{sel.check.engine_reason}</div> : null}
                  {sel.check.gap ? <div style={{ marginTop: 4 }}>Gap <b className="mono">{fmt(sel.check.gap, 3)} {sel.unit}</b> ({fmt(sel.check.gap_pct, 1)}%), worth about <b className="mono">{money(sel.check.gap * (sel.rate || 0))}</b> before mark-ups.</div> : null}
                </div>
                {sel.check.item ? <div className="pair"><span>Measured item</span><a href={href('takeoff', { item: sel.check.item })} className="mono">{sel.check.item}</a></div> : null}
                {explained.data?.item?.formula ? (
                  <div className="box">
                    <small>How it is calculated</small>
                    <div>{explained.data.item.label_en}</div>
                    <div className="mono">{explained.data.item.formula}</div>
                    {explained.data.item.substituted ? <div className="mono">{explained.data.item.substituted}</div> : null}
                  </div>
                ) : null}
                {explained.data?.inputs?.length ? (
                  <div className="section-label"><span className="eyebrow">Dimensions and counts used</span></div>
                ) : null}
                {explained.data?.inputs?.map((input) => {
                  const src = input.sources[0]
                  const where = src
                    ? [src.file?.split('/').pop(), src.page != null ? `page ${src.page + 1}` : null, src.row, src.col].filter(Boolean).join(' · ')
                    : ''
                  return (
                    <div key={input.label + String(input.value)} className="pair">
                      <span>{input.label}</span>
                      <b className="mono">{input.value == null ? '—' : fmt(input.value, 3)} {input.unit}{where ? ` · ${where}` : ''}</b>
                    </div>
                  )
                })}
                {sel.check.derived_from ? <div className="pair"><span>Follows from</span><a href={href('bill', { line: sel.check.derived_from })}>line <span className="mono">{sel.check.derived_from}</span></a></div> : null}
              </>
            ) : null}
            {sel.comment ? (
              <div className="box warn">
                <small>Client reviewer's comment in the workbook</small>
                <span lang="az">{sel.comment}</span>
                {sel.check?.reviewer?.kind === 'reduce' && sel.check.reviewer.delta != null && sel.check.reviewer.value != null ? <div>Read as: reduce by {fmt(-sel.check.reviewer.delta, 3)} → {fmt(sel.check.reviewer.value, 3)} {sel.unit}</div> : null}
              </div>
            ) : null}
            {selSources.length ? (
              <>
                <div className="section-label"><span className="eyebrow">{sel.check?.sources ? 'Where it is printed' : itemSources.length ? 'Evidence for the measured item' : 'Weak candidates, not accepted'}</span></div>
                {selSources.map((s, i) => <SourceCard key={i} src={s} onOpen={setTarget} active={JSON.stringify(targetOf(s)) === JSON.stringify(shown)} />)}
              </>
            ) : null}
            {editing ? (
              <div style={{ height: 240, marginTop: 12, borderTop: '1px solid var(--line)', display: 'flex' }}>
                <Viewer target={shown} emptyText={sel.check?.status === 'not_found' ? 'No drawing of this building prints or measures this line, so there is no sheet to show.' : 'This line has no source to show on a sheet.'} />
              </div>
            ) : null}
          </div>
          {editing ? null : (
            <div style={{ flex: 1, display: 'flex', minHeight: 260, borderTop: '1px solid var(--line)' }}>
              <Viewer target={shown} emptyText={sel.check?.status === 'not_found' ? 'No drawing of this building prints or measures this line, so there is no sheet to show.' : 'This line has no source to show on a sheet.'} />
            </div>
          )}
        </Card>
      ) : null}
    </div>
  )
}
