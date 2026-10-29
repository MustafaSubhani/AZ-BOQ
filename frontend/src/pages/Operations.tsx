import { useState } from 'react'
import { useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import { go, type Route } from '../router'
import { Card, ErrorBox, Label, Loading, tradeName, useBuildingName } from '../ui'

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
          <div className="rows" style={{ maxHeight: 'calc(100vh - 170px)' }}>
            {data.codes.sections.map((s) => (
              <div key={s.code} className="row" style={{ gridTemplateColumns: '48px minmax(0,1fr)' }}>
                <span className="code">{s.code}</span>
                <span><T az={s.title} /><span className="d" style={{ display: 'block' }}>{bname(s.building)} · {tradeName(s.trade)}</span></span>
              </div>
            ))}
          </div>
        </Card>
        <Card title={`Units as written · ${data.codes.units.length}`}>
          <div className="rows">
            {data.codes.units.map((u) => (
              <div key={u.written} className="row" style={{ gridTemplateColumns: 'minmax(0,1fr) auto' }}>
                <span lang="az">{u.written}</span><span className="num muted">{fmt(u.lines)} lines</span>
              </div>
            ))}
          </div>
        </Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card title={`Buildings · ${data.codes.buildings.length}`}>
            <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {data.codes.buildings.map((b) => <span key={b} className="pill">{bname(b)}</span>)}
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
  if (!reg) return <ErrorBox error={`no register ${id}`} />
  const cols = COLUMNS[id] || (reg.rows[0] ? Object.keys(reg.rows[0]).map((k) => [k, k] as [string, string]) : [])
  const rows = reg.rows.filter((r) => matches(q, ...Object.values(r).map((v) => (v === null || v === undefined ? '' : String(v)))))
  const rules = data.fraud_rules.filter((f) => f.needs.includes(id))

  return (
    <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) 320px' }}>
      <Card
        title={<span><Label en={reg.title} az={reg.title_az} /> <span className="muted" style={{ fontWeight: 500 }}>· workbook {reg.workbook}</span></span>}
        right={reg.rows.length ? <input className="search" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} /> : null}
        style={{ overflow: 'hidden' }}
      >
        {reg.rows.length ? (
          <div className="scroll" style={{ maxHeight: 'calc(100vh - 170px)' }}>
            <table>
              <thead><tr>{cols.map(([k, label]) => <th key={k} className={['qty', 'rate', 'amount', 'sheets'].includes(k) ? 'r' : ''}>{label}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 500).map((r, i) => (
                  <tr key={i} className={id === 'contract_bill' ? 'click' : ''} onClick={() => id === 'contract_bill' && go('bill', { line: r.id })}>
                    {cols.map(([k]) => (
                      <td key={k} className={['qty', 'rate', 'amount', 'sheets'].includes(k) ? 'r num' : k === 'description' ? 'desc' : ''}>
                        {k === 'description' ? <T az={r[k]} /> : k === 'building' ? bname(r[k]) : k === 'amount' || k === 'rate' ? money(r[k]) : typeof r[k] === 'number' ? fmt(r[k], 3) : r[k] ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 500 ? <div className="empty-state">Showing 500 of {fmt(rows.length)}.</div> : null}
          </div>
        ) : (
          <div className="empty-state">
            <b>Empty in this package.</b> {reg.empty_note} The package holds drawings and one bill, so there is nothing real to put here yet, and nothing is invented to fill it.
          </div>
        )}
      </Card>
      <Card title="Checks that use this register">
        <div className="card-body">
          {rules.length ? (
            rules.map((f) => (
              <div key={f.id} className={`box ${f.runnable ? 'ok' : ''}`}>
                <small>{f.id} · {f.runnable ? 'runs' : 'waits for data'}</small>
                {f.rule}
                <div className="muted" style={{ fontSize: 12 }}>needs: {f.needs.join(', ')}</div>
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
