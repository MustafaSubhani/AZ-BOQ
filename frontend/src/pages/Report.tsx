import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, ErrorBox, Label, LINE_STATUS, Loading, StatusTag, useBuildingName } from '../ui'
import type { Item } from './Takeoff'

type Row = { id: string; description: string; unit: string; bill_qty: number; our_qty: number | null; gap: number | null; gap_pct: number | null; status: string; reason: string; amount: number | null; building: string; row: number }
type ReportData = {
  counts: Record<string, number>
  value_by_status: Record<string, number>
  lists: Record<string, Row[]>
  measured_no_bill_line: Item[]
  total_value: number
}
type Exports = { files: { name: string; size: number }[]; info: any }

const TABS: [string, string][] = [
  ['different', 'Different'],
  ['matched', 'Backed by a drawing'],
  ['review', 'Needs review'],
  ['blocked', 'Blocked'],
  ['not_found', 'Not on drawings'],
  ['measured', 'Measured, no bill line'],
]

const EXPORT_LABEL: Record<string, string> = {
  'BOQ-Hadrut-checked.xlsx': 'Client bill with the check filled in (Excel)',
  'BOQ-Hadrut-checked.pdf': 'Client bill with the check, printed',
  'Hadrut-discrepancy-report.xlsx': 'Discrepancy report (Excel)',
  'Hadrut-discrepancy-report.pdf': 'Discrepancy report (PDF)',
  'BOQ-Hadrut-generated.xlsx': 'Bill generated from our own measurements (Excel)',
  'BOQ-Hadrut-generated.pdf': 'Generated bill, printed',
}

export function Report({ route }: { route: Route }) {
  const { data, error } = useData<ReportData>('/api/report')
  const ex = useData<Exports>('/api/exports')
  const bname = useBuildingName()
  const tab = route.query.get('tab') || 'different'
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the report" />
  const v = data.value_by_status
  const checkedValue = (v.matched || 0) + (v.printed || 0) + (v.derived || 0)
  const rows = tab === 'measured' ? [] : data.lists[tab] || []
  const info = ex.data?.info || {}
  const vals = info.client_bill_values_after_excel
  const print = info.print

  return (
    <>
      <div className="strip">
        <div className="kpi">
          <div className="k">Value backed by a drawing</div>
          <div className="v num">{money(checkedValue)}</div>
          <div className="s">{((checkedValue / data.total_value) * 100).toFixed(1)}% of {money(data.total_value)}</div>
        </div>
        <div className="kpi">
          <div className="k">Value on different lines</div>
          <div className="v num" style={{ color: 'var(--bad)' }}>{money(v.different || 0)}</div>
          <div className="s">{data.counts.different || 0} lines</div>
        </div>
        <div className="kpi">
          <div className="k">Value that needs a person</div>
          <div className="v num">{money((v.review || 0) + (v.blocked || 0))}</div>
          <div className="s">{fmt((data.counts.review || 0) + (data.counts.blocked || 0))} lines</div>
        </div>
        <div className="kpi">
          <div className="k">Value with no drawing evidence</div>
          <div className="v num">{money(v.not_found || 0)}</div>
          <div className="s">{fmt(data.counts.not_found || 0)} lines</div>
        </div>
      </div>

      <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) 360px' }}>
        <Card style={{ overflow: 'hidden' }}>
          <div className="toolbar">
            {TABS.map(([k, label]) => (
              <button key={k} className={`chip ${tab === k ? 'on' : ''}`} onClick={() => go('report', { tab: k })}>
                {label} <b>{fmt(k === 'measured' ? data.measured_no_bill_line.length : (data.lists[k] || []).length)}</b>
              </button>
            ))}
          </div>
          {tab === 'measured' ? (
            <table>
              <thead><tr><th>Measured item</th><th>Building</th><th className="r">Value</th><th>Rule</th></tr></thead>
              <tbody>
                {data.measured_no_bill_line.map((i) => (
                  <tr key={i.id} className="click" onClick={() => go('takeoff', { item: i.id })}>
                    <td><Label en={i.label_en} az={i.label_az} /></td>
                    <td>{bname(i.building)}</td>
                    <td className="r num">{fmt(i.value.value, 3)} {i.unit}</td>
                    <td className="muted">{i.citation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="scroll" style={{ maxHeight: 'calc(100vh - 290px)' }}>
              <table>
                <thead>
                  <tr><th>Line</th><th>Description</th><th className="r">Bill</th><th className="r">Drawings</th><th className="r">Amount</th><th>Reason</th></tr>
                </thead>
                <tbody>
                  {rows.slice(0, 600).map((r) => (
                    <tr key={r.id} className="click" onClick={() => go('bill', { line: r.id })}>
                      <td className="code">{r.id}<div><StatusTag status={r.status} /></div></td>
                      <td className="desc"><T az={r.description} /><div className="muted" style={{ fontSize: 12 }}>{bname(r.building)}</div></td>
                      <td className="r num">{fmt(r.bill_qty, 3)} {r.unit}</td>
                      <td className="r num">{r.our_qty === null ? '—' : fmt(r.our_qty, 3)}</td>
                      <td className="r num">{money(r.amount)}</td>
                      <td className="muted" style={{ fontSize: 12.5, maxWidth: 320 }}>{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 600 ? <div className="empty-state">Showing the first 600 of {fmt(rows.length)}. The Excel report has all of them.</div> : null}
              {!rows.length ? <div className="empty-state">{LINE_STATUS[tab]?.hint ? `No lines: ${LINE_STATUS[tab].hint.toLowerCase()}.` : 'No lines.'}</div> : null}
            </div>
          )}
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card title="Exports" right={info.written_at ? <span className="muted">{info.written_at}</span> : null}>
            <div className="rows">
              {(ex.data?.files || []).map((f) => (
                <a key={f.name} className="row" href={`/api/exports/file/${encodeURIComponent(f.name)}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <span className="dot ok" />
                  <span>
                    {EXPORT_LABEL[f.name] || f.name}
                    <span className="d" style={{ display: 'block' }}>{f.name} · {(f.size / 1024).toFixed(0)} KB</span>
                  </span>
                  <span className="tag info">Download</span>
                </a>
              ))}
              {ex.data && !ex.data.files.length ? <div className="empty-state">No exports yet. Run python -m azboq export.</div> : null}
            </div>
          </Card>
          <Card title="How faithful the filled bill is">
            <div className="card-body">
              <div className="pair"><span>Cell styles changed</span><span className={`tag ${info.client_bill_styles_after_excel?.cell_style_diffs === 0 ? 'ok' : 'bad'}`}>{info.client_bill_styles_after_excel?.cell_style_diffs ?? '—'}</span></div>
              <div className="pair"><span>Quantities changed</span><span className="num">{info.client_bill?.changed_rows?.length ?? '—'} (workbook rows {info.client_bill?.changed_rows?.join(', ')})</span></div>
              {vals?.examples?.length ? (
                <div className="pair"><span>Header after the change</span><span className="num">{money(vals.examples[0][1])} → {money(vals.examples[0][2])}</span></div>
              ) : null}
              {print ? <div className="pair"><span>Printed pages (client / ours)</span><span className="num">{print.original_pages ?? '—'} / {print.written_pages ?? '—'}</span></div> : null}
              <div className="box">
                External links were replaced by their cached values and broken names removed, so the file opens without prompts. The page count differs because Excel 2024 wraps a few long descriptions differently from the client's Excel; the cells and styles are the client's.
              </div>
              <div style={{ marginTop: 10 }}>
                <a href={href('inputs')}>Inputs ledger</a> · <a href={href('conflicts')}>Conflicts</a> · <a href={href('runlog')}>Run log</a>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
