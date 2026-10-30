import { useEffect, useMemo, useState } from 'react'
import { Cube, FileText, FileX, Scan, Search, Stack, Warning } from '../icons'
import { getJSON, useData } from '../api'
import { fmt, matches } from '../az'
import { T } from '../i18n'
import { sheetCount, useRegister, type FileRow, type Sheet } from '../register'
import { go, href, type Route } from '../router'
import { Card, Empty, ErrorBox, Loading, shortFile, useBuildingName, type Target } from '../ui'
import { openTab, visibleTabs, type Tab } from '../tabs'
import { Viewer, type SheetShape } from '../Viewer'

const KIND_LABEL: Record<string, string> = { drawing_cad: 'DWG', drawing_pdf: 'PDF', drawing_scan: 'Scan' }
const KIND_CLS: Record<string, string> = { drawing_cad: 'dwg', drawing_pdf: 'pdf', drawing_scan: 'scan' }
const DISCIPLINES: Record<string, string> = {
  architecture: 'Architecture',
  structure: 'Structure',
  water_sewer: 'Water and sewer',
  hvac: 'Heating and ventilation',
  construction_org: 'Construction organisation',
  electrical: 'Electrical',
  low_current: 'Fire alarm and low current',
  site: 'Site, grading and roads',
  general: 'General notes',
  gas: 'Gas',
}

function readTag(f: FileRow) {
  if (f.kind === 'drawing_scan') return <span className="tag warn" title="No vectors or text layer; nothing is matched from it automatically">Scan, review only</span>
  if (f.kind === 'drawing_pdf') return <span className="tag ok">Text layer read</span>
  if (f.read_status === 'read') return <span className="tag ok">Read, readers agree</span>
  if (f.read_status === 'reader disagreement') return <span className="tag warn" title="ODA and LibreDWG see different entity counts; values from this file go to review">Reader disagreement</span>
  if (!f.read_status) return <span className="tag muted">Not converted</span>
  return <span className="tag bad">{f.read_status}</span>
}

function Degraded({ why }: { why: string | null }) {
  if (!why) return null
  return (
    <div className="banner" title={why}>
      <Warning size={16} style={{ flex: 'none', marginTop: 1 }} />
      <span>
        <b>Built from the caches.</b> The full register reads the raw package (<span className="mono">data/</span>), which is not on this machine, so file sizes and scan page lists are missing. Everything the check found is still here.
      </span>
    </div>
  )
}

export function Drawings({ route }: { route: Route }) {
  const { data, error, degraded } = useRegister()
  const filter = route.query.get('filter') || 'all'
  const [q, setQ] = useState('')
  const bname = useBuildingName()
  const drawings = useMemo(() => (data ? data.files.filter((f) => f.kind.startsWith('drawing')) : []), [data])
  const others = useMemo(() => (data ? data.files.filter((f) => !f.kind.startsWith('drawing')) : []), [data])
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the drawing register" />

  const shown = drawings.filter((f) => {
    if (filter === 'dwg' && f.kind !== 'drawing_cad') return false
    if (filter === 'pdf' && f.kind !== 'drawing_pdf') return false
    if (filter === 'scan' && f.kind !== 'drawing_scan') return false
    if (filter === 'disagree' && f.read_status !== 'reader disagreement') return false
    return matches(q, f.rel, f.building, f.discipline, ...(f.sheets || []).map((s) => s.title || ''))
  })
  const groups = new Map<string, FileRow[]>()
  for (const f of shown) {
    const k = f.discipline || 'general'
    groups.set(k, [...(groups.get(k) || []), f])
  }
  const count = (kind: string) => drawings.filter((f) => f.kind === kind).length
  const disagree = drawings.filter((f) => f.read_status === 'reader disagreement').length
  const chips: [string, string, number][] = [
    ['all', 'All', drawings.length],
    ['dwg', 'DWG', count('drawing_cad')],
    ['pdf', 'PDF', count('drawing_pdf')],
    ['scan', 'Scans', count('drawing_scan')],
    ['disagree', 'Reader disagreement', disagree],
  ]
  const sheetsTotal = drawings.reduce((n, f) => n + sheetCount(f), 0)

  return (
    <>
      <Degraded why={degraded} />
      <div className="strip">
        <button className="kpi" onClick={() => go('drawings')}>
          <div className="k"><Stack size={14} /> Drawings</div>
          <div className="v num">{drawings.length}</div>
          <div className="s">{fmt(sheetsTotal)} sheets found in them</div>
        </button>
        <button className="kpi" onClick={() => go('drawings', { filter: 'dwg' })}>
          <div className="k"><Cube size={14} /> DWG files</div>
          <div className="v num">{count('drawing_cad')}</div>
          <div className="s">Converted with ODA, re-read with LibreDWG</div>
        </button>
        <button className="kpi" onClick={() => go('drawings', { filter: 'pdf' })}>
          <div className="k"><FileText size={14} /> PDF drawings</div>
          <div className="v num">{count('drawing_pdf')}</div>
          <div className="s">Text layer read directly</div>
        </button>
        <button className="kpi" onClick={() => go('drawings', { filter: 'scan' })}>
          <div className="k"><Scan size={14} /> Scans</div>
          <div className="v num">{count('drawing_scan')}</div>
          <div className="s">No text layer; review only</div>
        </button>
        <button className={`kpi ${disagree ? 'accent' : ''}`} onClick={() => go('drawings', { filter: 'disagree' })}>
          <div className="k"><FileX size={14} /> Reader disagreement</div>
          <div className="v num">{disagree}</div>
          <div className="s">Values from these go to review</div>
        </button>
      </div>
      <Card>
        <div className="toolbar" style={{ borderBottom: 0 }}>
          <div className="chips">
            {chips.map(([k, label, n]) => (
              <button key={k} className={`chip ${filter === k ? 'on' : ''}`} onClick={() => go('drawings', { filter: k === 'all' ? null : k })}>
                {label} <b>{n}</b>
              </button>
            ))}
          </div>
          <label className="field" style={{ marginLeft: 'auto' }}>
            <Search size={15} />
            <input placeholder="Search file, building or sheet title" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
        </div>
      </Card>
      {!shown.length ? <Empty icon={<Search size={20} />} title="No drawing matches">Try another filter or search word.</Empty> : null}
      {[...groups.entries()].map(([disc, files]) => (
        <div key={disc} className="stack" style={{ gap: 10 }}>
          <div className="group-title">
            <b>{DISCIPLINES[disc] || disc}</b>
            <span>
              {files.length} {files.length === 1 ? 'file' : 'files'}
            </span>
          </div>
          <div className="files">
            {files.map((f) => {
              const n = sheetCount(f)
              const inner = (
                <>
                  <div className="top-row">
                    <span className={`pill ${KIND_CLS[f.kind] || ''}`}>{KIND_LABEL[f.kind]}</span>
                    {readTag(f)}
                  </div>
                  <span className="name" lang="az">{shortFile(f.rel)}</span>
                  <div className="meta">
                    <span>
                      <Stack size={12} /> {n ? `${n} ${n === 1 ? 'sheet' : 'sheets'}` : 'no sheets found'}
                    </span>
                    <span>{bname(f.building)}</span>
                    {f.oda?.modelspace_entities ? <span className="mono">{fmt(f.oda.modelspace_entities)} entities</span> : null}
                  </div>
                  <div className="path" lang="az" title={f.rel}>
                    {f.rel.split('/').slice(1, -1).join(' / ')}
                  </div>
                </>
              )
              return f.sha256 ? (
                <a key={f.rel} className="file" href={href(`drawing/${f.sha256.slice(0, 12)}`)}>
                  {inner}
                </a>
              ) : (
                <div key={f.rel} className="file dead" title="No stage of the check cites this file, so there is no sheet to open">
                  {inner}
                </div>
              )
            })}
          </div>
        </div>
      ))}
      {others.length ? (
        <Card title={`Other files in the package · ${others.length}`}>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>File</th><th>Kind</th><th>Note</th></tr>
              </thead>
              <tbody>
                {others.map((f) => (
                  <tr key={f.sha256 || f.rel}>
                    <td lang="az">{f.rel}</td>
                    <td><span className="pill">{f.kind.replace(/_/g, ' ')}</span></td>
                    <td className="muted">{f.note || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </>
  )
}

function ScanReading({ file, page, vision }: { file: FileRow; page: number; vision: { model: string | null; files: any[] } | null }) {
  const v = vision?.files.find((f) => f.sha256 === file.sha256)
  if (!v || v.status === 'not run')
    return (
      <div className="box warn">
        <small>Scan, not read</small>
        This file is a scan with no text layer. {v?.reason ? `The vision reader did not run: ${v.reason}.` : 'The vision reader has not run.'} Nothing on it is matched automatically; its bill lines stay unchecked or in review.
      </div>
    )
  const p = v.pages.find((x: any) => x.page === page)
  if (!p) return <div className="box">No transcription for this page.</div>
  if (p.status === 'failed') return <div className="box bad"><small>Vision read failed</small>{p.error}</div>
  const r = p.result || {}
  return (
    <div className="box info">
      <small>Read by {vision?.model} · for review only</small>
      {r.sheet_number ? <div><b>{r.sheet_number}</b></div> : null}
      {r.title ? <div lang="az">{r.title}</div> : null}
      {(r.lines || []).slice(0, 30).map((l: string, i: number) => <div key={i} lang="az" style={{ fontSize: 12 }}>{l}</div>)}
      {(r.tables || []).map((t: any, i: number) => (
        <table key={i} style={{ marginTop: 6, fontSize: 11.5 }}>
          <tbody>{(t.rows || []).slice(0, 40).map((row: string[], j: number) => <tr key={j}>{row.map((c, k) => <td key={k} lang="az">{c}</td>)}</tr>)}</tbody>
        </table>
      ))}
      {r.unreadable?.length ? <div className="note warn">unreadable: {r.unreadable.join('; ')}</div> : null}
    </div>
  )
}

/** Sheets of one file: from the register when it has them, else from the DWG region list or the known page count. */
function useSheets(file: FileRow | undefined, sha: string): Sheet[] {
  const [regions, setRegions] = useState<Sheet[] | null>(null)
  const need = !!file && !file.sheets && file.kind === 'drawing_cad' && !!file.sha256
  useEffect(() => {
    if (!need) return
    let alive = true
    getJSON<{ regions: Sheet[] }>(`/api/drawing/${sha}/regions`)
      .then((r) => alive && setRegions(r.regions))
      .catch(() => alive && setRegions([]))
    return () => {
      alive = false
    }
  }, [need, sha])
  if (!file) return []
  if (file.sheets) return file.sheets
  if (file.kind === 'drawing_cad') return regions || []
  return Array.from({ length: file.sheet_count || 1 }, (_, page) => ({ page, building: file.building, kind: file.kind === 'drawing_scan' ? 'scan' : undefined }))
}

export function DrawingDetail({ route }: { route: Route }) {
  const sha = route.parts[1]
  const { data, error } = useRegister()
  const vision = useData<{ model: string | null; files: { sha256: string; status: string; reason?: string; pages: any[] }[] }>('/api/vision')
  const [texts, setTexts] = useState<{ key: string; text: string; target: Target }[]>([])
  const [q, setQ] = useState('')
  const [shapes, setShapes] = useState<SheetShape[]>([])
  const [banner, setBanner] = useState<string | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const [tabs, setTabs] = useState<Tab[]>([])
  const [mru, setMru] = useState<string[]>([])
  const [showCopies, setShowCopies] = useState(false)
  const bname = useBuildingName()
  const file = data?.files.find((f) => f.sha256 && f.sha256.startsWith(sha))
  const sheets = useSheets(file, sha)
  const isPdf = file?.kind !== 'drawing_cad'
  const sheetParam = route.query.get('sheet')
  const regionId = !isPdf && sheets.length ? sheetParam || sheets[0]?.id || null : null
  useEffect(() => {
    if (!file || isPdf || !regionId) {
      setShapes([])
      setBanner(null)
      return
    }
    let alive = true
    getJSON<{ shapes: SheetShape[]; banner?: string }>(`/api/drawing/${sha}/region/${regionId}/shapes`)
      .then((row) => {
        if (!alive) return
        setShapes(row.shapes || [])
        setBanner(row.banner || null)
        setPicked(null)
      })
      .catch(() => alive && setShapes([]))
    return () => {
      alive = false
    }
  }, [sha, regionId, isPdf, file])
  useEffect(() => {
    if (!regionId) return
    const sheet = sheets.find((item) => item.id === regionId)
    const num = typeof sheet?.number === 'string' ? sheet.number : sheet?.number?.raw
    setTabs((prev) => openTab(prev, { key: regionId, title: String(num || regionId), pinned: true }, false))
    setMru((prev) => [regionId, ...prev.filter((key) => key !== regionId)].slice(0, 24))
  }, [regionId, sheets])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'w') {
        e.preventDefault()
        setTabs((prev) => prev.filter((tab) => tab.key !== regionId))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [regionId])
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the drawing" />
  if (!file) return <ErrorBox error={`No drawing with the id ${sha} in this package.`} />
  const at = route.query.get('at')
  const current: Target | null = isPdf
    ? { kind: 'pdf', sha, page: Number(sheetParam ?? sheets[0]?.page ?? 0), bbox: at ? at.split(',').map(Number) : null }
    : sheets.length
      ? { kind: 'dwg', sha, region: regionId, at: at ? at.split(',').map(Number) : null }
      : null
  const curId = current ? (current.kind === 'pdf' ? String(current.page) : current.region) : null
  const shownTexts = texts.filter((t) => matches(q, t.text))
  const { shown: shownTabs, overflow } = visibleTabs(tabs, regionId || '', mru)
  const pickedShape = shapes.find((shape) => shape.id === picked) || null
  const copyCount = sheets.filter((s) => s.copy_of).length

  return (
    <>
      <div className="work">
        <Card title={<span>Sheets</span>} sub={<a href={href('drawings')}>← all drawings</a>} right={<span className="tag bare">{sheets.length}</span>}>
          <div className="rows">
            {sheets.map((s, i) => {
              if (s.copy_of && !showCopies) return null
              const id = isPdf ? String(s.page ?? i) : s.id!
              const num = typeof s.number === 'string' ? s.number : s.number?.raw
              return (
                <button key={id} className={`list-item ${id === curId ? 'on' : ''}`} onClick={() => go(`drawing/${sha}`, { sheet: id })}>
                  <span className="t">
                    {num || (isPdf ? `Page ${Number(id) + 1}` : `Sheet ${id}`)}
                    {!num && !isPdf ? <span className="faint"> · no number in the stamp</span> : null}
                  </span>
                  <span className="q muted" title="Scale estimated from the frame size">
                    {typeof s.scale === 'number' ? `≈1:${Math.round(s.scale)}` : s.scale || s.paper || ''}
                  </span>
                  <span className="m">
                    {s.title ? <T az={s.title} /> : <span className="faint">no title found</span>}
                    <span style={{ display: 'block' }}>
                      {bname(s.building)}
                      {s.discipline ? ` · ${s.discipline}` : ''}
                      {s.kind ? ` · ${s.kind}` : ''}
                    </span>
                  </span>
                </button>
              )
            })}
            {!sheets.length ? <Empty icon={<Stack size={20} />} title="No sheets">No sheets were detected in this file. It is listed so the gap is visible.</Empty> : null}
            {copyCount ? <button className="list-item" onClick={() => setShowCopies((v) => !v)}><span className="t">{showCopies ? 'Hide copies' : `${copyCount} copies of other sheets`}</span></button> : null}
          </div>
        </Card>
        <Card title={<span lang="az">{shortFile(file.rel)}</span>} sub={<span lang="az">{file.rel.split('/').slice(0, -1).join(' / ')}</span>} right={<span className={`pill ${KIND_CLS[file.kind] || ''}`}>{KIND_LABEL[file.kind]}</span>}>
          {!isPdf && shownTabs.length ? (
            <div className="tabbar">
              {shownTabs.map((tab) => (
                <button key={tab.key} className={`tab ${tab.key === regionId ? 'on' : ''} ${tab.pinned ? '' : 'preview'}`} title={tab.title} onClick={() => go(`drawing/${sha}`, { sheet: tab.key })}>
                  {tab.title}
                </button>
              ))}
              {overflow.length ? (
                <select aria-label="More sheets" value="" onChange={(e) => e.target.value && go(`drawing/${sha}`, { sheet: e.target.value })}>
                  <option value="">{`+${overflow.length}`}</option>
                  {overflow.map((tab) => <option key={tab.key} value={tab.key}>{tab.title}</option>)}
                </select>
              ) : null}
            </div>
          ) : null}
          {banner ? <div className="banner">{banner}</div> : null}
          <Viewer target={current} shapes={shapes} selectedShape={picked} onShape={setPicked} onMeta={(m, t) => {
              if (!m || !t) return setTexts([])
              if (m.texts) setTexts(m.texts.filter((x) => x.text.trim()).map((x) => ({ key: x.handle, text: x.text, target: { ...(t as any), at: x.at, handle: x.handle } })))
              else if (m.lines) setTexts(m.lines.map((l, i) => ({ key: String(i), text: l.text, target: { ...(t as any), bbox: l.bbox } })))
              else setTexts([])
            }}
          />
        </Card>
        <Card title="About this file">
          <div className="insp">
            {pickedShape ? (
              <div className="box">
                <small>{pickedShape.kind === 'area_unlinked' ? 'Area, no room tag inside' : pickedShape.kind === 'area_conflict' ? 'More than one room tag' : 'Room'}</small>
                <div>{pickedShape.label}</div>
                <div className="mono">{pickedShape.area_m2 == null ? 'area not scaled' : `${pickedShape.area_m2.toFixed(2)} m² hatch`}{pickedShape.schedule_m2 != null ? ` · schedule ${pickedShape.schedule_m2} m²` : ''}</div>
                {pickedShape.lines?.length ? <div>Bill lines {pickedShape.lines.map((id) => <a key={id} href={href('bill', { line: id })} className="mono"> {id}</a>)}</div> : null}
              </div>
            ) : null}
            <div className="pair"><span>Kind</span><span className={`pill ${KIND_CLS[file.kind] || ''}`}>{KIND_LABEL[file.kind] || file.kind}</span></div>
            <div className="pair"><span>Building</span><span>{bname(file.building)}</span></div>
            <div className="pair"><span>Read</span>{readTag(file)}</div>
            {file.oda ? (
              <>
                <div className="pair"><span>ODA conversion</span><span className="mono">{file.oda.status} · {file.oda.acadver} · {file.oda.seconds}s</span></div>
                <div className="pair"><span>Entities (ODA / LibreDWG)</span><span className="mono">{fmt(file.crosscheck?.oda_total)} / {fmt(file.crosscheck?.libredwg_total)}</span></div>
              </>
            ) : null}
            {file.crosscheck?.type_diffs?.length ? (
              <div className="box warn">
                <small>Readers disagree on</small>
                {file.crosscheck.type_diffs.slice(0, 6).map((d: any) => (
                  <div key={d.type} className="mono" style={{ fontSize: 12 }}>
                    {d.type}: ODA {fmt(d.oda)} · LibreDWG {fmt(d.libredwg)}
                  </div>
                ))}
                {file.crosscheck.libredwg_error ? <div>LibreDWG: {file.crosscheck.libredwg_error}</div> : null}
              </div>
            ) : null}
            {file.kind === 'drawing_scan' ? <ScanReading file={file} page={current?.kind === 'pdf' ? current.page : 0} vision={vision.data} /> : null}
            <div className="section-label">
              <span className="eyebrow">Text on this sheet · {texts.length}</span>
            </div>
            <label className="field" style={{ width: '100%', marginTop: 8, minWidth: 0 }}>
              <Search size={14} />
              <input placeholder="Find text (ə = e, ş = s…)" value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
            <div style={{ marginTop: 4 }}>
              {shownTexts.slice(0, 250).map((t, i) => (
                <button
                  key={`${t.key}-${i}`}
                  className="src"
                  onClick={() => {
                    const tg = t.target
                    if (tg.kind === 'dwg') go(`drawing/${sha}`, { sheet: tg.region, at: tg.at?.join(',') })
                    else go(`drawing/${sha}`, { sheet: tg.page, at: tg.bbox?.join(',') })
                  }}
                >
                  <T az={t.text} />
                </button>
              ))}
              {shownTexts.length > 250 ? <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>Showing 250 of {fmt(shownTexts.length)}; search to narrow.</div> : null}
            </div>
          </div>
        </Card>
      </div>
    </>
  )
}
