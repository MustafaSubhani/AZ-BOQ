export type Tab = { key: string; title: string; pinned: boolean }
export const MAX_VISIBLE = 6

export function openTab(tabs: Tab[], tab: Tab, preview: boolean): Tab[] {
  const at = tabs.findIndex((item) => item.key === tab.key)
  if (at >= 0) return [...tabs.slice(0, at), { ...tabs[at], pinned: tabs[at].pinned || !preview }, ...tabs.slice(at + 1)]
  const kept = preview ? tabs.filter((item) => item.pinned) : tabs
  return [...kept, { ...tab, pinned: !preview }]
}

export function visibleTabs(tabs: Tab[], activeKey: string, mru: string[]) {
  if (tabs.length <= MAX_VISIBLE) return { shown: tabs, overflow: [] as Tab[] }
  const rank = (key: string) => (key === activeKey ? -1 : mru.indexOf(key) < 0 ? 1e9 : mru.indexOf(key))
  const shown = [...tabs].sort((a, b) => rank(a.key) - rank(b.key)).slice(0, MAX_VISIBLE)
  const keys = new Set(shown.map((item) => item.key))
  return { shown: tabs.filter((item) => keys.has(item.key)), overflow: tabs.filter((item) => !keys.has(item.key)) }
}
