// Azerbaijani-aware folding for search. Display text is never folded.
const FOLD: Record<string, string> = { ə: 'e', ı: 'i', ö: 'o', ü: 'u', ş: 's', ç: 'c', ğ: 'g', ä: 'e' }

export function azLower(s: string): string {
  return s.normalize('NFC').toLocaleLowerCase('az')
}

export function foldKey(s: string): string {
  return azLower(s)
    .replace(/[əıöüşçğä]/g, (c) => FOLD[c] ?? c)
    .replace(/\s+/g, ' ')
    .trim()
}

export function matches(query: string, ...fields: (string | null | undefined)[]): boolean {
  const q = foldKey(query)
  if (!q) return true
  return fields.some((f) => f && foldKey(f).includes(q))
}

export function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

export function money(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
