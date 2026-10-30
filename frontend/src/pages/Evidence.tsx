import { useEffect, useMemo, useState } from 'react'
import { Compass, Info, Pencil, Search, Translate, Warning, WarningCircle, X } from '../icons'
import { postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { setTranslation, T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, Empty, ErrorBox, Loading, METHOD, pct, shortFile, SourceCard, tradeName, useBuildingName, ValueTag, type Target } from '../ui'
import { Viewer } from '../Viewer'
import type { Takeoff } from './Takeoff'

function SearchField({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="field" style={{ marginLeft: 'auto' }}>
      <Search size={14} />
      <input placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
      {value ? <button onClick={() => onChange('')} aria-label="Clear search" style={{ display: 'grid', color: 'var(--faint)' }}><X size={14} /></button> : null}
    </label>
  )
}

export function Inputs() {
  const { data, error } = useData<Takeoff>('/api/takeoff')
  const [q, setQ] = useState('')
  const [method, setMethod] = useState('all')
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the ledger" />
  const methods = [...new Set(data.ledger.map((r) => r.method))]
  const rows = data.ledger.filter((r) => (method === 'all' || r.method === method) && matches(q, r.path, r.note, r.item))
  return (
    <Card style={{ overflow: 'hidden' }}>
      <div className="toolbar">
        <div className="chips">
          <button className={`chip ${method === 'all' ? 'on' : ''}`} onClick={() => setMethod('all')}>All <b>{data.ledger.length}</b></button>
          {methods.map((m) => (
            <button key={m} className={`chip ${method === m ? 'on' : ''}`} onClick={() => setMethod(m)}>
              {METHOD[m] || m} <b>{data.ledger.filter((r) => r.method === m).length}</b>
            </button>
          ))}
        </div>
        <SearchField value={q} onChange={setQ} placeholder="Search value, item or note" />
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Value</th><th className="r">Number</th><th>Status</th><th>How</th><th>First source</th><th>Note</th></tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={r.method === 'rule' ? '' : 'click'} onClick={() => r.method !== 'rule' && go('takeoff', { item: r.item })} style={r.method === 'rule' ? { background: 'var(--warn-soft)' } : undefined}>
                <td><b>{r.path}</b><div className="muted code" style={{ fontSize: 11.5 }}>{r.item}</div></td>
                <td className="r num" style={{ whiteSpace: 'nowrap' }}>{r.value === null ? <span className="faint">—</span> : fmt(r.value, 4)} {r.unit}</td>
                <td><ValueTag status={r.status} />{r.conflicts ? <div className="note warn" style={{ marginTop: 4 }}>{r.conflicts} conflict</div> : null}</td>
                <td>{METHOD[r.method] || r.method}{r.missing?.length ? <div className="note bad">missing {r.missing.join(', ')}</div> : null}</td>
                <td className="muted" style={{ fontSize: 12.5 }} lang="az">
                  {r.sources?.[0] ? `${shortFile(r.sources[0].file_name)} · ${r.sources[0].locator?.region || (r.sources[0].locator?.page !== undefined ? `page ${r.sources[0].locator.page + 1}` : r.sources[0].locator?.rule_id || '')}` : '—'}
                  {r.sources?.length > 1 ? ` +${r.sources.length - 1}` : ''}
                </td>
                <td className="muted" style={{ fontSize: 12.5, maxWidth: 360 }}>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <Empty icon={<Search size={20} />} title="Nothing matches">Clear the search or pick another method.</Empty> : null}
      </div>
      <div className="card-body muted" style={{ borderTop: '1px solid var(--line)', fontSize: 12.5, display: 'flex', gap: 10 }}>
        <Info size={15} style={{ flex: 'none', marginTop: 2 }} />
        <span>
          Every number the check uses, with where it came from. A value with no source has no number: it is shown as blocked, and the bill lines that need it say so. Shaded rows are project rules: values a person read from a scan or the client's documents, each with its citation. They are never shown as measured.
        </span>
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
    <div className="fill-row" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 0.95fr)' }}>
      <div className="stack" style={{ overflow: 'auto', minHeight: 0, paddingRight: 2 }}>
        {data.conflicts.map((c) => (
          <Card key={c.id} title={<span>{c.topic}</span>} right={<span className={`tag ${c.decided ? 'ok' : 'warn'}`}>{c.decided ? 'Decided' : 'Not decided'}</span>}>
            <div className="card-body">
              <div className="sides" style={{ gridTemplateColumns: `repeat(${c.sides.length}, minmax(0, 1fr))` }}>
                {c.sides.map((s: any, i: number) => (
                  <div key={i} className={`side ${s.value === c.suggestion ? 'pick' : ''}`}>
                    <span className={`tag ${s.value === c.suggestion ? 'ok' : 'bare'}`}>{s.value === c.suggestion ? 'Suggested' : 'Other side'}</span>
                    <span className="val">{s.value}</span>
                    <div className="muted" style={{ fontSize: 12 }}>{s.citation}</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>
                      Found on {s.found_in_drawings?.length || 0} drawing text{(s.found_in_drawings?.length || 0) === 1 ? '' : 's'} searching “<span lang="az">{s.search}</span>”
                    </div>
                    {(s.found_in_drawings || []).slice(0, 3).map((f: any, j: number) => (
                      <button key={j} className={`src ${target?.kind === 'dwg' && target.handle === f.handle && target.sha === f.file_id.slice(0, 12) ? 'on' : ''}`} onClick={() => setTarget({ kind: 'dwg', sha: f.file_id.slice(0, 12), region: f.region, handle: f.handle, label: f.text })}>
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
          <Card key={i.id} title={<span>{i.label_en}</span>} right={<a href={href('takeoff', { item: i.id })}>Open item →</a>}>
            <div className="card-body" style={{ paddingTop: 4 }}>
              <div className="pair"><span>From the drawings</span><span className="mono">{fmt(i.value.value, 4)} {i.unit} <ValueTag status={i.value.status} /></span></div>
              {i.value.conflicts.map((c: any, k: number) => (
                <div key={k} className="pair"><span>{c.citation}</span><span className="mono">{fmt(c.value, 4)} {i.unit}</span></div>
              ))}
              <div className="box warn">Both are kept and shown. The bill check uses the drawing value and the item stays in review until a person decides.</div>
            </div>
          </Card>
        ))}
        {!data.conflicts.length && !itemConflicts.length ? <Empty title="No conflicts">No two documents disagree.</Empty> : null}
      </div>
      <Card title="On the sheet" sub="Pick a drawing text on the left">
        <Viewer target={target} />
      </Card>
    </div>
  )
}

type Cell = { building: string; trade: string; status: string; lines: number; value: number; source_count: number; sources: any[] }
type SourceMap = { buildings: string[]; trades: string[]; cells: Cell[]; value_total: number; value_with_drawing: number }

const COV: Record<string, [string, string, string]> = {
  drawing: ['ok', 'Drawing', 'A DWG or PDF drawing covers it'],
  'pdf only': ['info', 'PDF only', 'Only a PDF print covers it'],
  'scan only': ['warn', 'Scan only', 'Only a scan covers it; review only'],
  nothing: ['bad', 'Nothing', 'No drawing in the package'],
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
        <div className="kpi">
          <div className="k"><Compass size={14} /> Value with a drawing</div>
          <div className="v num">{pct(data.value_with_drawing, data.value_total)}</div>
          <div className="s"><span className="mono">{money(data.value_with_drawing)}</span> of {money(data.value_total)}</div>
        </div>
        {Object.entries(COV).map(([k, [cls, label, hint]]) => (
          <div key={k} className="kpi" title={hint}>
            <div className="k"><span className={`dot ${cls}`} /> {label}</div>
            <div className="v num">{data.cells.filter((c) => c.status === k).length}</div>
            <div className="s mono">{money(data.cells.filter((c) => c.status === k).reduce((s, c) => s + c.value, 0))}</div>
          </div>
        ))}
      </div>
      <div className={`fill-row ${sel ? 'with-insp' : ''}`}>
        <Card title="Bill value by building and trade" sub="Each cell is the value of those bill lines, coloured by what the package holds for it" className="cov">
          <div className="scroll">
            <table>
              <thead>
                <tr><th style={{ position: 'sticky', left: 0, zIndex: 2 }}>Building</th>{trades.map((t) => <th key={t}>{tradeName(t)}</th>)}</tr>
              </thead>
              <tbody>
                {buildings.map((b) => (
                  <tr key={b}>
                    <td style={{ position: 'sticky', left: 0, background: 'var(--paper)', zIndex: 1 }}><b>{bname(b)}</b></td>
                    {trades.map((t) => {
                      const c = cell(b, t)
                      if (!c) return <td key={t} className="faint" style={{ textAlign: 'center' }}>·</td>
                      const [cls] = COV[c.status] || ['muted']
                      return (
                        <td key={t} className="cellv">
                          <button className={`heat ${cls} ${sel === c ? 'on' : ''}`} onClick={() => setSel(sel === c ? null : c)} title={`${c.lines} lines · ${c.source_count} sheets · ${COV[c.status]?.[1]}`}>
                            {c.value >= 1000 ? `${(c.value / 1000).toFixed(0)}k` : fmt(c.value, 0)}
                          </button>
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
          <Card title={<span>{bname(sel.building)} · {tradeName(sel.trade)}</span>} right={<button className="icon" style={{ width: 30, height: 30 }} onClick={() => setSel(null)} aria-label="Close"><X size={14} /></button>}>
            <div className="insp">
              <div className="pair"><span>Status</span><span className={`tag ${COV[sel.status]?.[0]}`}>{COV[sel.status]?.[1]}</span></div>
              <div className="pair"><span>Bill lines</span><a href={href('bill', { building: sel.building })}>{sel.lines} in the bill →</a></div>
              <div className="pair"><span>Value</span><span className="mono">{money(sel.value)}</span></div>
              <div className="section-label"><span className="eyebrow">Sheets that cover it · {sel.source_count}</span></div>
              {sel.sources.map((s, i) => (
                <a key={i} className="src" href={s.file_id ? href(`drawing/${s.file_id.slice(0, 12)}`, { sheet: s.kind === 'dwg' ? s.region : s.page }) : undefined}>
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
  const [sev, setSev] = useState('all')
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the run log" />
  const stages = [...new Set(data.events.map((e) => e.stage))]
  const events = data.events.filter((e) => stage === 'all' || e.stage === stage)
  const sevs = data.review.reduce<Record<string, number>>((m, r) => ((m[r.severity] = (m[r.severity] || 0) + 1), m), {})
  const review = data.review.filter((r) => sev === 'all' || r.severity === sev)
  return (
    <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
      <Card title={`Review items · ${data.review.length}`} sub="Every warning is listed, none is swallowed">
        <div className="toolbar">
          <div className="chips">
            {['all', ...Object.keys(sevs)].map((s) => (
              <button key={s} className={`chip ${sev === s ? 'on' : ''}`} onClick={() => setSev(s)}>
                {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)} <b>{s === 'all' ? data.review.length : sevs[s]}</b>
              </button>
            ))}
          </div>
        </div>
        <div className="rows" style={{ maxHeight: 'calc(100vh - 300px)' }}>
          {review.map((r, i) => (
            <div key={i} className="row">
              <span className={`well sm ${r.severity === 'error' ? 'bad' : 'warn'}`}>{r.severity === 'error' ? <WarningCircle size={15} /> : <Warning size={15} />}</span>
              <span lang="az" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>{r.message}<span className="d" style={{ display: 'block' }}>{r.stage}</span></span>
              <span className={`tag ${r.severity === 'error' ? 'bad' : 'warn'}`}>{r.severity}</span>
            </div>
          ))}
        </div>
      </Card>
      <div className="stack">
        <Card title="Stage events" sub={`${data.events.length} events across ${stages.length} stages`}>
          <div className="toolbar">
            <div className="chips">
              {['all', ...stages].map((s) => (
                <button key={s} className={`chip ${stage === s ? 'on' : ''}`} onClick={() => setStage(s)}>{s}</button>
              ))}
            </div>
          </div>
          <div className="rows" style={{ maxHeight: 320 }}>
            {events.map((e, i) => (
              <div key={i} className="row plain">
                <span className={`dot ${e.kind === 'warning' ? 'warn' : e.kind === 'error' ? 'bad' : 'info'}`} />
                <span lang="az" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>{e.message}<span className="d" style={{ display: 'block' }}>{e.stage} · {new Date(e.t * 1000).toLocaleString()}</span></span>
                <span className="tag bare muted">{e.kind}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="DWG conversion and second reader" sub="ODA converts; LibreDWG re-reads to catch silent losses">
          <div className="scroll" style={{ maxHeight: 360 }}>
            <table>
              <thead><tr><th>File</th><th>ODA</th><th className="r">ODA / LibreDWG</th><th>Result</th></tr></thead>
              <tbody>
                {(conv.data?.files || []).map((f) => (
                  <tr key={f.sha256} className="click" onClick={() => go(`drawing/${f.sha256.slice(0, 12)}`)}>
                    <td lang="az">{f.name}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{f.oda?.status}</td>
                    <td className="r num">{fmt(f.crosscheck?.oda_total)} / {f.crosscheck?.libredwg_status === 'ok' ? fmt(f.crosscheck?.libredwg_total) : f.crosscheck?.libredwg_status}</td>
                    <td><span className={`tag ${f.status === 'read' ? 'ok' : 'warn'}`}>{f.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {conv.error ? <div className="card-body"><ErrorBox error={conv.error} /></div> : null}
          </div>
        </Card>
      </div>
    </div>
  )
}

type Entry = { text: string | null; origin: string }

const ORIGIN: Record<string, [string, string]> = { all: ['All', ''], human: ['Corrected', 'ok'], glossary: ['Glossary', 'info'], llm: ['Machine', 'info'], pending: ['Pending', 'muted'] }

export function Translations() {
  const bill = useData<{ sections: { title: string }[]; lines: { description: string }[] }>('/api/bill')
  const [entries, setEntries] = useState<Record<string, Entry>>({})
  const [q, setQ] = useState('')
  const [origin, setOrigin] = useState('all')
  const [editing, setEditing] = useState<{ src: string; text: string } | null>(null)
  const [saveErr, setSaveErr] = useState<string | null>(null)
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
    })().catch(() => {})
    return () => {
      alive = false
    }
  }, [texts])
  if (bill.error) return <ErrorBox error={bill.error} />
  if (!bill.data) return <Loading what="strings" />
  const counts = Object.values(entries).reduce<Record<string, number>>((m, e) => ((m[e.origin] = (m[e.origin] || 0) + 1), m), {})
  const rows = texts.filter((t) => (origin === 'all' || entries[t]?.origin === origin) && matches(q, t, entries[t]?.text))
  const loaded = Object.keys(entries).length
  const save = async () => {
    if (!editing) return
    try {
      await postJSON('/api/translations/correct', { source: editing.src, text: editing.text })
      setEntries((e) => ({ ...e, [editing.src]: { text: editing.text, origin: 'human' } }))
      setTranslation(editing.src, { text: editing.text, origin: 'human' })
      setEditing(null)
      setSaveErr(null)
    } catch (e: any) {
      setSaveErr(String(e?.message || e))
    }
  }
  return (
    <Card style={{ overflow: 'hidden', flex: 1, minHeight: 480 }}>
      <div className="toolbar">
        <div className="chips">
          {Object.entries(ORIGIN).map(([o, [label]]) => (
            <button key={o} className={`chip ${origin === o ? 'on' : ''}`} onClick={() => setOrigin(o)}>
              {label} <b>{fmt(o === 'all' ? texts.length : counts[o] || 0)}</b>
            </button>
          ))}
        </div>
        <SearchField value={q} onChange={setQ} placeholder="Search Azerbaijani or English" />
      </div>
      {loaded < texts.length ? (
        <div style={{ padding: '10px 14px 0' }}>
          <div className="spectrum" style={{ height: 6 }}><i style={{ flex: loaded, background: 'var(--accent)' }} /><i style={{ flex: texts.length - loaded, background: 'transparent' }} /></div>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>Looking up {fmt(loaded)} of {fmt(texts.length)} strings…</div>
        </div>
      ) : null}
      {counts.pending ? (
        <div className="banner" style={{ margin: '10px 12px 0' }}>
          <Translate size={16} style={{ flex: 'none', marginTop: 1 }} />
          <span>
            <b>{fmt(counts.pending)} strings have no English yet.</b> No OpenAI key is configured on this machine, so only the glossary translates. Set <span className="mono">OPENAI_API_KEY</span> and run <span className="mono">python -m azboq translate</span> to fill them; numbers and codes are guarded, and the Azerbaijani text is always what the check uses.
          </span>
        </div>
      ) : null}
      {saveErr ? <div style={{ margin: '10px 12px 0' }}><ErrorBox error={`Could not save: ${saveErr}`} /></div> : null}
      <div className="scroll" style={{ flex: 1 }}>
        <table>
          <thead><tr><th style={{ width: '44%' }}>Azerbaijani (source of truth)</th><th>English</th><th>Origin</th><th /></tr></thead>
          <tbody>
            {rows.slice(0, 500).map((t) => (
              <tr key={t}>
                <td lang="az" className="desc">{t}</td>
                <td className="desc">
                  {editing?.src === t ? (
                    <textarea
                      autoFocus
                      value={editing.text}
                      onChange={(e) => setEditing({ src: t, text: e.target.value })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save()
                        if (e.key === 'Escape') setEditing(null)
                      }}
                      style={{ width: '100%', minHeight: 64, font: 'inherit', padding: 8, borderRadius: 8, border: '1px solid var(--accent-line)', background: 'var(--paper)', outline: 0 }}
                    />
                  ) : (
                    entries[t]?.text || <span className="faint">pending</span>
                  )}
                </td>
                <td><span className={`tag ${ORIGIN[entries[t]?.origin]?.[1] || 'muted'}`}>{ORIGIN[entries[t]?.origin]?.[0] || entries[t]?.origin || '…'}</span></td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {editing?.src === t ? (
                    <>
                      <button className="btn sm" onClick={save} title="Save (Ctrl+Enter)">Save</button>{' '}
                      <button className="btn sm ghost" onClick={() => setEditing(null)}>Cancel</button>
                    </>
                  ) : (
                    <button className="btn sm ghost" onClick={() => setEditing({ src: t, text: entries[t]?.text || '' })}><Pencil size={12} /> Correct</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 500 ? <div className="empty-state">Showing 500 of {fmt(rows.length)}; search to narrow.</div> : null}
        {!rows.length ? <Empty icon={<Search size={20} />} title="Nothing matches" /> : null}
      </div>
    </Card>
  )
}

export function NotFound({ route }: { route: Route }) {
  return (
    <Empty icon={<Compass size={20} />} title={`No screen called “${route.parts.join('/')}”`}>
      <a href={href('home')}>Back to the overview</a>
    </Empty>
  )
}

export function Sources({ list, onOpen }: { list: any[]; onOpen: (t: Target) => void }) {
  return <>{list.map((s, i) => <SourceCard key={i} src={s} onOpen={onOpen} />)}</>
}
