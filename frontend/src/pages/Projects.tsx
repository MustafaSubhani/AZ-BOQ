import { useRef, useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { clearCache, delJSON, useData } from '../api'
import { fmt, money } from '../az'
import {
  ArrowRight,
  Buildings,
  Check,
  Clock,
  Cube,
  FileText,
  FolderOpen,
  Plus,
  Scan,
  Trash,
  Upload,
  Warning,
  X,
} from '../icons'
import { href } from '../router'
import { AnimatedNumber, Card, Empty, ErrorBox, Loading } from '../ui'

type ProjectStage = {
  step: string
  state: 'done' | 'ready' | 'queued' | 'blocked' | 'skipped'
  note: string
}

type ProjectFile = {
  name: string
  kind: string
  detail: string
  rows?: number
  size: number
  sha: string
}

type ProjectItem = {
  id: string
  name: string
  order_code: string
  location: string
  client: string
  status: string
  builtin: boolean
  created_at: number
  summary: {
    dwg_count: number
    pdf_count: number
    scan_count: number
    boq_lines: number
    ignored_count?: number
    contract_azn: number | null
    backed_lines: number
    contradictions: number
    backed_pct: number
    oda_available: boolean
    stages: ProjectStage[]
    files: ProjectFile[]
  }
}

function fmtSize(n: number) {
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(n / 1024))} KB`
}

function stageBadge(state: ProjectStage['state']) {
  if (state === 'done') return <span className="tag ok">Completed</span>
  if (state === 'ready') return <span className="tag info">Ready</span>
  if (state === 'queued') return <span className="tag warn">Queued</span>
  if (state === 'blocked') return <span className="tag bad">Missing Input</span>
  return <span className="tag muted">Skipped</span>
}

export function Projects() {
  const { data, error } = useData<{ projects: ProjectItem[] }>('/api/projects')
  const [showModal, setShowModal] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [orderCode, setOrderCode] = useState('')
  const [location, setLocation] = useState('')
  const [client, setClient] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [formErr, setFormErr] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="projects" />

  const projects = data.projects || []
  const inspected = projects.find((p) => p.id === selectedId) || null

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return
    const next = [...files]
    for (const f of Array.from(incoming)) {
      if (!next.some((x) => x.name === f.name && x.size === f.size)) next.push(f)
    }
    setFiles(next)
    setFormErr('')
  }

  const submitUpload = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setFormErr('Enter a project name.')
      return
    }
    if (!files.length) {
      setFormErr('Drop or select at least one DWG, PDF, XLSX, or ZIP file.')
      return
    }
    setUploading(true)
    setFormErr('')
    try {
      const fd = new FormData()
      fd.append('name', name.trim())
      fd.append('order_code', orderCode.trim())
      fd.append('location', location.trim())
      fd.append('client', client.trim())
      for (const f of files) fd.append('files', f)

      const res = await fetch('/api/projects/upload', { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const created = (await res.json()) as ProjectItem
      clearCache('/api/projects')
      setShowModal(false)
      setSelectedId(created.id)
      setName('')
      setOrderCode('')
      setLocation('')
      setClient('')
      setFiles([])
      toast.success(`Ingested package "${created.name}" (${created.summary.files.length} files hashed)`)
    } catch (err: any) {
      setFormErr(String(err?.message || err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      {/* Top KPI Row + Primary Upload CTA */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] text-[var(--muted)]">
          Drop a <span className="mono">.dwg</span>, <span className="mono">.dxf</span>, <span className="mono">.pdf</span>, <span className="mono">.xlsx</span>, or <span className="mono">.zip</span>.
          Files are hashed and classified. Takeoff is not rerun from this screen.
        </p>
        <button type="button" className="btn" onClick={() => setShowModal(true)}>
          <Plus size={14} /> Upload New Package
        </button>
      </div>

      <div className="strip">
        <div className="kpi">
          <div className="k"><Buildings size={14} /> Project Workspaces</div>
          <div className="v"><AnimatedNumber value={projects.length} /></div>
          <div className="s">1 verified baseline + {Math.max(0, projects.length - 1)} uploaded packages</div>
        </div>
        <div className="kpi">
          <div className="k"><Cube size={14} /> Total CAD Models (DWG/DXF)</div>
          <div className="v">
            <AnimatedNumber value={projects.reduce((s, p) => s + (p.summary.dwg_count || 0), 0)} />
          </div>
          <div className="s">ODA File Converter {projects[0]?.summary.oda_available ? 'ready on host' : 'offline cache mode'}</div>
        </div>
        <div className="kpi">
          <div className="k"><FileText size={14} /> Plotted & Scanned PDFs</div>
          <div className="v">
            <AnimatedNumber value={projects.reduce((s, p) => s + (p.summary.pdf_count || 0) + (p.summary.scan_count || 0), 0)} />
          </div>
          <div className="s">Automatic vector vs. raster scan classification</div>
        </div>
        <div className="kpi">
          <div className="k"><FolderOpen size={14} /> Total Audited BOQ Rows</div>
          <div className="v">
            <AnimatedNumber value={projects.reduce((s, p) => s + (p.summary.boq_lines || 0), 0)} />
          </div>
          <div className="s">Azerbaijani & bilingual contract bills</div>
        </div>
      </div>

      <div className={`fill-row ${inspected ? 'with-insp' : ''}`}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {projects.map((p) => {
            const active = p.builtin
            const isSel = inspected?.id === p.id
            return (
              <Card
                key={p.id}
                className={isSel ? 'ring-2 ring-[var(--accent)]' : ''}
                title={
                  <div className="flex items-center gap-2">
                    <span>{p.name}</span>
                    {active ? <span className="tag ok">Active Workspace</span> : <span className="tag info">Ingested</span>}
                  </div>
                }
                sub={`${p.order_code} · ${p.location} · ${p.client}`}
                right={
                  !p.builtin ? (
                    <button
                      type="button"
                      className="icon sm bare text-[var(--muted)] hover:text-[var(--bad-text)]!"
                      title="Delete uploaded package"
                      onClick={async () => {
                        if (!window.confirm(`Remove "${p.name}"? The uploaded files are deleted.`)) return
                        try {
                          await delJSON(`/api/projects/${p.id}`, {})
                          if (selectedId === p.id) setSelectedId(null)
                          clearCache('/api/projects')
                          toast.success(`Removed package "${p.name}"`)
                        } catch (err) {
                          toast.error(err instanceof Error ? err.message : 'Could not remove the package')
                        }
                      }}
                    >
                      <Trash size={14} />
                    </button>
                  ) : null
                }
              >
                <div className="card-body flex flex-col gap-3 pt-3!">
                  <div className="grid grid-cols-4 gap-2 rounded-lg border border-[var(--line)] bg-[var(--paper-2)] p-2.5 text-center">
                    <div>
                      <div className="font-mono text-[15px] font-semibold text-[var(--ink)] num">{p.summary.dwg_count}</div>
                      <div className="text-[11px] text-[var(--muted)]">DWG/DXF</div>
                    </div>
                    <div>
                      <div className="font-mono text-[15px] font-semibold text-[var(--ink)] num">{p.summary.pdf_count}</div>
                      <div className="text-[11px] text-[var(--muted)]">Vector PDF</div>
                    </div>
                    <div>
                      <div className="font-mono text-[15px] font-semibold text-[var(--ink)] num">{p.summary.scan_count}</div>
                      <div className="text-[11px] text-[var(--muted)]">Scans</div>
                    </div>
                    <div>
                      <div className="font-mono text-[15px] font-semibold text-[var(--ink)] num">{fmt(p.summary.boq_lines)}</div>
                      <div className="text-[11px] text-[var(--muted)]">BOQ Rows</div>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    {p.summary.stages.map((st, idx) => (
                      <div key={idx} className="flex items-center justify-between gap-2 text-[12px]">
                        <span className="flex items-center gap-1.5 text-[var(--ink-2)]">
                          {st.state === 'done' ? (
                            <Check size={12} className="text-[var(--ok)]" weight="bold" />
                          ) : st.state === 'blocked' ? (
                            <Warning size={12} className="text-[var(--bad)]" />
                          ) : (
                            <Clock size={12} className="text-[var(--muted)]" />
                          )}
                          {st.step}
                        </span>
                        <span className="muted truncate text-[11.5px]">{st.note}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-1 flex items-center justify-between border-t border-[var(--line)] pt-3">
                    <span className="font-mono text-[12px] text-[var(--muted)]">
                      {p.summary.contract_azn ? money(p.summary.contract_azn) : `Uploaded ${new Date(p.created_at * 1000).toLocaleDateString()}`}
                    </span>
                    <div className="flex items-center gap-2">
                      {!p.builtin ? (
                        <button
                          type="button"
                          className="btn outline sm"
                          onClick={() => setSelectedId(isSel ? null : p.id)}
                        >
                          {isSel ? 'Hide Manifest' : 'Inspect Manifest'}
                        </button>
                      ) : (
                        <a className="btn sm" href={href('home')}>
                          Open Audit <ArrowRight size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Right Manifest Inspector for Uploaded Packages */}
        {inspected ? (
          <Card
            title={`Manifest · ${inspected.name}`}
            sub={`${inspected.summary.files.length} files hashed & classified`}
            right={
              <button type="button" className="icon sm" onClick={() => setSelectedId(null)} aria-label="Close">
                <X size={13} />
              </button>
            }
          >
            <div className="insp">
              <div className="eyebrow accent">{inspected.order_code} · {inspected.location}</div>
              <div className="mt-2 space-y-2">
                {inspected.summary.stages.map((st, idx) => (
                  <div key={idx} className="pair py-1.5!">
                    <span>{st.step}</span>
                    {stageBadge(st.state)}
                  </div>
                ))}
              </div>

              <div className="section-label">
                <span className="eyebrow">Ingested Files · {inspected.summary.files.length}</span>
              </div>
              <div className="mt-2 space-y-1.5">
                {inspected.summary.files.map((f, i) => (
                  <div key={i} className="rounded-lg border border-[var(--line-2)] bg-[var(--paper-2)] px-3 py-2 text-[12px]">
                    <div className="flex items-center justify-between gap-2">
                      <b className="truncate text-[var(--ink)]" lang="az">{f.name}</b>
                      <span className="pill">{f.kind.toUpperCase()}</span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-[11px] text-[var(--muted)]">
                      <span>{f.detail}</span>
                      <span className="mono">{fmtSize(f.size)} · {f.sha}</span>
                    </div>
                  </div>
                ))}
                {!inspected.summary.files.length ? (
                  <Empty icon={<Scan size={16} />} title="Baseline package">
                    Inspect all 61 Hadrut files in the Drawings studio.
                  </Empty>
                ) : null}
              </div>
            </div>
          </Card>
        ) : null}
      </div>

      {/* Upload Modal (70% Figure-Ground Dimmed Backdrop) */}
      {showModal ? (
        <div className="palette-back" onMouseDown={() => !uploading && setShowModal(false)}>
          <div
            className="palette max-w-[540px]!"
            role="dialog"
            aria-label="Upload Project Package"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="card-h">
              <div>
                <div className="card-title">Upload New Design & BOQ Package</div>
                <span className="sub">Automatic SHA-256 hashing, CAD version check, PDF vector scan & BOQ row count</span>
              </div>
              <button type="button" className="icon sm ml-auto" onClick={() => setShowModal(false)} disabled={uploading}>
                <X size={14} />
              </button>
            </div>

            <form onSubmit={submitUpload} className="p-4 overflow-auto space-y-3">
              <div className="form-field mt-0!">
                <label htmlFor="up-name">Project Name *</label>
                <input
                  id="up-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Füzuli 3-Bay Fire Station"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="form-field mt-0!">
                  <label htmlFor="up-order">Order / Contract №</label>
                  <input
                    id="up-order"
                    value={orderCode}
                    onChange={(e) => setOrderCode(e.target.value)}
                    placeholder="e.g., Sifariş № 9540"
                  />
                </div>
                <div className="form-field mt-0!">
                  <label htmlFor="up-loc">District / Site</label>
                  <input
                    id="up-loc"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g., Füzuli rayonu"
                  />
                </div>
              </div>

              <div className="form-field mt-0!">
                <label htmlFor="up-client">Employer / Client</label>
                <input
                  id="up-client"
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                  placeholder="e.g., FHN Əsaslı Tikinti İdarəsi"
                />
              </div>

              {/* Dropzone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                  addFiles(e.dataTransfer.files)
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`mt-2 flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed p-5 text-center transition-colors ${
                  dragOver
                    ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                    : 'border-[var(--line-3)] bg-[var(--paper-2)] hover:border-[var(--muted)]'
                }`}
              >
                <span className="well sm accent">
                  <Upload size={16} />
                </span>
                <div className="text-[13px] font-medium text-[var(--ink)]">
                  Drop <span className="mono">.dwg</span>, <span className="mono">.pdf</span>, <span className="mono">.xlsx</span>, or <span className="mono">.zip</span> files here
                </div>
                <div className="text-[11.5px] text-[var(--muted)]">
                  Backups (<span className="mono">.bak</span>), plot logs (<span className="mono">.log</span>), and Word lock files are filtered out automatically
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".dwg,.dxf,.pdf,.xlsx,.xls,.zip,.doc,.docx"
                  className="hidden"
                  onChange={(e) => addFiles(e.target.files)}
                />
              </div>

              {files.length ? (
                <div className="max-h-[140px] overflow-auto rounded-lg border border-[var(--line-2)] divide-y divide-[var(--line)]">
                  {files.map((f, idx) => (
                    <div key={idx} className="flex items-center justify-between px-3 py-1.5 text-[12px]">
                      <span className="truncate font-medium text-[var(--ink)]">{f.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="mono text-[11px] text-[var(--muted)]">{fmtSize(f.size)}</span>
                        <button
                          type="button"
                          className="text-[var(--muted)] hover:text-[var(--bad-text)]"
                          onClick={() => setFiles((prev) => prev.filter((_, i) => i !== idx))}
                        >
                          <X size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {formErr ? <div className="err">{formErr}</div> : null}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--line)]">
                <button type="button" className="btn outline" onClick={() => setShowModal(false)} disabled={uploading}>
                  Cancel
                </button>
                <button type="submit" className="btn" disabled={uploading}>
                  <Upload size={14} /> {uploading ? 'Uploading…' : `Upload package${files.length ? ` (${files.length})` : ''}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  )
}
