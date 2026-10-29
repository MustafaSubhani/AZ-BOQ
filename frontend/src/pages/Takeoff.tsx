import { useState } from 'react'
import { useData } from '../api'
import { fmt, matches } from '../az'
import { go, href, type Route } from '../router'
import { Card, ErrorBox, Label, Loading, METHOD, SourceCard, targetOf, useBuildingName, ValueTag, type Source, type Target, type Value } from '../ui'
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

function rejectedText(r: Record<string, any>) {
  const what = r.value ?? r.level ?? r.text ?? r.measurement
  const why = r.why ?? r.reason ?? r.note
  const parts = [what !== undefined ? String(what) : null, r.count ? `seen ${r.count}×` : null, r.file ? String(r.file).split('/').pop() : null]
  const head = parts.filter(Boolean).join(' · ')
  return why ? `${head}: ${why}` : head || JSON.stringify(r)
}

function ValueNode({ name, v, onOpen, depth = 0 }: { name: string; v: Value; onOpen: (t: Target) => void; depth?: number }) {
  return (
    <div className="node">
      <div className="head">
        <span>{name}</span>
        <span>
          <b className="num">{v.value === null ? '—' : fmt(v.value, 4)}</b> {v.unit} <ValueTag status={v.status} />
        </span>
      </div>
      <div className="muted" style={{ fontSize: 12 }}>{METHOD[v.method] || v.method}{v.note ? ` · ${v.note}` : ''}</div>
      {v.missing?.length ? <div className="tag bad">missing: {v.missing.join(', ')}</div> : null}
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
  const [q, setQ] = useState('')
  const [target, setTarget] = useState<Target | null>(null)
  const bname = useBuildingName()
  const status = route.query.get('status') || 'all'
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the takeoff" />
  const items = data.items.filter((i) => (status === 'all' || i.value.status === status) && matches(q, i.label_en, i.label_az, i.building, i.element))
  const sel = data.items.find((i) => i.id === route.query.get('item')) || items[0]
  const first = sel?.viewer || sel?.value.sources.find((s) => targetOf(s)) || null
  const shown = target || (first ? targetOf(first) : null)
  const counts = data.items.reduce<Record<string, number>>((m, i) => ((m[i.value.status] = (m[i.value.status] || 0) + 1), m), {})

  const pick = (id: string) => {
    setTarget(null)
    go('takeoff', { item: id, status: status === 'all' ? null : status })
  }

  return (
    <div className="work">
      <Card
        title="Measured"
        right={
          <span className={`tag ${data.gate.pass ? 'ok' : 'bad'}`} title={data.gate.checks.map((c) => `${c.item}: ${c.got} vs ${c.expected} ± ${c.tolerance}`).join('\n')}>
            Depot gate {data.gate.pass ? 'passes' : 'fails'}
          </span>
        }
      >
        <div className="toolbar">
          {['all', 'verified', 'extracted', 'review', 'blocked'].map((s) => (
            <button key={s} className={`chip ${status === s ? 'on' : ''}`} onClick={() => go('takeoff', { status: s === 'all' ? null : s })}>
              {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)} <b>{s === 'all' ? data.items.length : counts[s] || 0}</b>
            </button>
          ))}
          <input className="search" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 0, flex: 1 }} />
        </div>
        <div className="rows">
          {items.map((i) => (
            <button key={i.id} className={`list-item ${sel?.id === i.id ? 'on' : ''}`} onClick={() => pick(i.id)}>
              <span className="t"><Label en={i.label_en} az={i.label_az} /></span>
              <span className="q num">
                {i.value.value === null ? '—' : fmt(i.value.value, 3)} <span className="muted" style={{ fontWeight: 500 }}>{i.unit}</span>
              </span>
              <span className="m">{bname(i.building)} · {METHOD[i.value.method] || i.value.method}</span>
              <span style={{ textAlign: 'right' }}><ValueTag status={i.value.status} /></span>
            </button>
          ))}
        </div>
      </Card>

      <Card title={sel ? <span>Evidence on the sheet</span> : 'Sheet'}>
        <Viewer target={shown} />
      </Card>

      <Card title="Why this number">
        {sel ? (
          <div className="insp">
            <div className="eyebrow">{bname(sel.building)} · {sel.element.replace(/_/g, ' ')}</div>
            <h1><Label en={sel.label_en} az={sel.label_az} /></h1>
            <div className="big num">
              {sel.value.value === null ? 'Blocked' : fmt(sel.value.value, 4)}
              {sel.value.value !== null ? <small>{sel.unit}</small> : null}
            </div>
            <div className="pair"><span>Status</span><ValueTag status={sel.value.status} /></div>
            <div className="pair"><span>Method</span><span>{METHOD[sel.value.method] || sel.value.method}</span></div>
            <div className="pair"><span>Rule</span><span style={{ textAlign: 'right' }}>{sel.citation}</span></div>
            {sel.value.note ? <div className="box">{sel.value.note}</div> : null}
            {sel.value.status === 'blocked' ? (
              <div className="box bad">
                <small>No number, by design</small>
                Missing {sel.value.missing.join(', ') || 'an input'}. Nothing is guessed in its place; the bill lines that need it are marked Blocked.
              </div>
            ) : null}
            {sel.value.formula ? <div className="box info"><small>Formula</small>{sel.value.formula}</div> : null}
            {Object.keys(sel.value.inputs || {}).length ? (
              <>
                <div className="eyebrow" style={{ marginTop: 14 }}>Inputs</div>
                <div className="tree">
                  {Object.entries(sel.value.inputs).map(([k, v]) => (
                    <ValueNode key={k} name={k} v={v} onOpen={setTarget} />
                  ))}
                </div>
              </>
            ) : null}
            {sel.value.conflicts?.length ? (
              <div className="box warn">
                <small>Another document says something else</small>
                {sel.value.conflicts.map((c: any, i: number) => (
                  <div key={i}>
                    <b className="num">{fmt(c.value, 4)}</b> · {c.citation || c.source?.file_name}
                  </div>
                ))}
                <a href={href('conflicts')}>Open conflicts</a>
              </div>
            ) : null}
            {sel.value.sources.length ? (
              <>
                <div className="eyebrow" style={{ marginTop: 14 }}>Sources · {sel.value.sources.length}</div>
                {sel.value.sources.slice(0, 12).map((s, i) => (
                  <SourceCard key={i} src={s} onOpen={setTarget} active={JSON.stringify(targetOf(s)) === JSON.stringify(shown)} />
                ))}
              </>
            ) : null}
            {sel.value.searched?.length ? (
              <>
                <div className="eyebrow" style={{ marginTop: 14 }}>Searched</div>
                <ul className="list-plain">{sel.value.searched.map((s, i) => <li key={i} lang="az">{s}</li>)}</ul>
              </>
            ) : null}
            {sel.value.rejected?.length ? (
              <>
                <div className="eyebrow" style={{ marginTop: 14 }}>Looked at and rejected</div>
                <ul className="list-plain">
                  {sel.value.rejected.slice(0, 10).map((r: any, i: number) => (
                    <li key={i}>{typeof r === 'string' ? r : rejectedText(r)}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : (
          <div className="empty-state">Nothing matches the filter.</div>
        )}
      </Card>
    </div>
  )
}
