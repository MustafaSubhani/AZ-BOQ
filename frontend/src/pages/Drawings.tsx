import { useMemo, useState } from 'react'
import { useData } from '../api'
import { fmt, matches } from '../az'
import { T } from '../i18n'
import { go, href, type Route } from '../router'
import { Card, ErrorBox, Loading, shortFile, useBuildingName, type Target } from '../ui'
import { Viewer } from '../Viewer'

type Sheet = { id?: string; page?: number; number?: any; building?: string | null; discipline?: string | null; title?: string | null; scale?: string | number | null; paper?: string | null; method?: string; text_count?: number; kind?: string }
type FileRow = {
  sha256: string
  rel: string
  name: string
  kind: string
  ext: string
  size: number
  discipline?: string | null
  building?: string | null
  order?: string | null
  read_status?: string
  crosscheck?: any
  oda?: any
  sheets?: Sheet[]
  note?: string | null
}
type Register = { files: FileRow[]; counts: Record<string, number>; total: number; duplicates: any[] }

const KIND_LABEL: Record<string, string> = { drawing_cad: 'DWG', drawing_pdf: 'PDF', drawing_scan: 'Scan' }
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
  return <span className="tag bad">{f.read_status || 'not read'}</span>
}

export function Drawings({ route }: { route: Route }) {
  const { data, error } = useData<Register>('/api/register')
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
  const chips: [string, string, number][] = [
    ['all', 'All', drawings.length],
    ['dwg', 'DWG', drawings.filter((f) => f.kind === 'drawing_cad').length],
    ['pdf', 'PDF', drawings.filter((f) => f.kind === 'drawing_pdf').length],
    ['scan', 'Scans', drawings.filter((f) => f.kind === 'drawing_scan').length],
    ['disagree', 'Reader disagreement', drawings.filter((f) => f.read_status === 'reader disagreement').length],
  ]

  return (
    <>
      <Card>
        <div className="toolbar" style={{ borderBottom: 0 }}>
          {chips.map(([k, label, n]) => (
            <button key={k} className={`chip ${filter === k ? 'on' : ''}`} onClick={() => go('drawings', { filter: k })}>
              {label} <b>{n}</b>
            </button>
          ))}
          <input className="search" placeholder="Search file, building or sheet title" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginLeft: 'auto' }} />
        </div>
      </Card>
      {[...groups.entries()].map(([disc, files]) => (
        <div key={disc}>
          <div className="eyebrow" style={{ margin: '4px 6px 8px' }}>
            {DISCIPLINES[disc] || disc} · {files.length}
          </div>
          <div className="files">
            {files.map((f) => (
              <a key={f.sha256} className="file" href={href(`drawing/${f.sha256.slice(0, 12)}`)} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="pill">{KIND_LABEL[f.kind]}</span>
                  {readTag(f)}
                </div>
                <b lang="az">{shortFile(f.rel)}</b>
                <div className="meta">
                  {bname(f.building)} · {f.sheets ? `${f.sheets.length} sheets` : 'no sheets found'}
                  {f.oda?.modelspace_entities ? ` · ${fmt(f.oda.modelspace_entities)} entities` : ''}
                </div>
                <div className="meta faint" lang="az">{f.rel.split('/').slice(1, -1).join(' / ')}</div>
              </a>
            ))}
          </div>
        </div>
      ))}
      <Card title={`Other files in the package · ${others.length}`}>
        <table>
          <thead>
            <tr><th>File</th><th>Kind</th><th>Note</th></tr>
          </thead>
          <tbody>
            {others.map((f) => (
              <tr key={f.sha256}>
                <td lang="az">{f.rel}</td>
                <td>{f.kind.replace(/_/g, ' ')}</td>
                <td className="muted">{f.note || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
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
      {r.unreadable?.length ? <div className="tag warn">unreadable: {r.unreadable.join('; ')}</div> : null}
    </div>
  )
}

export function DrawingDetail({ route }: { route: Route }) {
  const sha = route.parts[1]
  const { data, error } = useData<Register>('/api/register')
  const vision = useData<{ model: string | null; files: { sha256: string; status: string; reason?: string; pages: any[] }[] }>('/api/vision')
  const [texts, setTexts] = useState<{ key: string; text: string; target: Target }[]>([])
  const [q, setQ] = useState('')
  const bname = useBuildingName()
  const file = data?.files.find((f) => f.sha256.startsWith(sha))
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the drawing" />
  if (!file) return <ErrorBox error="no such file" />
  const isPdf = file.kind !== 'drawing_cad'
  const sheets = file.sheets || []
  const sheetParam = route.query.get('sheet')
  const at = route.query.get('at')
  const current: Target | null = isPdf
    ? { kind: 'pdf', sha, page: Number(sheetParam ?? sheets[0]?.page ?? 0), bbox: at ? at.split(',').map(Number) : null }
    : sheets.length
      ? { kind: 'dwg', sha, region: sheetParam || sheets[0].id || null, at: at ? at.split(',').map(Number) : null }
      : null
  const curId = current ? (current.kind === 'pdf' ? String(current.page) : current.region) : null

  return (
    <div className="work" style={{ gridTemplateColumns: '300px minmax(0, 1fr) 340px' }}>
      <Card title={<span><a href={href('drawings')}>Drawings</a> / sheets</span>} right={<span className="muted">{sheets.length}</span>}>
        <div className="rows">
          {sheets.map((s, i) => {
            const id = isPdf ? String(s.page ?? i) : s.id!
            const num = typeof s.number === 'string' ? s.number : s.number?.raw
            return (
              <button key={id} className={`list-item ${id === curId ? 'on' : ''}`} onClick={() => go(`drawing/${sha}`, { sheet: id })}>
                <span className="t">{num || (isPdf ? `Page ${Number(id) + 1}` : `Sheet ${id}`)}{!num && !isPdf ? <span className="faint" style={{ fontWeight: 500 }}> · no number in the stamp</span> : null}</span>
                <span className="q muted" style={{ fontWeight: 500, fontSize: 12 }} title="Scale estimated from the frame size">
                  {typeof s.scale === 'number' ? `≈1:${Math.round(s.scale)}` : s.scale || s.paper || ''}
                </span>
                <span className="m">
                  {s.title ? <T az={s.title} /> : <span className="faint">no title found</span>}
                  <span style={{ display: 'block' }}>{bname(s.building)}{s.discipline ? ` · ${s.discipline}` : ''}{s.kind ? ` · ${s.kind}` : ''}</span>
                </span>
              </button>
            )
          })}
          {!sheets.length ? <div className="empty-state">No sheets were detected in this file. It is listed so the gap is visible.</div> : null}
        </div>
      </Card>
      <Card title={<span lang="az">{shortFile(file.rel)}</span>}>
        <Viewer
          target={current}
          onMeta={(m, t) => {
            if (!m || !t) return setTexts([])
            if (m.texts)
              setTexts(m.texts.filter((x) => x.text.trim()).map((x) => ({ key: x.handle, text: x.text, target: { ...(t as any), at: x.at, handle: x.handle } })))
            else if (m.lines) setTexts(m.lines.map((l, i) => ({ key: String(i), text: l.text, target: { ...(t as any), bbox: l.bbox } })))
            else setTexts([])
          }}
        />
      </Card>
      <Card title="About this file">
        <div className="insp">
          <div className="pair"><span>Kind</span><span>{KIND_LABEL[file.kind] || file.kind}</span></div>
          <div className="pair"><span>Building</span><span>{bname(file.building)}</span></div>
          <div className="pair"><span>Read</span>{readTag(file)}</div>
          {file.oda ? (
            <>
              <div className="pair"><span>ODA conversion</span><span>{file.oda.status} · {file.oda.acadver} · {file.oda.seconds}s</span></div>
              <div className="pair"><span>Entities (ODA / LibreDWG)</span><span className="num">{fmt(file.crosscheck?.oda_total)} / {fmt(file.crosscheck?.libredwg_total)}</span></div>
            </>
          ) : null}
          {file.crosscheck?.type_diffs?.length ? (
            <div className="box warn">
              <small>Readers disagree on</small>
              {file.crosscheck.type_diffs.slice(0, 6).map((d: any) => (
                <div key={d.type}>{d.type}: ODA {fmt(d.oda)} · LibreDWG {fmt(d.libredwg)}</div>
              ))}
              {file.crosscheck.libredwg_error ? <div>LibreDWG: {file.crosscheck.libredwg_error}</div> : null}
            </div>
          ) : null}
          {file.kind === 'drawing_scan' ? <ScanReading file={file} page={current?.kind === 'pdf' ? current.page : 0} vision={vision.data} /> : null}
          <div className="eyebrow" style={{ marginTop: 16 }}>Text on this sheet · {texts.length}</div>
          <input className="search" placeholder="Find text (ə = e, ş = s…)" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: '100%', marginTop: 8 }} />
          <div style={{ marginTop: 6 }}>
            {texts
              .filter((t) => matches(q, t.text))
              .slice(0, 250)
              .map((t) => (
                <button
                  key={t.key}
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
          </div>
        </div>
      </Card>
    </div>
  )
}
