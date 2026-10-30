import { useMemo } from 'react'
import { useData } from './api'

export type Sheet = { id?: string; page?: number; number?: any; building?: string | null; discipline?: string | null; title?: string | null; scale?: string | number | null; paper?: string | null; method?: string; text_count?: number; kind?: string }
export type FileRow = {
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
  /** Known sheet count when the sheet list itself is not loaded (fallback mode). */
  sheet_count?: number
  note?: string | null
}
export type Register = { files: FileRow[]; counts: Record<string, number>; total: number; duplicates: any[] }

type OpsRow = { file: string; kind: string; discipline: string | null; building: string | null; order: string | null; sheets: number | null }
type Ops = { registers: { id: string; rows: OpsRow[] }[] }
type Conv = { files: { file: string; name: string; sha256: string; status: string; crosscheck: any; oda: any }[] }
type Cov = { cells: { sources: { file: string; file_id?: string }[] }[] }
type Vision = { files: { rel: string; sha256: string }[] }

export function sheetCount(f: FileRow) {
  return f.sheets ? f.sheets.length : f.sheet_count ?? 0
}

/**
 * The drawing register. /api/register reads the raw package to count scan pages, so it fails when
 * only the caches are shipped. In that case the same list is rebuilt from the operations register
 * (every drawing), the conversion log (DWG read status) and the hashes the other stages cite.
 */
export function useRegister(): { data: Register | null; error: string | null; degraded: string | null } {
  const reg = useData<Register>('/api/register')
  const failed = !!reg.error
  const ops = useData<Ops>(failed ? '/api/operations' : null)
  const conv = useData<Conv>(failed ? '/api/conversion' : null)
  const cov = useData<Cov>(failed ? '/api/coverage' : null)
  const vis = useData<Vision>(failed ? '/api/vision' : null)

  const rebuilt = useMemo<Register | null>(() => {
    if (!failed || !ops.data || !conv.data) return null
    const rows = ops.data.registers.find((r) => r.id === 'drawings')?.rows || []
    const byRel = new Map(conv.data.files.map((f) => [f.file, f]))
    const sha = new Map<string, string>()
    for (const c of cov.data?.cells || []) for (const s of c.sources) if (s.file_id) sha.set(s.file, s.file_id)
    for (const v of vis.data?.files || []) sha.set(v.rel, v.sha256)
    for (const f of conv.data.files) sha.set(f.file, f.sha256)
    const files: FileRow[] = rows.map((r) => {
      const c = byRel.get(r.file)
      const name = r.file.split('/').pop() || r.file
      return {
        sha256: sha.get(r.file) || '',
        rel: r.file,
        name,
        kind: r.kind,
        ext: name.split('.').pop()?.toLowerCase() || '',
        size: 0,
        discipline: r.discipline,
        building: r.building,
        order: r.order,
        read_status: c?.status,
        crosscheck: c?.crosscheck,
        oda: c?.oda,
        sheet_count: r.sheets ?? undefined,
      }
    })
    const counts = files.reduce<Record<string, number>>((m, f) => ((m[f.kind] = (m[f.kind] || 0) + 1), m), {})
    return { files, counts, total: files.length, duplicates: [] }
  }, [failed, ops.data, conv.data, cov.data, vis.data])

  if (!failed) return { data: reg.data, error: null, degraded: null }
  const err = ops.error || conv.error
  if (err) return { data: null, error: `${reg.error} · fallback: ${err}`, degraded: null }
  return { data: rebuilt, error: null, degraded: reg.error }
}
