import { useState } from 'react'
import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import {
  ArrowRight,
  ArrowUpRight,
  ChartBar,
  Check,
  CheckCircle,
  GitDiff,
  Prohibit,
  Receipt,
  Ruler,
  ShieldCheck,
  ShieldWarning,
  Stack,
  Warning,
  type Icon,
} from '../icons'
import { go, href } from '../router'
import {
  AnimatedNumber,
  Card,
  ErrorBox,
  Label,
  LINE_STATUS,
  Loading,
  pct,
  SegmentedTabs,
  STATUS_COLOR,
  STATUS_ORDER,
  useBuildingName,
} from '../ui'

type Summary = {
  counts: Record<string, number>
  drawings_not_read: number
  drawings_total: number
  inputs_missing: number
  reader_disagreements: number
  conflicts: number
  review_items: number
  bill: { lines: number; sections: number; line_sum: number; chain: Record<string, number | string>; totals: Record<string, number> }
  value_by_building: { building: string; value: number; checked: number; lines: number; checked_lines: number }[]
  attention: { kind: string; id: string; label: string; label_az: string; detail: string }[]
}
type TakeoffLite = { items: { value: { status: string } }[]; gate: { pass: boolean } }
type Exports = { files: { name: string }[] }
type FraudAlert = {
  id: string
  rule_id: string
  severity: 'critical' | 'high' | 'medium'
  title: string
  building: string
  exposure_azn: number
  summary: string
  register: string
}
type OpsData = {
  fraud_alerts?: FraudAlert[]
  summary?: { total_exposure_azn: number; critical_count: number }
}

type Step = { n: string; to: string; icon: Icon; title: string; v: string; of?: string; s: string; cls: '' | 'ok' | 'warn' | 'bad' }

const KIND: Record<string, [string, string, Icon]> = {
  different: ['bad', 'Contradicts', Warning],
  blocked: ['warn', 'Blocked', Prohibit],
  conflict: ['warn', 'Conflict', GitDiff],
}

export function Home() {
  const { data, error } = useData<Summary>('/api/summary')
  const take = useData<TakeoffLite>('/api/takeoff')
  const ex = useData<Exports>('/api/exports')
  const ops = useData<OpsData>('/api/operations')
  const [queueTab, setQueueTab] = useState<'audit' | 'fraud'>('audit')
  const bname = useBuildingName()

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the summary" />

  const c = data.counts
  const checked = (c.matched || 0) + (c.printed || 0) + (c.derived || 0)
  const person = (c.review || 0) + (c.blocked || 0)
  const chain = data.bill.chain as Record<string, number>
  const header = data.bill.totals.contract_price_c5
  const reproduced = Math.abs(chain.total - header) < 0.01
  const maxValue = Math.max(...data.value_by_building.map((b) => b.value), 1)
  const valueAll = data.value_by_building.reduce((s, b) => s + b.value, 0)
  const valueChecked = data.value_by_building.reduce((s, b) => s + b.checked, 0)
  const read = data.drawings_total - data.drawings_not_read
  const items = take.data?.items || []
  const measured = items.filter((i) => i.value.status !== 'blocked').length

  const fraudAlerts = ops.data?.fraud_alerts || []
  const fraudExposure = ops.data?.summary?.total_exposure_azn ?? fraudAlerts.reduce((acc, a) => acc + (a.exposure_azn || 0), 0)

  const steps: Step[] = [
    {
      n: '01',
      to: href('drawings'),
      icon: Stack,
      title: 'Drawings ingested',
      v: String(read),
      of: `/ ${data.drawings_total}`,
      s: data.reader_disagreements ? `${data.reader_disagreements} DWGs flagged for dual-reader review` : 'ODA & LibreDWG agree on all DWGs',
      cls: data.reader_disagreements ? 'warn' : 'ok',
    },
    {
      n: '02',
      to: href('takeoff'),
      icon: Ruler,
      title: 'Quantities extracted',
      v: take.data ? String(measured) : '…',
      of: take.data ? `/ ${items.length}` : undefined,
      s: take.data ? `Depot geometry gate ${take.data.gate.pass ? 'passed' : 'failed'} · ${data.inputs_missing} missing inputs` : 'Checking takeoff…',
      cls: take.data ? (take.data.gate.pass ? (data.inputs_missing ? 'warn' : 'ok') : 'bad') : '',
    },
    {
      n: '03',
      to: href('bill', { status: 'checked' }),
      icon: Receipt,
      title: 'BOQ lines verified',
      v: fmt(checked),
      of: `/ ${fmt(data.bill.lines)}`,
      s: `${c.different || 0} contradict drawings · ${fmt(person)} in review`,
      cls: c.different ? 'bad' : 'ok',
    },
    {
      n: '04',
      to: href('report'),
      icon: ChartBar,
      title: 'Audit handover pack',
      v: ex.data ? String(ex.data.files.length) : '…',
      of: ex.data ? 'files' : undefined,
      s: 'Checked BOQ, discrepancy report & generated BOQ',
      cls: ex.data ? (ex.data.files.length ? 'ok' : 'warn') : '',
    },
  ]

  return (
    <>
      {/* Clean Executive Header (One Primary CTA per Squint Test) */}
      <div className="flex flex-wrap items-end justify-between gap-4 pb-1">
        <div>
          <div className="mb-1 flex items-center gap-2 text-[11.5px] font-medium text-[var(--muted)]">
            <span className="inline-flex items-center gap-1.5 rounded-md border border-[var(--line-2)] bg-[var(--paper)] px-2 py-0.5 font-mono text-[11px] text-[var(--ink-2)]">
              ORDER 9335
            </span>
            <span>Hadrut 4-Bay Fire Protection Depot · Xocavənd</span>
          </div>
          <h1 className="m-0 text-[22px] font-semibold tracking-[-0.025em] text-[var(--ink)]">
            {c.different ? (
              <>
                <span className="text-[var(--bad-text)]">{c.different} BOQ lines contradict</span> the client’s own drawings
              </>
            ) : (
              'All verified BOQ lines match the drawings'
            )}
          </h1>
          <p className="mt-1 mb-0 max-w-[68ch] text-[13px] text-[var(--muted)]">
            {fmt(checked)} of {fmt(data.bill.lines)} contract lines are backed by CAD/PDF evidence ({pct(valueChecked, valueAll)} of line value), {fmt(person)} await human review, and {fraudAlerts.length} site operations anomalies are flagged.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a className="btn outline" href={href('bill')}>
            <Receipt size={14} /> Reconcile BOQ
          </a>
          <a className="btn outline" href={href('ops/fraud')}>
            <ShieldWarning size={14} /> Fraud Monitor {fraudAlerts.length ? <span className="ml-0.5 font-mono text-[11px] text-[var(--bad-text)]">({fraudAlerts.length})</span> : null}
          </a>
          <a className="btn" href={href('report', { tab: 'different' })}>
            <Warning size={14} /> Review {c.different || 0} Discrepancies
          </a>
        </div>
      </div>

      {/* Top 4 Executive KPI Cards (shadcn-admin + AnimatedNumber) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <a href={href('bill')} className="kpi">
          <ArrowUpRight size={14} className="go" />
          <div className="k">
            <ShieldCheck size={15} /> Contract Sum (With VAT)
          </div>
          <div className="v">
            <AnimatedNumber value={header} decimals={2} suffix="AZN" />
          </div>
          <div className="s flex items-center gap-1.5">
            <span className={`tag ${reproduced ? 'ok' : 'bad'}`}>{reproduced ? 'Reproduced to 0.00 AZN' : 'Header mismatch'}</span>
          </div>
        </a>

        <button type="button" className="kpi" onClick={() => go('bill', { status: 'checked' })}>
          <ArrowUpRight size={14} className="go" />
          <div className="k">
            <CheckCircle size={15} /> Drawing-Backed Value
          </div>
          <div className="v">
            <AnimatedNumber value={valueChecked} decimals={0} suffix="AZN" />
          </div>
          <div className="s">
            <b className="font-mono text-[var(--ok-text)]">{pct(valueChecked, valueAll)}</b> of {money(valueAll)} · {fmt(checked)} lines
          </div>
        </button>

        <button type="button" className={`kpi ${c.different ? 'bad' : ''}`} onClick={() => go('report', { tab: 'different' })}>
          <ArrowUpRight size={14} className="go" />
          <div className="k">
            <Warning size={15} /> Drawing Contradictions
          </div>
          <div className="v">
            <AnimatedNumber value={c.different || 0} suffix="lines" />
          </div>
          <div className="s">
            Plus {fmt(person)} lines needing human review · {data.conflicts} doc conflicts
          </div>
        </button>

        <button type="button" className={`kpi ${fraudAlerts.length ? 'warn' : ''}`} onClick={() => go('ops/fraud')}>
          <ArrowUpRight size={14} className="go" />
          <div className="k">
            <ShieldWarning size={15} /> Operations & Fraud Exposure
          </div>
          <div className="v">
            <AnimatedNumber value={fraudExposure} decimals={0} suffix="AZN" />
          </div>
          <div className="s">
            {fraudAlerts.length ? `${fraudAlerts.length} active violations across PO, Forma-2 & e-Qaimə` : 'Monitoring material, measurement & invoice registers'}
          </div>
        </button>
      </div>

      {/* Tremor-Style Segmented BOQ Distribution Bar */}
      <Card
        title="BOQ Verification Breakdown (2,175 Lines)"
        sub="Click any segment or legend badge to inspect those lines in the reconciliation table"
        right={
          <a href={href('bill')} className="inline-flex items-center gap-1 text-[12.5px] font-medium">
            Open full BOQ <ArrowRight size={13} />
          </a>
        }
      >
        <div className="card-body">
          <div className="spectrum" role="img" aria-label="Bill lines by check result">
            {STATUS_ORDER.filter((k) => c[k]).map((k) => (
              <i
                key={k}
                title={`${LINE_STATUS[k].label}: ${fmt(c[k])} lines (${pct(c[k], data.bill.lines)})`}
                style={{ flex: c[k], background: STATUS_COLOR[k], cursor: 'pointer' }}
                onClick={() => go('bill', { status: k })}
              />
            ))}
          </div>
          <div className="legend">
            {STATUS_ORDER.map((k) => (
              <button key={k} type="button" onClick={() => go('bill', { status: k })} title={LINE_STATUS[k].hint}>
                <span className="dot" style={{ background: STATUS_COLOR[k] }} />
                <span>{LINE_STATUS[k].label}</span>
                <b>{fmt(c[k] || 0)}</b>
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Connected 4-Stage Pipeline Track (Law of Uniform Connectedness) */}
      <Card title="Verification Pipeline" sub="End-to-end audit trace from raw CAD/PDF package to signed handover exports">
        <div className="stepper">
          {steps.map((st) => {
            const Ico = st.icon
            return (
              <a key={st.n} className="step" href={st.to}>
                <span className="rail-line">
                  <span className={`node ${st.cls}`}>{st.cls === 'ok' ? <Check size={13} weight="bold" /> : st.n}</span>
                  <span className={`track ${st.cls === 'ok' ? 'ok' : ''}`} />
                </span>
                <span className="idx">STAGE {st.n}</span>
                <span className="ttl">
                  <Ico size={14} /> {st.title}
                </span>
                <span className="v">
                  {st.v} {st.of ? <small>{st.of}</small> : null}
                </span>
                <span className="s">{st.s}</span>
              </a>
            )
          })}
        </div>
      </Card>

      {/* Bottom 2-Column Executive Grid */}
      <div className="grid2">
        <Card
          title="Needs Attention Queue"
          sub="Prioritized drawing discrepancies, document conflicts, and operational fraud alerts"
          right={
            <SegmentedTabs<'audit' | 'fraud'>
              id="home-queue"
              size="sm"
              value={queueTab}
              onChange={setQueueTab}
              options={[
                { value: 'audit', label: 'BOQ Audit', count: data.attention.length + 1, tone: 'bad' },
                { value: 'fraud', label: 'Fraud Flags', count: fraudAlerts.length, tone: 'warn' },
              ]}
            />
          }
        >
          {queueTab === 'audit' ? (
            <div className="rows" style={{ maxHeight: 440 }}>
              {data.attention.map((a) => {
                const [cls, word, Ico] = KIND[a.kind] || ['muted', a.kind, Warning]
                const link = a.kind === 'different' ? href('bill', { line: a.id }) : href('takeoff', { item: a.id })
                return (
                  <a key={a.kind + a.id} className="row" href={link}>
                    <span className={`well sm ${cls}`}>
                      <Ico size={15} />
                    </span>
                    <span style={{ minWidth: 0 }}>
                      <span className="font-medium text-[var(--ink)]">
                        {a.kind === 'different' ? <T az={a.label_az} /> : <Label en={a.label} az={a.label_az} />}
                      </span>
                      <span className="d" style={{ display: 'block' }}>{a.detail}</span>
                    </span>
                    <span className={`tag ${cls}`}>{word}</span>
                  </a>
                )
              })}
              <a className="row" href={href('conflicts')}>
                <span className="well sm info">
                  <GitDiff size={15} />
                </span>
                <span>
                  <span className="font-medium text-[var(--ink)]">{data.conflicts} cross-document conflicts</span>
                  <span className="d" style={{ display: 'block' }}>
                    Preserved side-by-side (seismic rating, ±0.000 datum, substation voltage) — never silently averaged
                  </span>
                </span>
                <span className="tag info">Review</span>
              </a>
            </div>
          ) : (
            <div className="rows" style={{ maxHeight: 440 }}>
              {fraudAlerts.map((fa) => {
                const cls = fa.severity === 'critical' ? 'bad' : 'warn'
                return (
                  <a key={fa.id} className="row" href={href(`ops/fraud`, { alert: fa.id })}>
                    <span className={`well sm ${cls}`}>
                      <ShieldWarning size={15} />
                    </span>
                    <span style={{ minWidth: 0 }}>
                      <span className="font-medium text-[var(--ink)]">
                        <span className="mono mr-1.5 text-[11.5px] text-[var(--muted)]">{fa.rule_id}</span>
                        {fa.title}
                      </span>
                      <span className="d" style={{ display: 'block' }}>
                        {bname(fa.building)} · {fa.summary}
                      </span>
                    </span>
                    <span className="text-right">
                      <span className={`tag ${cls}`}>{money(fa.exposure_azn)}</span>
                    </span>
                  </a>
                )
              })}
              {!fraudAlerts.length ? (
                <div className="empty-state">No operational fraud flags triggered.</div>
              ) : null}
            </div>
          )}
        </Card>

        <div className="stack">
          <Card
            title="Contract Price Reconstruction"
            sub="Header price rebuilt independently from the 2,175 work lines"
            right={<span className={`tag ${reproduced ? 'ok' : 'bad'}`}>{reproduced ? 'Exact match' : 'Mismatch'}</span>}
          >
            <div className="money">
              <div>
                <span>{fmt(data.bill.lines)} work lines across {data.bill.sections} sections</span>
                <span className="num">{money(data.bill.line_sum)}</span>
              </div>
              <div>
                <span>Temporary buildings & facilities (1.8%)</span>
                <span className="num">+ {money(chain.temporary_1_8)}</span>
              </div>
              <div>
                <span>Unforeseen / contingency allowance (2.0%)</span>
                <span className="num">+ {money(chain.contingency_2)}</span>
              </div>
              <div>
                <span>VAT 18% (after −0.02 workbook rounding)</span>
                <span className="num">+ {money(chain.vat_18)}</span>
              </div>
              <div className="total">
                <span>Contract Header Total (inc. VAT)</span>
                <b>{money(header)}</b>
              </div>
            </div>
          </Card>

          <Card
            title="Contract Value & Verification by Building"
            sub="Emerald fill shows AZN value backed by drawing evidence"
            right={
              <a href={href('coverage')} className="text-[12px]">
                Matrix <ArrowRight size={12} className="inline" />
              </a>
            }
          >
            <div className="bars">
              {data.value_by_building.slice(0, 9).map((b) => (
                <a
                  key={b.building}
                  className="bar"
                  href={href('bill', { building: b.building })}
                  title={`${fmt(b.checked_lines)} of ${fmt(b.lines)} lines backed · ${money(b.checked)} of ${money(b.value)}`}
                >
                  <span>{bname(b.building)}</span>
                  <i>
                    <b style={{ width: `${(b.value / maxValue) * 100}%` }}>
                      <b style={{ width: `${b.value ? (b.checked / b.value) * 100 : 0}%` }} />
                    </b>
                  </i>
                  <span className="n">{(b.value / 1e6).toFixed(2)}M AZN</span>
                </a>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
