import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import { ArrowRight, ArrowUpRight, ChartBar, Check, CheckCircle, Download, GitDiff, Prohibit, Receipt, Ruler, Scan, Stack, UserCheck, Warning, type Icon } from '../icons'
import { go, href } from '../router'
import { Card, ErrorBox, Label, LINE_STATUS, Loading, pct, Ring, STATUS_COLOR, STATUS_ORDER, useBuildingName } from '../ui'

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
type Step = { n: string; to: string; icon: Icon; title: string; v: string; of?: string; s: string; cls: '' | 'ok' | 'warn' | 'bad' }

const KIND: Record<string, [string, string, Icon]> = {
  different: ['bad', 'Different', Warning],
  blocked: ['warn', 'Blocked', Prohibit],
  conflict: ['warn', 'Conflict', GitDiff],
}

export function Home() {
  const { data, error } = useData<Summary>('/api/summary')
  const take = useData<TakeoffLite>('/api/takeoff')
  const ex = useData<Exports>('/api/exports')
  const bname = useBuildingName()
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the summary" />
  const c = data.counts
  const checked = (c.matched || 0) + (c.printed || 0) + (c.derived || 0)
  const person = (c.review || 0) + (c.blocked || 0)
  const chain = data.bill.chain as Record<string, number>
  const header = data.bill.totals.contract_price_c5
  const reproduced = Math.abs(chain.total - header) < 0.01
  const maxValue = Math.max(...data.value_by_building.map((b) => b.value))
  const valueAll = data.value_by_building.reduce((s, b) => s + b.value, 0)
  const valueChecked = data.value_by_building.reduce((s, b) => s + b.checked, 0)
  const read = data.drawings_total - data.drawings_not_read
  const items = take.data?.items || []
  const measured = items.filter((i) => i.value.status !== 'blocked').length

  const steps: Step[] = [
    {
      n: '01', to: href('drawings'), icon: Stack, title: 'Drawings read', v: String(read), of: `/ ${data.drawings_total}`,
      s: data.reader_disagreements ? `${data.reader_disagreements} DWGs with a reader doubt` : 'Both readers agree on every DWG',
      cls: data.reader_disagreements ? 'warn' : 'ok',
    },
    {
      n: '02', to: href('takeoff'), icon: Ruler, title: 'Quantities measured', v: take.data ? String(measured) : '…', of: take.data ? `/ ${items.length}` : undefined,
      s: take.data ? `Depot gate ${take.data.gate.pass ? 'passes' : 'fails'} · ${data.inputs_missing} blocked by a missing input` : 'Loading the takeoff',
      cls: take.data ? (take.data.gate.pass ? (data.inputs_missing ? 'warn' : 'ok') : 'bad') : '',
    },
    {
      n: '03', to: href('bill', { status: 'checked' }), icon: Receipt, title: 'Bill lines backed', v: fmt(checked), of: `/ ${fmt(data.bill.lines)}`,
      s: `${c.different || 0} different · ${fmt(person)} need a person`,
      cls: c.different ? 'bad' : 'ok',
    },
    {
      n: '04', to: href('report'), icon: ChartBar, title: 'Report and exports', v: ex.data ? String(ex.data.files.length) : '…', of: ex.data ? 'files' : undefined,
      s: 'Checked bill, discrepancy report, generated bill',
      cls: ex.data ? (ex.data.files.length ? 'ok' : 'warn') : '',
    },
  ]

  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow accent">Hadrut fire station · order 9335 · Xocavənd</span>
          <h2>
            {c.different ? <em>{c.different} bill {c.different === 1 ? 'line contradicts' : 'lines contradict'}</em> : 'No bill line contradicts'} the client’s own drawings.
          </h2>
          <p>
            {fmt(checked)} of {fmt(data.bill.lines)} lines are backed by a drawing, {fmt(person)} wait for a person, and {fmt(c.not_found || 0)} have no drawing evidence in the package. Every number below opens the sheet it came from.
          </p>
          <div className="acts">
            <a className="btn" href={href('report', { tab: 'different' })}>
              <Warning size={16} /> Open the differences
            </a>
            <a className="btn ghost" href={href('bill')}>
              <Receipt size={16} /> Walk the bill
            </a>
            <a className="btn ghost" href={href('report')}>
              <Download size={16} /> Exports
            </a>
          </div>
        </div>
        <div className="hero-ring">
          <Ring value={valueAll ? valueChecked / valueAll : 0} size={88} stroke={8} label={pct(valueChecked, valueAll, 0)} />
          <div className="lbl">
            <b>Bill value backed</b>
            <span className="fig">{money(valueChecked)}</span>
            <span>of {money(valueAll)} sits on lines a drawing confirms</span>
          </div>
        </div>
      </section>

      <Card title="How the check runs" sub="Four stages, from the client’s package to the files you hand over">
        <div className="stepper">
          {steps.map((st) => {
            const Ico = st.icon
            return (
              <a key={st.n} className="step" href={st.to}>
                <span className="rail-line">
                  <span className={`node ${st.cls}`}>{st.cls === 'ok' ? <Check size={15} weight="bold" /> : st.n}</span>
                  <span className={`track ${st.cls === 'ok' ? 'ok' : ''}`} />
                </span>
                <span className="idx">STEP {st.n}</span>
                <span className="ttl"><Ico size={15} /> {st.title}</span>
                <span className="v">
                  {st.v} {st.of ? <small>{st.of}</small> : null}
                </span>
                <span className="s">{st.s}</span>
              </a>
            )
          })}
        </div>
      </Card>

      <div className="strip">
        <button className={`kpi ${c.different ? 'bad' : ''}`} onClick={() => go('report', { tab: 'different' })}>
          <ArrowUpRight size={15} className="go" />
          <div className="k"><Warning size={15} /> Different from drawings</div>
          <div className="v">{c.different || 0}</div>
          <div className="s">Bill lines the drawings contradict</div>
        </button>
        <button className="kpi" onClick={() => go('bill', { status: 'checked' })}>
          <ArrowUpRight size={15} className="go" />
          <div className="k"><CheckCircle size={15} /> Backed by a drawing</div>
          <div className="v">{fmt(checked)}</div>
          <div className="s">{pct(checked, data.bill.lines)} of {fmt(data.bill.lines)} bill lines</div>
        </button>
        <button className="kpi" onClick={() => go('report', { tab: 'review' })}>
          <ArrowUpRight size={15} className="go" />
          <div className="k"><UserCheck size={15} /> Needs a person</div>
          <div className="v">{fmt(person)}</div>
          <div className="s">Weak candidates or a missing input</div>
        </button>
        <button className="kpi" onClick={() => go('coverage')}>
          <ArrowUpRight size={15} className="go" />
          <div className="k"><Prohibit size={15} /> Not on any drawing</div>
          <div className="v">{fmt(c.not_found || 0)}</div>
          <div className="s">See which sheets are missing</div>
        </button>
        <button className="kpi" onClick={() => go('drawings', { filter: 'disagree' })}>
          <ArrowUpRight size={15} className="go" />
          <div className="k"><Scan size={15} /> Reader doubt</div>
          <div className="v">{data.reader_disagreements}</div>
          <div className="s">of {data.drawings_total} DWGs; their values go to review</div>
        </button>
      </div>

      <Card
        title="Every bill line, by what the drawings say"
        sub="Click a part to open those lines in the bill"
        right={
          <a href={href('bill')} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            Open the bill <ArrowRight size={14} />
          </a>
        }
      >
        <div className="card-body">
          <div className="spectrum" role="img" aria-label="Bill lines by check result">
            {STATUS_ORDER.filter((k) => c[k]).map((k) => (
              <i key={k} title={`${LINE_STATUS[k].label}: ${fmt(c[k])} lines`} style={{ flex: c[k], background: STATUS_COLOR[k], cursor: 'pointer' }} onClick={() => go('bill', { status: k })} />
            ))}
          </div>
          <div className="legend">
            {STATUS_ORDER.map((k) => (
              <button key={k} onClick={() => go('bill', { status: k })} title={LINE_STATUS[k].hint}>
                <span className="dot" style={{ background: STATUS_COLOR[k] }} />
                {LINE_STATUS[k].label} <b>{fmt(c[k] || 0)}</b>
              </button>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid2">
        <Card title="Needs attention" sub="Contradictions, blocked measurements and disagreements" right={<a href={href('runlog')}>{data.review_items} pipeline warnings</a>}>
          <div className="rows">
            {data.attention.map((a) => {
              const [cls, word, Ico] = KIND[a.kind] || ['muted', a.kind, Warning]
              const link = a.kind === 'different' ? href('bill', { line: a.id }) : href('takeoff', { item: a.id })
              return (
                <a key={a.kind + a.id} className="row" href={link}>
                  <span className={`well sm ${cls}`}><Ico size={16} /></span>
                  <span style={{ minWidth: 0 }}>
                    {a.kind === 'different' ? <T az={a.label_az} /> : <Label en={a.label} az={a.label_az} />}
                    <span className="d" style={{ display: 'block' }}>{a.detail}</span>
                  </span>
                  <span className={`tag ${cls}`}>{word}</span>
                </a>
              )
            })}
            <a className="row" href={href('conflicts')}>
              <span className="well sm info"><GitDiff size={16} /></span>
              <span>
                {data.conflicts} conflicts between documents
                <span className="d" style={{ display: 'block' }}>Each one lists both sides and a suggestion; nothing is averaged or chosen silently</span>
              </span>
              <span className="tag info">Open</span>
            </a>
          </div>
        </Card>

        <div className="stack">
          <Card title="Contract" sub="The bill header rebuilt from its own lines" right={<span className={`tag ${reproduced ? 'ok' : 'bad'}`}>{reproduced ? 'Reproduced to the cent' : 'Does not reproduce'}</span>}>
            <div className="money">
              <div><span>{fmt(data.bill.lines)} work lines in {data.bill.sections} sections</span><span className="num">{money(data.bill.line_sum)}</span></div>
              <div><span>Temporary buildings 1.8%</span><span className="num">+ {money(chain.temporary_1_8)}</span></div>
              <div><span>Contingency 2%</span><span className="num">+ {money(chain.contingency_2)}</span></div>
              <div><span>VAT 18% (after a −0.02 rounding)</span><span className="num">+ {money(chain.vat_18)}</span></div>
              <div className="total"><span>Header price, with VAT</span><b>{money(header)}</b></div>
            </div>
          </Card>
          <Card title="Where the line value sits" sub="The orange part is backed by a drawing">
            <div className="bars">
              {data.value_by_building.slice(0, 9).map((b) => (
                <a key={b.building} className="bar" href={href('bill', { building: b.building })} title={`${fmt(b.checked_lines)} of ${fmt(b.lines)} lines backed by a drawing · ${money(b.checked)} of ${money(b.value)}`}>
                  <span>{bname(b.building)}</span>
                  <i>
                    <b style={{ width: `${(b.value / maxValue) * 100}%` }}>
                      <b style={{ width: `${b.value ? (b.checked / b.value) * 100 : 0}%` }} />
                    </b>
                  </i>
                  <span className="n">{(b.value / 1e6).toFixed(2)}m</span>
                </a>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
