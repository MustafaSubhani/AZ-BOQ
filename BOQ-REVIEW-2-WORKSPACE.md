# Review of the audit fixes, and the workspace to build next

Second pass, 30 Oct 2026, evening. It checks the changes made against `BOQ-ENGINE-AUDIT.md` on the stored run (`cache/azboq.sqlite`) and the dumps. It then specifies the frontend workspace: annotated drawings, a source inspector, file tabs and "review required" labels. The interaction patterns come from Constech's UI.

Rules that still bind:

- `D:\Constech` is read for **code patterns only**. Copy no data, outputs, rates, rules or measurements. Each pointer below names a file and a line range to read, not something to import.
- No number without a source, and no missing value replaced silently.
- PDF page numbers in this file are the stored 0-based index (`locator.page`), as in the audit: the window schedule is page 21 here, which a viewer shows as page 22. The UI always displays index + 1.
- The UI never says "hardcoded" (`test_platform_ui_never_mentions_hardcoding` stays). A value a person set, or a link a person made, shows **Review required** on its source, with the citation (section 4).

---

## 1. What the fixes achieved (verified)

All 102 backend tests pass. Run totals before and after:

| | Before | After |
|---|---:|---:|
| matched | 26 | 53 |
| printed | 90 | 142 |
| derived | 20 | 14 |
| different | 2 | **20** (189,925 AZN) |
| review | 628 | 757 |
| not_found | 1,408 (2.23M AZN) | 1,188 (1.68M AZN) |
| takeoff items | 26 | 51 |
| bill headers | 132 | 145 (132 + 13 retaining-wall sub-headers) |

Acceptance lines from the audit, checked one by one against the new report:

| Line | Bill | Engine now | Verdict |
|---|---:|---|---|
| 2.5.13 / 2.5.14 gutters and downpipes | 154.2 / 190.5 m | different, swap explained | correct |
| 2.5.19 roof windows | 9 | printed, `DP-1 (9 əd)` | correct |
| 2.6.7 / 2.6.8 / 2.6.10 / 2.6.11 | 252 / 2.88 / 39 / 37.52 m² | matched 252.276 / 2.88 / 38.988 / 37.52 | correct |
| 2.7.3 keramzit | 1.533 m³ | matched 43.8 × 0.035 | correct |
| 2.7.30, 2.7.37 polystyrene | 7.322, 13.174 m³ | matched | correct |
| 2.7.31, 2.7.38 mesh | 0.141, 0.254 t | matched 0.14121, 0.25407 | correct |
| 2.7.14 timber floor | 130 m² | different, 129.0 | correct |
| 2.7.15, 2.7.23 (0.8 coverage) | 104, 184.5 m² | review, labelled as the estimator's factor | correct |
| 2.8.1, 2.8.2, 2.8.6, 2.8.7, 2.8.9 | | different 1368.7, 2005.6, 61.4, 3380.0, 3892.7 | correct |
| 2.8.4 plasterboard ceiling | 96 m² | matched | correct |
| 10.1.15, 11.1.15 tank walls and bottom | 27.73 m³ | matched 9.41 + 4.58 × count. The count comes from the Md-1 marks or the sheet, never assumed (`engine/tanks.py`) | correct |
| 12.1.13 drinking tank | 14.49 m³ | matched 3.89 + 10.60, no multiplier | correct |
| 19.1.3 / 20.1.3 asphalt | 383.7 / 216 | each line keeps its own `our_qty` | correct (B1 fixed) |
| 3.5.7 gutters, guard room | 12.8 m | from sheet 9335-08-MT, no longer from the 9336 copy | correct (B7 fixed) |
| floor bill total | | `=SUM(...)-0.02` | correct (B3 fixed) |

The tile transform is also right. `render.py` pads the region by 2% only to pick entities; the PNG's render box is the unpadded region, which matches `crops.region_transform`.

---

## 2. New bugs found in this pass (fix before any UI work)

### N1. "Found automatically" matches unrelated items (6 lines, all wrong)

`match/run.py` around line 113 matches every unlinked takeoff item to any bill line of the same building and unit. The tolerance comes from the bill's decimals. A whole-number bill quantity therefore accepts ±0.5:

| Line | Bill | Matched to | Why it is wrong |
|---|---:|---|---|
| 12.1.2, 13.1.2 | 4 m³ hand excavation | `drinking_tank_bottom` 3.89 m³ | concrete is not excavation |
| 2.13.6, 2.13.11, 2.13.12 | 3 m of pipe | `storey_basement` 2.7 m | a storey height is not a pipe length |
| 2.20.17 | 6 m air duct | `bay_module` 6.0 m | a grid module is not a duct |

Fix, all three parts:

1. Items that are inputs (gate dimensions, storey heights, bay module, thicknesses, counts) get `billable: false` in `extractors.yaml` and are never matched to a line.
2. An automatic match requires the element classifier (`match/elements.py`) to give the line and the item the same element.
3. For a value read off a drawing (schedule, stated), compare at the drawing's own decimals as well. 3.89 printed with 2 decimals cannot "equal" a bill 4. Rounding to the bill's decimals is only for derived values, whose decimals are produced by arithmetic (252.276 against 252).

```python
# match/run.py
def source_decimals(v: dict) -> int | None:
    """Decimals as printed. Derived values have no printed precision."""
    if v["method"] in ("derived", "geometry", "manual"):
        return None
    raw = next((s.get("decoded_text") for s in v["sources"] if s.get("decoded_text")), None)
    m = re.search(r"\d+(?:[.,](\d+))?", raw or "")
    return len(m.group(1) or "") if m else None

def auto_match_ok(item: dict, line: dict) -> bool:
    if not item.get("billable", True):
        return False
    if element_of_item(item) is None or element_of_item(item) != element_of_line(line):
        return False
    v = item["value"]
    d_bill = bill_decimals(line["qty"])
    d_src = source_decimals(v)
    d = d_bill if d_src is None else max(d_bill, d_src)
    return close_at(line["qty"], v["value"], d)
```

Test: none of the six lines above is matched. `2.6.7` (derived 252.276 against 252) stays matched.

### N2. Small whole numbers still become "printed"

| Line | Bill | Printed from | Why it is wrong |
|---|---:|---|---|
| 2.7.27 plywood sheets `Dikt (1,52*1,52) 18 mm` | 100 each | a `100` in the floor-type schedule, a layer thickness in mm | not a count |
| 12.1.25 pipe-sleeve seals | 3 each | `3.00 x 3,00 m` in the tank note, the plan size | not a count |

The audit (section 5.2) already says one or two significant digits must never be evidence alone. Rule: an `each` quantity with fewer than 3 significant digits is `printed` only when the number is in a count column of a schedule (header `Sayı`, `Miqdarı`, `ədəd`, `Cəmi` of a count table), or written as `N əd` / `N ədəd` next to a label that the element classifier maps to the line's element (the `DP - 1 (9 əd)` case). Otherwise it is at most a review candidate.

```python
# match/evidence.py, inside Finder.direct, before accepting an 'each' hit
COUNT_WORD = re.compile(r"(?<!\d)\d+\s*(?:əd\b|əd\.|ədəd)", re.I)

def count_hit_ok(e: dict, line_element: str | None) -> bool:
    if significant_digits(e["value"]) >= 3:
        return True
    if (e.get("col_header") or "") and re.search(r"(?i)say[ıi]|miqdar|ədəd|\bəd\b", e["col_header"]):
        return element_of_text(e.get("row_label") or "") == line_element
    if COUNT_WORD.search(e["context"]):
        return element_of_text(e["context"]) == line_element
    return False
```

2.7.27 can then be derived legitimately: 230.6 m² (laminate, plywood underlay) ÷ (1.52 × 1.52 m) = 99.8, rounded up to 100 sheets. The sheet size is in the bill line's own text, so record `factor_source = "bill_text"` (audit 4.4) and show it as "consistent with the parent, factor from the bill's own text".

### N3. The garage conflict hides two readings

2.7.12 and 2.7.13 (665.3 m²) say "658.30 on the floor schedule, 658.30 on the room schedule (Qaraj), 665.3 on the finish schedule". Both PDF readings are right (`9335 MH.pdf` page 5 prints `Qaraj 658.30`). Two more readings exist and are missing from the reason:

- The DWG room schedules print **665.30** next to `1 Qaraj` (`(SON).dwg` region with sheet `9335 - 1 - VM`, `elektrik.dwg`, `9335-1-SK ... 2-ci variant.dwg`). Some of these are architecture backgrounds or other-order copies, so they are one lineage. They still show that the DWG and its PDF plot disagree, which means the PDF and the DWG are different revisions. The plan's open question 10 asks exactly this.
- The floor hatch in the garage on the first-floor plan of `(SON).dwg` measures **659.39 m²** (geometry, `geom.json` hatches). That is an independent lineage and supports 658.30 (0.17% off).

Fix: list every reading with its lineage label ("PDF plot", "DWG", "DWG background in electrical", "geometry: hatch"). Suggest the side with the most independent lineages (658.30: floor schedule, PDF room schedule, hatch). Keep the line at `review` until a person decides (section 3.6).

### N4. Cosmetic: raw row text leaks into reasons

2.7.14's reason says `the schedule prints 129 m² (floor_1 2 100 500)`. That is the internal row key, not words. Use "1st floor, type 2 (timber floor)". The tolerance label `within 8% of one schedule figure` is how the candidate was found, not how it was judged. Show it as "candidate found within 8%; compared exactly: 129.0 against 130".

### N5. The fire-tank wall count has no geometry cross-check

`tanks.py` takes the count from the sheet text or from one cluster of Md-1 marks, which is correct. The audit's second check is not built: centreline perimeter × wall height × 0.25 m ≈ count × 4.58 m³, within 5%. Add it as a second lineage so the tank walls can become `verified`.

### N6. Open items the other agent reported, with a way forward

- **Steel (66 depot tables, about 125 t).** The bill has no element marks (S-6 …), but every reinforced-concrete line is followed by its A-1 and A-3 lines (2.3.1 columns → 2.3.2 A-1, 2.3.3 A-3; 2.3.4 beams → 2.3.5, 2.3.6; 2.3.10 slabs → 2.3.11, 2.3.12 …). Group the DK steel tables by element family, taken from the table title and the region title: `Sütun S-n` → columns, `Tir`/`Rigel` → beams, `örtük`/`tava` → slabs, `kəmər` → belts, `pilləkən` → stairs, `Bünövrə`/`Lentvari` → foundations. Sum A240 and A500C per family. Compare each family total with the A-1 / A-3 pair under the bill's concrete line of the same element. Report family totals as `different` or `matched` at 1% tolerance, because the bill is in tonnes to 3 decimals and the tables are in kg. Before summing, apply the same per-element count rule as the tanks (`Bir element üçün` × count of the mark on the plan). Without the count, the family is `blocked`, not summed.
- **Roof and walls.** Hatches are now read. On the second floor they add up to about 72 m² against 779 m² in the room schedule, because only tiled rooms are hatched (layer `M-2 keramitin shtrixi` is the ceramic tile pattern). Use hatches per room, not per floor (section 3.3). Wall pairing still needs the line pairing in audit 4.6.

---

## 3. Workspace: annotated drawings, inspector, files and tabs

Today the app has a single-target `Viewer.tsx` (one marker per source), a read-only Takeoff panel and a read-only Bill drawer. The review API (`POST /api/review`, `GET /api/reviews`, `DELETE /api/review/{id}`, `backend/azboq/reviews.py`) exists, but no screen calls it. The pieces to build follow, each with the Constech file that shows the pattern.

### 3.1 Layout (one workspace, three panes)

Pattern: Constech `pages/project/DrawingsPage.tsx` lines 1080–1125 (sheet rail), 1127–1215 (toolbar), 1217–1311 (banners), 1313+ (canvas), 1440+ (inspector); CSS in `styles/workspace.css` lines 4–19.

```text
┌ Files ──────────┬ tabs: [MH.pdf p20 ×] [(SON) R4 1st floor ×] [+2 ▾] ────────┬ Inspector ─────────┐
│ ▸ Depot         │ toolbar: select · layers · kinds ▾ · reviewed 12/40 · fit │ Sources | Calc |   │
│   ▾ 9335 MH.pdf │                                                            │ History            │
│     p5 1st fl.  │    sheet image + SVG overlay of annotated shapes          │                    │
│     p20 floors  │                                                            │                    │
│   ▸ (SON).dwg   │                                                            │                    │
│ ▸ Guard room    │  banner: "Showing sources of 2.7.36 · 3 on this sheet"    │                    │
└─────────────────┴────────────────────────────────────────────────────────────┴────────────────────┘
```

Grid: `248px minmax(0,1fr) 360px`, both side panes collapsible (Constech `.ws.no-sheets`, `.ws.no-inspector`). Keep the Quiet Utility rules from the brief: hairlines, no shadows, one accent.

### 3.2 Project files and tabs without clutter

The package has 84 files and 429 sheets. Showing them all at once is the clutter to avoid.

**Files rail.** A tree: building → file → sheet. Files come from `/api/register`; sheets are the DWG regions and PDF pages already returned there.

- Group by building, then by discipline (Architecture, Structure, Water, Electrical, HVAC, Site). Collapse everything except the building of the current selection.
- Hide what is not a drawing source: junk (already hidden), copies for other orders (`copy_of`, behind "3 copies for other orders"), reference-only files (ecology, LIRA). Show a count, never a silent drop.
- Each sheet row: sheet number, title (AZ, with EN on hover), small colour dots for the annotation kinds on it, and a progress bar of reviewed shapes (Constech `DrawingsPage.tsx` 1089–1107: `sheet-kinds`, `sheet-progress`).
- A search box filters file names, sheet numbers and titles with `fold_key` folding (so `nezaretci` finds `Nəzarətçi`).
- Each sheet row also shows how many bill lines take values from it, so the useful sheets stand out.

**Tabs.** Opening a sheet adds a tab, like an editor:

- At most 6 visible tabs; the rest go behind a `+N ▾` overflow menu, ordered by last use.
- Opening a source from the inspector reuses a "preview" tab (italic title) that the next source replaces. Double-click or edit to pin it. This keeps tab count low during review.
- A tab title is short: `MH p20` or `(SON) R4`, with the full file name and sheet title in the tooltip.
- Ctrl+W closes, Ctrl+Tab cycles, and the state lives in the URL (`?tabs=…&active=…`) so a reload restores it.

```tsx
// frontend/src/tabs.ts
export type Tab = { key: string; target: Target; title: string; pinned: boolean }
const MAX_VISIBLE = 6

export function openTab(tabs: Tab[], t: Tab, preview: boolean): Tab[] {
  const at = tabs.findIndex((x) => x.key === t.key)
  if (at >= 0) return [...tabs.slice(0, at), { ...tabs[at], pinned: tabs[at].pinned || !preview }, ...tabs.slice(at + 1)]
  const kept = preview ? tabs.filter((x) => x.pinned) : tabs      // a preview tab replaces the last preview
  return [...kept, { ...t, pinned: !preview }]
}

export function visibleTabs(tabs: Tab[], activeKey: string, mru: string[]) {
  if (tabs.length <= MAX_VISIBLE) return { shown: tabs, overflow: [] }
  const rank = (k: string) => (k === activeKey ? -1 : mru.indexOf(k) < 0 ? 1e9 : mru.indexOf(k))
  const shown = [...tabs].sort((a, b) => rank(a.key) - rank(b.key)).slice(0, MAX_VISIBLE)
  const keys = new Set(shown.map((x) => x.key))
  return { shown: tabs.filter((x) => keys.has(x.key)), overflow: tabs.filter((x) => !keys.has(x.key)) }
}
```

### 3.3 Annotated shapes on the sheet

Pattern: Constech `components/workspace/SheetCanvas.tsx` lines 616–653 (one SVG polygon per shape with `data-shape`, classes `selected` / `hit` / `faded` / `reviewed`, colour via a CSS variable), the click handling around lines 318 and 480–495, and `styles/workspace.css` lines 142–154 and 292–293. Kinds and colours: `lib/kinds.ts`. Here the kinds are areas, not structural elements.

What can be annotated on this package today, from data already extracted:

| Kind | Geometry source | Where | Links to |
|---|---|---|---|
| Room or floor area | DWG hatch boundary (`geom.json` hatches; add the rings, see below) | depot plans in `(SON).dwg` | room number → floor type → schedule row → bill lines |
| Room tag (pin) | the room-number text on the plan | every plan region | the room schedule row (area, name) |
| Schedule cell | the cell's bbox | PDF pages 4–6, 19–22; DXF table cells | the takeoff item that read it |
| Note value | the text bbox (`L=190.5`, `V=7625.40`, `S dam= 27.64`) | PDF and DWG | the stated item |
| Opening | window and door marks on the plan (P-1, QP-2 …) | plan regions | the schedule row of that mark |
| Element mark | Md-1, S-6 … (texts and multileaders) | DK plans | per-element tables × count |

Colours: one per kind, flat, with a word in the legend (brief: status colours always come with text). A shape's stroke style shows its check state: solid = checked, dashed = reviewed (Constech's `.shape.reviewed`), red outline = `different` or a conflict.

**Backend: store hatch outlines and serve shapes per sheet.** Today `geom.json` hatches have `area_du2`, `bbox` and `at` only. Store a simplified outer ring and holes, in drawing units, simplified to about 20 mm so a sheet stays under a few hundred KB.

```python
# dwg/read.py, in the hatch reader, after geom is built
simple = geom.simplify(self.flat_tol * 20, preserve_topology=True)
polys = [simple] if simple.geom_type == "Polygon" else list(getattr(simple, "geoms", []))
rec["rings"] = [[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords] for p in polys if p.area > 0]
rec["holes"] = [[[round(x, 1), round(y, 1)] for x, y in r.coords] for p in polys for r in p.interiors]
```

```python
# api/app.py
@app.get("/api/drawing/{sha}/region/{rid}/shapes")
def region_shapes(sha: str, rid: str):
    """Everything worth outlining on one sheet, in image pixels, each with what it feeds."""
    meta = drawing_region_meta(sha, rid)
    tr = meta["transform"]
    x0, y0, x1, y1 = meta["region"]["bbox"]

    def px(p):
        return [tr["offset"][0] + (p[0] - x0) * tr["scale"], tr["offset"][1] + (y1 - p[1]) * tr["scale"]]

    shapes = []
    for h in load_geom(meta_sha(sha))["hatches"]:
        if not (x0 <= h["at"][0] <= x1 and y0 <= h["at"][1] <= y1) or not h.get("rings"):
            continue
        link = area_links().get((meta_sha(sha), h["handle"]))      # built in the takeoff stage, see below
        shapes.append({"id": f"h:{h['handle']}", "kind": link["kind"] if link else "area_unlinked",
                       "points": [px(p) for p in h["rings"][0]], "area_m2": unit_area(h, meta),
                       "label": link["label"] if link else h["layer"], "item": link and link["item"],
                       "lines": link["lines"] if link else [], "status": link["status"] if link else None})
    shapes += tag_pins(sha, rid, px) + schedule_cells(sha, rid, px)
    return {"shapes": shapes, "transform": tr}
```

**Linking a hatch to a room.** This happens in the takeoff stage, so the API only reads results. A room-number text inside the hatch polygon gives the room. The floor-type schedule gives the room's type. The type's row gives the takeoff item and its bill lines. A hatch with no room tag inside is drawn as `area_unlinked` in grey, never hidden.

```python
from shapely.geometry import Point, Polygon

def link_hatches_to_rooms(hatches, texts, rooms_by_number: dict) -> dict:
    """rooms_by_number: {'1': {'floor': 'floor_1', 'type': '1', 'item': 'floor_1_type_1', ...}} from the schedules."""
    out = {}
    tags = [t for t in texts if re.fullmatch(r"\d{1,2}\*?", t["text"].strip())]
    for h in hatches:
        if not h.get("rings"):
            continue
        poly = Polygon(h["rings"][0], h.get("holes") or [])
        inside = [t["text"].strip() for t in tags if poly.contains(Point(t["at"]))]
        rooms = [rooms_by_number[n] for n in inside if n in rooms_by_number]
        if len(rooms) == 1:
            out[h["handle"]] = {**rooms[0], "hatch_area_du2": h["area_du2"]}
        elif len(rooms) > 1:
            out[h["handle"]] = {"kind": "area_conflict", "rooms": inside, "label": f"rooms {', '.join(inside)}"}
    return out
```

Edge cases:

- Room tags that are not plain numbers (`12*`, `26 x2 əd`) need the same parsing as the schedules (audit R6).
- Several regions show the same plan: canonical and copies, and a background inside MEP files. Link and annotate on the canonical region only; copies show a banner "copy for order 9337: see 9335-01-MH".
- Area units: `area_du2` is in drawing units². Convert with the region's confirmed unit (the 45.2 m gate), never with `$INSUNITS`.
- Each hatch area also goes into the takeoff as a `GEOMETRY` value, a second lineage for its room. That is how 658.30 gets confirmed by 659.39 (N3).

**Frontend overlay.** Extend `Viewer.tsx`, or better, add `SheetCanvas.tsx` next to it, using Constech's structure:

```tsx
// frontend/src/SheetCanvas.tsx (overlay part)
<svg className="overlay" width={img.w} height={img.h} style={{ transform }}>
  {shapes.filter((s) => kinds.has(s.kind)).map((s) => (
    <polygon
      key={s.id}
      data-shape={s.id}
      points={s.points.map((p) => p.join(',')).join(' ')}
      className={['shape', `k-${s.kind}`, s.id === selected ? 'selected' : '', hits?.has(s.id) ? 'hit' : '',
                  hits && hits.size && !hits.has(s.id) ? 'faded' : '', reviewed.has(s.id) ? 'reviewed' : '',
                  s.status === 'different' ? 'bad' : ''].join(' ')}
      style={{ ['--c' as string]: KIND[s.kind]?.color }}
      onClick={(e) => { e.stopPropagation(); onSelect(s.id) }}
    >
      <title>{`${s.label} · ${fmt(s.area_m2, 2)} m²`}</title>
    </polygon>
  ))}
</svg>
```

Interaction:

- Hover fills and shows a tooltip with label and area. Click selects and fills the inspector (3.4). Click on empty paper deselects.
- Opening a bill line highlights all its shapes on the sheet and fades the rest. A banner says "Showing sources of 2.7.36 · 3 on this sheet · Clear" (Constech `DrawingsPage.tsx` 1218–1236, `traceLine`).
- Opening a source on another sheet shows "Viewing a source · Back to 1st floor plan" (Constech 1303–1310, `returnSheetId`).
- A kinds menu toggles each kind, with counts. A "hide reviewed" toggle shows reviewed / total (Constech 1195–1209).
- Keys: N / P (or J / K) step through shapes in reading order, R marks reviewed and steps, Esc clears, F fits the sheet (Constech `DrawingsPage.tsx` 1018–1056). Show them in a shortcuts dialog (Constech `components/shell/ShortcutsDialog.tsx`).
- Pan and zoom stay as in the current `Viewer.tsx` (wheel zoom with a non-passive listener). Use `vector-effect: non-scaling-stroke` so strokes stay thin when zoomed.

### 3.4 Inspector (right pane)

Pattern: Constech `components/workspace/ElementInspector.tsx` (whole file), `components/bill/BillInspector.tsx` lines 86–126 (header, Bill / Measured / Difference / Variance strip), 136–243 (Sources tab grouped by sheet with "jump to this element"), 245–330 (Calculation tab and override with reason), `QuantityRow.tsx` (engine value kept beside an edit), `EvidenceList.tsx` and `EvidenceCrop.tsx` (a crop of the exact sheet area, with file name and sheet code under it).

The same inspector serves a selected shape, a takeoff item and a bill line:

**Header.** Label (AZ / EN), building · floor · element, status chip. Then a strip: Bill | Drawing | Difference | % | money. Any "review required" reasons appear as chips here (section 4).

**Sources tab.** One card per source, grouped by file and sheet:

- the crop (`EvidenceCrop`): the PDF page PNG or the DWG region tile, centred on the bbox. Use the `transform` the API already returns (`crops.py`); do not re-derive the scale in the browser;
- the file name, sheet number, page or region, and the cell (`row 4, column Sahə m²`) or the handle and layer;
- the raw text and the decoded text, with the decode scheme on hover (legacy font, mixed script);
- the lineage label ("PDF plot of 9335-01-MH", "DWG background in electrical", "geometry: hatch");
- buttons: show on sheet (opens a preview tab, 3.2), copy reference.

Below the cards: "Looked in" (`searched`) and "Rejected" (`rejected`), already in every `Value`.

**Calculation tab.** The formula as math (Constech `components/formula/FormulaEditor.tsx`, `MathView`). Each variable is a chip with value, unit and method; hovering it shows its crop. For schedule sums, a breakdown table with one row per schedule row (`P-1: 1200 × 2700 × 62 = 200.88 m²`) and a total. Then the tolerance used, how the candidate was found, the build-up group (parent and children) and the floor with `floor_from`.

**History tab.** Every review on this target (`GET /api/reviews?target=`), newest first: who, when, reason, before → after.

**Editing (through the existing review API).** Every edit needs a reason, keeps the engine value visible ("engine 129.0"), and has a reset:

- *Set a value* on an item or input (`override` with expression and variables, evaluated by `reviews.evaluate`, never `eval`);
- *Set a missing input* (`set_input`, e.g. the Md-1 count);
- *Accept / reject a candidate* (`accept`, `reject`);
- *Link line ↔ item* (`map`): replaces hand edits of `bill_map.yaml` during the demo;
- *Decide a conflict* (`decide`, with the chosen side).

`apply_reviews` today applies only `override` on items (`reviews.py` lines 115–135). Extend it to `set_input`, `accept`, `reject`, `map` and `decide`. Re-run `match` and `floors` after each `POST /api/review` and return the changed lines, so the screen updates in place.

### 3.5 Inputs register (new screen)

Pattern: Constech `pages/project/InputsPage.tsx` (statuses Found / Partly found / Missing / Set by hand, grouped, with the sheets each input was found on, and a manual value field).

Here: every input the takeoff uses (storey heights, slab levels, thicknesses, element counts, densities, the region unit) with its status, its value and source, the bill lines it feeds, and where it was looked for. "Set by hand" here is a `set_input` review. The existing Inputs ledger in `Evidence.tsx` becomes this register.

### 3.6 Area book (new screen, the "perfect areas" view)

Per building → floor → rooms, from the room, floor-type and finish schedules plus hatch geometry:

| Room | Name | Room schedule | Floor-type schedule | Hatch | Floor type | Ceiling | Walls | Status |
|---|---|---:|---:|---:|---|---|---|---|
| 1 | Qaraj | 658.30 (PDF) / 665.30 (DWG) | 658.30 | 659.39 | 1 mosaic B25 | emulsion, 665.3 | 375.7 | conflict |

Under each floor: the sum of rooms against `Cəmi`, and the sum per floor type against the floor-type schedule. Every cell opens the inspector. The conflict row offers "Decide" (a `decide` review). This is the screen to show the client.

### 3.7 Smaller features worth taking

- **Command palette** (Constech `components/shell/CommandPalette.tsx`): Ctrl+K to jump to a bill line id, a sheet number, a room, or a file, with Azerbaijani folding.
- **Right-click menu on a shape** (Constech `components/workspace/CanvasContextMenu.tsx`): open in inspector, show bill lines, copy reference, mark reviewed.
- **Schedule check** (Constech `components/workspace/ScheduleCheckPanel.tsx` and `lib/measure/scheduleCheck.ts`): draw a polygon on a DWG tile and get its area. The scale is exact here (the region transform), so no calibration step is needed. Compare it with the schedule row and save the polygon as a `GEOMETRY` value with source "drawn by <name>" and status `review`. Good for the garage conflict in a live demo.
- **Approve all in view** (Constech `SheetOverview.tsx` lines 85–106): mark every unflagged shape in the filtered list as reviewed. Flagged ones (conflicts, `different`, review required) are skipped, with a count.

---

## 4. "Review required" instead of "hardcoded"

Everything in `backend/demo_rules/*.yaml` that shapes a number or a status must be visible on the value it affects. Today the UI shows method "Project rule" for `RULE` values, but nothing for the 38 hand links in `bill_map.yaml`, the estimator factors (densities, the 0.8 coverage), factors read from the bill's own text, or values read from a single reader or an other-order copy. The user's requirement: put **Review required** on the source, with the reason and the citation.

### 4.1 Reasons, computed in the match stage

| Code | When | Text on the chip | Detail shown |
|---|---|---|---|
| `project_rule` | any input in the value tree has method `rule` | Review required · project rule | rule id, citation, why it could not be read |
| `hand_link` | the line was joined to its item by a `bill_map.yaml` entry | Review required · linked by hand | link id and citation |
| `estimator_factor` | a density, a coverage ratio, or another factor that is not on a drawing | Review required · estimator's factor | factor, the lines that imply it |
| `bill_text_factor` | `factor_source == "bill_text"` | Review required · factor from the bill text | the quoted words |
| `single_reader` | the source file has no second reader (LibreDWG crash or 0 entities) | Review required · one reader | file, reader status |
| `copy_only` | the only source is a sheet for another order | Review required · other order's sheet | sheet number |
| `conflict` | the value or line has conflicts | Review required · documents disagree | the sides |
| `manual` | a person set it | Set by <name> | reason, date |

```python
# match/provenance.py
def review_reasons(line_result: dict, item: dict | None, bill_map_ids: set[str], files: dict) -> list[dict]:
    out = []

    def walk(v: dict):
        if v["method"] == "rule":
            src = (v.get("sources") or [{}])[0].get("locator", {})
            out.append({"code": "project_rule", "rule": src.get("rule_id"), "citation": src.get("citation")})
        if v["method"] == "manual":
            out.append({"code": "manual", "note": v.get("note")})
        if v.get("conflicts"):
            out.append({"code": "conflict", "n": len(v["conflicts"])})
        for s in v.get("sources") or []:
            f = files.get(s.get("file_id"))
            if f and f.get("reader") == "single":
                out.append({"code": "single_reader", "file": f["rel"]})
        for child in (v.get("inputs") or {}).values():
            walk(child)

    if item:
        walk(item["value"])
    if line_result.get("link") in bill_map_ids:
        out.append({"code": "hand_link", "link": line_result["link"]})
    if line_result.get("kind") == "density" or line_result.get("coverage"):
        out.append({"code": "estimator_factor"})
    if line_result.get("factor_source") == "bill_text":
        out.append({"code": "bill_text_factor"})
    seen, uniq = set(), []
    for r in out:
        key = (r["code"], r.get("rule") or r.get("link") or r.get("file"))
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq
```

Store `review_reasons` on every report line and every takeoff item. Then:

- **Bill table:** a small "review" marker next to the status; hover lists the reasons.
- **Inspector header:** one chip per reason. Clicking a chip opens its detail (rule id and citation, link id, factor).
- **Source cards:** a rule source shows "Project rule R-DENSITY-SOIL · Review required" with the citation as the source text. It never says "measured".
- **Home:** a count "Values needing review" that opens the list grouped by reason. It replaces the current "values from project rules" count, which hides the hand links.
- **Exports:** the Evidence sheet gets a "Review" column with the reason codes.

Keep `test_platform_ui_never_mentions_hardcoding`. Add a test that every report line whose item has a `rule` input, or whose link is in `bill_map.yaml`, has a non-empty `review_reasons`.

### 4.2 Accepting a reason

A person may accept a reason ("density 1.75 confirmed by the estimator"). That is a review with action `accept` and target `reason:<line>:<code>`. The chip turns from "Review required" to "Reviewed by <name>" and stays visible. Nothing is ever silently cleared.

---

## 5. Bill screen: what a clicked line must show

When a person clicks a bill line, the drawer must answer three questions without a second click:

1. What number did we use?
2. How was it calculated: the formula, with every dimension and count?
3. Exactly where did each number come from: file, sheet, page or region, table row and column, entity handle, and the text as printed?

The link that joined the line to its item (`bill_map.yaml` BM-016 and so on) is **not** a source. It appears at most as a small "Linked by hand · Review required" chip (section 4). The sources are always the drawing cells.

### 5.1 What the drawer gets today, and why it shows so little

The data is complete in the takeoff. For example, line 10.1.15 (27.73 m³) has this value tree in the stored run:

```text
27.73 m³ = bottom_m3 + wall_m3 × count
  bottom_m3  9.41 m³  9335 Xocevend yangin su anbari dk.dwg · R1 · handle 146307 · "9.41 m³"
                      table "Bünövrə tavasının armaturlanması. Material sərfi", row "Beton "B 25"" (handle 14630A)
  wall_m3    4.58 m³  same file · R1 · handle 146B2E · "4.58 m³"
                      table "Monolit divar Md-1 armaturlanması. Material sərfi; 1 ədəd üçün"
  count      4        same file · R1 · handle 1675EF · "4", column Miq. on row "Monolit divar" (handle 145CFB)
```

And 2.6.7 (252 m²) is the sum of B × H × n over P-1 to P-4, each factor a cell on `9335 MH.pdf` page 21 (shown as page 22).

`frontend/src/pages/Bill.tsx` (around lines 110–112) only reads `item.value.sources`. A `derived` item has no sources of its own; its sources sit on its inputs. So for every derived line the drawer shows only "Measured item: depot_window_glass" and a one-line reason. No formula, no dimensions, no files.

Three data problems make the explanation weak even once it is rendered:

- **Inputs have code names.** `depot_ceiling_paint` is `a1 + a2 + a3`. They must be named "1st floor, garage (room 1): ceiling", "1st floor, other rooms: ceiling", "2nd floor: ceiling".
- **Schedule sources do not record their cell.** The locator has page and bbox but no row or column. The drawer cannot say "row P-1, column B".
- **One source points at the wrong text.** The mesh weight `kg_per_m2 = 1.35` (line 2.7.38) cites the text `4.İstilik izolyasiya qatı(penopolisterol )-70mm 5.Monolit də…`, not the span `1m2 -1.35kq`. When a number is parsed out of a longer cell, the source must be the span that contains the number, with the full cell as `context`.

Fix the data in the takeoff stage (it already has all of it):

```python
# when an extractor builds an input from a schedule cell
def cell_value(cell, *, name: str, label_en: str, label_az: str, unit: str) -> Value:
    """One schedule cell as a Value whose source says exactly which cell it is."""
    src = Source(cell.file_id, cell.file_name, {
        **cell.locator,                       # kind, page/region, bbox or handle
        "table": cell.table_title,            # 'Qapı-pəncərə və pəncərələrin təsnifatı'
        "row": cell.row_label,                # 'P-1'
        "col": cell.col_header,               # 'Ölçülər B' / 'Sahə m²' / 'Miq.'
        "sheet": cell.sheet_number,           # '9335- 01- MH'
        "span_bbox": cell.number_bbox,        # the number itself, for the crop
    }, cell.raw_text, cell.text)
    return Value(cell.number, unit, Method.SCHEDULE, Status.EXTRACTED, sources=(src,),
                 note=f"{label_en} | {label_az}")
```

The input names in `derive(...)` stay short for the formula (`P1_B_mm`). Every input `Value` also carries `label_en` / `label_az`, so the UI never shows a code name.

### 5.2 One endpoint that explains a line

```python
# api/app.py
@app.get("/api/line/{line_id}/explain")
def explain_line(line_id: str):
    """Everything a person needs to trust or question one bill line, flattened for display."""
    bill, report, take = _need("bill"), _need("report"), _need("takeoff")
    line = next((l for l in bill["lines"] if l["id"] == line_id), None)
    if line is None:
        raise HTTPException(404, "no such line")
    res = report["lines"][line_id]
    item = next((i for i in take["items"] if i["id"] == res.get("item")), None)

    def leaves(v: dict, path: list[str]):
        if not v.get("inputs"):
            yield {"path": path, "value": v["value"], "unit": v["unit"], "method": v["method"],
                   "status": v["status"], "label": v.get("note") or (path[-1] if path else ""),
                   "sources": [_source_view(s) for s in v.get("sources", [])]}
            return
        for name, child in v["inputs"].items():
            yield from leaves(child, path + [name])

    chain = []                                    # derived lines: walk up to the line that has an item
    cur = res
    while cur.get("derived_from") and len(chain) < 8:
        parent_id = cur["derived_from"]
        chain.append({"line": parent_id, "relation": cur.get("kind"), "factor": cur.get("density") or cur.get("coverage")})
        cur = report["lines"][parent_id]

    value = item["value"] if item else None
    return {
        "line": {k: line[k] for k in ("id", "description", "unit", "qty", "rate", "amount", "row")},
        "result": {k: res.get(k) for k in ("status", "our_qty", "gap", "gap_pct", "tolerance", "reason", "floor")},
        "item": item and {"id": item["id"], "label_en": item["label_en"], "label_az": item["label_az"],
                          "citation": item["citation"], "value": value["value"], "unit": value["unit"],
                          "method": value["method"], "formula": value.get("formula"),
                          "substituted": substitute(value) if value else None},
        "inputs": list(leaves(value, [])) if value else [],
        "printed": [_source_view(s) for s in res.get("sources") or []],   # 'printed' lines have no item
        "chain": chain,
        "review_reasons": res.get("review_reasons", []),
        "searched": value.get("searched", []) if value else [],
        "rejected": value.get("rejected", []) if value else [],
    }

def _source_view(s: dict) -> dict:
    loc = s.get("locator", {})
    return {"file": s["file_name"], "file_id": s["file_id"], "sheet": loc.get("sheet"),
            "page": loc.get("page"), "region": loc.get("region"), "handle": loc.get("handle"),
            "table": loc.get("table"), "row": loc.get("row"), "col": loc.get("col"),
            "printed": s.get("decoded_text"), "raw": s.get("raw_text"),
            "bbox": loc.get("span_bbox") or loc.get("bbox"), "at": loc.get("at"),
            "is_rule": s["file_id"] == "rule", "rule_id": loc.get("rule_id"), "citation": loc.get("citation")}
```

`substitute(value)` writes the formula with the numbers in place, for example `1200 × 2700 × 62 + 1200 × 900 × 9 + 1800 × 3020 × 6 + 3000 × 3020 × 1 = 252,276,000 mm² = 252.276 m²`. It walks the formula's names and replaces each with its input's value and unit. Write it with the same tokenizer as `reviews.evaluate`. Do not rebuild the formula from the note text.

A source whose `file_id == "rule"` (project rules) is shown as a rule with its citation and "Review required", never as a file (section 4).

### 5.3 What the drawer shows, top to bottom

```text
2.6.7  Paket şəffaf şüşə 4mm+şəffaf şüşə 4mm                          Depot · 1st and 2nd floor
Bill 252 m²   Drawings 252.276 m²   matched (exact at 0 decimals)

How it is calculated
  Window glass = Σ B × H × count, windows P-1 to P-4
  1200 × 2700 × 62 + 1200 × 900 × 9 + 1800 × 3020 × 6 + 3000 × 3020 × 1 = 252.276 m²

Dimensions and counts used
  Mark  B mm   H mm   Count  Area m²   Source
  P-1   1200   2700   62     200.88    9335 MH.pdf · p22 · 9335-01-MH · window schedule · row P-1
  P-2   1200    900    9       9.72    9335 MH.pdf · p22 · row P-2
  P-3   1800   3020    6      32.616   9335 MH.pdf · p22 · row P-3
  P-4   3000   3020    1       9.06    9335 MH.pdf · p22 · row P-4
  Count check: P-1 29 + 33 = 62 (1st + 2nd floor) ✓

Where each number is printed                                  [crop] [crop] [crop] …
  1200  9335 MH.pdf · page 22 · window schedule, row P-1, column "Ölçülər B"   [show on sheet]
  …

Linked by hand (BM-016) · Review required        ← small chip, not a source
Looked in: …   Rejected: …
```

Rules for the drawer:

- **The formula block** shows the item's label, the symbolic formula with readable names, then the substituted line and the result. For a schedule row read directly (no formula), it shows "Read from the schedule: 1344.00 m², floor type 1, basement".
- **The dimensions table** groups inputs by their schedule row (row label), one column per input kind (B, H, count, area, thickness, kg/m²), and a computed column per row. This is Constech's placement row pattern (`BillInspector.tsx` lines 163–190: tag, dimensions, quantity).
- **Every input row names its file, page or region, sheet number, table, row and column.** Clicking it opens the sheet in a preview tab with that cell outlined (section 3.2). Crops sit next to the row (`EvidenceCrop`).
- **Derived lines** (copies, area × thickness, m³ × density) show the chain: "2.7.37 = 188.2 m² (line 2.7.36, floor type 5) × 0.070 m (polystyrene 70 mm, same schedule row)". Each step names its source, and the parent's sources open the same way.
- **Printed lines** (no item) show the printed text with its file, page and context sentence, plus the label check result from B6 ("label: Novalça (downpipes), bill line: gutters").
- **`different` lines** show the gap in units, percent and money, and which side each number comes from.
- **Rule inputs** (densities, the basement note area) show "Project rule R-DENSITY-SOIL · Review required" with the citation where a file would be.
- **Not found / blocked lines** show "Looked in" (sheet titles, not just file names) and what is missing.

### 5.4 Tests

- `GET /api/line/2.6.7/explain` returns 12 inputs. Each has a file name ending `9335 MH.pdf`, a page, a `row` in {P-1, P-2, P-3, P-4} and a `col`. `substituted` ends with `252.276 m²`.
- `GET /api/line/10.1.15/explain` returns 3 inputs. `count` has `col == "Miq."` and handle `1675EF`.
- `GET /api/line/2.7.38/explain`: the `kg_per_m2` input's `printed` contains `1.35`.
- No input has a label equal to its code name (`a1`, `P1_B_mm`).
- No source in any explanation has a file name under `demo_rules/` unless `is_rule` is true.

## 6. Order of work

1. N1 and N2 (false matches). Add tests for the eight lines first. Then N3 and N4.
2. Section 5 (bill line explanation): the data fixes in 5.1, the endpoint, then the drawer. This is the screen the user looks at most.
3. Section 4 backend (`review_reasons`) and the chips in the existing Bill and Takeoff screens. This is small and makes the hand-set parts visible straight away.
4. Hatch rings and room linking (3.3 backend), the shapes endpoint, then the overlay in the viewer.
5. The inspector with Sources / Calculation / History, wired to the review API, with `apply_reviews` extended. It reuses the explanation endpoint from section 5.
6. Files rail and tabs (3.2).
7. Area book, Inputs register, command palette, schedule check.
8. N5 and N6 (tank geometry check, steel families), then roof and walls.

Done when:

- the eight lines in N1 and N2 are no longer matched or printed;
- clicking any matched or different bill line shows its formula with numbers in place, a dimensions table, and for every number the file, page or region, table row and column; no source is a rules file unless it is labelled as a project rule;
- clicking a coloured room on the first-floor plan of `(SON).dwg` opens an inspector that shows the schedule cell crops, the hatch area, the bill lines and the conflict;
- every hand-set value or link shows "Review required" with its citation;
- no more than 6 tabs are ever visible.
