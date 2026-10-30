import { CheckCircle, Download, Prohibit, UserCheck, Warning } from '../icons'
import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, Empty, ErrorBox, Label, LINE_STATUS, Loading, pct, StatusTag, useBuildingName } from '../ui'
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
  'BOQ-Hadrut-checked.xlsx': 'Client bill with the check filled in',
  'BOQ-Hadrut-checked.pdf': 'Client bill with the check, printed',
  'Hadrut-discrepancy-report.xlsx': 'Discrepancy report',
  'Hadrut-discrepancy-report.pdf': 'Discrepancy report, printed',
  'BOQ-Hadrut-generated.xlsx': 'Bill generated from our own measurements',
  'BOQ-Hadrut-generated.pdf': 'Generated bill, printed',
}

function size(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`
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
  const styleDiffs = info.client_bill_styles_after_excel?.cell_style_diffs

  return (
    <>
      <div className="strip">
        <div className="kpi">
          <div className="k"><CheckCircle size={14} /> Value backed by a drawing</div>
          <div className="v num">{money(checkedValue)}</div>
          <div className="s">{pct(checkedValue, data.total_value)} of {money(data.total_value)}</div>
        </div>
        <button className={`kpi ${v.different ? 'bad' : ''}`} onClick={() => go('report', { tab: 'different' })}>
          <div className="k"><Warning size={14} /> Value on different lines</div>
          <div className="v num">{money(v.different || 0)}</div>
          <div className="s">{data.counts.different || 0} lines</div>
        </button>
        <button className="kpi" onClick={() => go('report', { tab: 'review' })}>
          <div className="k"><UserCheck size={14} /> Value that needs a person</div>
          <div className="v num">{money((v.review || 0) + (v.blocked || 0))}</div>
          <div className="s">{fmt((data.counts.review || 0) + (data.counts.blocked || 0))} lines</div>
        </button>
        <button className="kpi" onClick={() => go('report', { tab: 'not_found' })}>
          <div className="k"><Prohibit size={14} /> Value with no drawing evidence</div>
          <div className="v num">{money(v.not_found || 0)}</div>
          <div className="s">{fmt(data.counts.not_found || 0)} lines</div>
        </button>
      </div>

      <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(300px, 380px)' }}>
        <Card style={{ overflow: 'hidden' }}>
          <div className="toolbar">
            <div className="chips">
              {TABS.map(([k, label]) => (
                <button key={k} className={`chip ${tab === k ? 'on' : ''}`} onClick={() => go('report', { tab: k })}>
                  {label} <b>{fmt(k === 'measured' ? data.measured_no_bill_line.length : (data.lists[k] || []).length)}</b>
                </button>
              ))}
            </div>
          </div>
          {tab === 'measured' ? (
            <div className="scroll">
              <table>
                <thead><tr><th>Measured item</th><th>Building</th><th className="r">Value</th><th>Rule</th></tr></thead>
                <tbody>
                  {data.measured_no_bill_line.map((i) => (
                    <tr key={i.id} className="click" onClick={() => go('takeoff', { item: i.id })}>
                      <td><Label en={i.label_en} az={i.label_az} /></td>
                      <td>{bname(i.building)}</td>
                      <td className="r num">{fmt(i.value.value, 3)} {i.unit}</td>
                      <td className="muted mono" style={{ fontSize: 12 }}>{i.citation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="scroll" style={{ maxHeight: 'calc(100vh - 330px)', minHeight: 320 }}>
              <table>
                <thead>
                  <tr><th>Line</th><th>Description</th><th className="r">Bill</th><th className="r">Drawings</th><th className="r">Amount</th><th>Reason</th></tr>
                </thead>
                <tbody>
                  {rows.slice(0, 600).map((r) => (
                    <tr key={r.id} className="click" onClick={() => go('bill', { line: r.id })}>
                      <td className="code">{r.id}<div style={{ marginTop: 4 }}><StatusTag status={r.status} /></div></td>
                      <td className="desc"><T az={r.description} /><div className="muted" style={{ fontSize: 12 }}>{bname(r.building)}</div></td>
                      <td className="r num">{fmt(r.bill_qty, 3)} {r.unit}</td>
                      <td className={`r num ${r.status === 'different' ? 'bad-fig' : ''}`}>{r.our_qty === null ? <span className="faint">—</span> : fmt(r.our_qty, 3)}</td>
                      <td className="r num">{money(r.amount)}</td>
                      <td className="muted" style={{ fontSize: 12.5, maxWidth: 320 }}>{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 600 ? <div className="empty-state">Showing the first 600 of {fmt(rows.length)}. The Excel report has all of them.</div> : null}
              {!rows.length ? <Empty title="No lines">{LINE_STATUS[tab]?.hint ? `Nothing here: ${LINE_STATUS[tab].hint.toLowerCase()}.` : null}</Empty> : null}
            </div>
          )}
        </Card>

        <div className="stack">
          <Card title="Exports" sub={info.written_at ? `Written ${info.written_at}` : 'Files to hand over'} right={<Download size={15} className="muted" />}>
            <div className="rows">
              {(ex.data?.files || []).map((f) => {
                const ext = f.name.split('.').pop()?.toLowerCase() || ''
                return (
                  <a key={f.name} className="dl" href={`/api/exports/file/${encodeURIComponent(f.name)}`} download>
                    <span className={`ext ${ext === 'xlsx' || ext === 'pdf' ? ext : 'other'}`}>{ext.toUpperCase()}</span>
                    <div className="info">
                      <b>{EXPORT_LABEL[f.name] || f.name}</b>
                      <span>{f.name} · {size(f.size)}</span>
                    </div>
                    <Download size={16} className="get" />
                  </a>
                )
              })}
              {ex.data && !ex.data.files.length ? <Empty title="No exports yet">Run <span className="mono">python -m azboq export</span> to write them.</Empty> : null}
              {ex.error ? <div className="card-body"><ErrorBox error={ex.error} /></div> : null}
            </div>
          </Card>
          <Card title="How faithful the filled bill is" sub="The client’s workbook, with only the check added">
            <div className="card-body" style={{ paddingTop: 4 }}>
              <div className="pair"><span>Cell styles changed</span><span className={`tag ${styleDiffs === 0 ? 'ok' : styleDiffs === undefined ? 'muted' : 'bad'}`}>{styleDiffs ?? '—'}</span></div>
              <div className="pair"><span>Quantities changed</span><span className="mono" style={{ fontSize: 12 }}>{info.client_bill?.changed_rows?.length ?? '—'} (rows {info.client_bill?.changed_rows?.join(', ')})</span></div>
              {vals?.examples?.length ? (
                <div className="pair"><span>Header after the change</span><span className="mono" style={{ fontSize: 12 }}>{money(vals.examples[0][1])} → {money(vals.examples[0][2])}</span></div>
              ) : null}
              {print ? <div className="pair"><span>Printed pages (client / ours)</span><span className="mono">{print.original_pages ?? '—'} / {print.written_pages ?? '—'}</span></div> : null}
              <div className="box">
                External links were replaced by their cached values and broken names removed, so the file opens without prompts. The page count differs because Excel 2024 wraps a few long descriptions differently from the client's Excel; the cells and styles are the client's.
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <a className="chip solo" href={href('inputs')}>Inputs ledger</a>
                <a className="chip solo" href={href('conflicts')}>Conflicts</a>
                <a className="chip solo" href={href('runlog')}>Run log</a>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
