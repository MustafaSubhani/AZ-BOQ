import { useEffect, useState } from 'react'
import { useData } from './api'
import { fmt } from './az'
import { LangProvider, useLang, type Lang } from './i18n'
import { go, useRoute } from './router'
import { Bill } from './pages/Bill'
import { DrawingDetail, Drawings } from './pages/Drawings'
import { Conflicts, Coverage, Inputs, NotFound, RunLog, Translations } from './pages/Evidence'
import { Home } from './pages/Home'
import { Operations } from './pages/Operations'
import { Report } from './pages/Report'
import { Takeoff } from './pages/Takeoff'

type Summary = { counts: Record<string, number>; drawings_total: number; conflicts: number; review_items: number; bill: { lines: number } }

const TITLES: Record<string, [string, string]> = {
  home: ['Home', 'Hadrut fire station · order 9335 · drawing-to-bill check'],
  drawings: ['Drawings', 'Every file in the package, how it was read, and its sheets'],
  drawing: ['Drawing', 'One file, sheet by sheet, with the text the check reads from it'],
  takeoff: ['Takeoff', 'What was measured or read from the drawings, with the evidence'],
  bill: ['Bill', 'The client bill, line by line, against the drawings'],
  report: ['Report', 'Differences, gaps and the exports'],
  inputs: ['Inputs ledger', 'Every number the check uses and where it came from'],
  conflicts: ['Conflicts', 'Where two documents disagree; both sides are kept'],
  coverage: ['Coverage', 'Which buildings and trades the package has drawings for'],
  translations: ['Translations', 'English is for reading only; the Azerbaijani is what the check uses'],
  runlog: ['Run log', 'Stages, warnings and the DWG reader cross-check'],
  ops: ['Operations', 'Registers for later checks, seeded from this package only'],
}

function Nav({ to, label, count, hot, current }: { to: string; label: string; count?: number | string; hot?: boolean; current: string }) {
  const on = current === to || (to === 'drawings' && current === 'drawing') || current === to.split('/')[0] + '/' + to.split('/')[1]
  return (
    <button className={`nav ${on ? 'on' : ''}`} onClick={() => go(to)}>
      {label}
      {count !== undefined ? <em className={hot ? 'hot' : ''}>{typeof count === 'number' ? fmt(count) : count}</em> : null}
    </button>
  )
}

function Shell() {
  const route = useRoute()
  const { lang, setLang } = useLang()
  const [theme, setTheme] = useState(() => localStorage.getItem('azboq.theme') || 'light')
  const [find, setFind] = useState('')
  const { data: s } = useData<Summary>('/api/summary')
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('azboq.theme', theme)
  }, [theme])

  const page = route.parts[0]
  const current = page === 'ops' ? `ops/${route.parts[1] || 'drawings'}` : page
  const [title, sub] = TITLES[page] || [page, '']

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

  return (
    <div className="app">
      <aside className="rail">
        <div className="mark">
          <i>H</i>
          <div>
            <b>Hadrut</b>
            <span>Order 9335 · fire station</span>
          </div>
        </div>
        <div className="group">
          <p>Bill check</p>
          <Nav to="home" label="Home" current={current} />
          <Nav to="drawings" label="Drawings" count={s?.drawings_total} current={current} />
          <Nav to="takeoff" label="Takeoff" current={current} />
          <Nav to="bill" label="Bill" count={s?.bill.lines} current={current} />
          <Nav to="report" label="Report" count={s?.counts.different} hot={!!s?.counts.different} current={current} />
        </div>
        <div className="group">
          <p>Evidence</p>
          <Nav to="inputs" label="Inputs ledger" current={current} />
          <Nav to="conflicts" label="Conflicts" count={s?.conflicts} hot={!!s?.conflicts} current={current} />
          <Nav to="coverage" label="Coverage" current={current} />
          <Nav to="translations" label="Translations" current={current} />
          <Nav to="runlog" label="Run log" count={s?.review_items} current={current} />
        </div>
        <div className="group">
          <p>Operations</p>
          <Nav to="ops/drawings" label="Drawing register" current={current} />
          <Nav to="ops/contract_bill" label="Contract bill" current={current} />
          <Nav to="ops/materials" label="Materials" count="—" current={current} />
          <Nav to="ops/measurements" label="Measurements" count="—" current={current} />
          <Nav to="ops/invoices" label="Invoices" count="—" current={current} />
          <Nav to="ops/codes" label="Codes" current={current} />
        </div>
        <div className="foot">
          <i className="ava">FS</i>
          <div>
            <b>Xocavənd</b>
            <span>Depot, tower, tanks, site</span>
          </div>
        </div>
      </aside>
      <div className="stage">
        <header className="top">
          <div className="proj">
            <b>{title}</b>
            <span>{sub}</span>
          </div>
          <form
            className="find"
            onSubmit={(e) => {
              e.preventDefault()
              go('bill', { q: find })
            }}
          >
            <input placeholder="Search the bill (ə = e, ş = s…)" value={find} onChange={(e) => setFind(e.target.value)} />
          </form>
          <div className="right">
            <button className="btn" onClick={() => go('report', { tab: route.query.get('tab') || 'different' })}>Export</button>
            <div className="seg" title="Language of descriptions. Hover any text to see the Azerbaijani original.">
              {(['en', 'az', 'both'] as Lang[]).map((l) => (
                <button key={l} className={lang === l ? 'on' : ''} onClick={() => setLang(l)}>
                  {l === 'both' ? 'Both' : l.toUpperCase()}
                </button>
              ))}
            </div>
            <button className="icon" title="Light or dark" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>◐</button>
          </div>
        </header>
        <main>{body}</main>
      </div>
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
