import { toast } from 'sonner'
import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import { CheckCircle, Download, Prohibit, UserCheck, Warning } from '../icons'
import { go, href, type Route } from '../router'
import {
  AnimatedNumber,
  Card,
  Empty,
  ErrorBox,
  Label,
  LINE_STATUS,
  Loading,
  pct,
  SegmentedTabs,
  StatusTag,
  useBuildingName,
} from '../ui'
import type { Item } from './Takeoff'

type Row = {
  id: string
  description: string
  unit: string
  bill_qty: number
  our_qty: number | null
  gap: number | null
  gap_pct: number | null
  status: string
  reason: string
  amount: number | null
  building: string
  row: number
}
type ReportData = {
  counts: Record<string, number>
  value_by_status: Record<string, number>
  lists: Record<string, Row[]>
  measured_no_bill_line: Item[]
  total_value: number
  steel?: { id: string; label: string; status: string; marks: number; reason: string; bill_lines: { id: string; qty: number; unit: string; description: string }[] }[]
}
type Exports = { files: { name: string; size: number }[]; info: any }

const EXPORT_LABEL: Record<string, string> = {
  'BOQ-Hadrut-checked.xlsx': 'Client BOQ with Audit Columns Filled',
  'BOQ-Hadrut-checked.pdf': 'Client BOQ with Audit Columns (PDF)',
  'Hadrut-discrepancy-report.xlsx': 'Auditable Discrepancy Report',
  'Hadrut-discrepancy-report.pdf': 'Auditable Discrepancy Report (PDF)',
  'BOQ-Hadrut-generated.xlsx': 'Independent Takeoff-Generated BOQ',
  'BOQ-Hadrut-generated.pdf': 'Independent Takeoff-Generated BOQ (PDF)',
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
        <button type="button" className="kpi" onClick={() => go('report', { tab: 'matched' })}>
          <div className="k"><CheckCircle size={14} /> Value Backed by Drawings</div>
          <div className="v"><AnimatedNumber value={checkedValue} decimals={0} suffix="AZN" /></div>
          <div className="s">{pct(checkedValue, data.total_value)} of {money(data.total_value)}</div>
        </button>

        <button type="button" className={`kpi ${v.different ? 'bad' : ''}`} onClick={() => go('report', { tab: 'different' })}>
          <div className="k"><Warning size={14} /> Value on Contradicted Lines</div>
          <div className="v"><AnimatedNumber value={v.different || 0} decimals={0} suffix="AZN" /></div>
          <div className="s">{data.counts.different || 0} lines contradict drawings</div>
        </button>

        <button type="button" className="kpi" onClick={() => go('report', { tab: 'review' })}>
          <div className="k"><UserCheck size={14} /> Value Needing Human Review</div>
          <div className="v"><AnimatedNumber value={(v.review || 0) + (v.blocked || 0)} decimals={0} suffix="AZN" /></div>
          <div className="s">{fmt((data.counts.review || 0) + (data.counts.blocked || 0))} lines</div>
        </button>

        <button type="button" className="kpi" onClick={() => go('report', { tab: 'not_found' })}>
          <div className="k"><Prohibit size={14} /> Value Without Drawing Evidence</div>
          <div className="v"><AnimatedNumber value={v.not_found || 0} decimals={0} suffix="AZN" /></div>
          <div className="s">{fmt(data.counts.not_found || 0)} lines</div>
        </button>
      </div>

      {data.steel?.length ? (
        <Card title="Reinforcement & Steel Schedules" sub="Grouped by structural mark; per-element tables are preserved without assuming multipliers">
          <div className="card-body grid grid-cols-1 gap-3 md:grid-cols-2 pt-2!">
            {data.steel.map((family) => (
              <div key={family.id} className="box mt-0!">
                <small>{family.label} · {family.status} · {fmt(family.marks)} marks</small>
                <div>{family.reason}</div>
                {family.bill_lines.length ? (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[12px]">
                    <span className="muted">BOQ lines:</span>
                    {family.bill_lines.map((line) => (
                      <a key={line.id} className="pill" href={href('bill', { line: line.id })}>
                        {line.id}
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(310px, 380px)' }}>
        <Card style={{ overflow: 'hidden' }}>
          <div className="toolbar">
            <SegmentedTabs<string>
              id="report-tabs"
              value={tab}
              onChange={(k) => go('report', { tab: k })}
              options={[
                { value: 'different', label: 'Contradicts', count: fmt((data.lists.different || []).length), tone: 'bad' },
                { value: 'matched', label: 'Backed', count: fmt((data.lists.matched || []).length), tone: 'ok' },
                { value: 'review', label: 'Review', count: fmt((data.lists.review || []).length), tone: 'warn' },
                { value: 'blocked', label: 'Blocked', count: fmt((data.lists.blocked || []).length), tone: 'warn' },
                { value: 'not_found', label: 'Unbacked', count: fmt((data.lists.not_found || []).length) },
                { value: 'measured', label: 'Unbilled Takeoff', count: fmt(data.measured_no_bill_line.length) },
              ]}
            />
          </div>

          {tab === 'measured' ? (
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Measured Item</th>
                    <th>Building</th>
                    <th className="r">Extracted Value</th>
                    <th>Citation</th>
                  </tr>
                </thead>
                <tbody>
                  {data.measured_no_bill_line.map((i) => (
                    <tr key={i.id} className="click" onClick={() => go('takeoff', { item: i.id })}>
                      <td><Label en={i.label_en} az={i.label_az} /></td>
                      <td>{bname(i.building)}</td>
                      <td className="r num">{fmt(i.value.value, 3)} {i.unit}</td>
                      <td className="muted mono text-[12px]">{i.citation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="scroll" style={{ maxHeight: 'calc(100vh - 300px)', minHeight: 340 }}>
              <table>
                <thead>
                  <tr>
                    <th>Line</th>
                    <th>Description</th>
                    <th className="r">Client BOQ</th>
                    <th className="r">Drawings</th>
                    <th className="r">Variance</th>
                    <th className="r">Amount</th>
                    <th>Audit Note</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 800).map((r) => (
                    <tr key={r.id} className="click" onClick={() => go('bill', { line: r.id })}>
                      <td className="code">
                        <div>{r.id}</div>
                        <div className="mt-1"><StatusTag status={r.status} /></div>
                      </td>
                      <td className="desc">
                        <T az={r.description} />
                        <div className="muted text-[11.5px] mt-0.5">{bname(r.building)}</div>
                      </td>
                      <td className="r num whitespace-nowrap">{fmt(r.bill_qty, 3)} {r.unit}</td>
                      <td className={`r num whitespace-nowrap ${r.status === 'different' ? 'bad-fig' : ''}`}>
                        {r.our_qty === null ? <span className="faint">—</span> : fmt(r.our_qty, 3)}
                      </td>
                      <td className="r num whitespace-nowrap">
                        {r.gap != null ? (
                          <span className={r.status === 'different' ? 'text-[var(--bad-text)] font-medium' : 'muted'}>
                            {r.gap > 0 ? '+' : ''}{fmt(r.gap, 2)} ({fmt(r.gap_pct, 1)}%)
                          </span>
                        ) : (
                          <span className="faint">—</span>
                        )}
                      </td>
                      <td className="r num whitespace-nowrap">{money(r.amount)}</td>
                      <td className="muted text-[12px] max-w-[280px]">{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 800 ? (
                <div className="empty-state">Showing 800 of {fmt(rows.length)} rows. Download the XLSX report for the full set.</div>
              ) : null}
              {!rows.length ? (
                <Empty title="No lines in this category">
                  {LINE_STATUS[tab]?.hint ? `${LINE_STATUS[tab].hint}.` : null}
                </Empty>
              ) : null}
            </div>
          )}
        </Card>

        <div className="stack">
          <Card
            title="Handover Package"
            sub={info.written_at ? `Generated ${info.written_at}` : 'Ready-to-share Excel & PDF deliverables'}
            right={<Download size={15} className="muted" />}
          >
            <div className="rows">
              {(ex.data?.files || []).map((f) => {
                const ext = f.name.split('.').pop()?.toLowerCase() || ''
                return (
                  <a
                    key={f.name}
                    className="dl"
                    href={`/api/exports/file/${encodeURIComponent(f.name)}`}
                    download
                    onClick={() => toast.success(`Downloading ${f.name}`)}
                  >
                    <span className={`ext ${ext === 'xlsx' || ext === 'pdf' ? ext : 'other'}`}>{ext.toUpperCase()}</span>
                    <div className="info">
                      <b>{EXPORT_LABEL[f.name] || f.name}</b>
                      <span>{f.name} · {size(f.size)}</span>
                    </div>
                    <Download size={15} className="get" />
                  </a>
                )
              })}
              {ex.data && !ex.data.files.length ? (
                <Empty title="No export files generated yet">
                  Run <span className="mono">python -m azboq export</span> to generate XLSX and PDF deliverables.
                </Empty>
              ) : null}
              {ex.error ? <div className="card-body"><ErrorBox error={ex.error} /></div> : null}
            </div>
          </Card>

          <Card title="Workbook Fidelity Check" sub="Verifies original client formatting & formulas">
            <div className="card-body pt-1!">
              <div className="pair">
                <span>Cell styles altered</span>
                <span className={`tag ${styleDiffs === 0 ? 'ok' : styleDiffs === undefined ? 'muted' : 'bad'}`}>
                  {styleDiffs ?? '—'}
                </span>
              </div>
              <div className="pair">
                <span>Quantities modified</span>
                <span className="mono text-[12px]">
                  {info.client_bill?.changed_rows?.length ?? '—'}
                </span>
              </div>
              {vals?.examples?.length ? (
                <div className="pair">
                  <span>Header sum check</span>
                  <span className="mono text-[12px]">{money(vals.examples[0][1])} → {money(vals.examples[0][2])}</span>
                </div>
              ) : null}
              {print ? (
                <div className="pair">
                  <span>Printed pages (client / ours)</span>
                  <span className="mono">{print.original_pages ?? '—'} / {print.written_pages ?? '—'}</span>
                </div>
              ) : null}
              <div className="box">
                External workbook links were resolved to cached values so the XLSX opens cleanly without broken-link prompts while preserving client cell formatting.
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <a className="chip solo" href={href('inputs')}>Inputs Ledger</a>
                <a className="chip solo" href={href('conflicts')}>Conflicts</a>
                <a className="chip solo" href={href('runlog')}>Pipeline Log</a>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
