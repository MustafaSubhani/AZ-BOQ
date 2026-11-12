import { useState } from 'react'
import { toast } from 'sonner'
import { clearCache, delJSON, postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import {
  ArrowsLeftRight,
  Check,
  CheckCircle,
  Gauge,
  Invoice,
  Package,
  Search,
  ShieldCheck,
  ShieldWarning,
  Undo,
  Warning,
  X,
} from '../icons'
import { go, href, type Route } from '../router'
import {
  AnimatedNumber,
  Card,
  Empty,
  ErrorBox,
  Label,
  Loading,
  SegmentedTabs,
  tradeName,
  useBuildingName,
} from '../ui'

type Register = {
  id: string
  title: string
  title_az: string
  workbook: string
  rows: Record<string, any>[]
  empty_note: string
  simulated?: boolean
}

type FraudDecision = {
  id: number
  action: 'hold' | 'exception'
  author: string
  reason: string
  created_at: number
}

type FraudAlert = {
  id: string
  rule_id: string
  severity: 'critical' | 'high' | 'medium'
  title: string
  building: string
  boq_line: string
  register: string
  left_label: string
  left_val: string
  left_sub: string
  right_label: string
  right_val: string
  right_sub: string
  variance: string
  exposure_azn: number
  summary: string
  decision?: FraudDecision | null
}

type Ops = {
  registers: Register[]
  codes: {
    buildings: string[]
    trades: string[]
    units: { written: string; lines: number }[]
    sections: { code: string; title: string; building: string; trade: string }[]
  }
  fraud_rules: { id: string; rule: string; needs: string[]; runnable: boolean; hits?: number }[]
  fraud_alerts?: FraudAlert[]
  summary?: {
    total_exposure_azn: number
    active_exposure_azn?: number
    held_exposure_azn?: number
    holds_count?: number
    exceptions_count?: number
    critical_count: number
    high_count: number
    medium_count: number
    deliveries_count: number
    measurements_count: number
    invoices_count: number
    invoices_total_azn: number
  }
}

const COLUMNS: Record<string, [string, string][]> = {
  drawings: [
    ['file', 'File'],
    ['kind', 'Format'],
    ['discipline', 'Discipline'],
    ['building', 'Building'],
    ['order', 'Order'],
    ['sheets', 'Sheets'],
    ['version', 'DWG Ver'],
  ],
  contract_bill: [
    ['id', 'BOQ Code'],
    ['description', 'Description'],
    ['unit', 'Unit'],
    ['qty', 'Contract Qty'],
    ['rate', 'Rate (AZN)'],
    ['amount', 'Total (AZN)'],
    ['building', 'Building'],
  ],
  materials: [
    ['rec_id', 'Receipt №'],
    ['date', 'Date'],
    ['waybill', 'Waybill'],
    ['supplier', 'Supplier'],
    ['material', 'Material'],
    ['boq_line', 'BOQ Line'],
    ['qty', 'Delivered'],
    ['contract_qty', 'BOQ Limit'],
    ['unit', 'Unit'],
    ['status', 'Audit Status'],
  ],
  measurements: [
    ['cert_no', 'Forma-2 №'],
    ['period', 'Period'],
    ['boq_line', 'BOQ Line'],
    ['work', 'Certified Work'],
    ['building', 'Building'],
    ['measured_qty', 'Certified Qty'],
    ['contract_qty', 'Contract Qty'],
    ['unit', 'Unit'],
    ['inspector', 'Inspector'],
    ['status', 'Status'],
  ],
  invoices: [
    ['eqaime', 'e-Qaimə №'],
    ['date', 'Date'],
    ['vendor', 'Contractor / Vendor'],
    ['boq_line', 'BOQ Line'],
    ['billed_qty', 'Billed Qty'],
    ['unit', 'Unit'],
    ['billed_rate', 'Billed Rate'],
    ['contract_rate', 'BOQ Rate'],
    ['amount', 'Amount (AZN)'],
    ['status', 'Payment Gate'],
  ],
}

const NUMERIC = [
  'qty',
  'contract_qty',
  'measured_qty',
  'billed_qty',
  'rate',
  'billed_rate',
  'contract_rate',
  'amount',
  'sheets',
]

const KIND: Record<string, string> = { drawing_cad: 'DWG', drawing_pdf: 'PDF', drawing_scan: 'Scan' }

function statusBadge(v: string) {
  const low = v.toLowerCase()
  if (low.includes('hold') || low.includes('duplicate') || low.includes('over-delivery')) {
    return <span className="tag bad">{v}</span>
  }
  if (low.includes('waste') || low.includes('review')) {
    return <span className="tag warn">{v}</span>
  }
  if (low.includes('verified') || low.includes('certified') || low.includes('paid') || low.includes('approved')) {
    return <span className="tag ok">{v}</span>
  }
  return <span className="tag">{v}</span>
}

export function Operations({ route }: { route: Route }) {
  const { data, error } = useData<Ops>('/api/operations')
  const [q, setQ] = useState('')
  const [sevFilter, setSevFilter] = useState<'all' | 'critical' | 'high' | 'medium'>('all')
  const [draftAlert, setDraftAlert] = useState<{ id: string; action: 'hold' | 'exception' } | null>(null)
  const [who, setWho] = useState(() => {
    try {
      return localStorage.getItem('azboq.author') || ''
    } catch {
      return ''
    }
  })
  const [why, setWhy] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const bname = useBuildingName()

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="registers" />

  const id = route.parts[1] || 'fraud'
  const alerts = data.fraud_alerts || []
  const sum = data.summary

  /* ── 1. Master Codes View (#/ops/codes) ─────────────── */
  if (id === 'codes') {
    return (
      <div className="grid3">
        <Card title={`BOQ Sections · ${data.codes.sections.length}`} sub="Standardized WBS / BOQ section breakdown">
          <div className="rows" style={{ maxHeight: 'calc(100vh - 220px)' }}>
            {data.codes.sections.map((s) => (
              <a
                key={s.code}
                className="row"
                style={{ gridTemplateColumns: '54px minmax(0,1fr)' }}
                href={`#/bill?q=${encodeURIComponent(s.code)}`}
              >
                <span className="code">{s.code}</span>
                <span style={{ minWidth: 0 }}>
                  <T az={s.title} />
                  <span className="d block">
                    {bname(s.building)} · {tradeName(s.trade)}
                  </span>
                </span>
              </a>
            ))}
          </div>
        </Card>

        <Card title={`Units of Measure · ${data.codes.units.length}`} sub="Exact unit tokens used in client BOQ">
          <div className="rows">
            {data.codes.units.map((u) => (
              <div key={u.written} className="row" style={{ gridTemplateColumns: 'minmax(0,1fr) auto', minHeight: 42 }}>
                <span lang="az" className="mono font-medium">{u.written}</span>
                <span className="num muted text-[12px]">{fmt(u.lines)} lines</span>
              </div>
            ))}
          </div>
        </Card>

        <div className="stack">
          <Card title={`Buildings & Structures · ${data.codes.buildings.length}`}>
            <div className="card-body flex flex-wrap gap-1.5">
              {data.codes.buildings.map((b) => (
                <button key={b} type="button" className="chip solo" onClick={() => go('bill', { building: b })}>
                  {bname(b)}
                </button>
              ))}
            </div>
          </Card>

          <Card title={`Engineering Trades · ${data.codes.trades.length}`}>
            <div className="card-body flex flex-wrap gap-1.5">
              {data.codes.trades.map((t) => (
                <span key={t} className="pill">{tradeName(t)}</span>
              ))}
            </div>
          </Card>
        </div>
      </div>
    )
  }

  /* ── 2. Fraud & Process Violation Workspace (#/ops/fraud) ── */
  if (id === 'fraud') {
    const shownAlerts = alerts.filter(
      (a) => (sevFilter === 'all' || a.severity === sevFilter) && matches(q, a.title, a.rule_id, a.boq_line, a.summary, a.left_sub, a.right_sub),
    )
    const activeExposure =
      sum?.active_exposure_azn ??
      alerts.filter((a) => a.decision?.action !== 'exception').reduce((acc, a) => acc + a.exposure_azn, 0)

    return (
      <>
        <div className="strip">
          <div className="kpi bad">
            <div className="k"><ShieldWarning size={15} /> Flagged Financial Exposure</div>
            <div className="v"><AnimatedNumber value={activeExposure} decimals={2} suffix="AZN" /></div>
            <div className="s">{alerts.length} cross-register violations detected</div>
          </div>

          <button type="button" className="kpi warn" onClick={() => setSevFilter('critical')}>
            <div className="k"><Warning size={15} /> Critical Payment Holds</div>
            <div className="v"><AnimatedNumber value={sum?.critical_count || 0} /></div>
            <div className="s">Plus {sum?.high_count || 0} high & {sum?.medium_count || 0} medium flags</div>
          </button>

          <button type="button" className="kpi" onClick={() => go('ops/invoices')}>
            <div className="k"><Invoice size={15} /> Monitored e-Qaimə Value</div>
            <div className="v"><AnimatedNumber value={sum?.invoices_total_azn || 0} decimals={0} suffix="AZN" /></div>
            <div className="s">{sum?.invoices_count || 0} invoices · {sum?.measurements_count || 0} Forma-2 acts</div>
          </button>

          <button type="button" className="kpi" onClick={() => go('ops/materials')}>
            <div className="k"><Package size={15} /> Material Receipts Audited</div>
            <div className="v"><AnimatedNumber value={sum?.deliveries_count || 0} /></div>
            <div className="s">Cross-checked against BOQ & weighbridge logs</div>
          </button>
        </div>

        <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(300px, 360px)' }}>
          <Card style={{ overflow: 'hidden' }}>
            <div className="toolbar">
              <SegmentedTabs<'all' | 'critical' | 'high' | 'medium'>
                id="fraud-sev"
                value={sevFilter}
                onChange={setSevFilter}
                options={[
                  { value: 'all', label: 'All Alerts', count: alerts.length },
                  { value: 'critical', label: 'Critical', count: sum?.critical_count || 0, tone: 'bad' },
                  { value: 'high', label: 'High', count: sum?.high_count || 0, tone: 'warn' },
                  { value: 'medium', label: 'Medium', count: sum?.medium_count || 0 },
                ]}
              />
              <label className="field ml-auto">
                <Search size={14} />
                <input
                  placeholder="Filter by e-Qaimə, waybill, vendor, or BOQ code…"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
                {q ? (
                  <button type="button" onClick={() => setQ('')} className="clear" aria-label="Clear">
                    <X size={13} />
                  </button>
                ) : null}
              </label>
            </div>

            <div className="divide-y divide-[var(--line)]">
              {shownAlerts.map((a) => {
                const dec = a.decision
                const sevCls = a.severity === 'critical' ? 'bad' : 'warn'
                const isDrafting = draftAlert?.id === a.id
                return (
                  <div key={a.id} className="p-4 transition-colors hover:bg-[var(--paper-2)]/60">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`tag ${sevCls}`}>{a.rule_id} · {a.severity.toUpperCase()}</span>
                          <span className="pill">{bname(a.building)}</span>
                          <a href={href('bill', { line: a.boq_line })} className="pill hover:border-[var(--accent)]">
                            BOQ {a.boq_line} →
                          </a>
                          {dec?.action === 'hold' ? (
                            <span className="tag bad" title={`${dec.author}: ${dec.reason}`}>
                              Payment Frozen · {dec.author}
                            </span>
                          ) : null}
                          {dec?.action === 'exception' ? (
                            <span className="tag ok" title={`${dec.author}: ${dec.reason}`}>
                              Exception Logged · {dec.author}
                            </span>
                          ) : null}
                        </div>
                        <h3 className="mt-2 mb-0.5 text-[14.5px] font-semibold text-[var(--ink)]">{a.title}</h3>
                        <p className="m-0 text-[12.5px] text-[var(--muted)]">{a.summary}</p>
                        {dec ? (
                          <div className="mt-1.5 text-[12px] text-[var(--ink-2)]">
                            <b>Audit trail:</b> {dec.author} ({new Date(dec.created_at * 1000).toLocaleString()}) — “{dec.reason}”
                          </div>
                        ) : null}
                      </div>

                      <div className="text-right">
                        <div className="text-[11px] font-medium uppercase tracking-[0.05em] text-[var(--muted)]">
                          Flagged Exposure
                        </div>
                        <div className="font-mono text-[18px] font-semibold text-[var(--bad-text)] num">
                          {money(a.exposure_azn)}
                        </div>
                        <div className="font-mono text-[11.5px] text-[var(--muted)]">{a.variance}</div>
                      </div>
                    </div>

                    {/* DUKU Two-Sided Comparison Strip */}
                    <div className="relative mt-3">
                      <div className="vs m-0!">
                        <div className="bad">
                          <small>{a.left_label}</small>
                          <b>{a.left_val}</b>
                          <span>{a.left_sub}</span>
                        </div>
                        <div className="ok">
                          <small>{a.right_label}</small>
                          <b>{a.right_val}</b>
                          <span>{a.right_sub}</span>
                        </div>
                      </div>
                      <span
                        className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 grid h-6 w-6 place-items-center rounded-full border border-[var(--line-2)] bg-[var(--paper)] text-[var(--muted)] shadow-xs"
                        aria-hidden
                      >
                        <ArrowsLeftRight size={12} />
                      </span>
                    </div>

                    {isDrafting ? (
                      <form
                        className="box edit mt-3"
                        onSubmit={async (e) => {
                          e.preventDefault()
                          if (!who.trim() || !why.trim()) {
                            toast.error('Enter your name and audit justification.')
                            return
                          }
                          setBusyId(a.id)
                          try {
                            try {
                              localStorage.setItem('azboq.author', who.trim())
                            } catch {
                              /* ignore */
                            }
                            await postJSON('/api/review', {
                              target_kind: 'fraud',
                              target_id: a.id,
                              action: draftAlert.action,
                              author: who.trim(),
                              reason: why.trim(),
                              payload: { exposure_azn: a.exposure_azn, rule_id: a.rule_id },
                            })
                            clearCache('/api/operations')
                            setDraftAlert(null)
                            setWhy('')
                            toast.success(
                              draftAlert.action === 'hold'
                                ? `Persisted payment hold on ${a.id} (${money(a.exposure_azn)})`
                                : `Persisted audit exception on ${a.id}`,
                            )
                          } catch (err: any) {
                            toast.error(String(err?.message || err))
                          } finally {
                            setBusyId(null)
                          }
                        }}
                      >
                        <small>
                          {draftAlert.action === 'hold'
                            ? `Enforce Payment Hold · ${a.left_label}`
                            : `Log Approved Audit Exception · ${a.left_label}`}
                        </small>
                        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 mt-2">
                          <div className="form-field mt-0!">
                            <label>Auditor / Manager Name</label>
                            <input
                              value={who}
                              onChange={(e) => setWho(e.target.value)}
                              placeholder="e.g., G. Feyzullayev"
                              autoFocus
                            />
                          </div>
                          <div className="form-field mt-0!">
                            <label>Audit Justification</label>
                            <input
                              value={why}
                              onChange={(e) => setWhy(e.target.value)}
                              placeholder={
                                draftAlert.action === 'hold'
                                  ? 'Freeze payment pending site re-measurement'
                                  : 'Approved via signed Variation Order №04'
                              }
                            />
                          </div>
                        </div>
                        <div className="acts">
                          <button type="submit" className="btn sm" disabled={busyId === a.id}>
                            <Check size={13} />{' '}
                            {busyId === a.id
                              ? 'Saving to SQLite…'
                              : draftAlert.action === 'hold'
                                ? 'Confirm Payment Hold'
                                : 'Save Exception'}
                          </button>
                          <button type="button" className="btn outline sm" onClick={() => setDraftAlert(null)}>
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : null}

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <a className="btn outline sm" href={href(`ops/${a.register}`)}>
                          Open {a.register === 'invoices' ? 'e-Qaimə Register' : 'Material Receipts'} →
                        </a>
                        <a className="btn outline sm" href={href('bill', { line: a.boq_line })}>
                          Inspect Drawing Evidence
                        </a>
                      </div>

                      <div className="flex items-center gap-2">
                        {dec ? (
                          <button
                            type="button"
                            className="btn outline sm"
                            disabled={busyId === a.id}
                            onClick={async () => {
                              const author = who.trim() || dec.author
                              setBusyId(a.id)
                              try {
                                await delJSON(`/api/review/${dec.id}`, {
                                  author,
                                  reason: 'Cleared fraud decision',
                                })
                                clearCache('/api/operations')
                                toast.success(`Cleared decision on ${a.id}`)
                              } catch (err: any) {
                                toast.error(String(err?.message || err))
                              } finally {
                                setBusyId(null)
                              }
                            }}
                          >
                            <Undo size={13} /> Clear Decision
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="btn outline sm"
                          onClick={() => {
                            setDraftAlert({ id: a.id, action: 'exception' })
                            setWhy('')
                          }}
                        >
                          <Check size={13} /> Log Exception
                        </button>
                        <button
                          type="button"
                          className="btn sm"
                          onClick={() => {
                            setDraftAlert({ id: a.id, action: 'hold' })
                            setWhy('')
                          }}
                        >
                          <ShieldWarning size={13} /> Enforce Payment Hold
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}

              {!shownAlerts.length ? (
                <Empty icon={<ShieldCheck size={18} />} title="No alerts match filter">
                  Switch severity filter or clear your search term.
                </Empty>
              ) : null}
            </div>
          </Card>

          <div className="stack">
            <Card title="Active Fraud & Control Rules" sub="Continuous cross-register verification engine">
              <div className="rows">
                {data.fraud_rules.map((f) => (
                  <div key={f.id} className="row" style={{ gridTemplateColumns: '28px minmax(0, 1fr) auto' }}>
                    <span className={`well sm ${f.hits ? 'bad' : 'ok'}`}>
                      {f.hits ? <ShieldWarning size={14} /> : <CheckCircle size={14} />}
                    </span>
                    <span style={{ minWidth: 0 }}>
                      <b className="font-mono text-[12px] mr-1.5">{f.id}</b>
                      <span className="font-medium text-[var(--ink)]">{f.rule}</span>
                      <span className="d block">Inputs: {f.needs.join(' + ')}</span>
                    </span>
                    <span className={`tag ${f.hits ? 'bad' : 'ok'}`}>
                      {f.hits ? `${f.hits} hit${f.hits === 1 ? '' : 's'}` : 'Clean'}
                    </span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Departmental Scope Note" sub="Simulated execution records on real Hadrut BOQ">
              <div className="card-body pt-2! text-[12.5px] text-[var(--muted)] leading-relaxed">
                Contract BOQ (<span className="mono">PJ_12</span>) and Drawing Register (<span className="mono">PJ_04</span>) come directly from the client’s Hadrut Order 9335 files. Material Receiving (<span className="mono">PJ_08</span>), Forma-2 (<span className="mono">PJ_12</span>), and e-Qaimə (<span className="mono">PJ_13</span>) contain cross-linked operational records demonstrating live <span className="mono">F1–F5</span> anomaly detection.
              </div>
            </Card>
          </div>
        </div>
      </>
    )
  }

  /* ── 3. Departmental Register Views (#/ops/materials, measurements, invoices, drawings, contract_bill) ── */
  const reg = data.registers.find((r) => r.id === id)
  if (!reg) return <ErrorBox error={`Register "${id}" does not exist.`} />

  const cols = COLUMNS[id] || (reg.rows[0] ? Object.keys(reg.rows[0]).map((k) => [k, k] as [string, string]) : [])
  const rows = reg.rows.filter((r) =>
    matches(q, ...Object.values(r).map((v) => (v === null || v === undefined ? '' : String(v)))),
  )
  const rules = data.fraud_rules.filter((f) => f.needs.includes(id))
  const relatedAlerts = alerts.filter((a) => a.register === id)

  const cellOf = (k: string, r: Record<string, any>) => {
    const v = r[k]
    if (k === 'description') return <T az={v} />
    if (k === 'building') return bname(v)
    if (k === 'kind') return <span className="pill">{KIND[v] || v}</span>
    if (k === 'boq_line') {
      return (
        <a
          href={href('bill', { line: v })}
          onClick={(e) => e.stopPropagation()}
          className="pill hover:border-[var(--accent)]"
        >
          {v} →
        </a>
      )
    }
    if (k === 'status') return statusBadge(String(v || ''))
    if (k === 'amount' || k === 'rate' || k === 'billed_rate' || k === 'contract_rate') return money(v)
    if (typeof v === 'number') return fmt(v, 3)
    return v ?? <span className="faint">—</span>
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <SegmentedTabs<string>
          id="ops-reg-switch"
          value={id}
          onChange={(next) => go(`ops/${next}`)}
          options={[
            { value: 'materials', label: 'Material Receiving', count: data.registers.find((r) => r.id === 'materials')?.rows.length },
            { value: 'measurements', label: 'Forma-2 Measurements', count: data.registers.find((r) => r.id === 'measurements')?.rows.length },
            { value: 'invoices', label: 'Invoices (e-Qaimə)', count: data.registers.find((r) => r.id === 'invoices')?.rows.length },
            { value: 'drawings', label: 'Drawing Register', count: data.registers.find((r) => r.id === 'drawings')?.rows.length },
            { value: 'contract_bill', label: 'Contract BOQ', count: fmt(data.registers.find((r) => r.id === 'contract_bill')?.rows.length || 0) },
          ]}
        />
        {reg.simulated ? (
          <span className="tag info ml-auto" title="Simulated site execution records linked to real Hadrut Order 9335 BOQ lines">
            <Gauge size={12} /> Simulated Site Execution Data
          </span>
        ) : (
          <span className="tag ok ml-auto">
            <CheckCircle size={12} /> Extracted from Client Package
          </span>
        )}
      </div>

      <div className="grid2" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(290px, 350px)' }}>
        <Card
          title={<Label en={reg.title} az={reg.title_az} />}
          sub={
            <>
              Workbook <span className="mono">{reg.workbook}</span> · {fmt(reg.rows.length)} records
            </>
          }
          right={
            reg.rows.length ? (
              <label className="field min-w-[210px]!">
                <Search size={14} />
                <input placeholder="Filter register…" value={q} onChange={(e) => setQ(e.target.value)} />
                {q ? (
                  <button type="button" onClick={() => setQ('')} aria-label="Clear search" className="clear">
                    <X size={13} />
                  </button>
                ) : null}
              </label>
            ) : null
          }
          style={{ overflow: 'hidden' }}
        >
          {reg.rows.length ? (
            <div className="scroll" style={{ maxHeight: 'calc(100vh - 260px)' }}>
              <table>
                <thead>
                  <tr>
                    {cols.map(([k, label]) => (
                      <th key={k} className={NUMERIC.includes(k) ? 'r' : ''}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 600).map((r, i) => (
                    <tr
                      key={i}
                      className={id === 'contract_bill' ? 'click' : ''}
                      onClick={() => id === 'contract_bill' && go('bill', { line: r.id })}
                    >
                      {cols.map(([k]) => (
                        <td
                          key={k}
                          className={
                            NUMERIC.includes(k)
                              ? 'r num whitespace-nowrap'
                              : k === 'description' || k === 'material' || k === 'work'
                                ? 'desc'
                                : k === 'id' || k === 'rec_id' || k === 'cert_no' || k === 'eqaime' || k === 'waybill'
                                  ? 'code'
                                  : ''
                          }
                          lang={k === 'file' ? 'az' : undefined}
                        >
                          {cellOf(k, r)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 600 ? (
                <div className="empty-state">Showing 600 of {fmt(rows.length)} records; filter above to narrow.</div>
              ) : null}
              {!rows.length ? <Empty icon={<Search size={18} />} title="No matching records" /> : null}
            </div>
          ) : (
            <Empty title="Register is empty">{reg.empty_note}</Empty>
          )}
        </Card>

        <div className="stack">
          {relatedAlerts.length ? (
            <Card
              title={`Active Flags on This Register · ${relatedAlerts.length}`}
              right={
                <a href={href('ops/fraud')} className="text-[12px]">
                  All alerts →
                </a>
              }
            >
              <div className="rows">
                {relatedAlerts.map((a) => (
                  <a key={a.id} className="row" href={href('ops/fraud')}>
                    <span className={`well sm ${a.severity === 'critical' ? 'bad' : 'warn'}`}>
                      <ShieldWarning size={14} />
                    </span>
                    <span style={{ minWidth: 0 }}>
                      <b className="font-mono text-[11.5px] mr-1">{a.rule_id}</b>
                      <span className="font-medium text-[var(--ink)]">{a.title}</span>
                      <span className="d block">{a.variance} · {money(a.exposure_azn)}</span>
                    </span>
                  </a>
                ))}
              </div>
            </Card>
          ) : null}

          <Card title="Control Rules Using This Register" sub="Automated cross-department checks">
            <div className="rows">
              {rules.map((f) => (
                <div key={f.id} className="row" style={{ gridTemplateColumns: '28px minmax(0,1fr) auto' }}>
                  <span className={`well sm ${f.hits ? 'bad' : 'ok'}`}>
                    {f.hits ? <ShieldWarning size={14} /> : <CheckCircle size={14} />}
                  </span>
                  <span style={{ minWidth: 0 }}>
                    <b className="font-mono text-[11.5px] mr-1">{f.id}</b>
                    <span>{f.rule}</span>
                    <span className="d block">Joins: {f.needs.join(' + ')}</span>
                  </span>
                  <span className={`tag ${f.hits ? 'bad' : 'ok'}`}>
                    {f.hits ? `${f.hits} flagged` : 'Active'}
                  </span>
                </div>
              ))}
              {!rules.length ? (
                <div className="card-body muted text-[12.5px]">Reference register supporting master BOQ validation.</div>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
