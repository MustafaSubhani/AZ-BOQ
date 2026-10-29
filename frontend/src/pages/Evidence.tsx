import { useEffect, useMemo, useState } from 'react'
import { postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { setTranslation, T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, ErrorBox, Loading, METHOD, shortFile, SourceCard, tradeName, useBuildingName, ValueTag, type Target } from '../ui'
import { Viewer } from '../Viewer'
import type { Takeoff } from './Takeoff'

export function Inputs() {
  const { data, error } = useData<Takeoff>('/api/takeoff')
  const [q, setQ] = useState('')
  const [method, setMethod] = useState('all')
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the ledger" />
  const methods = [...new Set(data.ledger.map((r) => r.method))]
  const rows = data.ledger.filter((r) => (method === 'all' || r.method === method) && matches(q, r.path, r.note, r.item))
  return (
    <Card style={{ overflow: 'hidden', flex: 1 }}>
      <div className="toolbar">
        <button className={`chip ${method === 'all' ? 'on' : ''}`} onClick={() => setMethod('all')}>All <b>{data.ledger.length}</b></button>
        {methods.map((m) => (
          <button key={m} className={`chip ${method === m ? 'on' : ''}`} onClick={() => setMethod(m)}>
            {METHOD[m] || m} <b>{data.ledger.filter((r) => r.method === m).length}</b>
          </button>
        ))}
        <input className="search" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginLeft: 'auto' }} />
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Value</th><th className="r">Number</th><th>Status</th><th>How</th><th>First source</th><th>Note</th></tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={r.method === 'rule' ? '' : 'click'} onClick={() => r.method !== 'rule' && go('takeoff', { item: r.item })} style={r.method === 'rule' ? { background: 'var(--warn-soft)' } : undefined}>
                <td><b>{r.path}</b><div className="muted code" style={{ fontSize: 12 }}>{r.item}</div></td>
                <td className="r num">{r.value === null ? '—' : fmt(r.value, 4)} {r.unit}</td>
                <td><ValueTag status={r.status} />{r.conflicts ? <div className="tag warn">{r.conflicts} conflict</div> : null}</td>
                <td>{METHOD[r.method] || r.method}{r.missing?.length ? <div className="tag bad">missing {r.missing.join(', ')}</div> : null}</td>
                <td className="muted" style={{ fontSize: 12.5 }} lang="az">
                  {r.sources?.[0] ? `${shortFile(r.sources[0].file_name)} · ${r.sources[0].locator?.region || (r.sources[0].locator?.page !== undefined ? `page ${r.sources[0].locator.page + 1}` : r.sources[0].locator?.rule_id || '')}` : '—'}
                  {r.sources?.length > 1 ? ` +${r.sources.length - 1}` : ''}
                </td>
                <td className="muted" style={{ fontSize: 12.5, maxWidth: 360 }}>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card-body muted" style={{ paddingTop: 10, fontSize: 12.5 }}>
        Every number the check uses, with where it came from. A value with no source has no number: it is shown as blocked, and the bill lines that need it say so. Shaded rows are project rules: values a person read from a scan or the client's documents, each with its citation. They are never shown as measured.
      </div>
    </Card>
  )
}

export function Conflicts() {
  const { data, error } = useData<Takeoff>('/api/takeoff')
  const [target, setTarget] = useState<Target | null>(null)
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="conflicts" />
  const itemConflicts = data.items.filter((i) => i.value.conflicts?.length)
  return (
    <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 0.9fr)', flex: 1, minHeight: 0 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, overflow: 'auto', minHeight: 0 }}>
        {data.conflicts.map((c) => (
          <Card key={c.id} title={<span>{c.topic}</span>} right={<span className="tag warn">{c.decided ? 'Decided' : 'Not decided'}</span>}>
            <div className="card-body">
              <div className="grid2" style={{ gridTemplateColumns: `repeat(${c.sides.length}, minmax(0, 1fr))`, gap: 10 }}>
                {c.sides.map((s: any, i: number) => (
                  <div key={i} className={`box ${s.value === c.suggestion ? 'ok' : ''}`} style={{ marginTop: 0 }}>
                    <small>{s.value === c.suggestion ? 'Suggested' : 'Other side'}</small>
                    <b style={{ fontSize: 16 }}>{s.value}</b>
                    <div className="muted" style={{ fontSize: 12 }}>{s.citation}</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>
                      Found on {s.found_in_drawings?.length || 0} drawing text{(s.found_in_drawings?.length || 0) === 1 ? '' : 's'} searching “{s.search}”
                    </div>
                    {(s.found_in_drawings || []).slice(0, 3).map((f: any, j: number) => (
                      <button
                        key={j}
                        className="src"
                        onClick={() => setTarget({ kind: 'dwg', sha: f.file_id.slice(0, 12), region: f.region, handle: f.handle, label: f.text })}
                      >
                        <small>{shortFile(f.file)} · {f.region}</small>
                        <span lang="az">{f.text}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
              <div className="box info"><small>Why the suggestion</small>{c.reason}</div>
            </div>
          </Card>
        ))}
        {itemConflicts.map((i) => (
          <Card key={i.id} title={<span>{i.label_en}</span>} right={<a href={href('takeoff', { item: i.id })}>Open item</a>}>
            <div className="card-body">
              <div className="pair"><span>From the drawings</span><span className="num">{fmt(i.value.value, 4)} {i.unit} <ValueTag status={i.value.status} /></span></div>
              {i.value.conflicts.map((c: any, k: number) => (
                <div key={k} className="pair"><span>{c.citation}</span><span className="num">{fmt(c.value, 4)} {i.unit}</span></div>
              ))}
              <div className="box warn">Both are kept and shown. The bill check uses the drawing value and the item stays in review until a person decides.</div>
            </div>
          </Card>
        ))}
      </div>
      <Card title="On the sheet">
        <Viewer target={target} />
      </Card>
    </div>
  )
}

type Cell = { building: string; trade: string; status: string; lines: number; value: number; source_count: number; sources: any[] }
type SourceMap = { buildings: string[]; trades: string[]; cells: Cell[]; value_total: number; value_with_drawing: number }

const COV: Record<string, [string, string]> = {
  drawing: ['ok', 'Drawing'],
  'pdf only': ['info', 'PDF only'],
  'scan only': ['warn', 'Scan only'],
  nothing: ['bad', 'Nothing'],
}

export function Coverage() {
  const { data, error } = useData<SourceMap>('/api/coverage')
  const [sel, setSel] = useState<Cell | null>(null)
  const bname = useBuildingName()
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="coverage" />
  const trades = data.trades.filter((t) => data.cells.some((c) => c.trade === t))
  const buildings = data.buildings.filter((b) => data.cells.some((c) => c.building === b))
  const cell = (b: string, t: string) => data.cells.find((c) => c.building === b && c.trade === t)
  return (
    <>
      <div className="strip">
        <div className="kpi"><div className="k">Bill value with a drawing of its building and trade</div><div className="v num">{money(data.value_with_drawing)}</div><div className="s">{((data.value_with_drawing / data.value_total) * 100).toFixed(1)}% of {money(data.value_total)}</div></div>
        {Object.entries(COV).map(([k, [cls, label]]) => (
          <div key={k} className="kpi">
            <div className="k"><span className={`dot ${cls}`} /> {label}</div>
            <div className="v num">{data.cells.filter((c) => c.status === k).length}</div>
            <div className="s">{money(data.cells.filter((c) => c.status === k).reduce((s, c) => s + c.value, 0))}</div>
          </div>
        ))}
      </div>
      <div className="grid2" style={{ gridTemplateColumns: sel ? 'minmax(0, 1fr) 360px' : 'minmax(0, 1fr)' }}>
        <Card title="Bill value by building and trade, and what the package holds for it" className="cov">
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Building</th>{trades.map((t) => <th key={t}>{tradeName(t)}</th>)}</tr>
              </thead>
              <tbody>
                {buildings.map((b) => (
                  <tr key={b}>
                    <td><b>{bname(b)}</b></td>
                    {trades.map((t) => {
                      const c = cell(b, t)
                      if (!c) return <td key={t} className="faint">·</td>
                      const [cls] = COV[c.status] || ['muted']
                      return (
                        <td key={t} className="click" onClick={() => setSel(c)} style={{ cursor: 'pointer', background: sel === c ? 'var(--accent-soft)' : undefined }} title={`${c.lines} lines · ${c.source_count} sources`}>
                          <span className="cell"><span className={`dot ${cls}`} /> <span className="num">{(c.value / 1000).toFixed(0)}k</span></span>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        {sel ? (
          <Card title={<span>{bname(sel.building)} · {tradeName(sel.trade)}</span>} right={<button className="chip" onClick={() => setSel(null)}>Close</button>}>
            <div className="insp">
              <div className="pair"><span>Status</span><span className={`tag ${COV[sel.status]?.[0]}`}>{COV[sel.status]?.[1]}</span></div>
              <div className="pair"><span>Bill lines</span><a href={href('bill', { building: sel.building })}>{sel.lines}</a></div>
              <div className="pair"><span>Value</span><span className="num">{money(sel.value)}</span></div>
              <div className="eyebrow" style={{ marginTop: 12 }}>Sheets that cover it · {sel.source_count}</div>
              {sel.sources.map((s, i) => (
                <a key={i} className="src" href={s.file_id ? href(`drawing/${s.file_id.slice(0, 12)}`, { sheet: s.kind === 'dwg' ? s.region : s.page }) : undefined} style={{ color: 'inherit', textDecoration: 'none' }}>
                  <small>{shortFile(s.file)} · {s.sheet || s.region || (s.page !== undefined ? `page ${s.page + 1}` : '')}</small>
                  {s.title ? <T az={s.title} /> : <span className="faint">untitled sheet</span>}
                </a>
              ))}
              {!sel.sources.length ? <div className="box bad">The package has no drawing for this building and trade. These lines can only be checked against another source.</div> : null}
            </div>
          </Card>
        ) : null}
      </div>
    </>
  )
}

export function RunLog() {
  const { data, error } = useData<{ events: any[]; review: any[] }>('/api/runlog')
  const conv = useData<{ files: any[] }>('/api/conversion')
  const [stage, setStage] = useState('all')
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the run log" />
  const stages = [...new Set(data.events.map((e) => e.stage))]
  const events = data.events.filter((e) => stage === 'all' || e.stage === stage)
  return (
    <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
      <Card title={`Review items · ${data.review.length}`} right={<span className="muted">every warning is listed, none is swallowed</span>}>
        <div className="rows" style={{ maxHeight: 'calc(100vh - 180px)' }}>
          {data.review.map((r, i) => (
            <div key={i} className="row">
              <span className={`dot ${r.severity === 'error' ? 'bad' : 'warn'}`} />
              <span lang="az">{r.message}<span className="d" style={{ display: 'block' }}>{r.stage}</span></span>
              <span className={`tag ${r.severity === 'error' ? 'bad' : 'warn'}`}>{r.severity}</span>
            </div>
          ))}
        </div>
      </Card>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Card title="Stage events">
          <div className="toolbar">
            {['all', ...stages].map((s) => (
              <button key={s} className={`chip ${stage === s ? 'on' : ''}`} onClick={() => setStage(s)}>{s}</button>
            ))}
          </div>
          <div className="rows" style={{ maxHeight: 300 }}>
            {events.map((e, i) => (
              <div key={i} className="row">
                <span className={`dot ${e.kind === 'warning' ? 'warn' : e.kind === 'error' ? 'bad' : 'info'}`} />
                <span lang="az">{e.message}<span className="d" style={{ display: 'block' }}>{e.stage} · {new Date(e.t * 1000).toLocaleString()}</span></span>
                <span className="tag muted">{e.kind}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="DWG conversion and second reader">
          <div className="scroll" style={{ maxHeight: 340 }}>
            <table>
              <thead><tr><th>File</th><th>ODA</th><th className="r">ODA / LibreDWG</th><th>Result</th></tr></thead>
              <tbody>
                {(conv.data?.files || []).map((f) => (
                  <tr key={f.sha256} className="click" onClick={() => go(`drawing/${f.sha256.slice(0, 12)}`)}>
                    <td lang="az">{f.name}</td>
                    <td>{f.oda?.status}</td>
                    <td className="r num">{fmt(f.crosscheck?.oda_total)} / {f.crosscheck?.libredwg_status === 'ok' ? fmt(f.crosscheck?.libredwg_total) : f.crosscheck?.libredwg_status}</td>
                    <td><span className={`tag ${f.status === 'read' ? 'ok' : 'warn'}`}>{f.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  )
}

type Entry = { text: string | null; origin: string }

export function Translations() {
  const bill = useData<{ sections: { title: string }[]; lines: { description: string }[] }>('/api/bill')
  const [entries, setEntries] = useState<Record<string, Entry>>({})
  const [q, setQ] = useState('')
  const [origin, setOrigin] = useState('all')
  const [editing, setEditing] = useState<{ src: string; text: string } | null>(null)
  const texts = useMemo(() => {
    if (!bill.data) return []
    return [...new Set([...bill.data.sections.map((s) => s.title), ...bill.data.lines.map((l) => l.description)].filter(Boolean))]
  }, [bill.data])
  useEffect(() => {
    let alive = true
    ;(async () => {
      for (let i = 0; i < texts.length; i += 800) {
        const res = await postJSON<Record<string, Entry>>('/api/translations', texts.slice(i, i + 800))
        if (!alive) return
        setEntries((e) => ({ ...e, ...res }))
      }
    })()
    return () => {
      alive = false
    }
  }, [texts])
  if (bill.error) return <ErrorBox error={bill.error} />
  if (!bill.data) return <Loading what="strings" />
  const counts = Object.values(entries).reduce<Record<string, number>>((m, e) => ((m[e.origin] = (m[e.origin] || 0) + 1), m), {})
  const rows = texts.filter((t) => (origin === 'all' || entries[t]?.origin === origin) && matches(q, t, entries[t]?.text))
  const save = async () => {
    if (!editing) return
    await postJSON('/api/translations/correct', { source: editing.src, text: editing.text })
    setEntries((e) => ({ ...e, [editing.src]: { text: editing.text, origin: 'human' } }))
    setTranslation(editing.src, { text: editing.text, origin: 'human' })
    setEditing(null)
  }
  return (
    <Card style={{ overflow: 'hidden', flex: 1 }}>
      <div className="toolbar">
        {['all', 'human', 'glossary', 'llm', 'pending'].map((o) => (
          <button key={o} className={`chip ${origin === o ? 'on' : ''}`} onClick={() => setOrigin(o)}>
            {o === 'all' ? 'All' : o === 'llm' ? 'Machine' : o === 'human' ? 'Corrected' : o.charAt(0).toUpperCase() + o.slice(1)} <b>{fmt(o === 'all' ? texts.length : counts[o] || 0)}</b>
          </button>
        ))}
        <input className="search" placeholder="Search Azerbaijani or English" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginLeft: 'auto' }} />
      </div>
      {counts.pending ? (
        <div className="box warn" style={{ margin: '10px 12px 0' }}>
          {fmt(counts.pending)} strings have no English yet: no OpenAI key is configured on this machine, so only the glossary translates. Set OPENAI_API_KEY and run python -m azboq translate to fill them; numbers and codes are guarded, and the Azerbaijani text is always what the check uses.
        </div>
      ) : null}
      <div className="scroll">
        <table>
          <thead><tr><th style={{ width: '46%' }}>Azerbaijani (source of truth)</th><th>English</th><th>Origin</th><th /></tr></thead>
          <tbody>
            {rows.slice(0, 500).map((t) => (
              <tr key={t}>
                <td lang="az" className="desc">{t}</td>
                <td className="desc">
                  {editing?.src === t ? (
                    <textarea value={editing.text} onChange={(e) => setEditing({ src: t, text: e.target.value })} style={{ width: '100%', minHeight: 60, font: 'inherit' }} />
                  ) : (
                    entries[t]?.text || <span className="faint">pending</span>
                  )}
                </td>
                <td><span className={`tag ${entries[t]?.origin === 'human' ? 'ok' : entries[t]?.origin === 'pending' ? 'muted' : 'info'}`}>{entries[t]?.origin || '…'}</span></td>
                <td>
                  {editing?.src === t ? (
                    <>
                      <button className="chip on" onClick={save}>Save</button> <button className="chip" onClick={() => setEditing(null)}>Cancel</button>
                    </>
                  ) : (
                    <button className="chip" onClick={() => setEditing({ src: t, text: entries[t]?.text || '' })}>Correct</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 500 ? <div className="empty-state">Showing 500 of {fmt(rows.length)}; search to narrow.</div> : null}
      </div>
    </Card>
  )
}

export function NotFound({ route }: { route: Route }) {
  return <div className="empty-state">No screen called “{route.parts.join('/')}”. <a href={href('home')}>Home</a></div>
}

export function Sources({ list, onOpen }: { list: any[]; onOpen: (t: Target) => void }) {
  return <>{list.map((s, i) => <SourceCard key={i} src={s} onOpen={onOpen} />)}</>
}
