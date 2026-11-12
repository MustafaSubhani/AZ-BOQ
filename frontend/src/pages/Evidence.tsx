import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { setTranslation, T } from '../i18n'
import { Compass, Info, Pencil, Search, Translate, Warning, WarningCircle, X } from '../icons'
import { go, href, type Route } from '../router'
import {
  Card,
  Empty,
  ErrorBox,
  Loading,
  METHOD,
  pct,
  SegmentedTabs,
  shortFile,
  SourceCard,
  tradeName,
  useBuildingName,
  ValueTag,
  type Target,
} from '../ui'
import { Viewer } from '../Viewer'
import type { Takeoff } from './Takeoff'

function SearchField({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="field ml-auto">
      <Search size={14} />
      <input placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
      {value ? (
        <button type="button" onClick={() => onChange('')} aria-label="Clear search" className="clear">
          <X size={13} />
        </button>
      ) : null}
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
        <SegmentedTabs<string>
          id="inputs-method"
          value={method}
          onChange={setMethod}
          options={[
            { value: 'all', label: 'All', count: data.ledger.length },
            ...methods.map((m) => ({
              value: m,
              label: METHOD[m] || m,
              count: data.ledger.filter((r) => r.method === m).length,
            })),
          ]}
        />
        <SearchField value={q} onChange={setQ} placeholder="Search dimension, item, or note…" />
      </div>

      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Parameter</th>
              <th className="r">Value</th>
              <th>Status</th>
              <th>Extraction Method</th>
              <th>Primary Source</th>
              <th>Audit Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={i}
                className={r.method === 'rule' ? '' : 'click'}
                onClick={() => r.method !== 'rule' && go('takeoff', { item: r.item })}
                style={r.method === 'rule' ? { background: 'var(--warn-soft)' } : undefined}
              >
                <td>
                  <b>{r.path}</b>
                  <div className="muted code text-[11.5px]">{r.item}</div>
                </td>
                <td className="r num whitespace-nowrap">
                  {r.value === null ? <span className="faint">—</span> : fmt(r.value, 4)} {r.unit}
                </td>
                <td>
                  <ValueTag status={r.status} />
                  {r.conflicts ? <div className="note warn mt-1">{r.conflicts} conflict</div> : null}
                </td>
                <td>
                  {METHOD[r.method] || r.method}
                  {r.missing?.length ? <div className="note bad">missing {r.missing.join(', ')}</div> : null}
                </td>
                <td className="muted text-[12px]" lang="az">
                  {r.sources?.[0]
                    ? `${shortFile(r.sources[0].file_name)} · ${
                        r.sources[0].locator?.region ||
                        (r.sources[0].locator?.page !== undefined ? `page ${r.sources[0].locator.page + 1}` : r.sources[0].locator?.rule_id || '')
                      }`
                    : '—'}
                  {r.sources?.length > 1 ? ` +${r.sources.length - 1}` : ''}
                </td>
                <td className="muted text-[12px] max-w-[360px]">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <Empty icon={<Search size={18} />} title="No ledger entries match">Clear search or switch method filter.</Empty> : null}
      </div>

      <div className="card-body muted flex gap-2.5 border-t border-[var(--line)] text-[12px]">
        <Info size={15} className="mt-0.5 shrink-0" />
        <span>
          Every parameter feeding the check is audited here. Missing inputs remain explicitly blocked; amber-tinted rows denote cited project rules (such as norm densities or scanned-page values) and are never misrepresented as CAD geometry.
        </span>
      </div>
    </Card>
  )
}

export function Conflicts() {
  const { data, error } = useData<Takeoff>('/api/takeoff')
  const report = useData<{ drawing_conflicts?: { id: string; text: string }[] }>('/api/report')
  const [target, setTarget] = useState<Target | null>(null)
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="conflicts" />

  const itemConflicts = data.items.filter((i) => i.value.conflicts?.length)
  const drawn = report.data?.drawing_conflicts || []
  const lineFor = (id: string) => (id === 'room-1-floor_1' ? '2.7.12' : id === 'downpipes' ? '2.5.14' : null)

  return (
    <div className="fill-row" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 0.95fr)' }}>
      <div className="stack overflow-auto min-h-0 pr-1">
        {drawn.map((c) => {
          const line = lineFor(c.id)
          return (
            <Card
              key={c.id}
              title={c.id.startsWith('cemi') ? 'Room Schedule Total Mismatch' : c.id === 'downpipes' ? 'Downpipes Count Disagreement' : 'Drawing Disagreement'}
              right={<span className="tag warn">Unresolved</span>}
            >
              <div className="card-body pt-2!">
                <div className="box warn mt-0!">{c.text}</div>
                <div className="mt-2.5">
                  {line ? (
                    <a className="btn outline sm" href={href('bill', { line })}>
                      Inspect BOQ line {line} →
                    </a>
                  ) : c.id.startsWith('cemi') ? (
                    <a className="btn outline sm" href={href('areas')}>
                      Open Area Book →
                    </a>
                  ) : null}
                </div>
              </div>
            </Card>
          )
        })}

        {data.conflicts.map((c) => (
          <Card
            key={c.id}
            title={c.topic}
            right={<span className={`tag ${c.decided ? 'ok' : 'warn'}`}>{c.decided ? 'Decided' : 'Open Conflict'}</span>}
          >
            <div className="card-body pt-3!">
              <div className="sides" style={{ gridTemplateColumns: `repeat(${c.sides.length}, minmax(0, 1fr))` }}>
                {c.sides.map((s: any, i: number) => (
                  <div key={i} className={`side ${s.value === c.suggestion ? 'pick' : ''}`}>
                    <span className={`tag ${s.value === c.suggestion ? 'ok' : 'bare'}`}>
                      {s.value === c.suggestion ? 'Recommended' : 'Alternative Source'}
                    </span>
                    <span className="val">{s.value}</span>
                    <div className="muted text-[12px]">{s.citation}</div>
                    <div className="mt-1.5 text-[11.5px] text-[var(--ink-2)]">
                      Matched on {s.found_in_drawings?.length || 0} sheet text{(s.found_in_drawings?.length || 0) === 1 ? '' : 's'} (“<span lang="az">{s.search}</span>”)
                    </div>
                    {(s.found_in_drawings || []).slice(0, 3).map((f: any, j: number) => (
                      <button
                        key={j}
                        type="button"
                        className={`src ${target?.kind === 'dwg' && target.handle === f.handle && target.sha === f.file_id.slice(0, 12) ? 'on' : ''}`}
                        onClick={() => setTarget({ kind: 'dwg', sha: f.file_id.slice(0, 12), region: f.region, handle: f.handle, label: f.text })}
                      >
                        <small>{shortFile(f.file)} · {f.region}</small>
                        <span lang="az">{f.text}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
              <div className="box info">
                <small>Engineering Recommendation</small>
                {c.reason}
              </div>
            </div>
          </Card>
        ))}

        {itemConflicts.map((i) => (
          <Card key={i.id} title={i.label_en} right={<a href={href('takeoff', { item: i.id })}>Open Takeoff →</a>}>
            <div className="card-body pt-1!">
              <div className="pair">
                <span>Primary Drawing Value</span>
                <span className="mono">{fmt(i.value.value, 4)} {i.unit} <ValueTag status={i.value.status} /></span>
              </div>
              {i.value.conflicts.map((c: any, k: number) => (
                <div key={k} className="pair">
                  <span>{c.citation}</span>
                  <span className="mono">{fmt(c.value, 4)} {i.unit}</span>
                </div>
              ))}
              <div className="box warn">
                Both values are preserved side-by-side without silent averaging until a reviewer signs off.
              </div>
            </div>
          </Card>
        ))}

        {!data.conflicts.length && !itemConflicts.length && !drawn.length ? (
          <Empty title="Zero Document Conflicts">All cross-checked documents agree.</Empty>
        ) : null}
      </div>

      <Card title="Sheet Evidence Preview" sub="Select any cited drawing text on the left to zoom onto the sheet">
        <Viewer target={target} />
      </Card>
    </div>
  )
}

type Cell = { building: string; trade: string; status: string; lines: number; value: number; source_count: number; sources: any[] }
type SourceMap = { buildings: string[]; trades: string[]; cells: Cell[]; value_total: number; value_with_drawing: number }

const COV: Record<string, [string, string, string]> = {
  drawing: ['ok', 'CAD / Vector PDF', 'Covered by measurable DWG or vector PDF sheets'],
  'pdf only': ['info', 'PDF Plot Only', 'Covered by plotted PDF sheets'],
  'scan only': ['warn', 'Raster Scan Only', 'Covered only by scanned PDFs; human review required'],
  nothing: ['bad', 'Missing Drawings', 'No drawings for this building & trade in the package'],
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
          <div className="k"><Compass size={14} /> Value Covered by Drawings</div>
          <div className="v num">{pct(data.value_with_drawing, data.value_total)}</div>
          <div className="s"><span className="mono">{money(data.value_with_drawing)}</span> of {money(data.value_total)}</div>
        </div>
        {Object.entries(COV).map(([k, [cls, label, hint]]) => (
          <div key={k} className="kpi" title={hint}>
            <div className="k"><span className={`dot ${cls}`} /> {label}</div>
            <div className="v num">{data.cells.filter((c) => c.status === k).length} <span className="text-[13px] font-normal text-[var(--muted)]">cells</span></div>
            <div className="s mono">{money(data.cells.filter((c) => c.status === k).reduce((s, c) => s + c.value, 0))}</div>
          </div>
        ))}
      </div>

      <div className={`fill-row ${sel ? 'with-insp' : ''}`}>
        <Card title="Contract Value Coverage Matrix (Building × Trade)" sub="Click any cell to inspect the covering sheets or open those BOQ lines" className="cov">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ position: 'sticky', left: 0, zIndex: 3 }}>Building</th>
                  {trades.map((t) => <th key={t}>{tradeName(t)}</th>)}
                </tr>
              </thead>
              <tbody>
                {buildings.map((b) => (
                  <tr key={b}>
                    <td style={{ position: 'sticky', left: 0, background: 'var(--paper)', zIndex: 1 }}>
                      <b>{bname(b)}</b>
                    </td>
                    {trades.map((t) => {
                      const c = cell(b, t)
                      if (!c) return <td key={t} className="faint text-center">·</td>
                      const [cls] = COV[c.status] || ['muted']
                      return (
                        <td key={t} className="cellv">
                          <button
                            type="button"
                            className={`heat ${cls} ${sel === c ? 'on' : ''}`}
                            onClick={() => setSel(sel === c ? null : c)}
                            title={`${c.lines} lines · ${c.source_count} sheets · ${COV[c.status]?.[1]}`}
                          >
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
          <Card
            title={`${bname(sel.building)} · ${tradeName(sel.trade)}`}
            right={
              <button type="button" className="icon sm" onClick={() => setSel(null)} aria-label="Close">
                <X size={13} />
              </button>
            }
          >
            <div className="insp">
              <div className="pair"><span>Coverage Status</span><span className={`tag ${COV[sel.status]?.[0]}`}>{COV[sel.status]?.[1]}</span></div>
              <div className="pair"><span>Contract Lines</span><a href={href('bill', { building: sel.building })}>{sel.lines} BOQ lines →</a></div>
              <div className="pair"><span>Contract Value</span><span className="mono">{money(sel.value)}</span></div>
              <div className="section-label"><span className="eyebrow">Covering Sheets · {sel.source_count}</span></div>
              {sel.sources.map((s, i) => (
                <a
                  key={i}
                  className="src"
                  href={s.file_id ? href(`drawing/${s.file_id.slice(0, 12)}`, { sheet: s.kind === 'dwg' ? s.region : s.page }) : undefined}
                >
                  <small>{shortFile(s.file)} · {s.sheet || s.region || (s.page !== undefined ? `page ${s.page + 1}` : '')}</small>
                  {s.title ? <T az={s.title} /> : <span className="faint">Untitled sheet</span>}
                </a>
              ))}
              {!sel.sources.length ? (
                <div className="box bad">
                  No drawings for this building & trade were supplied in the client package. Request the missing sheets from the design institute to verify these lines.
                </div>
              ) : null}
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
      <Card title={`Pipeline Warnings · ${data.review.length}`} sub="Every anomaly surfaced during extraction and matching">
        <div className="toolbar">
          <SegmentedTabs<string>
            id="runlog-sev"
            size="sm"
            value={sev}
            onChange={setSev}
            options={[
              { value: 'all', label: 'All', count: data.review.length },
              ...Object.keys(sevs).map((s) => ({
                value: s,
                label: s.charAt(0).toUpperCase() + s.slice(1),
                count: sevs[s],
                tone: (s === 'error' ? 'bad' : 'warn') as 'bad' | 'warn',
              })),
            ]}
          />
        </div>
        <div className="rows" style={{ maxHeight: 'calc(100vh - 280px)' }}>
          {review.map((r, i) => (
            <div key={i} className="row">
              <span className={`well sm ${r.severity === 'error' ? 'bad' : 'warn'}`}>
                {r.severity === 'error' ? <WarningCircle size={15} /> : <Warning size={15} />}
              </span>
              <span lang="az" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
                {r.message}
                <span className="d block">{r.stage}</span>
              </span>
              <span className={`tag ${r.severity === 'error' ? 'bad' : 'warn'}`}>{r.severity}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="stack">
        <Card title="Execution Stage Log" sub={`${data.events.length} events across ${stages.length} pipeline stages`}>
          <div className="toolbar">
            <SegmentedTabs<string>
              id="runlog-stage"
              size="sm"
              value={stage}
              onChange={setStage}
              options={[{ value: 'all', label: 'All' }, ...stages.map((s) => ({ value: s, label: s }))]}
            />
          </div>
          <div className="rows" style={{ maxHeight: 310 }}>
            {events.map((e, i) => (
              <div key={i} className="row plain">
                <span className={`dot ${e.kind === 'warning' ? 'warn' : e.kind === 'error' ? 'bad' : 'info'}`} />
                <span lang="az" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
                  {e.message}
                  <span className="d block">{e.stage} · {new Date(e.t * 1000).toLocaleString()}</span>
                </span>
                <span className="tag bare muted">{e.kind}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Dual-Reader DWG Verification" sub="ODA File Converter cross-checked against LibreDWG">
          <div className="scroll" style={{ maxHeight: 350 }}>
            <table>
              <thead>
                <tr><th>DWG File</th><th>ODA</th><th className="r">ODA / LibreDWG Entities</th><th>Status</th></tr>
              </thead>
              <tbody>
                {(conv.data?.files || []).map((f) => (
                  <tr key={f.sha256} className="click" onClick={() => go(`drawing/${f.sha256.slice(0, 12)}`)}>
                    <td lang="az">{f.name}</td>
                    <td className="mono text-[12px]">{f.oda?.status}</td>
                    <td className="r num">
                      {fmt(f.crosscheck?.oda_total)} / {f.crosscheck?.libredwg_status === 'ok' ? fmt(f.crosscheck?.libredwg_total) : f.crosscheck?.libredwg_status}
                    </td>
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
const ORIGIN: Record<string, [string, string]> = {
  all: ['All', ''],
  human: ['Human Verified', 'ok'],
  glossary: ['Glossary', 'info'],
  llm: ['Machine', 'info'],
  pending: ['Pending', 'muted'],
}

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
      toast.success('Saved English translation gloss')
    } catch (e: any) {
      setSaveErr(String(e?.message || e))
    }
  }

  return (
    <Card style={{ overflow: 'hidden', flex: 1, minHeight: 480 }}>
      <div className="toolbar">
        <SegmentedTabs<string>
          id="trans-origin"
          value={origin}
          onChange={setOrigin}
          options={Object.entries(ORIGIN).map(([o, [label]]) => ({
            value: o,
            label,
            count: fmt(o === 'all' ? texts.length : counts[o] || 0),
          }))}
        />
        <SearchField value={q} onChange={setQ} placeholder="Search Azerbaijani or English…" />
      </div>

      {loaded < texts.length ? (
        <div className="px-4 pt-2.5">
          <div className="spectrum h-1.5!">
            <i style={{ flex: loaded, background: 'var(--accent)' }} />
            <i style={{ flex: texts.length - loaded, background: 'transparent' }} />
          </div>
          <div className="muted mt-1.5 text-[12px]">Loading {fmt(loaded)} of {fmt(texts.length)} strings…</div>
        </div>
      ) : null}

      {counts.pending ? (
        <div className="banner mx-3 mt-2.5">
          <Translate size={15} className="mt-0.5 shrink-0 text-[var(--accent)]" />
          <span>
            <b>{fmt(counts.pending)} strings use Azerbaijani original text.</b> Configure <span className="mono">OPENAI_API_KEY</span> and run <span className="mono">python -m azboq translate</span> to pre-translate remaining items; quantities and norm checks always evaluate against the Azerbaijani original.
          </span>
        </div>
      ) : null}

      {saveErr ? <div className="mx-3 mt-2.5"><ErrorBox error={`Could not save: ${saveErr}`} /></div> : null}

      <div className="scroll flex-1">
        <table>
          <thead>
            <tr>
              <th style={{ width: '44%' }}>Azerbaijani (Authoritative Source)</th>
              <th>English Reading Gloss</th>
              <th>Source</th>
              <th />
            </tr>
          </thead>
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
                      className="w-full min-h-[60px] rounded-lg border border-[var(--accent)] bg-[var(--paper)] p-2 text-[13px] outline-none"
                    />
                  ) : (
                    entries[t]?.text || <span className="faint">pending</span>
                  )}
                </td>
                <td>
                  <span className={`tag ${ORIGIN[entries[t]?.origin]?.[1] || 'muted'}`}>
                    {ORIGIN[entries[t]?.origin]?.[0] || entries[t]?.origin || '…'}
                  </span>
                </td>
                <td className="whitespace-nowrap">
                  {editing?.src === t ? (
                    <div className="flex gap-1.5">
                      <button type="button" className="btn sm" onClick={save} title="Save (Ctrl+Enter)">Save</button>
                      <button type="button" className="btn sm outline" onClick={() => setEditing(null)}>Cancel</button>
                    </div>
                  ) : (
                    <button type="button" className="btn sm outline" onClick={() => setEditing({ src: t, text: entries[t]?.text || '' })}>
                      <Pencil size={12} /> Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 500 ? <div className="empty-state">Showing 500 of {fmt(rows.length)}; search above to narrow.</div> : null}
        {!rows.length ? <Empty icon={<Search size={18} />} title="No translations match" /> : null}
      </div>
    </Card>
  )
}

export function NotFound({ route }: { route: Route }) {
  return (
    <Empty icon={<Compass size={18} />} title={`Screen “${route.parts.join('/')}” not found`}>
      <a href={href('home')}>Return to Command Summary</a>
    </Empty>
  )
}

export function Sources({ list, onOpen }: { list: any[]; onOpen: (t: Target) => void }) {
  return <>{list.map((s, i) => <SourceCard key={i} src={s} onOpen={onOpen} />)}</>
}
