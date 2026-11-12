import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Toaster } from 'sonner'
import { useData } from './api'
import { fmt, matches } from './az'
import { LangProvider, useLang, type Lang } from './i18n'
import {
  Buildings,
  ChartBar,
  Download,
  EnterKey,
  FolderOpen,
  Gauge,
  GitDiff,
  GridFour,
  Hash,
  Invoice,
  List,
  Moon,
  Package,
  Pulse,
  Receipt,
  Ruler,
  Search,
  ShieldCheck,
  ShieldWarning,
  SidebarSimple,
  SquaresFour,
  Stack,
  Sun,
  Table,
  Translate,
  TreeStructure,
  type Icon,
} from './icons'
import { Areas } from './pages/Areas'
import { Bill } from './pages/Bill'
import { DrawingDetail, Drawings } from './pages/Drawings'
import { Conflicts, Coverage, Inputs, NotFound, RunLog, Translations } from './pages/Evidence'
import { Home } from './pages/Home'
import { Operations } from './pages/Operations'
import { Projects } from './pages/Projects'
import { Report } from './pages/Report'
import { Takeoff } from './pages/Takeoff'
import { go, href, useRoute } from './router'
import { cn, LINE_STATUS, Ring, SegmentedTabs } from './ui'

type Summary = {
  counts: Record<string, number>
  drawings_total: number
  conflicts: number
  review_items: number
  bill: { lines: number; line_sum: number }
  value_by_building: { value: number; checked: number }[]
}

type OpsSummary = {
  fraud_alerts?: { id: string; severity: string }[]
}

type PageDef = { title: string; desc: string; icon: Icon; group: string; fill?: boolean }

const PAGES: Record<string, PageDef> = {
  home: { title: 'Command Summary', desc: 'Hadrut Fire Depot · Order 9335 · Executive BOQ verification & site fraud overview', icon: SquaresFour, group: 'Overview' },
  projects: { title: 'Projects & Upload', desc: 'Manage active audit workspaces and ingest new client DWG, PDF, and BOQ packages', icon: Buildings, group: 'Overview' },
  drawings: { title: 'Drawings', desc: 'All 61 package files, reader verification status, and extracted sheets', icon: Stack, group: 'BOQ Verification' },
  drawing: { title: 'Sheet Studio', desc: 'Interactive CAD/PDF blueprint canvas and synchronized Azerbaijani text layer', icon: Stack, group: 'BOQ Verification', fill: true },
  takeoff: { title: 'Takeoff', desc: '51 measured quantities, Depot geometry gate, and live sheet citations', icon: Ruler, group: 'BOQ Verification', fill: true },
  bill: { title: 'Bill Reconciliation', desc: 'All 2,175 client BOQ lines compared side-by-side against drawing evidence', icon: Receipt, group: 'BOQ Verification', fill: true },
  report: { title: 'Discrepancy Report', desc: 'Contradictions, unbacked scope, steel schedules, and handover exports', icon: ChartBar, group: 'BOQ Verification' },
  inputs: { title: 'Inputs Ledger', desc: 'Every dimension, count, and cited project rule feeding the check', icon: TreeStructure, group: 'Audit Evidence' },
  areas: { title: 'Area Book', desc: 'Room-by-room schedule areas cross-checked against CAD hatch polygons', icon: GridFour, group: 'Audit Evidence', fill: true },
  conflicts: { title: 'Document Conflicts', desc: 'Disagreements across client documents preserved side-by-side for decision', icon: GitDiff, group: 'Audit Evidence', fill: true },
  coverage: { title: 'Coverage Matrix', desc: 'Verification coverage across every Hadrut building and engineering trade', icon: ShieldCheck, group: 'Audit Evidence' },
  translations: { title: 'Translations', desc: 'Azerbaijani source strings paired with English reading glosses', icon: Translate, group: 'Audit Evidence', fill: true },
  runlog: { title: 'Pipeline Log', desc: 'Stage execution audit, warnings, and dual-reader DWG verification', icon: Pulse, group: 'Audit Evidence' },
  'ops/fraud': { title: 'Fraud & Alerts', desc: 'Automated cross-register rules flagging overbilling, duplicate deliveries, and excess waste', icon: ShieldWarning, group: 'Operations & Fraud' },
  'ops/drawings': { title: 'Drawing Register', desc: 'PJ_04 engineering register seeded from the Hadrut design package', icon: FolderOpen, group: 'Operations & Fraud' },
  'ops/contract_bill': { title: 'Contract BOQ', desc: 'PJ_12 baseline contract bill register for progress & commercial control', icon: Table, group: 'Operations & Fraud' },
  'ops/materials': { title: 'Material Receiving', desc: 'PJ_08 site material deliveries, weighbridge tickets, and BOQ consumption', icon: Package, group: 'Operations & Fraud' },
  'ops/measurements': { title: 'Measurements (Forma 2)', desc: 'PJ_12 certified monthly site quantities measured against contract BOQ', icon: Gauge, group: 'Operations & Fraud' },
  'ops/invoices': { title: 'Invoices (e-Qaimə)', desc: 'PJ_13 subcontractor & supplier invoices matched against Forma-2 and deliveries', icon: Invoice, group: 'Operations & Fraud' },
  'ops/codes': { title: 'Master Codes', desc: 'PJ_16 standardized sections, units, buildings, and trade classifications', icon: Hash, group: 'Operations & Fraud' },
}

type NavItem = { to: string; count?: number; tone?: 'hot' | 'warn' }
type NavGroup = { label: string; items: NavItem[] }

function readPref(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) || fallback
  } catch {
    return fallback
  }
}

function writePref(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* ignore blocked storage */
  }
}

function SidebarNavRow({
  it,
  current,
  collapsed,
  onNavigate,
}: {
  it: NavItem
  current: string
  collapsed: boolean
  onNavigate?: () => void
}) {
  const p = PAGES[it.to]
  if (!p) return null
  const Ico = p.icon
  const active = current === it.to
  return (
    <a
      href={href(it.to)}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      title={collapsed ? `${p.title}${it.count !== undefined ? ` (${fmt(it.count)})` : ''}` : undefined}
      className={cn('nav-link', active && 'active')}
    >
      <Ico size={16} weight={active ? 'fill' : 'regular'} />
      {!collapsed ? (
        <>
          <span className="nav-label">{p.title}</span>
          {it.count !== undefined ? (
            <span className={cn('nav-badge', it.tone === 'hot' && 'hot', it.tone === 'warn' && 'warn')}>
              {fmt(it.count)}
            </span>
          ) : null}
        </>
      ) : it.tone === 'hot' && it.count ? (
        <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-[var(--bad)] ring-2 ring-[var(--paper)]" />
      ) : null}
    </a>
  )
}

/* ── Command Palette (Ctrl+K / Cmd+K) ─────────────────── */
type Hit = { key: string; group: string; icon: ReactNode; title: string; sub?: string; right?: string; run: () => void }

function Palette({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState('')
  const [at, setAt] = useState(0)
  const bill = useData<{ lines: { id: string; description: string; building: string; qty: number; unit: string; check: { status: string } | null }[] }>('/api/bill')
  const take = useData<{ items: { id: string; label_en: string; label_az: string; unit: string; building: string }[] }>('/api/takeoff')
  const list = useRef<HTMLDivElement>(null)

  const hits = useMemo<Hit[]>(() => {
    const out: Hit[] = []
    for (const [k, p] of Object.entries(PAGES)) {
      if (k === 'drawing') continue
      if (!matches(q, p.title, p.group, p.desc)) continue
      const Ico = p.icon
      out.push({ key: `p:${k}`, group: 'Screens', icon: <Ico size={15} />, title: p.title, sub: p.group, run: () => go(k) })
      if (!q && out.length >= 8) break
    }
    if (q.trim().length >= 2) {
      const items = (take.data?.items || []).filter((i) => matches(q, i.id, i.label_en, i.label_az)).slice(0, 5)
      for (const i of items) {
        out.push({
          key: `t:${i.id}`,
          group: 'Measured Takeoff Items',
          icon: <Ruler size={15} />,
          title: i.label_en,
          sub: i.label_az,
          right: i.unit,
          run: () => go('takeoff', { item: i.id }),
        })
      }
      const lines = (bill.data?.lines || []).filter((l) => matches(q, l.id, l.description)).slice(0, 8)
      for (const l of lines) {
        out.push({
          key: `b:${l.id}`,
          group: 'Contract BOQ Lines',
          icon: <Receipt size={15} />,
          title: l.description,
          sub: `Line ${l.id} · ${(l.check && LINE_STATUS[l.check.status]?.label) || 'not checked'}`,
          right: `${fmt(l.qty, 3)} ${l.unit}`,
          run: () => go('bill', { line: l.id }),
        })
      }
      out.push({
        key: 'all',
        group: 'Contract BOQ Lines',
        icon: <Search size={15} />,
        title: `Filter full BOQ for “${q.trim()}”`,
        sub: 'Opens Bill Reconciliation filtered to every matching row',
        run: () => go('bill', { q: q.trim() }),
      })
    }
    return out
  }, [q, bill.data, take.data])

  useEffect(() => {
    list.current?.querySelector('.it.on')?.scrollIntoView({ block: 'nearest' })
  }, [at])

  const pick = (h: Hit | undefined) => {
    if (!h) return
    h.run()
    onClose()
  }

  let lastGroup = ''
  return (
    <div className="palette-back" onMouseDown={onClose}>
      <div className="palette" role="dialog" aria-label="Global Search" onMouseDown={(e) => e.stopPropagation()}>
        <div className="in">
          <Search size={16} />
          <input
            autoFocus
            placeholder="Jump to screen, BOQ code, or Azerbaijani/English item… (ə = e, ş = s)"
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setAt(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setAt((a) => Math.min(a + 1, Math.max(hits.length - 1, 0)))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setAt((a) => Math.max(a - 1, 0))
              } else if (e.key === 'Enter') {
                pick(hits[at])
              } else if (e.key === 'Escape') {
                onClose()
              }
            }}
          />
          <kbd>Esc</kbd>
        </div>
        <div className="res" ref={list}>
          {hits.map((h, i) => {
            const head = h.group !== lastGroup ? <div className="grp">{h.group}</div> : null
            lastGroup = h.group
            return (
              <div key={h.key}>
                {head}
                <button className={`it ${i === at ? 'on' : ''}`} onMouseMove={() => setAt(i)} onClick={() => pick(h)}>
                  <span className="ico">{h.icon}</span>
                  <span style={{ minWidth: 0 }}>
                    <b lang={h.group === 'Contract BOQ Lines' && h.key !== 'all' ? 'az' : undefined}>{h.title}</b>
                    {h.sub ? <span>{h.sub}</span> : null}
                  </span>
                  {h.right ? <span className="r">{h.right}</span> : <span />}
                </button>
              </div>
            )
          })}
          {!hits.length ? <div className="empty-state">No results matching “{q}”.</div> : null}
          {q.trim().length >= 2 && !bill.data ? <div className="grp">Indexing 2,175 bill lines…</div> : null}
        </div>
        <div className="foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd><EnterKey size={11} /></kbd> open</span>
          <span style={{ marginLeft: 'auto' }}>Azerbaijani folding enabled (ə↔e, ı↔i, ş↔s)</span>
        </div>
      </div>
    </div>
  )
}

function PageHead({ def }: { def: PageDef }) {
  return (
    <div className="page-head">
      <div className="t">
        <h1>{def.title}</h1>
        <p>{def.desc}</p>
      </div>
    </div>
  )
}

function Shell() {
  const route = useRoute()
  const { lang, setLang } = useLang()
  // Default strictly to crisp Light Mode per design direction
  const [theme, setTheme] = useState(() => readPref('azboq.theme.v2', 'light'))
  const [collapsed, setCollapsed] = useState(() => readPref('azboq.sidebar', 'expanded') === 'collapsed')
  const [mobileMenu, setMobileMenu] = useState(false)
  const [palette, setPalette] = useState(false)

  const { data: s } = useData<Summary>('/api/summary')
  const { data: ops } = useData<OpsSummary>('/api/operations')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    writePref('azboq.theme.v2', theme)
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = lang === 'az' ? 'az' : 'en'
  }, [lang])

  useEffect(() => {
    writePref('azboq.sidebar', collapsed ? 'collapsed' : 'expanded')
  }, [collapsed])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
        e.preventDefault()
        setPalette(true)
      } else if (e.key === 'b' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        setCollapsed((c) => !c)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const page = route.parts[0]
  const current = page === 'ops' ? `ops/${route.parts[1] || 'fraud'}` : page
  const def = PAGES[current] || { title: page, desc: '', icon: SquaresFour, group: '' }
  const navCurrent = current === 'drawing' ? 'drawings' : current

  useEffect(() => {
    document.title = `${def.title} · Hadrut · AZ-Takeoff`
  }, [def.title])

  let body
  switch (page) {
    case 'home': body = <Home />; break
    case 'projects': body = <Projects />; break
    case 'drawings': body = <Drawings route={route} />; break
    case 'drawing': body = <DrawingDetail route={route} />; break
    case 'takeoff': body = <Takeoff route={route} />; break
    case 'bill': body = <Bill key={route.query.get('q') || ''} route={route} />; break
    case 'report': body = <Report route={route} />; break
    case 'inputs': body = <Inputs />; break
    case 'areas': body = <Areas />; break
    case 'conflicts': body = <Conflicts />; break
    case 'coverage': body = <Coverage />; break
    case 'translations': body = <Translations />; break
    case 'runlog': body = <RunLog />; break
    case 'ops': body = <Operations route={route} />; break
    default: body = <NotFound route={route} />
  }

  const valueAll = s?.value_by_building?.reduce((acc, b) => acc + b.value, 0) || 0
  const valueChecked = s?.value_by_building?.reduce((acc, b) => acc + b.checked, 0) || 0
  const valueShare = valueAll ? valueChecked / valueAll : 0
  const fraudCount = ops?.fraud_alerts?.length || 0

  const groups: NavGroup[] = [
    {
      label: 'Overview',
      items: [{ to: 'home' }, { to: 'projects' }],
    },
    {
      label: 'BOQ Verification',
      items: [
        { to: 'drawings', count: s?.drawings_total },
        { to: 'takeoff' },
        { to: 'bill', count: s?.bill.lines },
        { to: 'report', count: s?.counts.different, tone: s?.counts.different ? 'hot' : undefined },
      ],
    },
    {
      label: 'Audit Evidence',
      items: [
        { to: 'inputs' },
        { to: 'areas' },
        { to: 'conflicts', count: s?.conflicts, tone: s?.conflicts ? 'warn' : undefined },
        { to: 'coverage' },
        { to: 'translations' },
        { to: 'runlog', count: s?.review_items },
      ],
    },
    {
      label: 'Operations & Fraud',
      items: [
        { to: 'ops/fraud', count: fraudCount || undefined, tone: fraudCount ? 'hot' : undefined },
        { to: 'ops/materials' },
        { to: 'ops/measurements' },
        { to: 'ops/invoices' },
        { to: 'ops/drawings' },
        { to: 'ops/contract_bill' },
        { to: 'ops/codes' },
      ],
    },
  ]

  return (
    <div className="app-shell">
      <Toaster
        position="bottom-right"
        theme={theme === 'dark' ? 'dark' : 'light'}
        toastOptions={{
          style: {
            borderRadius: '10px',
            border: '1px solid var(--line-2)',
            background: 'var(--paper)',
            color: 'var(--ink)',
            fontSize: '13px',
          },
        }}
      />

      {/* Desktop Left Sidebar (shadcn-admin pattern) */}
      <aside className={cn('sidebar', collapsed && 'collapsed')} aria-label="Sidebar navigation">
        <a href={href('home')} className="sidebar-head no-underline!">
          <span className="brand-mark">
            <Ruler size={16} weight="bold" />
          </span>
          {!collapsed ? (
            <div className="brand-copy">
              <b>AZ-Takeoff</b>
              <span>
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--ok)]" />
                Hadrut · Order 9335
              </span>
            </div>
          ) : null}
        </a>

        <nav className="sidebar-scroll" aria-label="Main">
          {groups.map((g) => (
            <div key={g.label} className="nav-section">
              <div className="nav-section-label">{g.label}</div>
              {g.items.map((it) => (
                <SidebarNavRow key={it.to} it={it} current={navCurrent} collapsed={collapsed} />
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <a
            href={href('bill', { status: 'checked' })}
            className="flex items-center gap-2.5 rounded-lg p-1 text-inherit no-underline! hover:bg-[var(--paper-3)] transition-colors"
            title="Contract value backed by drawing evidence"
          >
            <Ring value={valueShare} size={34} stroke={3.5} label={valueAll ? `${Math.round(valueShare * 100)}%` : '…'} />
            {!collapsed ? (
              <div className="min-w-0 flex-1 leading-tight">
                <div className="text-[12px] font-semibold text-[var(--ink)] truncate">
                  {valueAll ? `${(valueShare * 100).toFixed(1)}% Value Backed` : 'Loading audit…'}
                </div>
                <div className="text-[11px] text-[var(--muted)] font-mono truncate">
                  {valueAll ? '908.3K / 3.11M AZN' : 'Order 9335'}
                </div>
              </div>
            ) : null}
          </a>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="shell-main">
        <header className="topbar">
          <button
            className="icon bare mobile-menu-btn"
            onClick={() => setMobileMenu(true)}
            aria-label="Open menu"
          >
            <List size={17} />
          </button>
          <button
            className="icon bare hidden lg:inline-grid!"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? 'Expand sidebar (Ctrl+B)' : 'Collapse sidebar (Ctrl+B)'}
            aria-label="Toggle sidebar"
          >
            <SidebarSimple size={17} />
          </button>

          <nav className="crumbs" aria-label="Breadcrumb">
            <a href={href('home')}>Hadrut 9335</a>
            {def.group && def.group !== 'Overview' ? (
              <>
                <i>/</i>
                <span>{def.group}</span>
              </>
            ) : null}
            <i>/</i>
            {page === 'drawing' ? (
              <>
                <a href={href('drawings')}>Drawings</a>
                <i>/</i>
                <b className="mono">{route.parts[1]}</b>
              </>
            ) : (
              <b>{def.title}</b>
            )}
          </nav>

          <button className="find" onClick={() => setPalette(true)} title="Global Search (Ctrl+K)">
            <Search size={14} />
            <span>Search BOQ, takeoff, drawings…</span>
            <kbd>Ctrl K</kbd>
          </button>

          <div className="topbar-right">
            <SegmentedTabs<Lang>
              id="topbar-lang"
              size="sm"
              value={lang}
              onChange={setLang}
              options={[
                { value: 'en', label: 'EN' },
                { value: 'az', label: 'AZ' },
                { value: 'both', label: 'Both' },
              ]}
            />
            <button
              className="icon"
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle color theme"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <a className="btn" href={href('report', { tab: route.query.get('tab') || 'different' })}>
              <Download size={14} />
              <span>Exports</span>
            </a>
          </div>
        </header>

        <main key={current + (route.parts[1] || '')} className={cn('page-in', def.fill && 'fill')}>
          {page !== 'home' ? <PageHead def={def} /> : null}
          {body}
        </main>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenu ? (
        <>
          <div className="drawer-back" onClick={() => setMobileMenu(false)} />
          <nav className="drawer" aria-label="Mobile navigation">
            <div className="mb-3 flex items-center justify-between px-2">
              <div className="flex items-center gap-2">
                <span className="brand-mark"><Ruler size={15} weight="bold" /></span>
                <b className="text-[13.5px]">AZ-Takeoff</b>
              </div>
            </div>
            {groups.map((g) => (
              <div key={g.label} className="mb-3">
                <div className="nav-section-label">{g.label}</div>
                {g.items.map((it) => (
                  <SidebarNavRow key={it.to} it={it} current={navCurrent} collapsed={false} onNavigate={() => setMobileMenu(false)} />
                ))}
              </div>
            ))}
          </nav>
        </>
      ) : null}

      {palette ? <Palette onClose={() => setPalette(false)} /> : null}
    </div>
  )
}

export function App() {
  return (
    <LangProvider>
      <Shell />
    </LangProvider>
  )
}
