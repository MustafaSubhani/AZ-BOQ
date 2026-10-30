import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useData } from './api'
import { fmt, matches } from './az'
import { LangProvider, useLang, type Lang } from './i18n'
import {
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
  PushPin,
  PushPinSlash,
  Receipt,
  Ruler,
  Search,
  ShieldCheck,
  SquaresFour,
  Stack,
  Sun,
  Table,
  Translate,
  TreeStructure,
  type Icon,
} from './icons'
import { go, href, useRoute } from './router'
import { Bill } from './pages/Bill'
import { DrawingDetail, Drawings } from './pages/Drawings'
import { Conflicts, Coverage, Inputs, NotFound, RunLog, Translations } from './pages/Evidence'
import { Home } from './pages/Home'
import { Operations } from './pages/Operations'
import { Report } from './pages/Report'
import { Takeoff } from './pages/Takeoff'
import { LINE_STATUS, Ring } from './ui'

type Summary = { counts: Record<string, number>; drawings_total: number; conflicts: number; review_items: number; bill: { lines: number } }

type PageDef = { title: string; desc: string; icon: Icon; group: string; fill?: boolean }

const PAGES: Record<string, PageDef> = {
  home: { title: 'Overview', desc: 'Hadrut fire station · order 9335 · how far the client bill is backed by its own drawings', icon: SquaresFour, group: 'Overview' },
  drawings: { title: 'Drawings', desc: 'Every drawing in the package, how it was read, and the sheets found in it', icon: Stack, group: 'Bill check' },
  drawing: { title: 'Drawing', desc: 'One file, sheet by sheet, with the text the check reads from it', icon: Stack, group: 'Bill check', fill: true },
  takeoff: { title: 'Takeoff', desc: 'What was measured or read from the drawings, with the evidence on the sheet', icon: Ruler, group: 'Bill check', fill: true },
  bill: { title: 'Bill', desc: 'The client bill, line by line, against the drawings', icon: Receipt, group: 'Bill check', fill: true },
  report: { title: 'Report', desc: 'Differences, gaps and the files to hand over', icon: ChartBar, group: 'Bill check' },
  inputs: { title: 'Inputs ledger', desc: 'Every number the check uses and where it came from', icon: TreeStructure, group: 'Evidence' },
  conflicts: { title: 'Conflicts', desc: 'Where two documents disagree; both sides are kept and nothing is averaged', icon: GitDiff, group: 'Evidence', fill: true },
  coverage: { title: 'Coverage', desc: 'Which buildings and trades the package has drawings for', icon: GridFour, group: 'Evidence' },
  translations: { title: 'Translations', desc: 'English is for reading only; the Azerbaijani is what the check uses', icon: Translate, group: 'Evidence', fill: true },
  runlog: { title: 'Run log', desc: 'Pipeline stages, every warning, and the second DWG reader', icon: Pulse, group: 'Evidence' },
  'ops/drawings': { title: 'Drawing register', desc: 'Register seeded from this package, ready for later checks', icon: FolderOpen, group: 'Operations' },
  'ops/contract_bill': { title: 'Contract bill', desc: 'The contract bill as a register for later checks', icon: Table, group: 'Operations' },
  'ops/materials': { title: 'Materials', desc: 'Material deliveries, empty until the site sends them', icon: Package, group: 'Operations' },
  'ops/measurements': { title: 'Measurements', desc: 'Site measurements, empty until the site sends them', icon: Gauge, group: 'Operations' },
  'ops/invoices': { title: 'Invoices', desc: 'Contractor invoices, empty until they are received', icon: Invoice, group: 'Operations' },
  'ops/codes': { title: 'Codes', desc: 'Sections, units, buildings and trades used by the bill', icon: Hash, group: 'Operations' },
}

type NavItem = { to: string; count?: number; hot?: boolean; soon?: boolean }
type NavGroup = { label: string; desc: string; icon: Icon; items: NavItem[]; alert?: boolean }

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
    /* storage can be blocked; the preference just does not stick */
  }
}

function LeafRow({ it, current, onNavigate }: { it: NavItem; current: string; onNavigate: () => void }) {
  const p = PAGES[it.to]
  const Ico = p.icon
  const on = current === it.to
  return (
    <a className={`leaf-row ${on ? 'on' : ''}`} href={href(it.to)} aria-current={on ? 'page' : undefined} onClick={onNavigate}>
      <Ico size={17} weight={on ? 'fill' : 'regular'} />
      <span className="lbl">{p.title}</span>
      {it.soon ? <em className="soon">Empty</em> : it.count !== undefined ? <em className={it.hot ? 'hot' : ''}>{fmt(it.count)}</em> : null}
    </a>
  )
}

/* ── Floating dock (Construction OS): icon rail + a petal of pages beside the hovered group ── */
function Dock({ groups, current, share, checked, lines }: { groups: NavGroup[]; current: string; share: number; checked: number; lines?: number }) {
  const [pinned, setPinned] = useState(() => readPref('azboq.dock', 'float') === 'pinned')
  const [open, setOpen] = useState<string | null>(null)
  const [top, setTop] = useState(0)
  const dock = useRef<HTMLDivElement>(null)
  const leaf = useRef<HTMLDivElement>(null)
  const timer = useRef<number | null>(null)
  const here = groups.find((g) => g.items.some((i) => i.to === current))?.label || null
  const shown = pinned ? null : open
  const group = groups.find((g) => g.label === shown)

  useEffect(() => writePref('azboq.dock', pinned ? 'pinned' : 'float'), [pinned])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  // Keep the petal inside the dock once its real height is known.
  useLayoutEffect(() => {
    const d = dock.current
    const l = leaf.current
    if (!d || !l || pinned) return
    const max = d.clientHeight - l.offsetHeight - 12
    if (top > max) setTop(Math.max(12, max))
  }, [top, shown, pinned])

  const cancel = () => {
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = null
  }
  const later = (fn: () => void, ms: number) => {
    cancel()
    timer.current = window.setTimeout(fn, ms)
  }
  const anchor = (btn: HTMLElement) => {
    const d = dock.current!.getBoundingClientRect()
    const b = btn.getBoundingClientRect()
    return Math.max(12, b.top - d.top - 46)
  }
  const show = (g: NavGroup, btn: HTMLElement) => {
    if (g.items.length < 2) return later(() => setOpen(null), 120)
    const t = anchor(btn)
    later(() => {
      setTop(t)
      setOpen(g.label)
    }, open ? 40 : 90)
  }

  return (
    <div className={`dock ${pinned ? 'pinned' : ''} ${open && !pinned ? 'leaf-open' : ''}`} ref={dock} onMouseLeave={() => later(() => setOpen(null), 220)} onMouseEnter={cancel}>
      <nav className="rail" aria-label="Main navigation">
        {pinned
          ? groups.map((g) =>
              g.items.length === 1 ? (
                <LeafRow key={g.label} it={g.items[0]} current={current} onNavigate={() => {}} />
              ) : (
                <div key={g.label} className="rail-group">
                  <div className="rail-group-label">{g.label}</div>
                  {g.items.map((it) => (
                    <LeafRow key={it.to} it={it} current={current} onNavigate={() => {}} />
                  ))}
                </div>
              ),
            )
          : groups.map((g) => {
              const Ico = g.icon
              const single = g.items.length === 1
              const isHere = here === g.label
              const isOpen = shown === g.label && !single
              const cls = `rail-btn ${isOpen ? 'open' : isHere ? 'here' : ''}`
              const inner = (
                <>
                  <Ico size={19} weight={isOpen || isHere ? 'fill' : 'regular'} />
                  <span className="lbl">{g.label}</span>
                  {g.alert ? <i className="badge" /> : null}
                  <span className="rail-tip">{g.label}</span>
                </>
              )
              return single ? (
                <a key={g.label} className={cls} href={href(g.items[0].to)} aria-current={isHere ? 'page' : undefined} onMouseEnter={(e) => show(g, e.currentTarget)}>
                  {inner}
                </a>
              ) : (
                <button
                  key={g.label}
                  className={cls}
                  aria-expanded={isOpen}
                  onMouseEnter={(e) => show(g, e.currentTarget)}
                  onClick={(e) => {
                    cancel()
                    setTop(anchor(e.currentTarget))
                    setOpen(open === g.label ? null : g.label)
                  }}
                >
                  {inner}
                </button>
              )
            })
        }
        <span className="rail-sep" />
        <a className="rail-ring" href={href('bill', { status: 'checked' })} title={`${fmt(checked)} of ${fmt(lines)} bill lines are backed by a drawing`}>
          <Ring value={share} size={36} stroke={4} label={lines ? `${Math.round(share * 100)}%` : '…'} />
          <span className="txt">
            <b>{Math.round(share * 100)}% backed</b>
            <span>{fmt(checked)} of {fmt(lines)} lines</span>
          </span>
        </a>
        <button className="rail-btn" onClick={() => setPinned((p) => !p)} aria-pressed={pinned} title={pinned ? 'Let the menu float' : 'Keep the menu open'}>
          {pinned ? <PushPinSlash size={17} /> : <PushPin size={17} />}
          <span className="lbl">{pinned ? 'Unpin menu' : 'Pin menu'}</span>
          <span className="rail-tip">Pin menu</span>
        </button>
      </nav>
      {group ? (
        <div className="leaf" ref={leaf} style={{ top }} onMouseEnter={cancel} key={group.label}>
          <div className="leaf-head">
            <b>{group.label}</b>
            <span>{group.desc}</span>
          </div>
          {group.items.map((it) => (
            <LeafRow key={it.to} it={it} current={current} onNavigate={() => !pinned && setOpen(null)} />
          ))}
        </div>
      ) : null}
    </div>
  )
}

/* ── Command palette (Ctrl+K) ─────────────────────── */
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
      out.push({ key: `p:${k}`, group: 'Screens', icon: <Ico size={16} />, title: p.title, sub: p.group, run: () => go(k) })
      if (!q && out.length >= 6) break
    }
    if (q.trim().length >= 2) {
      const items = (take.data?.items || []).filter((i) => matches(q, i.id, i.label_en, i.label_az)).slice(0, 5)
      for (const i of items) out.push({ key: `t:${i.id}`, group: 'Measured items', icon: <Ruler size={16} />, title: i.label_en, sub: i.label_az, right: i.unit, run: () => go('takeoff', { item: i.id }) })
      const lines = (bill.data?.lines || []).filter((l) => matches(q, l.id, l.description)).slice(0, 8)
      for (const l of lines)
        out.push({ key: `b:${l.id}`, group: 'Bill lines', icon: <Receipt size={16} />, title: l.description, sub: `Line ${l.id} · ${(l.check && LINE_STATUS[l.check.status]?.label) || 'not checked'}`, right: `${fmt(l.qty, 3)} ${l.unit}`, run: () => go('bill', { line: l.id }) })
      out.push({ key: 'all', group: 'Bill lines', icon: <Search size={16} />, title: `Search the whole bill for “${q.trim()}”`, sub: 'Opens the bill filtered to every match', run: () => go('bill', { q: q.trim() }) })
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
      <div className="palette" role="dialog" aria-label="Search" onMouseDown={(e) => e.stopPropagation()}>
        <div className="in">
          <Search size={18} />
          <input
            autoFocus
            placeholder="Search screens, bill lines, measured items… (ə = e, ş = s)"
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setAt(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setAt((a) => Math.min(a + 1, hits.length - 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                setAt((a) => Math.max(a - 1, 0))
              } else if (e.key === 'Enter') pick(hits[at])
              else if (e.key === 'Escape') onClose()
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
                    <b lang={h.group === 'Bill lines' && h.key !== 'all' ? 'az' : undefined}>{h.title}</b>
                    {h.sub ? <span>{h.sub}</span> : null}
                  </span>
                  {h.right ? <span className="r">{h.right}</span> : <span />}
                </button>
              </div>
            )
          })}
          {!hits.length ? <div className="empty-state">Nothing matches “{q}”.</div> : null}
          {q.trim().length >= 2 && !bill.data ? <div className="grp">Loading the bill…</div> : null}
        </div>
        <div className="foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> move</span>
          <span><kbd><EnterKey size={11} /></kbd> open</span>
          <span style={{ marginLeft: 'auto' }}>Azerbaijani letters fold: ə to e, ı to i, ş to s</span>
        </div>
      </div>
    </div>
  )
}

function PageHead({ def }: { def: PageDef }) {
  const Ico = def.icon
  return (
    <div className="page-head">
      <span className="well accent">
        <Ico size={22} weight="duotone" />
      </span>
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
  const [theme, setTheme] = useState(() => readPref('azboq.theme', window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
  const [menu, setMenu] = useState(false)
  const [palette, setPalette] = useState(false)
  const { data: s } = useData<Summary>('/api/summary')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    writePref('azboq.theme', theme)
  }, [theme])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
        e.preventDefault()
        setPalette(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const page = route.parts[0]
  const current = page === 'ops' ? `ops/${route.parts[1] || 'drawings'}` : page
  const def = PAGES[current] || { title: page, desc: '', icon: SquaresFour, group: '' }
  const navCurrent = current === 'drawing' ? 'drawings' : current
  useEffect(() => {
    document.title = `${def.title} · Hadrut · AZ-Takeoff`
  }, [def.title])

  let body
  switch (page) {
    case 'home': body = <Home />; break
    case 'drawings': body = <Drawings route={route} />; break
    case 'drawing': body = <DrawingDetail route={route} />; break
    case 'takeoff': body = <Takeoff route={route} />; break
    case 'bill': body = <Bill key={route.query.get('q') || ''} route={route} />; break
    case 'report': body = <Report route={route} />; break
    case 'inputs': body = <Inputs />; break
    case 'conflicts': body = <Conflicts />; break
    case 'coverage': body = <Coverage />; break
    case 'translations': body = <Translations />; break
    case 'runlog': body = <RunLog />; break
    case 'ops': body = <Operations route={route} />; break
    default: body = <NotFound route={route} />
  }

  const checked = s ? (s.counts.matched || 0) + (s.counts.printed || 0) + (s.counts.derived || 0) : 0
  const share = s ? checked / (s.bill.lines || 1) : 0
  const groups: NavGroup[] = [
    { label: 'Overview', desc: 'The whole check on one page', icon: SquaresFour, items: [{ to: 'home' }] },
    {
      label: 'Bill check',
      desc: 'Drawings, measurements and the client bill',
      icon: Receipt,
      alert: !!s?.counts.different,
      items: [{ to: 'drawings', count: s?.drawings_total }, { to: 'takeoff' }, { to: 'bill', count: s?.bill.lines }, { to: 'report', count: s?.counts.different, hot: !!s?.counts.different }],
    },
    {
      label: 'Evidence',
      desc: 'Where every number came from',
      icon: ShieldCheck,
      alert: !!s?.conflicts,
      items: [{ to: 'inputs' }, { to: 'conflicts', count: s?.conflicts, hot: !!s?.conflicts }, { to: 'coverage' }, { to: 'translations' }, { to: 'runlog', count: s?.review_items }],
    },
    {
      label: 'Operations',
      desc: 'Registers for later checks',
      icon: FolderOpen,
      items: [{ to: 'ops/drawings' }, { to: 'ops/contract_bill' }, { to: 'ops/materials', soon: true }, { to: 'ops/measurements', soon: true }, { to: 'ops/invoices', soon: true }, { to: 'ops/codes' }],
    },
  ]

  return (
    <div className="app">
      <header className="top">
        <button className="icon menu-btn" onClick={() => setMenu(true)} aria-label="Open navigation">
          <List size={18} />
        </button>
        <a className="brand" href={href('home')}>
          <span className="logo">
            <Ruler size={17} weight="bold" />
          </span>
          <span className="word">
            <b>AZ<em>-</em>Takeoff</b>
            <small>Drawing-to-bill check</small>
          </span>
        </a>
        <nav className="crumbs" aria-label="Breadcrumb">
          <a href={href('home')}>Hadrut</a>
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
        <button className="find" onClick={() => setPalette(true)} title="Search (Ctrl+K)">
          <Search size={16} />
          <span>Search the bill, items, screens…</span>
          <kbd>Ctrl K</kbd>
        </button>
        <div className="right">
          <div className="seg" title="Language of descriptions. Hover any text to see the Azerbaijani original.">
            {(['en', 'az', 'both'] as Lang[]).map((l) => (
              <button key={l} className={lang === l ? 'on' : ''} onClick={() => setLang(l)}>
                {l === 'both' ? 'Both' : l.toUpperCase()}
              </button>
            ))}
          </div>
          <button className="icon" title={theme === 'dark' ? 'Light theme' : 'Dark theme'} aria-label="Toggle theme" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
          </button>
          <a className="btn" href={href('report', { tab: route.query.get('tab') || 'different' })}>
            <Download size={16} />
            <span>Exports</span>
          </a>
        </div>
      </header>
      <div className="body">
        <Dock groups={groups} current={navCurrent} share={share} checked={checked} lines={s?.bill.lines} />
        <main key={current + (route.parts[1] || '')} className={`page-in ${def.fill ? 'fill' : ''}`}>
          {page !== 'home' ? <PageHead def={def} /> : null}
          {body}
        </main>
      </div>
      {menu ? (
        <>
          <div className="drawer-back" onClick={() => setMenu(false)} />
          <nav className="drawer" aria-label="Main navigation">
            {groups.map((g) => (
              <div key={g.label}>
                <div className="grp-label">{g.label}</div>
                {g.items.map((it) => (
                  <LeafRow key={it.to} it={it} current={navCurrent} onNavigate={() => setMenu(false)} />
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
