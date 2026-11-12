import { useVirtualizer } from '@tanstack/react-virtual'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { clearCache, delJSON, postJSON, useData } from '../api'
import { fmt, matches, money } from '../az'
import { T } from '../i18n'
import { ArrowDown, ArrowsLeftRight, ArrowUp, Check, Search, Undo, X } from '../icons'
import { reasonText } from '../reasons'
import { go, href, type Route } from '../router'
import {
  Card,
  Empty,
  ErrorBox,
  LINE_STATUS,
  Loading,
  SegmentedTabs,
  SourceCard,
  StatusTag,
  targetOf,
  tradeName,
  useBuildingName,
  type Source,
  type Target,
} from '../ui'
import { Viewer } from '../Viewer'

type Line = {
  id: string
  row: number
  section: string
  item: number | string | null
  description: string
  unit_raw: string | null
  unit: string
  unit_known: boolean
  qty: number
  rate: number | null
  amount: number | null
  building: string
  trade: string
  comment: string | null
  check: {
    status: string
    reason: string
    our_qty: number | null
    gap?: number | null
    gap_pct?: number | null
    item?: string
    sources?: Source[]
    candidates?: Source[]
    derived_from?: string
    reviewer?: { kind?: string; delta?: number; value?: number }
    method?: string
    group_total?: number
    engine_qty?: number | null
    engine_reason?: string
    override?: { id: number; expression: string; author: string; reason: string }
    review_reasons?: { code: string; link?: string; citation?: string; rule?: string; note?: string; accepted_by?: string; file?: string }[]
  } | null
}

type Explain = {
  item?: { label_en?: string; formula?: string | null; substituted?: string | null; citation?: string } | null
  inputs: {
    label: string
    value: number | null
    unit: string
    sources: { file?: string; page?: number | null; row?: string | null; col?: string | null; printed?: string | null; is_rule?: boolean; citation?: string | null }[]
  }[]
  printed: { file?: string; page?: number | null; row?: string | null; col?: string | null; printed?: string | null; is_rule?: boolean }[]
}

type Section = { code: string; stored_code: any; row: number; title: string; trade: string; building: string; code_repaired: boolean }
type BillData = { sections: Section[]; lines: Line[]; totals: Record<string, number>; chain: Record<string, any>; line_sum: number; unknown_units: any[]; external_links: any }

type FlatRow =
  | { kind: 'section'; section: Section; count: number }
  | { kind: 'line'; line: Line }

const CHECKED = new Set(['matched', 'printed', 'derived'])
const EDITABLE = new Set(['review', 'different', 'not_found'])

function cleanNum(n: number): string {
  return n.toFixed(6).replace(/\.?0+$/, '')
}

function quantityHint(line: Line): string {
  const measured = line.check?.override ? line.check.engine_qty : line.check?.our_qty
  const figure = measured != null ? `${fmt(measured, 3)} ${line.unit}` : ''
  if (line.check?.override) {
    return figure ? `Engine measured ${figure}. Currently overridden by ${line.check.override.author}.` : `Currently overridden by ${line.check.override.author}.`
  }
  return figure ? `Engine measured ${figure}. Enter quantity or formula (e.g. 12.4 or 3 * 4.2).` : 'No automatic figure yet. Enter verified quantity or formula.'
}

function errText(err: unknown): string {
  const raw = String((err as Error).message || err)
  const body = raw.replace(/^\d+\s+/, '')
  let detail = raw
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string') detail = parsed.detail
  } catch {
    /* plain text error */
  }
  if (detail.startsWith('unknown name') || detail.startsWith('cannot read') || detail.startsWith('unexpected')) {
    return 'Use a valid number or arithmetic expression, e.g. 12.4 or 3 * 4.2.'
  }
  if (detail === 'division by zero') return 'Cannot divide by zero.'
  if (detail === 'the expression is empty') return 'Enter a quantity.'
  return detail
}

/* ── Single-Column Override Form ("Reward Early, Punish Late" + Zero Page Reload) ── */
function QuantityForm({
  line,
  expr,
  setExpr,
  who,
  setWho,
  qtyWhy,
  setQtyWhy,
}: {
  line: Line
  expr: string
  setExpr: (v: string) => void
  who: string
  setWho: (v: string) => void
  qtyWhy: string
  setQtyWhy: (v: string) => void
}) {
  const [editErr, setEditErr] = useState('')
  const [touched, setTouched] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setEditErr('')
    setTouched(false)
    setSaving(false)
  }, [line.id])

  // Reward early: clear validation message immediately when fields become valid
  useEffect(() => {
    if (touched && editErr && expr.trim() && who.trim() && qtyWhy.trim()) {
      setEditErr('')
    }
  }, [expr, who, qtyWhy, touched, editErr])

  return (
    <form
      id="qty-editor"
      className="box edit"
      onSubmit={async (e) => {
        e.preventDefault()
        if (saving) return
        setTouched(true)
        if (!expr.trim() || !who.trim() || !qtyWhy.trim()) {
          setEditErr('Please provide the quantity, your name, and an audit reason.')
          return
        }
        setSaving(true)
        setEditErr('')
        try {
          try {
            localStorage.setItem('azboq.author', who.trim())
          } catch {
            /* ignore */
          }
          await postJSON('/api/review', {
            target_kind: 'line',
            target_id: line.id,
            action: 'override',
            reason: qtyWhy.trim(),
            author: who.trim(),
            payload: { expression: expr.trim(), unit: line.unit },
          })
          clearCache()
          setQtyWhy('')
          toast.success(`Saved quantity override on line ${line.id}`)
        } catch (err) {
          setEditErr(errText(err))
        } finally {
          setSaving(false)
        }
      }}
    >
      <small>{line.check?.override ? 'Active Quantity Override' : 'Override / Confirm Quantity'}</small>
      <div className="faint text-[12px]">{quantityHint(line)}</div>

      <div className="form-field">
        <label htmlFor="qf-expr">Verified quantity or formula ({line.unit})</label>
        <input
          id="qf-expr"
          inputMode="decimal"
          value={expr}
          onChange={(e) => setExpr(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder="e.g., 12.4 or 3 * 4.2"
        />
      </div>

      <div className="form-field">
        <label htmlFor="qf-who">Reviewer name</label>
        <input
          id="qf-who"
          value={who}
          onChange={(e) => setWho(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder="e.g., E. Hüseynov"
        />
      </div>

      <div className="form-field">
        <label htmlFor="qf-why">Audit justification</label>
        <input
          id="qf-why"
          value={qtyWhy}
          onChange={(e) => setQtyWhy(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder="Cite drawing sheet, schedule row, or site measurement"
        />
      </div>

      {editErr ? <div className="err">{editErr}</div> : null}

      <div className="acts">
        <button className="btn" type="submit" disabled={saving}>
          <Check size={14} /> {saving ? 'Saving…' : 'Save Override'}
        </button>
        {line.check?.override ? (
          <button
            className="quiet inline-flex items-center gap-1.5"
            type="button"
            disabled={saving}
            onClick={async () => {
              if (!who.trim()) {
                setEditErr('Enter your name before restoring the engine measurement.')
                return
              }
              setSaving(true)
              setEditErr('')
              try {
                try {
                  localStorage.setItem('azboq.author', who.trim())
                } catch {
                  /* ignore */
                }
                await delJSON(`/api/review/${line.check!.override!.id}`, {
                  author: who.trim(),
                  reason: qtyWhy.trim() || 'Restored engine measurement',
                })
                clearCache()
                toast.success(`Restored engine figure on line ${line.id}`)
              } catch (err) {
                setEditErr(errText(err))
              } finally {
                setSaving(false)
              }
            }}
          >
            <Undo size={13} /> Restore measured figure
          </button>
        ) : null}
      </div>
    </form>
  )
}

export function Bill({ route }: { route: Route }) {
  const { data, error } = useData<BillData>('/api/bill')
  const take = useData<{ items: { id: string; value: { sources: Source[] }; viewer?: Source | null }[] }>('/api/takeoff')
  const [q, setQ] = useState(route.query.get('q') || '')
  const [tradeFilter, setTradeFilter] = useState('')
  const [target, setTarget] = useState<Target | null>(null)
  const [who, setWho] = useState(() => {
    try {
      return localStorage.getItem('azboq.author') || ''
    } catch {
      return ''
    }
  })
  const [why, setWhy] = useState('')
  const [expr, setExpr] = useState('')
  const [qtyWhy, setQtyWhy] = useState('')

  const bname = useBuildingName()
  const status = route.query.get('status') || 'all'
  const building = route.query.get('building') || ''
  const selId = route.query.get('line')
  const explained = useData<Explain>(selId ? `/api/line/${selId}/explain` : null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const nav = (patch: Record<string, string | null>) => {
    const cur: Record<string, string | null> = {
      status: status === 'all' ? null : status,
      building: building || null,
      line: selId,
      q: q || null,
    }
    go('bill', { ...cur, ...patch })
  }

  const counts = useMemo(() => {
    const m: Record<string, number> = {}
    for (const l of data?.lines || []) {
      const s = l.check?.status || 'none'
      m[s] = (m[s] || 0) + 1
    }
    m.checked = (m.matched || 0) + (m.printed || 0) + (m.derived || 0)
    return m
  }, [data])

  const buildings = useMemo(() => [...new Set((data?.lines || []).map((l) => l.building))], [data])
  const trades = useMemo(() => [...new Set((data?.lines || []).map((l) => l.trade))].filter(Boolean).sort(), [data])

  const { flatRows, visible } = useMemo(() => {
    const bySection = new Map<string, Line[]>()
    const visible: Line[] = []
    const flatRows: FlatRow[] = []
    if (!data) return { flatRows, visible }

    const titleHit = new Set(q ? data.sections.filter((s) => matches(q, s.code, s.title)).map((s) => s.code) : [])
    for (const l of data.lines) {
      const s = l.check?.status || ''
      if (status === 'checked' ? !CHECKED.has(s) : status !== 'all' && s !== status) continue
      if (building && l.building !== building) continue
      if (tradeFilter && l.trade !== tradeFilter) continue
      if (!(titleHit.has(l.section) || matches(q, l.id, l.description, l.comment))) continue
      bySection.set(l.section, [...(bySection.get(l.section) || []), l])
    }
    for (const s of data.sections) {
      const ls = bySection.get(s.code)
      if (!ls || !ls.length) continue
      flatRows.push({ kind: 'section', section: s, count: ls.length })
      for (const line of ls) {
        flatRows.push({ kind: 'line', line })
        visible.push(line)
      }
    }
    return { flatRows, visible }
  }, [data, q, status, building, tradeFilter])

  // 60fps Virtualizer for all 2,175 BOQ rows + section headers
  const rowVirtualizer = useVirtualizer({
    count: flatRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (idx) => (flatRows[idx]?.kind === 'section' ? 38 : 54),
    overscan: 18,
  })

  // Scroll selected line into view when opened via deep link or keyboard navigation
  useEffect(() => {
    if (!selId || !flatRows.length) return
    const idx = flatRows.findIndex((r) => r.kind === 'line' && r.line.id === selId)
    if (idx >= 0) {
      rowVirtualizer.scrollToIndex(idx, { align: 'auto' })
    }
  }, [selId, flatRows, rowVirtualizer])

  // Keyboard ↑/↓ or J/K stepping across visible lines
  const visibleRef = useRef(visible)
  visibleRef.current = visible
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const list = visibleRef.current
      if (!list.length) return
      const at = list.findIndex((l) => l.id === selId)
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setTarget(null)
        nav({ line: list[Math.min(at + 1, list.length - 1)].id })
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault()
        setTarget(null)
        nav({ line: list[Math.max(at - 1, 0)].id })
      } else if (e.key === 'Escape' && selId) {
        nav({ line: null })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selId, status, building, q, tradeFilter])

  const selected = data?.lines.find((l) => l.id === selId) || null
  const overrideId = selected?.check?.override?.id
  const overrideExpr = selected?.check?.override?.expression

  useEffect(() => {
    const figure = selected?.check?.our_qty
    setExpr(overrideExpr ?? (figure != null ? cleanNum(figure) : ''))
    setQtyWhy('')
  }, [selected?.id, overrideId, overrideExpr, selected?.check?.our_qty])

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the bill" />

  const sel = selected
  const item = sel?.check?.item ? take.data?.items.find((i) => i.id === sel.check!.item) : undefined
  const itemSources = item ? [...(item.viewer ? [item.viewer] : []), ...item.value.sources.filter((s) => s !== item.viewer)].slice(0, 6) : []
  const selSources = sel?.check?.sources || (itemSources.length ? itemSources : sel?.check?.candidates) || []
  const shown = target || (selSources[0] ? targetOf(selSources[0]) : null)

  const head = data.totals.contract_price_c5
  const selIdx = sel ? visible.findIndex((l) => l.id === sel.id) : -1
  const different = sel?.check?.status === 'different'
  const editing = !!(sel?.check && (EDITABLE.has(sel.check.status) || sel.check.override))

  const step = (d: number) => {
    const next = selIdx >= 0 ? visible[selIdx + d] : undefined
    if (!next) return
    setTarget(null)
    nav({ line: next.id })
  }

  return (
    <div className={`fill-row ${sel ? 'with-insp' : ''}`}>
      <Card style={{ overflow: 'hidden' }}>
        <div className="toolbar">
          <SegmentedTabs<string>
            id="bill-status"
            value={status}
            onChange={(val) => nav({ status: val === 'all' ? null : val })}
            options={[
              { value: 'all', label: 'All', count: fmt(data.lines.length) },
              { value: 'different', label: 'Contradicts', count: fmt(counts.different || 0), tone: 'bad' },
              { value: 'checked', label: 'Backed', count: fmt(counts.checked || 0), tone: 'ok' },
              { value: 'review', label: 'Review', count: fmt(counts.review || 0), tone: 'warn' },
              { value: 'blocked', label: 'Blocked', count: fmt(counts.blocked || 0), tone: 'warn' },
              { value: 'not_found', label: 'Unbacked', count: fmt(counts.not_found || 0) },
            ]}
          />

          <select
            className="search"
            value={building}
            onChange={(e) => nav({ building: e.target.value || null })}
            aria-label="Filter by building"
          >
            <option value="">All buildings</option>
            {buildings.map((b) => (
              <option key={b} value={b}>{bname(b)}</option>
            ))}
          </select>

          <select
            className="search"
            value={tradeFilter}
            onChange={(e) => setTradeFilter(e.target.value)}
            aria-label="Filter by trade"
          >
            <option value="">All trades</option>
            {trades.map((tr) => (
              <option key={tr} value={tr}>{tradeName(tr)}</option>
            ))}
          </select>

          <label className="field grow">
            <Search size={14} />
            <input
              placeholder="Filter by BOQ code or Azerbaijani/English text…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            {q ? (
              <button type="button" onClick={() => setQ('')} aria-label="Clear search" className="clear">
                <X size={14} />
              </button>
            ) : null}
          </label>

          <span className="muted text-[12px] whitespace-nowrap">
            <b className="mono text-[var(--ink)]">{fmt(visible.length)}</b> rows · <span className="mono">{money(head)}</span>
          </span>
        </div>

        {/* Sticky Column Header */}
        <div className="grid grid-cols-[74px_minmax(220px,1fr)_64px_92px_104px_112px_118px] items-center border-b border-[var(--line-2)] bg-[var(--paper-2)] px-3 h-[34px] text-[11px] font-medium uppercase tracking-[0.04em] text-[var(--muted)] select-none">
          <span>Code</span>
          <span>Description</span>
          <span>Unit</span>
          <span className="text-right">Bill Qty</span>
          <span className="text-right">Drawings</span>
          <span className="text-right">Amount</span>
          <span className="pl-3">Status</span>
        </div>

        {/* Virtualized 60fps Viewport */}
        <div ref={scrollRef} className="scroll flex-1 relative">
          {flatRows.length ? (
            <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
              {rowVirtualizer.getVirtualItems().map((vRow) => {
                const entry = flatRows[vRow.index]
                if (!entry) return null

                if (entry.kind === 'section') {
                  const s = entry.section
                  return (
                    <div
                      key={`sec-${s.code}-${s.row}`}
                      data-index={vRow.index}
                      ref={rowVirtualizer.measureElement}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        transform: `translateY(${vRow.start}px)`,
                      }}
                      className="flex items-center gap-3 border-b border-[var(--line-2)] bg-[var(--paper-2)] px-3 py-2 text-[12.5px] font-semibold"
                    >
                      <span className="mono text-[var(--accent-2)]">
                        {s.code}
                        {s.code_repaired ? (
                          <span className="note warn" title={`Stored in workbook as ${s.stored_code}; repaired from position`}>
                            *
                          </span>
                        ) : null}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-[var(--ink)]">
                        <T az={s.title} />{' '}
                        <span className="font-normal text-[var(--muted)]">
                          · {bname(s.building)} · {tradeName(s.trade)} · {entry.count} {entry.count === 1 ? 'line' : 'lines'}
                        </span>
                      </span>
                    </div>
                  )
                }

                const l = entry.line
                const isSel = sel?.id === l.id
                const isDiff = l.check?.status === 'different'
                return (
                  <div
                    key={l.id}
                    data-index={vRow.index}
                    data-line={l.id}
                    ref={rowVirtualizer.measureElement}
                    tabIndex={0}
                    onClick={() => {
                      setTarget(null)
                      nav({ line: l.id })
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        setTarget(null)
                        nav({ line: l.id })
                      }
                    }}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${vRow.start}px)`,
                    }}
                    className={`grid grid-cols-[74px_minmax(220px,1fr)_64px_92px_104px_112px_118px] items-start border-b border-[var(--line)] px-3 py-2 text-[13px] cursor-pointer transition-colors ${
                      isSel
                        ? 'bg-[var(--accent-soft)] shadow-[inset_2px_0_0_var(--accent)]'
                        : 'hover:bg-[var(--paper-2)]'
                    }`}
                  >
                    <span className="code pt-0.5">{l.id}</span>
                    <div className="min-w-0 pr-3 leading-[1.42]">
                      <T az={l.description} />
                      {l.comment ? (
                        <span className="pill ml-1.5" title={l.comment}>
                          note
                        </span>
                      ) : null}
                    </div>
                    <span className="pt-0.5 text-[12px] text-[var(--muted)] font-mono">
                      {l.unit_known ? l.unit_raw : <span className="note warn" title="Unrecognised unit">{l.unit_raw}</span>}
                    </span>
                    <span className="num text-right font-mono text-[12px] pt-0.5">{fmt(l.qty, 3)}</span>
                    <span className={`num text-right font-mono text-[12px] pt-0.5 ${isDiff ? 'text-[var(--bad-text)] font-semibold' : ''}`}>
                      {l.check?.our_qty === null || l.check?.our_qty === undefined ? (
                        <span className="faint">—</span>
                      ) : (
                        fmt(l.check.our_qty, 3)
                      )}
                      {l.check?.override ? (
                        <span className="pill ml-1" title={`${l.check.override.author}: ${l.check.override.reason}`}>
                          edited
                        </span>
                      ) : null}
                    </span>
                    <span className="num text-right font-mono text-[12px] pt-0.5 text-[var(--ink-2)]">{money(l.amount)}</span>
                    <span className="pl-3 pt-0.5">{l.check ? <StatusTag status={l.check.status} /> : null}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <Empty
              icon={<Search size={18} />}
              title="No BOQ lines match these filters"
              action={
                <button
                  type="button"
                  className="btn outline sm"
                  onClick={() => {
                    setQ('')
                    setTradeFilter('')
                    nav({ status: null, building: null, q: null })
                  }}
                >
                  Reset filters
                </button>
              }
            >
              Clear your search term or widen the selected building, trade, or verification status.
            </Empty>
          )}
        </div>
      </Card>

      {/* Spring-Animated Two-Sided Reconciliation & Evidence Drawer */}
      <AnimatePresence mode="wait">
        {sel ? (
          <motion.div
            key="bill-inspector"
            initial={{ opacity: 0, x: 18 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 14 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="inspector flex min-h-0 flex-col"
          >
            <Card
              title={
                <span className="flex items-center gap-2">
                  <span>Line <span className="mono">{sel.id}</span></span>
                  {sel.check ? <StatusTag status={sel.check.status} /> : null}
                </span>
              }
              sub={selIdx >= 0 ? `Row ${selIdx + 1} of ${fmt(visible.length)} · ↑ / ↓ or J / K to step` : 'Filtered row'}
              right={
                <>
                  <button className="icon sm" title="Previous line (↑)" disabled={selIdx <= 0} onClick={() => step(-1)}>
                    <ArrowUp size={13} />
                  </button>
                  <button className="icon sm" title="Next line (↓)" disabled={selIdx < 0 || selIdx >= visible.length - 1} onClick={() => step(1)}>
                    <ArrowDown size={13} />
                  </button>
                  <button className="icon sm" title="Close inspector (Esc)" onClick={() => nav({ line: null })}>
                    <X size={13} />
                  </button>
                </>
              }
              style={{ overflow: 'hidden', flex: 1 }}
            >
              <div className="insp" style={editing ? { flex: '1 1 auto', minHeight: 0 } : { flex: '0 1 auto', maxHeight: '58%' }}>
                <div className="eyebrow accent">
                  {bname(sel.building)} · {tradeName(sel.trade)} · Excel row {sel.row}
                </div>
                <h1>
                  <T az={sel.description} />
                </h1>

                {/* DUKU Two-Sided Reconciliation Pair */}
                <div className="relative">
                  <div className="vs">
                    <div>
                      <small>Client BOQ</small>
                      <b>
                        {fmt(sel.qty, 3)} <span>{sel.unit}</span>
                      </b>
                      <span className="mono">
                        @ {money(sel.rate)} = {money(sel.amount)}
                      </span>
                    </div>

                    <div className={different ? 'bad' : sel.check && LINE_STATUS[sel.check.status]?.cls === 'ok' ? 'ok' : ''}>
                      <small>Drawing Evidence</small>
                      <b>
                        {sel.check?.our_qty === null || sel.check?.our_qty === undefined ? '—' : fmt(sel.check.our_qty, 3)}{' '}
                        <span>{sel.check?.our_qty != null ? sel.unit : ''}</span>
                      </b>
                      {sel.check?.gap ? (
                        <span className="mono font-medium text-[var(--bad-text)]">
                          Δ {sel.check.gap > 0 ? '+' : ''}{fmt(sel.check.gap, 3)} {sel.unit} ({fmt(sel.check.gap_pct, 1)}%)
                        </span>
                      ) : (
                        <span>{sel.check ? LINE_STATUS[sel.check.status]?.label : 'Unchecked'}</span>
                      )}
                    </div>
                  </div>
                  <span
                    className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 grid h-6 w-6 place-items-center rounded-full border border-[var(--line-2)] bg-[var(--paper)] text-[var(--muted)] shadow-xs"
                    aria-hidden
                  >
                    <ArrowsLeftRight size={12} />
                  </span>
                </div>

                {/* Review Reasons & Inline Acceptance */}
                {(sel.check?.review_reasons || []).length ? (
                  <div className="box warn">
                    <small>Review Flags</small>
                    {(sel.check?.review_reasons || []).map((reason) => (
                      <div key={reason.code + (reason.link || reason.rule || '')} className="mt-1 text-[12px]">
                        • {reasonText(reason)}
                      </div>
                    ))}
                    {(sel.check?.review_reasons || []).some((reason) => !reason.accepted_by) ? (
                      <form
                        className="mt-2.5 border-t border-[var(--warn-line)] pt-2.5"
                        onSubmit={async (e) => {
                          e.preventDefault()
                          const open = (sel.check?.review_reasons || []).find((reason) => !reason.accepted_by)
                          if (!open || !who.trim() || !why.trim()) {
                            toast.error('Enter your name and acceptance note first.')
                            return
                          }
                          try {
                            localStorage.setItem('azboq.author', who.trim())
                          } catch {
                            /* ignore */
                          }
                          await postJSON('/api/review', {
                            target_kind: 'reason',
                            target_id: `reason:${sel.id}:${open.code}`,
                            action: 'accept',
                            reason: why.trim(),
                            author: who.trim(),
                            payload: {},
                          })
                          setWhy('')
                          clearCache()
                          toast.success(`Accepted review flag on line ${sel.id}`)
                        }}
                      >
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            className="search min-w-0!"
                            placeholder="Reviewer name"
                            value={who}
                            onChange={(e) => setWho(e.target.value)}
                          />
                          <input
                            className="search min-w-0!"
                            placeholder="Why accepted"
                            value={why}
                            onChange={(e) => setWhy(e.target.value)}
                          />
                        </div>
                        <button className="btn sm mt-2" type="submit">
                          Accept flag
                        </button>
                      </form>
                    ) : null}
                  </div>
                ) : null}

                {/* Single-Column Override Form */}
                {sel.check && (EDITABLE.has(sel.check.status) || sel.check.override) ? (
                  <QuantityForm
                    line={sel}
                    expr={expr}
                    setExpr={setExpr}
                    who={who}
                    setWho={setWho}
                    qtyWhy={qtyWhy}
                    setQtyWhy={setQtyWhy}
                  />
                ) : null}

                {sel.check ? (
                  <>
                    <div className={`box ${LINE_STATUS[sel.check.status]?.cls === 'bad' ? 'bad' : LINE_STATUS[sel.check.status]?.cls === 'ok' ? 'ok' : ''}`}>
                      <small>Verification Finding</small>
                      {sel.check.reason}
                      {sel.check.override && sel.check.engine_reason ? (
                        <div className="faint mt-1">Original engine note: {sel.check.engine_reason}</div>
                      ) : null}
                      {sel.check.gap ? (
                        <div className="mt-1.5">
                          Financial impact: <b className="mono">{money(Math.abs(sel.check.gap) * (sel.rate || 0))}</b> before mark-ups & VAT.
                        </div>
                      ) : null}
                    </div>

                    {sel.check.item ? (
                      <div className="pair">
                        <span>Takeoff item</span>
                        <a href={href('takeoff', { item: sel.check.item })} className="mono">
                          {sel.check.item} →
                        </a>
                      </div>
                    ) : null}

                    {explained.data?.item?.formula ? (
                      <div className="box">
                        <small>Formula & Substitution</small>
                        <div className="font-medium text-[var(--ink)]">{explained.data.item.label_en}</div>
                        <div className="mono mt-1 text-[12px]">{explained.data.item.formula}</div>
                        {explained.data.item.substituted ? (
                          <div className="mono text-[12px] text-[var(--muted)]">= {explained.data.item.substituted}</div>
                        ) : null}
                      </div>
                    ) : null}

                    {explained.data?.inputs?.length ? (
                      <div className="section-label">
                        <span className="eyebrow">Dimensions & Inputs</span>
                      </div>
                    ) : null}
                    {explained.data?.inputs?.map((input) => {
                      const src = input.sources[0]
                      const loc = src
                        ? [src.file?.split('/').pop(), src.page != null ? `p.${src.page + 1}` : null, src.row, src.col].filter(Boolean).join(' · ')
                        : ''
                      return (
                        <div key={input.label + String(input.value)} className="pair">
                          <span>{input.label}</span>
                          <b className="mono">
                            {input.value == null ? '—' : fmt(input.value, 3)} {input.unit}
                            {loc ? <span className="font-normal text-[var(--muted)]"> · {loc}</span> : ''}
                          </b>
                        </div>
                      )
                    })}

                    {sel.check.derived_from ? (
                      <div className="pair">
                        <span>Inherits parent surface from</span>
                        <a href={href('bill', { line: sel.check.derived_from })}>
                          line <span className="mono">{sel.check.derived_from}</span>
                        </a>
                      </div>
                    ) : null}
                  </>
                ) : null}

                {sel.comment ? (
                  <div className="box warn">
                    <small>Workbook Reviewer Comment</small>
                    <span lang="az">{sel.comment}</span>
                    {sel.check?.reviewer?.kind === 'reduce' && sel.check.reviewer.delta != null && sel.check.reviewer.value != null ? (
                      <div className="mt-1">
                        Parsed as: reduce by {fmt(-sel.check.reviewer.delta, 3)} → {fmt(sel.check.reviewer.value, 3)} {sel.unit}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {selSources.length ? (
                  <>
                    <div className="section-label">
                      <span className="eyebrow">
                        {sel.check?.sources ? 'Sheet Citations' : itemSources.length ? 'Takeoff Sheet Citations' : 'Candidate Mentions (Unaccepted)'}
                      </span>
                    </div>
                    {selSources.map((s, i) => (
                      <SourceCard key={i} src={s} onOpen={setTarget} active={JSON.stringify(targetOf(s)) === JSON.stringify(shown)} />
                    ))}
                  </>
                ) : null}

                {editing ? (
                  <div style={{ height: 240, marginTop: 12, borderTop: '1px solid var(--line)', display: 'flex', borderRadius: 8, overflow: 'hidden' }}>
                    <Viewer
                      target={shown}
                      emptyText={
                        sel.check?.status === 'not_found'
                          ? 'No drawing of this building prints or measures this item.'
                          : 'No sheet region linked to this line.'
                      }
                    />
                  </div>
                ) : null}
              </div>

              {editing ? null : (
                <div style={{ flex: 1, display: 'flex', minHeight: 260, borderTop: '1px solid var(--line)' }}>
                  <Viewer
                    target={shown}
                    emptyText={
                      sel.check?.status === 'not_found'
                        ? 'No drawing of this building prints or measures this item.'
                        : 'No sheet region linked to this line.'
                    }
                  />
                </div>
              )}
            </Card>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
