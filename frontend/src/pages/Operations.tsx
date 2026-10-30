import { useState } from 'react'
import { CheckCircle, Clock, Search, Tray, X } from '../icons'
import { useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import { go, type Route } from '../router'
import { Card, Empty, ErrorBox, Label, Loading, tradeName, useBuildingName } from '../ui'

type Register = { id: string; title: string; title_az: string; workbook: string; rows: Record<string, any>[]; empty_note: string }
type Ops = {
  registers: Register[]
  codes: { buildings: string[]; trades: string[]; units: { written: string; lines: number }[]; sections: { code: string; title: string; building: string; trade: string }[] }
  fraud_rules: { id: string; rule: string; needs: string[]; runnable: boolean }[]
}

const COLUMNS: Record<string, [string, string][]> = {
  drawings: [['file', 'File'], ['kind', 'Kind'], ['discipline', 'Discipline'], ['building', 'Building'], ['order', 'Order'], ['sheets', 'Sheets'], ['version', 'Version']],
  contract_bill: [['id', 'Code'], ['description', 'Description'], ['unit', 'Unit'], ['qty', 'Quantity'], ['rate', 'Rate'], ['amount', 'Amount'], ['building', 'Building']],
}
const NUMERIC = ['qty', 'rate', 'amount', 'sheets']
const KIND: Record<string, string> = { drawing_cad: 'DWG', drawing_pdf: 'PDF', drawing_scan: 'Scan' }

export function Operations({ route }: { route: Route }) {
  const { data, error } = useData<Ops>('/api/operations')
  const [q, setQ] = useState('')
  const bname = useBuildingName()
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="registers" />
  const id = route.parts[1] || 'drawings'

  if (id === 'codes') {
    return (
      <div className="grid3">
        <Card title={`Bill sections · ${data.codes.sections.length}`}>
          <div className="rows" style={{ maxHeight: 'calc(100vh - 230px)' }}>
            {data.codes.sections.map((s) => (
              <a key={s.code} className="row" style={{ gridTemplateColumns: '52px minmax(0,1fr)' }} href={`#/bill?q=${encodeURIComponent(s.code)}`}>
                <span className="code">{s.code}</span>
                <span style={{ minWidth: 0 }}><T az={s.title} /><span className="d" style={{ display: 'block' }}>{bname(s.building)} · {tradeName(s.trade)}</span></span>
              </a>
            ))}
          </div>
        </Card>
        <Card title={`Units as written · ${data.codes.units.length}`} sub="Spelled the way the workbook spells them">
          <div className="rows">
            {data.codes.units.map((u) => (
              <div key={u.written} className="row" style={{ gridTemplateColumns: 'minmax(0,1fr) auto', minHeight: 44 }}>
                <span lang="az" className="mono">{u.written}</span><span className="num muted">{fmt(u.lines)} lines</span>
              </div>
            ))}
          </div>
        </Card>
        <div className="stack">
          <Card title={`Buildings · ${data.codes.buildings.length}`}>
            <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {data.codes.buildings.map((b) => <button key={b} className="chip solo" onClick={() => go('bill', { building: b })}>{bname(b)}</button>)}
            </div>
          </Card>
          <Card title={`Trades · ${data.codes.trades.length}`}>
            <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {data.codes.trades.map((t) => <span key={t} className="pill">{tradeName(t)}</span>)}
            </div>
          </Card>
        </div>
      </div>
    )
  }

  const reg = data.registers.find((r) => r.id === id)
  if (!reg) return <ErrorBox error={`There is no register called ${id}.`} />
  const cols = COLUMNS[id] || (reg.rows[0] ? Object.keys(reg.rows[0]).map((k) => [k, k] as [string, string]) : [])
  const rows = reg.rows.filter((r) => matches(q, ...Object.values(r).map((v) => (v === null || v === undefined ? '' : String(v)))))
  const rules = data.fraud_rules.filter((f) => f.needs.includes(id))

  const cellOf = (k: string, r: Record<string, any>) => {
    const v = r[k]
    if (k === 'description') return <T az={v} />
    if (k === 'building') return bname(v)
    if (k === 'kind') return <span className="pill">{KIND[v] || v}</span>
    if (k === 'amount' || k === 'rate') return money(v)
    if (typeof v === 'number') return fmt(v, 3)
    return v ?? <span className="faint">—</span>
  }

  return (
    <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(280px, 340px)' }}>
      <Card
        title={<Label en={reg.title} az={reg.title_az} />}
        sub={<>Workbook <span className="mono">{reg.workbook}</span> · {fmt(reg.rows.length)} rows</>}
        right={
          reg.rows.length ? (
            <label className="field" style={{ minWidth: 200 }}>
              <Search size={14} />
              <input placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
              {q ? <button onClick={() => setQ('')} aria-label="Clear search" style={{ display: 'grid', color: 'var(--faint)' }}><X size={14} /></button> : null}
            </label>
          ) : null
        }
        style={{ overflow: 'hidden' }}
      >
        {reg.rows.length ? (
          <div className="scroll" style={{ maxHeight: 'calc(100vh - 250px)' }}>
            <table>
              <thead><tr>{cols.map(([k, label]) => <th key={k} className={NUMERIC.includes(k) ? 'r' : ''}>{label}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 500).map((r, i) => (
                  <tr key={i} className={id === 'contract_bill' ? 'click' : ''} onClick={() => id === 'contract_bill' && go('bill', { line: r.id })}>
                    {cols.map(([k]) => (
                      <td key={k} className={NUMERIC.includes(k) ? 'r num' : k === 'description' ? 'desc' : k === 'id' ? 'code' : ''} lang={k === 'file' ? 'az' : undefined}>
                        {cellOf(k, r)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 500 ? <div className="empty-state">Showing 500 of {fmt(rows.length)}; search to narrow.</div> : null}
            {!rows.length ? <Empty icon={<Search size={20} />} title="Nothing matches" /> : null}
          </div>
        ) : (
          <Empty icon={<Tray size={20} />} title="Empty in this package">
            {reg.empty_note} The package holds drawings and one bill, so there is nothing real to put here yet, and nothing is invented to fill it.
          </Empty>
        )}
      </Card>
      <Card title="Checks that use this register" sub="Cross-checks that run once their data exists">
        <div className="card-body">
          {rules.length ? (
            rules.map((f) => (
              <div key={f.id} className={`box ${f.runnable ? 'ok' : ''}`}>
                <small style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {f.runnable ? <CheckCircle size={12} /> : <Clock size={12} />} {f.id} · {f.runnable ? 'runs' : 'waits for data'}
                </small>
                {f.rule}
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>needs: {f.needs.join(', ')}</div>
              </div>
            ))
          ) : (
            <div className="muted">No cross-check depends on this register alone.</div>
          )}
        </div>
      </Card>
    </div>
  )
}
