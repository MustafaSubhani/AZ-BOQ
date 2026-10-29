import { useData } from '../api'
import { fmt, money } from '../az'
import { T } from '../i18n'
import { go, href } from '../router'
import { Card, ErrorBox, Label, Loading, useBuildingName } from '../ui'

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

const KIND = { different: ['bad', 'Different'], blocked: ['warn', 'Blocked'], conflict: ['warn', 'Conflict'] } as Record<string, [string, string]>

export function Home() {
  const { data, error } = useData<Summary>('/api/summary')
  const bname = useBuildingName()
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the summary" />
  const c = data.counts
  const checked = (c.matched || 0) + (c.printed || 0) + (c.derived || 0)
  const chain = data.bill.chain as Record<string, number>
  const header = data.bill.totals.contract_price_c5
  const reproduced = Math.abs(chain.total - header) < 0.01
  const maxValue = Math.max(...data.value_by_building.map((b) => b.value))

  return (
    <>
      <div className="strip">
        <button className="kpi" onClick={() => go('report', { tab: 'different' })}>
          <div className="k">Different from drawings</div>
          <div className="v num" style={{ color: c.different ? 'var(--bad)' : undefined }}>{c.different || 0}</div>
          <div className="s">Bill lines the drawings contradict</div>
        </button>
        <button className="kpi" onClick={() => go('bill', { status: 'checked' })}>
          <div className="k">Backed by a drawing</div>
          <div className="v num">{fmt(checked)}</div>
          <div className="s">of {fmt(data.bill.lines)} bill lines</div>
        </button>
        <button className="kpi" onClick={() => go('report', { tab: 'review' })}>
          <div className="k">Needs a person</div>
          <div className="v num">{fmt((c.review || 0) + (c.blocked || 0))}</div>
          <div className="s">Weak candidates or a missing input</div>
        </button>
        <button className="kpi" onClick={() => go('coverage')}>
          <div className="k">Not on any drawing</div>
          <div className="v num">{fmt(c.not_found || 0)}</div>
          <div className="s">See which sheets are missing</div>
        </button>
        <button className="kpi" onClick={() => go('drawings', { filter: 'disagree' })}>
          <div className="k">Drawings with a reader doubt</div>
          <div className="v num">{data.reader_disagreements}</div>
          <div className="s">of {data.drawings_total} DWGs; their values go to review</div>
        </button>
      </div>

      <div className="grid2">
        <Card title="Needs attention" right={<a href={href('runlog')}>{data.review_items} pipeline warnings</a>}>
          <div className="rows">
            {data.attention.map((a) => {
              const [cls, word] = KIND[a.kind] || ['muted', a.kind]
              const link = a.kind === 'different' ? href('bill', { line: a.id }) : href('takeoff', { item: a.id })
              return (
                <a key={a.kind + a.id} className="row" href={link} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <span className={`dot ${cls}`} />
                  <span>
                    {a.kind === 'different' ? <T az={a.label_az} /> : <Label en={a.label} az={a.label_az} />}
                    <span className="d" style={{ display: 'block' }}>{a.detail}</span>
                  </span>
                  <span className={`tag ${cls}`}>{word}</span>
                </a>
              )
            })}
            <a className="row" href={href('conflicts')} style={{ textDecoration: 'none', color: 'inherit' }}>
              <span className="dot info" />
              <span>
                {data.conflicts} conflicts between documents
                <span className="d" style={{ display: 'block' }}>Each one lists both sides and a suggestion; nothing is averaged or chosen silently</span>
              </span>
              <span className="tag info">Open</span>
            </a>
          </div>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card title="Contract" right={<span className={`tag ${reproduced ? 'ok' : 'bad'}`}>{reproduced ? 'Header reproduced to the cent' : 'Header does not reproduce'}</span>}>
            <div className="money">
              <div><span>Header price, with VAT</span><b className="num">{money(header)}</b></div>
              <div><span>{fmt(data.bill.lines)} work lines in {data.bill.sections} sections</span><b className="num">{money(data.bill.line_sum)}</b></div>
              <div><span>Temporary buildings 1.8%</span><span className="num">{money(chain.temporary_1_8)}</span></div>
              <div><span>Contingency 2%</span><span className="num">{money(chain.contingency_2)}</span></div>
              <div><span>VAT 18% (after a −0.02 rounding)</span><span className="num">{money(chain.vat_18)}</span></div>
            </div>
          </Card>
          <Card title="Where the line value sits" right={<span className="muted">orange = backed by a drawing</span>}>
            <div className="bars">
              {data.value_by_building.slice(0, 9).map((b) => (
                <a key={b.building} className="bar" href={href('bill', { building: b.building })} style={{ textDecoration: 'none' }} title={`${fmt(b.checked_lines)} of ${fmt(b.lines)} lines backed by a drawing`}>
                  <span>{bname(b.building)}</span>
                  <i>
                    <b style={{ width: `${(b.value / maxValue) * 100}%`, background: 'var(--line-2)', position: 'relative' }}>
                      <b style={{ width: `${b.value ? (b.checked / b.value) * 100 : 0}%`, position: 'absolute', inset: 0 }} />
                    </b>
                  </i>
                  <span className="n num">{(b.value / 1e6).toFixed(2)}m</span>
                </a>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
