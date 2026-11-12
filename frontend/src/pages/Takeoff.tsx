import { useState } from 'react'
import { useData } from '../api'
import { fmt, matches } from '../az'
import { Prohibit, Search, ShieldCheck, ShieldWarning, X } from '../icons'
import { reasonText } from '../reasons'
import { go, href, type Route } from '../router'
import {
  Card,
  Empty,
  ErrorBox,
  Label,
  Loading,
  METHOD,
  SegmentedTabs,
  SourceCard,
  targetOf,
  useBuildingName,
  ValueTag,
  type Source,
  type Target,
  type Value,
} from '../ui'
import { Viewer } from '../Viewer'

export type Item = {
  id: string
  building: string
  element: string
  label_en: string
  label_az: string
  unit: string
  type: string
  citation: string
  parent: boolean
  value: Value
  viewer?: Source | null
}
export type Takeoff = {
  items: Item[]
  ledger: any[]
  gate: { pass: boolean; checks: { item: string; expected: number; got: number | null; tolerance: number; pass: boolean }[] }
  conflicts: any[]
  rule_count: number
  problems: string[]
}

const STATUS_BAR: Record<string, string> = {
  verified: 'var(--ok)',
  extracted: 'var(--info)',
  review: 'var(--warn)',
  blocked: 'var(--bad)',
}

function rejectedText(r: Record<string, any>) {
  const what = r.value ?? r.level ?? r.text ?? r.measurement
  const why = r.why ?? r.reason ?? r.note
  const parts = [what !== undefined ? String(what) : null, r.count ? `seen ${r.count}×` : null, r.file ? String(r.file).split('/').pop() : null]
  const head = parts.filter(Boolean).join(' · ')
  return why ? `${head}: ${why}` : head || JSON.stringify(r)
}

function ValueNode({ name, v, onOpen, depth = 0 }: { name: string; v: Value; onOpen: (t: Target) => void; depth?: number }) {
  const label = v.note && v.note.includes('·') ? v.note.split('|')[0].trim() : name.replace(/_/g, ' ')
  const open = v.sources.map((s) => targetOf(s)).find((t): t is Target => t != null)
  return (
    <div className="node">
      <div className="head">
        {open ? (
          <button type="button" className="text-[var(--accent-2)] hover:underline text-left" onClick={() => onOpen(open)}>
            {label}
          </button>
        ) : (
          <span>{label}</span>
        )}
        <span className="inline-flex items-center gap-1.5">
          <span className="mono">{v.value === null ? '—' : fmt(v.value, 4)} {v.unit}</span>
          <ValueTag status={v.status} />
        </span>
      </div>
      <div className="muted text-[12px]">
        {METHOD[v.method] || v.method}
        {v.note ? ` · ${v.note}` : ''}
      </div>
      {v.missing?.length && !v.note ? <div className="note bad">missing: {v.missing.join(', ')}</div> : null}
      {v.sources.slice(0, 2).map((s, i) => (
        <SourceCard key={i} src={s} onOpen={onOpen} />
      ))}
      {depth < 3 && Object.keys(v.inputs || {}).length ? (
        <div className="tree">
          {Object.entries(v.inputs).map(([k, iv]) => (
            <ValueNode key={k} name={k} v={iv} onOpen={onOpen} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function Takeoff({ route }: { route: Route }) {
  const { data, error } = useData<Takeoff>('/api/takeoff')
  const report = useData<{ lines: Record<string, { item?: string; review_reasons?: { code: string; accepted_by?: string; link?: string; citation?: string; rule?: string; file?: string }[] }> }>('/api/report')
  const [q, setQ] = useState('')
  const [target, setTarget] = useState<Target | null>(null)
  const bname = useBuildingName()
  const status = route.query.get('status') || 'all'

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the takeoff" />

  const items = data.items.filter(
    (i) => (status === 'all' || i.value.status === status) && matches(q, i.label_en, i.label_az, i.building, i.element),
  )
  const sel = data.items.find((i) => i.id === route.query.get('item')) || items[0]
  const first = sel?.viewer || sel?.value.sources.find((s) => targetOf(s)) || null
  const shown = target || (first ? targetOf(first) : null)
  const counts = data.items.reduce<Record<string, number>>((m, i) => ((m[i.value.status] = (m[i.value.status] || 0) + 1), m), {})
  const gateTitle = data.gate.checks.map((c) => `${c.pass ? '✓' : '✗'} ${c.item}: ${c.got ?? '—'} vs ${c.expected} ± ${c.tolerance}`).join('\n')

  const pick = (id: string) => {
    setTarget(null)
    go('takeoff', { item: id, status: status === 'all' ? null : status })
  }

  return (
    <div className="work">
      <Card
        title="Extracted Quantities"
        sub={`${data.items.length} items · ${data.rule_count} cited project rules`}
        right={
          <span className={`tag ${data.gate.pass ? 'ok' : 'bad'}`} title={`Depot Geometry Gate\n${gateTitle}`}>
            {data.gate.pass ? <ShieldCheck size={12} /> : <ShieldWarning size={12} />} Gate {data.gate.pass ? 'Passed' : 'Failed'}
          </span>
        }
      >
        <div className="toolbar">
          <SegmentedTabs<string>
            id="takeoff-status"
            size="sm"
            value={status}
            onChange={(s) => go('takeoff', { status: s === 'all' ? null : s, item: sel?.id })}
            options={[
              { value: 'all', label: 'All', count: data.items.length },
              { value: 'verified', label: 'Verified', count: counts.verified || 0, tone: 'ok' },
              { value: 'extracted', label: 'Extracted', count: counts.extracted || 0 },
              { value: 'review', label: 'Review', count: counts.review || 0, tone: 'warn' },
              { value: 'blocked', label: 'Blocked', count: counts.blocked || 0, tone: 'bad' },
            ]}
          />
          <label className="field w-full min-w-0!">
            <Search size={14} />
            <input placeholder="Filter item, building, or element…" value={q} onChange={(e) => setQ(e.target.value)} />
            {q ? (
              <button type="button" onClick={() => setQ('')} className="clear" aria-label="Clear search">
                <X size={13} />
              </button>
            ) : null}
          </label>
        </div>

        <div className="rows">
          {items.map((i) => (
            <button key={i.id} type="button" className={`list-item ${sel?.id === i.id ? 'on' : ''}`} onClick={() => pick(i.id)}>
              <span className="t"><Label en={i.label_en} az={i.label_az} /></span>
              <span className="q">
                {i.value.value === null ? <span className="text-[var(--bad-text)]">blocked</span> : fmt(i.value.value, 3)}{' '}
                <span className="muted">{i.unit}</span>
              </span>
              <span className="m">
                <span className="dot mr-1.5 align-[1px]" style={{ background: STATUS_BAR[i.value.status], width: 6, height: 6 }} />
                {bname(i.building)} · {METHOD[i.value.method] || i.value.method}
              </span>
              <span className="text-right"><ValueTag status={i.value.status} /></span>
            </button>
          ))}
          {!items.length ? <Empty icon={<Search size={18} />} title="No takeoff items match">Clear search or switch status tab.</Empty> : null}
        </div>
      </Card>

      <Card title="Drawing Sheet Evidence" sub={sel ? <Label en={sel.label_en} az={sel.label_az} /> : undefined}>
        <Viewer target={shown} />
      </Card>

      <Card title="Derivation & Citations">
        {sel ? (
          <div className="insp">
            <div className="eyebrow accent">{bname(sel.building)} · {sel.element.replace(/_/g, ' ')}</div>
            <h1><Label en={sel.label_en} az={sel.label_az} /></h1>
            <div className={`big ${sel.value.value === null ? 'blocked' : ''}`}>
              {sel.value.value === null ? (
                <span className="inline-flex items-center gap-2"><Prohibit size={20} /> Blocked</span>
              ) : (
                fmt(sel.value.value, 4)
              )}
              {sel.value.value !== null ? <small>{sel.unit}</small> : null}
            </div>

            <div className="pair"><span>Status</span><ValueTag status={sel.value.status} /></div>
            {Object.values(report.data?.lines || {})
              .flatMap((row) => (row.item === sel.id ? row.review_reasons || [] : []))
              .map((reason) => (
                <div key={reason.code + (reason.link || '')} className="faint mt-1 text-[12px]">
                  {reasonText(reason)}
                </div>
              ))}
            <div className="pair"><span>Method</span><span>{METHOD[sel.value.method] || sel.value.method}</span></div>
            <div className="pair"><span>Rule / Citation</span><span className="mono text-[12px]">{sel.citation}</span></div>

            {sel.value.note ? <div className="box">{sel.value.note}</div> : null}
            {sel.value.status === 'blocked' ? (
              <div className="box bad">
                <small>Intentionally Uncomputed</small>
                Required dimension or input is missing from the drawings; dependent BOQ lines remain flagged as Blocked rather than guessed.
              </div>
            ) : null}

            {sel.value.formula ? (
              <div className="box info formula">
                <small>Formula</small>
                {sel.value.formula}
              </div>
            ) : null}

            {Object.keys(sel.value.inputs || {}).length ? (
              <>
                <div className="section-label"><span className="eyebrow">Input Tree</span></div>
                <div className="tree">
                  {Object.entries(sel.value.inputs).map(([k, v]) => (
                    <ValueNode key={k} name={k} v={v} onOpen={setTarget} />
                  ))}
                </div>
              </>
            ) : null}

            {sel.value.conflicts?.length ? (
              <div className="box warn">
                <small>Cross-Document Disagreement</small>
                {sel.value.conflicts.map((c: any, i: number) => (
                  <div key={i}>
                    <b className="mono">{fmt(c.value, 4)}</b> · {c.citation || c.source?.file_name}
                  </div>
                ))}
                <a href={href('conflicts')} className="mt-1 inline-block">Open Conflicts →</a>
              </div>
            ) : null}

            {sel.value.sources.length ? (
              <>
                <div className="section-label"><span className="eyebrow">Sheet Sources · {sel.value.sources.length}</span></div>
                {sel.value.sources.slice(0, 12).map((s, i) => (
                  <SourceCard key={i} src={s} onOpen={setTarget} active={JSON.stringify(targetOf(s)) === JSON.stringify(shown)} />
                ))}
              </>
            ) : null}

            {sel.value.searched?.length ? (
              <>
                <div className="section-label"><span className="eyebrow">Search Patterns</span></div>
                <ul className="list-plain">{sel.value.searched.map((s, i) => <li key={i} lang="az">{s}</li>)}</ul>
              </>
            ) : null}

            {sel.value.rejected?.length ? (
              <>
                <div className="section-label"><span className="eyebrow">Evaluated & Rejected</span></div>
                <ul className="list-plain">
                  {sel.value.rejected.slice(0, 10).map((r: any, i) => (
                    <li key={i}>{typeof r === 'string' ? r : rejectedText(r)}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : (
          <Empty title="No item selected">Select a takeoff item on the left.</Empty>
        )}
      </Card>
    </div>
  )
}
