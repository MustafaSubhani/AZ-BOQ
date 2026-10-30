import { useState } from 'react'
import { clearCache, postJSON, useData } from '../api'
import { fmt } from '../az'
import { T } from '../i18n'
import { href } from '../router'
import { Card, Empty, ErrorBox, Loading } from '../ui'

type Room = { room: string; name: string; room_schedule: number | null; room_text?: string; hatch_m2: number | null; lines: string[] }
type Floor = { floor: string; file?: string; page?: number; total: number | null; total_text?: string | null; sum: number | null; gap: number | null; rooms: Room[] }
type Book = { floors: Floor[]; conflicts: { id: string; text: string }[] }

const FLOOR: Record<string, string> = { basement: 'Basement', floor_1: '1st floor', floor_2: '2nd floor' }

export function Areas() {
  const { data, error } = useData<Book>('/api/areas')
  const [who, setWho] = useState(() => { try { return localStorage.getItem('azboq.author') || '' } catch { return '' } })
  const [why, setWhy] = useState('')
  if (error) return <ErrorBox error={error} />
  if (!data) return <Loading what="the area book" />
  return (
    <>
      {data.floors.map((floor) => (
        <Card key={`${floor.file}-${floor.floor}-${floor.page}`} title={FLOOR[floor.floor] || floor.floor} sub={floor.gap == null ? undefined : `Rooms sum ${fmt(floor.sum, 2)} m² · Cəmi ${floor.total_text || fmt(floor.total, 2)} · gap ${fmt(floor.gap, 2)}`}>
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>Room</th><th>Name</th><th>Room schedule</th><th>Hatch</th><th>Bill lines</th>
                </tr>
              </thead>
              <tbody>
                {floor.rooms.map((room) => (
                  <tr key={room.room}>
                    <td className="mono">{room.room}</td>
                    <td><T az={room.name} /></td>
                    <td className="num">{room.room_schedule == null ? '—' : fmt(room.room_schedule, 2)}</td>
                    <td className="num">{room.hatch_m2 == null ? '—' : fmt(room.hatch_m2, 2)}</td>
                    <td>{room.lines.map((id) => <a key={id} className="mono" href={href('bill', { line: id })}>{id} </a>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!floor.rooms.length ? <Empty title="No rooms on this floor" /> : null}
          </div>
        </Card>
      ))}
      {data.conflicts.filter((conflict) => conflict.id.startsWith('room-')).map((conflict) => {
        const floorKey = conflict.id.split('-').slice(2).join('-')
        const line = data.floors.find((floor) => floor.floor === floorKey)?.rooms.find((room) => room.lines.length)?.lines[0]
        return (
        <Card key={conflict.id} title="Documents disagree">
          <div className="box warn">{conflict.text}</div>
          {line ? (
          <form className="box" onSubmit={async (e) => {
            e.preventDefault()
            const chosen = new FormData(e.currentTarget).get('side')
            if (!who.trim() || !why.trim() || chosen == null || chosen === '') return
            try { localStorage.setItem('azboq.author', who.trim()) } catch { /* keep going */ }
            await postJSON('/api/review', { target_kind: 'line', target_id: line, action: 'decide', reason: why.trim(), author: who.trim(), payload: { value: Number(chosen) } })
            clearCache()
            window.location.reload()
          }}>
            <small>Choose a number already printed above. Line {line} stays in review.</small>
            <input name="side" placeholder="A number printed above" />
            <input placeholder="Your name" value={who} onChange={(e) => setWho(e.target.value)} />
            <input placeholder="Why this side" value={why} onChange={(e) => setWhy(e.target.value)} />
            <button className="btn" type="submit">Decide</button>
          </form>
          ) : null}
        </Card>
        )
      })}
      {!data.floors.length ? <Empty title="No room schedules were read" /> : null}
    </>
  )
}
