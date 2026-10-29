import { useMemo, useState } from 'react'
import { useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, ErrorBox, LINE_STATUS, Loading, SourceCard, StatusTag, targetOf, tradeName, useBuildingName, type Source, type Target } from '../ui'
import { Viewer } from '../Viewer'

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
  check: { status: string; reason: string; our_qty: number | null; gap?: number | null; gap_pct?: number | null; item?: string; sources?: Source[]; candidates?: Source[]; derived_from?: string; reviewer?: any; method?: string; group_total?: number } | null
}
type Section = { code: string; stored_code: any; row: number; title: string; trade: string; building: string; code_repaired: boolean }
type BillData = { sections: Section[]; lines: Line[]; totals: Record<string, number>; chain: Record<string, any>; line_sum: number; unknown_units: any[]; external_links: any }

const CHECKED = new Set(['matched', 'printed', 'derived'])

export function Bill({ route }: { route: Route }) {
  const { data, error } = useData<BillData>('/api/bill')
  const take = useData<{ items: { id: string; value: { sources: Source[] }; viewer?: Source | null }[] }>('/api/takeoff')
  const [q, setQ] = useState(route.query.get('q') || '')
  const [target, setTarget] = useState<Target | null>(null)
  const bname = useBuildingName()
  const status = route.query.get('status') || 'all'
  const building = route.query.get('building') || ''
  const selId = route.query.get('line')
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

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the bill" />

  const titleHit = new Set(q ? data.sections.filter((s) => matches(q, s.code, s.title)).map((s) => s.code) : [])
  const keep = (l: Line) => {
    const s = l.check?.status || ''
    if (status === 'checked' ? !CHECKED.has(s) : status !== 'all' && s !== status) return false
    if (building && l.building !== building) return false
    return titleHit.has(l.section) || matches(q, l.id, l.description, l.comment)
  }
  const bySection = new Map<string, Line[]>()
  for (const l of data.lines) if (keep(l)) bySection.set(l.section, [...(bySection.get(l.section) || []), l])
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

  return (
    <div style={{ display: 'grid', gridTemplateColumns: sel ? 'minmax(0, 1fr) 400px' : 'minmax(0,1fr)', gap: 14, flex: 1, minHeight: 0 }}>
      <Card style={{ overflow: 'hidden' }}>
        <div className="toolbar">
          {chips.map(([k, label]) => (
            <button key={k} className={`chip ${status === k ? 'on' : ''}`} onClick={() => nav({ status: k === 'all' ? null : k })} title={LINE_STATUS[k]?.hint}>
              {label} <b>{fmt(k === 'all' ? data.lines.length : counts[k] || 0)}</b>
            </button>
          ))}
          <select className="search" style={{ minWidth: 150 }} value={building} onChange={(e) => nav({ building: e.target.value || null })}>
            <option value="">All buildings</option>
            {buildings.map((b) => <option key={b} value={b}>{bname(b)}</option>)}
          </select>
          <input className="search" placeholder="Search code or words (ə = e, ı = i…)" value={q} onChange={(e) => setQ(e.target.value)} />
          <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>
            Header {money(head)} · lines {money(data.line_sum)}
          </span>
        </div>
        <div className="scroll" style={{ flex: 1 }}>
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
                      {s.code_repaired ? <span className="tag warn" title={`Stored in the workbook as ${s.stored_code}; repaired from its position`}> *</span> : null}
                    </td>
                    <td colSpan={6}>
                      <T az={s.title} /> <span className="muted" style={{ fontWeight: 500 }}>· {bname(s.building)} · {tradeName(s.trade)}</span>
                    </td>
                  </tr>,
                  ...ls.map((l) => (
                    <tr key={l.id} className={`click ${sel?.id === l.id ? 'sel' : ''}`} onClick={() => { setTarget(null); nav({ line: l.id }) }}>
                      <td className="code">{l.id}</td>
                      <td className="desc"><T az={l.description} />{l.comment ? <span className="pill" style={{ marginLeft: 6 }} title={l.comment}>reviewer note</span> : null}</td>
                      <td title={l.unit_known ? undefined : 'Unit not recognised'} className={l.unit_known ? '' : 'tag warn'}>{l.unit_raw}</td>
                      <td className="r num">{fmt(l.qty, 3)}</td>
                      <td className="r num" style={{ color: l.check?.status === 'different' ? 'var(--bad)' : undefined, fontWeight: l.check?.status === 'different' ? 650 : undefined }}>
                        {l.check?.our_qty === null || l.check?.our_qty === undefined ? '—' : fmt(l.check.our_qty, 3)}
                      </td>
                      <td className="r num">{money(l.amount)}</td>
                      <td>{l.check ? <StatusTag status={l.check.status} /> : null}</td>
                    </tr>
                  )),
                ]
              })}
            </tbody>
          </table>
          {!bySection.size ? <div className="empty-state">No line matches these filters.</div> : null}
        </div>
      </Card>

      {sel ? (
        <Card title={<span>Line {sel.id}</span>} right={<button className="chip" onClick={() => nav({ line: null })}>Close</button>} style={{ overflow: 'hidden' }}>
          <div className="insp" style={{ flex: '0 0 auto', maxHeight: '55%' }}>
            <div className="eyebrow">{bname(sel.building)} · {tradeName(sel.trade)} · row {sel.row}</div>
            <h1 style={{ fontSize: 15 }}><T az={sel.description} /></h1>
            <div className="pair"><span>Bill</span><span className="num">{fmt(sel.qty, 3)} {sel.unit} × {money(sel.rate)} = <b>{money(sel.amount)}</b></span></div>
            <div className="pair"><span>From drawings</span><span className="num">{sel.check?.our_qty === null || sel.check?.our_qty === undefined ? '—' : `${fmt(sel.check.our_qty, 3)} ${sel.unit}`}</span></div>
            {sel.check ? (
              <>
                <div className="pair"><span>Check</span><StatusTag status={sel.check.status} /></div>
                <div className={`box ${LINE_STATUS[sel.check.status]?.cls === 'bad' ? 'bad' : LINE_STATUS[sel.check.status]?.cls === 'ok' ? 'ok' : ''}`}>
                  <small>Reason</small>
                  {sel.check.reason}
                  {sel.check.gap ? <div>Gap {fmt(sel.check.gap, 3)} {sel.unit} ({fmt(sel.check.gap_pct, 1)}%), worth about {money(sel.check.gap * (sel.rate || 0))} before mark-ups.</div> : null}
                </div>
                {sel.check.item ? <div className="pair"><span>Measured item</span><a href={href('takeoff', { item: sel.check.item })}>{sel.check.item}</a></div> : null}
                {sel.check.derived_from ? <div className="pair"><span>Follows from</span><a href={href('bill', { line: sel.check.derived_from })}>line {sel.check.derived_from}</a></div> : null}
              </>
            ) : null}
            {sel.comment ? (
              <div className="box warn">
                <small>Client reviewer's comment in the workbook</small>
                <span lang="az">{sel.comment}</span>
                {sel.check?.reviewer?.kind === 'reduce' ? <div>Read as: reduce by {fmt(-sel.check.reviewer.delta, 3)} → {fmt(sel.check.reviewer.value, 3)} {sel.unit}</div> : null}
              </div>
            ) : null}
            {selSources.length ? (
              <>
                <div className="eyebrow" style={{ marginTop: 12 }}>{sel.check?.sources ? 'Where it is printed' : itemSources.length ? 'Evidence for the measured item' : 'Weak candidates, not accepted'}</div>
                {selSources.map((s, i) => <SourceCard key={i} src={s} onOpen={setTarget} active={JSON.stringify(targetOf(s)) === JSON.stringify(shown)} />)}
              </>
            ) : null}
          </div>
          <div style={{ flex: 1, display: 'flex', minHeight: 260, borderTop: '1px solid var(--line)' }}>
            <Viewer target={shown} />
          </div>
        </Card>
      ) : null}
    </div>
  )
}
