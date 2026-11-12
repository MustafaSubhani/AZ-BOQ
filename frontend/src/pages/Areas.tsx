import { useState } from 'react'
import { toast } from 'sonner'
import { clearCache, postJSON, useData } from '../api'
import { fmt } from '../az'
import { T } from '../i18n'
import { Check, Warning } from '../icons'
import { href } from '../router'
import { Card, Empty, ErrorBox, Loading } from '../ui'

type Room = { room: string; name: string; room_schedule: number | null; room_text?: string; hatch_m2: number | null; lines: string[] }
type Floor = { floor: string; file?: string; page?: number; total: number | null; total_text?: string | null; sum: number | null; gap: number | null; rooms: Room[] }
type Book = { floors: Floor[]; conflicts: { id: string; text: string }[] }

const FLOOR: Record<string, string> = { basement: 'Basement (−2.75)', floor_1: 'First Floor (±0.00)', floor_2: 'Second Floor (+3.30)' }

export function Areas() {
  const { data, error } = useData<Book>('/api/areas')
  const [who, setWho] = useState(() => {
    try {
      return localStorage.getItem('azboq.author') || ''
    } catch {
      return ''
    }
  })
  const [why, setWhy] = useState('')
  const [chosenMap, setChosenMap] = useState<Record<string, string>>({})
  const [savingId, setSavingId] = useState<string | null>(null)

  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the area book" />

  return (
    <>
      {data.floors.map((floor) => {
        const hasGap = floor.gap != null && Math.abs(floor.gap) > 0.05
        return (
          <Card
            key={`${floor.file}-${floor.floor}-${floor.page}`}
            title={FLOOR[floor.floor] || floor.floor}
            sub={
              floor.gap == null
                ? undefined
                : `Schedule rows sum to ${fmt(floor.sum, 2)} m² · Printed Cəmi: ${floor.total_text || fmt(floor.total, 2)} m²`
            }
            right={
              floor.gap != null ? (
                <span className={`tag ${hasGap ? 'warn' : 'ok'}`}>
                  {hasGap ? `Δ ${fmt(floor.gap, 2)} m²` : 'Exact match'}
                </span>
              ) : null
            }
          >
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Room №</th>
                    <th>Room Name</th>
                    <th className="r">Schedule (m²)</th>
                    <th className="r">CAD Hatch (m²)</th>
                    <th>Linked BOQ Lines</th>
                  </tr>
                </thead>
                <tbody>
                  {floor.rooms.map((room) => {
                    const diff =
                      room.room_schedule != null &&
                      room.hatch_m2 != null &&
                      Math.abs(room.room_schedule - room.hatch_m2) > 0.5
                    return (
                      <tr key={room.room}>
                        <td className="mono">{room.room}</td>
                        <td><T az={room.name} /></td>
                        <td className="r num">{room.room_schedule == null ? <span className="faint">—</span> : fmt(room.room_schedule, 2)}</td>
                        <td className={`r num ${diff ? 'text-[var(--warn-text)] font-medium' : ''}`}>
                          {room.hatch_m2 == null ? <span className="faint">—</span> : fmt(room.hatch_m2, 2)}
                        </td>
                        <td>
                          <div className="flex flex-wrap gap-1">
                            {room.lines.map((id) => (
                              <a key={id} className="pill" href={href('bill', { line: id })}>
                                {id}
                              </a>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              {!floor.rooms.length ? <Empty title="No rooms extracted on this floor" /> : null}
            </div>
          </Card>
        )
      })}

      {data.conflicts
        .filter((conflict) => conflict.id.startsWith('room-'))
        .map((conflict) => {
          const floorKey = conflict.id.split('-').slice(2).join('-')
          const line = data.floors.find((floor) => floor.floor === floorKey)?.rooms.find((room) => room.lines.length)?.lines[0]
          const sideVal = chosenMap[conflict.id] || ''
          return (
            <Card
              key={conflict.id}
              title="Schedule vs. CAD Polygon Disagreement"
              right={<span className="tag warn"><Warning size={12} /> Needs Decision</span>}
            >
              <div className="card-body pt-2!">
                <div className="box warn mt-0!">{conflict.text}</div>
                {line ? (
                  <form
                    className="box edit"
                    onSubmit={async (e) => {
                      e.preventDefault()
                      if (!who.trim() || !why.trim() || !sideVal.trim()) {
                        toast.error('Enter the chosen figure, your name, and a reason.')
                        return
                      }
                      setSavingId(conflict.id)
                      try {
                        try {
                          localStorage.setItem('azboq.author', who.trim())
                        } catch {
                          /* ignore */
                        }
                        await postJSON('/api/review', {
                          target_kind: 'line',
                          target_id: line,
                          action: 'decide',
                          reason: why.trim(),
                          author: who.trim(),
                          payload: { value: Number(sideVal) },
                        })
                        clearCache()
                        setWhy('')
                        toast.success(`Recorded area decision for line ${line}`)
                      } catch (err: any) {
                        toast.error(String(err?.message || err))
                      } finally {
                        setSavingId(null)
                      }
                    }}
                  >
                    <small>Record Authoritative Area for Line {line}</small>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 mt-2">
                      <div className="form-field mt-0!">
                        <label>Selected area (m²)</label>
                        <input
                          value={sideVal}
                          onChange={(e) => setChosenMap((m) => ({ ...m, [conflict.id]: e.target.value }))}
                          placeholder="Printed figure above"
                        />
                      </div>
                      <div className="form-field mt-0!">
                        <label>Reviewer name</label>
                        <input value={who} onChange={(e) => setWho(e.target.value)} placeholder="Your name" />
                      </div>
                      <div className="form-field mt-0!">
                        <label>Audit note</label>
                        <input value={why} onChange={(e) => setWhy(e.target.value)} placeholder="Why this figure governs" />
                      </div>
                    </div>
                    <div className="acts">
                      <button className="btn" type="submit" disabled={savingId === conflict.id}>
                        <Check size={14} /> {savingId === conflict.id ? 'Saving…' : 'Record Decision'}
                      </button>
                    </div>
                  </form>
                ) : null}
              </div>
            </Card>
          )
        })}

      {!data.floors.length ? <Empty title="No room schedules extracted" /> : null}
    </>
  )
}
