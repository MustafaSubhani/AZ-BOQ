# BOQ engine audit: bugs, misses, edge cases and fixes

Audit of the Hadrut demo engine (`backend/azboq/`) against the plan (`.cursor/plans/az_boq_demo.plan.md`), done on 30 Oct 2026 against the stored run in `cache/azboq.sqlite` and the dumps in `cache/sheets/` and `cache/pdf/`. Every number below was read from those files or from the client drawings, not guessed.

Written for the agent that will make the fixes. Work top to bottom. Each item says what is wrong, the evidence, the fix, and the test that proves it. Code snippets are given only where the fix is easy to get subtly wrong.

The plan's rules still bind every fix:

- No number without a source, and no missing value replaced silently (`Value`, `blocked()`, `derive()` in `azboq/values.py`).
- The takeoff stage never reads the bill. Anything that uses bill text (descriptions, quantities) lives in `match/`.
- Constech (`D:\Constech`) is for UI patterns only. Copy no data, rules, rates or measurements from it.

---

## Contents

0. Where the engine stands today
1. P0 bugs: numbers or statuses that are wrong today
2. Readers: data the package has but the reader throws away
3. Sheet identity: copies for other orders, independence, building mapping
4. The area engine: schedules first, geometry second
5. Matcher: from "printed somewhere" to matched or different
6. Source inspector and editing in the frontend (ideas taken from Constech's UI)
7. Smaller issues (P2)
8. Acceptance table: what the engine must return after the fixes
9. Order of work

---

## 0. Where the engine stands today

From the stored run (`report`, `takeoff` stages):

| Status | Lines | Bill value (AZN) |
|---|---:|---:|
| matched | 26 | 162,025 |
| printed | 90 | 230,232 |
| derived | 20 | 71,462 |
| different | 2 | 208 |
| blocked | 1 | 26,338 |
| review (weak candidates only) | 628 | 391,307 |
| not_found | 1,408 | 2,228,934 |
| **total** | **2,175** | **3,110,506** |

The takeoff has 26 items, mostly stated notes and a few schedule rows. Only 2 lines come out `different`, so the product's main output, the discrepancy list, is nearly empty.

The drawings hold far more than this. Section 4 shows that the depot's floor, ceiling, wall-finish, window and sill areas are all printed as schedules in `9335 MH.pdf` (pages 20, 21 and 22). Several reproduce the bill to the cent, and several disagree with it, which is exactly what the demo should show. The engine misses them because:

- the table readers don't exist (no column headers, so no units, so the evidence finder rejects the numbers);
- whole entity types are never read (`ACAD_TABLE`, `MULTILEADER`, `HATCH`, most `LINE`s);
- the matcher only finds exact equality, so a schedule value that disagrees with the bill shows as `not_found` instead of `different`.

---

## 1. P0 bugs: numbers or statuses that are wrong today

### B1. A "sum" bill-map relation gives the group total to every line (double count)

`match/run.py`, `relation == "sum"` branch. BM-008 links lines 19.1.3 (383.7 m²) and 20.1.3 (216 m²) to `area_asphalt_roads` (599.7 m²). Both lines get `our_qty = 599.7` (verified in the stored report). Consequences:

- `export/generated_bill.py` writes 599.7 into both rows: 1,199.4 m² of asphalt instead of 599.7.
- The `Evidence` sheet of the client bill shows 599.7 as "our quantity" for a 383.7 line.
- `export/run.py` writes `our_qty` into column D for `different` lines. If a sum group ever disagrees, the group total lands in every row of the client's bill.

Fix: a group total is not a per-line quantity. Store the group result once and give lines no `our_qty` unless the group matches.

```python
# match/run.py, relation == "sum"
total = sum(l["qty"] for l in present)
dec = max(bill_decimals(l["qty"]) for l in present)
same = close_at(total, v["value"], dec)
group = {"lines": [x["id"] for x in present], "bill_total": total, "drawing_total": v["value"],
         "gap": None if same else total - v["value"]}
for l in present:
    out[l["id"]] = {
        "status": "matched" if same else "different",
        "item": item["id"], "link": bm["id"], "method": v["method"], "item_status": v["status"],
        # Only a matching group proves each line; a differing group says nothing about how to split the gap.
        "our_qty": l["qty"] if same else None,
        "group": group,
        "reason": f"lines {' + '.join(group['lines'])} = {total:g} "
                  f"{'equals' if same else 'differs from'} the printed {v['value']:g} {v['unit']}",
    }
```

In the report and the Home "money at stake" sort, count a group's gap once, not once per line. In exports, write nothing into D for a line whose `our_qty` is `None`; add the comment only.

Test: after a run, for every line `abs(our_qty - qty)` is either 0 or the line is `different` with a per-line source; no two lines share a `group` and each carry the group total.

### B2. Exports and derived lines copy the bill's own quantity as "ours"

Three places put a bill quantity into `our_qty`, which the plan forbids ("never take any quantity from BOQ-Hadrut.xlsx as our measurement"):

1. `printed` lines: `"our_qty": l["qty"]`. It is numerically equal to the printed value, but the source of the number in the record is the bill. Use the printed entry's own value: `strong[0]["value"]`.
2. Density lines in `_derived`: `"our_qty": l["qty"]`. It must be `parent_our_qty × density`, rounded to the bill line's decimals.
3. Copy lines in `_derived`: `parent.get("our_qty") or parent["qty"]`. This is the Constech silent-default pattern: when the parent has no `our_qty`, the bill quantity slips in.

The CI guard did not catch #3 because `tests/test_no_silent_defaults.py` only scans `azboq/engine/`. Extend it to `azboq/match/` and `azboq/export/` too. Expect a few legitimate `l["amount"] or 0.0` sums of money; mark those `# allow-default: money total, not a quantity`.

Test: no line in the report has `our_qty` taken from `bill.lines[*].qty` unless `status == "printed"` and the value equals the printed entry's value. Add a unit test where the parent has `our_qty=None` and check that the child is not derived.

### B3. The floor-grouped bill drops the −0.02 and no longer totals to the contract

`export/floor_bill.py` writes row 2333 as `=SUM(F{FIRST}:F{last+2})`. Its docstring says the total is the contract total, but the client formula is `=SUM(F11:F2332)-0.02`. The floor bill keeps every client line and rate, so it must reproduce 3,811,193.36. Today it is 0.0236 AZN off (0.02 × 1.18).

Fix: in the floor bill only (not the generated bill, which the plan says must not carry the fudge), write `=SUM(...)-0.02`. Also start the sums at row 11, as the client does, or prove that row 10 is empty.

Test: open the floor bill through `excel_finish`, read F of the total row, and assert 3,811,193.36.

### B4. Fire-tank concrete is wrong: one table row missed, per-element count never applied

Takeoff item `fire_tank_concrete` = 8.71 m³ ("sum of 2 material-table rows: 4.13 + 4.58"). The 27 m³ drinking tank comes out at 16.07 m³, more than the 81 m³ fire tank, which cannot be right.

What the fire-tank DK sheet (`9335 Xocevend yangin su anbari dk.dwg`, region R1) actually prints:

| Table title | Value |
|---|---|
| `Örtük tavasının armaturlanması. Material sərfi` (cover slab) | `Beton "B25"` 4.13 m³ |
| `Bünövrə tavasının armaturlanması. Material sərfi` (bottom slab) | `Beton "B 25"` 9.41 m³ (missed today) |
| `Monolit divar Md-1 armaturlanması. Material sərfi` (one wall) | `Beton "B25"` 4.58 m³ |

Bill 10.1.15 (walls and flat bottoms) is 27.73 m³ = 9.41 + **4** × 4.58. Bill 10.1.24 (cover slab) is 4.13. So the wall table is for **one** wall `Md-1`, and the tank has four.

The drinking tank (`9335 Xocavend icmeli su anbari dk.dwg`) titles its wall table `Monolit divarlar Md-1` (plural). There 3.89 + 10.60 = 14.49 m³ = bill 12.1.13 with no multiplier. **So never assume a multiplier.** The count must come from the drawing:

- Count the `Md-1` mark texts or leaders on the tank's plan region, de-duplicated by position (the mark may be drawn once per wall).
- Cross-check by geometry: centreline perimeter × wall height × 0.25 m (the note says `Su çəninin divarları dəmirbetondan 250mm qalınlığında`) must land within 5% of count × 4.58.
- If neither gives a count, the wall total is `BLOCKED` with `missing=("Md-1 wall count",)`. Do not use 4 because the bill fits.

Also fix the missed 9.41 row. It is a row-alignment failure: the value text and the label text sit at baselines further apart than `row_tol = 0.6 × h`. The real fix is reading tables by cell (section 4.2), not by baseline. As a stopgap, `sum_pattern` must log every anchor it found and every anchor it dropped, so a missing row becomes a review item instead of a silent omission.

Split the single `sum_pattern` item into one item per element (cover, bottom, wall per element, wall count, walls total), because the bill prices them separately. Then link them: 10.1.24 / 11.1.24 to cover; 10.1.15 / 11.1.15 to bottom + walls; 12.1.22 / 13.1.22 to cover; 12.1.13 / 13.1.13 to bottom + walls.

Test: fire tank cover 4.13, bottom 9.41, wall 4.58 × count; with the count `BLOCKED`, 10.1.15 is `blocked` with that reason. With the count found as 4, 10.1.15 `matched` at 27.73.

### B5. The upper-storey gate passes by tie-break luck

`storey_upper` reads slab levels −0.10, +3.20, +5.00, +6.50 from depot DK region titles. The steps are 3.30, 1.80 and 1.50, each seen once. `Counter.most_common(1)` returns the first inserted on a tie, which happens to be 3.30. The +5.00 is probably a stair landing or a tower level that lives in the same file.

Fix:

1. Use only titles that name a full slab (`səviyyəsində örtük` with `tava` or `örtük elementləri`), not `sütun` (column) or `pilləkən` (stair).
2. If the most common step is a tie, return `REVIEW` with all steps in `conflicts`.
3. Confirm the chosen step with a section dimension `3300` on a `Kəsim` page, the same way `floor_level_depth` already does for the basement.

Test: inject a fourth level and check the result becomes `REVIEW`, not a silently different number.

### B6. "Printed" accepts a number whose label says something else (gutters and downpipes swapped)

The depot roof note (`9335 MH.pdf` page 16, `Damın planı`) says:

```text
- Novun ümumi uzunluğu L=190.5 p.m.          gutters, total 190.5 m
- Novalçaların ümumi uzunluğu L=154.2 p.m    downpipes, total 154.2 m
Novalçalar Ø 100 mm; H=5.4 p.m - 5 ədəd
Novalçalar Ø 100 mm; H=7.1 p.m - 2 ədəd
Novalçalar Ø 100 mm; H=7.9 p.m - 3 ədəd
```

The bill has 2.5.13 `Novların düzəldilməsi: asma` (hanging gutters) = **154.2** and 2.5.14 `Metal su axıdıcı sistemin qurulması ... (PVC 100 mm)` (drain pipes) = **190.5**. The bill swapped the two. The engine marks both lines `printed` because the finder only checks the number and the unit (`unit_enough = e.unit == unit and sig >= 3`).

There is a second finding in the same note: the itemised downpipes sum to 5 × 5.4 + 2 × 7.1 + 3 × 7.9 = **64.9 m**, not the 154.2 the note states as their total. That is an inconsistency inside the drawing.

Fix (match stage): when the printed number's own sentence names a subject before `L=`/`S=`/`V=` (here `Nov`, `Novalça`), classify that subject with the same element classifier used for bill descriptions (section 5.1). If the subject class differs from the bill line's class, the hit is not `printed`. Report it as `different` with reason "the drawing gives this number to {subject}; the bill gives it to {line}", and link the line to the right number if one exists.

Add a consistency check (section 4.8): a note total next to itemised parts must equal their sum; if not, raise a drawing conflict.

Test: 2.5.13 and 2.5.14 both come out `different`, with the 190.5 / 154.2 swap explained; the conflicts list contains "downpipes: stated 154.2 m, itemised 64.9 m".

### B7. Copies of the same sheet for other orders count as independent evidence

`YRS - VM - XOCAVEND-NƏZARƏT.dwg` holds the same sheets three times, stamped for orders 9335, 9336 and 9337 (for example R10, R11 and R12 are all `Damın planı`, sheets `9336-02-MH`, `9337-02-MH` and `9335-02-MH`). It also has sheets from orders 9183 and 9083. `(SON).dwg` has `9336- 01- MH` and `9337- 1- RS` regions next to the 9335 ones.

Effects today:

- Bill 3.5.7 (12.8 m of gutters) is `printed` from sheet **9336**-08-MT, another order's copy.
- `table_row` marks a value `VERIFIED` when `values[best] > 1`, which three copies of one sheet satisfy trivially.
- Any `sum_pattern` over a file with copies adds the same row up to three times (its dedupe key includes the region id, which differs per copy).
- The plan's statement that `9336-04-MT` is a typo is wrong: `9335-04-MT` (R27, R28) exists in the same file. It is a copy, not a typo.

Fix: group regions into sheet families and keep one canonical member. See the snippet in section 3.1.

### B8. VERIFIED is inflated by sources that are not independent

The plan defines `VERIFIED` as "two independent sources agree". The code counts:

- a DWG text plus the PDF plot of the same DWG (`text_value`: `verified = len(kinds) > 1`);
- the same number twice in one file (`table_row`: `values[best] > 1`);
- copies of the architecture inside MEP files (room schedules repeated in `elektrik.dwg` and `9335-1-SK ... 2-ci variant.dwg`; `1395.80` and `665.30` show up in five files).

A plot or a copy agrees by construction. Fix: give each source a lineage key and require two distinct lineages (section 3.2).

### B9. A reader disagreement on REGION entities downgrades every value in the file

`elektrik.dwg` differs from LibreDWG by 28 `REGION` entities (0.06%). `Baş plan`, both `DYNX` files and both `POS` files differ only by `REGION` on layer `polygon`. LibreDWG does not read `REGION`. Every value from those files goes to `REVIEW`, including note text such as the demolition `V=7625.40m³`. `Vertikalka.dwg` is a real disagreement (11,152 against 2,591 entities), but its `MTEXT`/`TEXT` counts are what matter for the earth-balance values.

Fix: in `engine/extract.py::_status`, downgrade a value only when the disagreement touches the entity types and layers its sources came from. Store per-type and per-layer counts in the cross-check (they already exist as `type_diffs` and `layer_diffs`) and look up the source's type and layer.

```python
def _source_affected(src, cross) -> bool:
    kind = {"dxf_entity": ("TEXT", "MTEXT", "ATTRIB", "MULTILEADER"), "dxf_dimension": ("DIMENSION",)}.get(
        src.locator.get("kind"), ())
    types = {d["type"] for d in cross.get("type_diffs") or []}
    layers = {d["layer"] for d in cross.get("layer_diffs") or []}
    return bool(types & set(kind)) or src.locator.get("layer") in layers
```

A file where LibreDWG crashed or returned 0 entities has no second reading at all. Keep those as "single reader" with a visible note, not as "reader disagreement".

### B10. Bill sub-section headers with comma codes are dropped (retaining walls İD-1 to İD-13)

`bill/parse.py` treats a row as a header only when column A is a float. Rows 2099, 2107, …, 2195 have A = `'25,1,1'` … `'25,1,13'` (strings) and B = `İstinad divarı və daş hasar (İstinad divarı İD-1)` … `İD-13`. The parser skips them. Their 7 lines each (crushed stone, B7.5 prep, strip footing, A-3, wall, A-1, A-3) fall into section 25.1 `(Torpaq işləri)`. As a result:

- ids become `25.1.r2100` because item numbers restart in each group;
- the trade becomes `earthworks` (wrong) for about 400,000 AZN of reinforced concrete;
- the wall mark İD-n, which is the key to the drawing, is lost. `9335 Xocavend istinad divari ve hasar dk.dwg` labels the same walls İD-1 to İD-13 on its plan, on layer `BERKITME DIVARI`.

Fix: accept a header when A matches `^\d+([.,]\d+)+$` (string) and C/D are empty or 0. Give it code `25.1.1` (normalise the comma). Make it a child of 25.1. Line ids become `25.1.1.3` and so on. Copy the mark (`İD-1`) from the title into a `mark` field on the section and its lines. The section count becomes 132 headers + 13 sub-headers. Update `tests/test_bill.py::test_counts` to assert both numbers, and keep the line count at 2,175.

Also log every row with content that is neither a header nor a line. Today row 1149 (`0, 0, 0`) and these 13 rows vanish without a trace.

### B11. Sections without a building name fall to "site"

`_building(title)` only reads the title. `9.13 (Borular)` sits under building 9 (heating point) but becomes `site`. `24.1 (Qum meydançası)` is the sand pit, mark 12, and also becomes `site`. Fix: when the title names no building, inherit the building of the first section with the same `building_no`. Section 24 needs a `sand_pit` building (and `BUILDING_OK`, `BUILDING_ALIASES` entries). Log every inheritance as an event so it is visible.

### B12. Derived-line detection is too loose in one way and too strict in others

`match/run.py::_derived`:

- **Too loose.** It searches every earlier line of the section for an equal quantity, not the adjacent build-up. For `each` lines (1, 2, 4, 6 …) this links unrelated lines. Rule: `same quantity` only inside a contiguous build-up group (section 5.3), and for `each` only when the description has a repeat word.
- **Too strict on tolerance.** `_close(..., 3)` compares at 3 decimals. The bill rounds to its own decimals: 1,389.4 m³ × 1.8 = 2,500.92 t is billed as 2,501. Compare at the bill line's own decimals.
- **One direction only.** It looks backwards. Section 1.1 has the tonnes (1.1.2, 1.1.3 = 2,501 t) before the volume (1.1.4 = 1,389.4 m³). Look both ways inside the group.
- **Children of a `different` parent stay `not_found`.** A copy of a parent that differs must inherit `different`, with `our_qty` = the parent's `our_qty` (or × factor) and the reason "inherits from X".
- **Volumes and mesh weights are not derived at all.** Many m³ and t lines are area × thickness or area × kg/m² of a parent in the same group. Section 4.4 has the rules and the examples.

### B13. Tolerance by method is not implemented

Plan section 12: schedule and stated values exact at the bill's decimals, geometry 1%. Every comparison uses `_close(a, b, 3)`. Add `tolerance_for(value, line)`. Record the tolerance used on each report row and show it in the inspector.

```python
def bill_decimals(q: float) -> int:
    s = f"{q:.6f}".rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0

def close_at(a: float, b: float, decimals: int) -> bool:
    return abs(a - b) <= 0.5 * 10 ** -decimals + 1e-9

def tolerance_for(method: str, bill_qty: float, ours: float) -> tuple[str, bool]:
    if method in ("schedule", "stated", "derived", "rule", "manual"):
        d = bill_decimals(bill_qty)
        return f"exact at {d} decimals", close_at(bill_qty, ours, d)
    if method == "geometry":
        return "1%", abs(bill_qty - ours) <= 0.01 * abs(ours)
    return "review", False   # vision: never auto-matched
```

### B14. Floors: 2,006 of 2,175 lines "not stated", and parents split from their copies

`floors.py` tags a line only when its own text or its section title names a floor. Results: basement 37, 1st floor 8, 2nd floor 39, roof 85, not stated 2,006. Line 2.7.1 (basement concrete floor, 1,344 m²) is "not stated" while its copy 2.7.2 says `(Zirzəmi)` and lands under basement. The floor bill therefore puts a parent and its layer copy under different headings.

The estimator's convention is visible in section 2.7: the floor tag sits on one line of each build-up, often the last (`2.7.13 ... əlavə 5 mm üçün (1-ci mərtəbə)`, `2.7.21 ... (1-ci mərtəbə)`, `2.7.35 ... (1-ci mərtəbə Tip-4)`).

Fix, in this order:

1. A floor named on any line of a build-up group applies to the whole group. If two lines of one group name different floors, leave the group unstated and log it.
2. When a line is matched to a drawing source, take the floor from that source: the floor-type schedule row (`Texniki döşəməaltı`, `1-ci mərtəbə`, `2-ci mərtəbə` headings on page 20) or the sheet title of the region.
3. Recognise more spellings: `I mərtəbə`, `II mərtəbə`, `birinci`, `ikinci`, `texniki döşəməaltı` (= basement here), `zirzəmi`, `mərtəbəarası` (between floors: not a floor).
4. Record `floor_from` (`line`, `group`, `drawing`, `section`) and show it in the UI.

### B15. Mixed-script words break keyword matching

PDF spans switch font inside a word, and single Cyrillic letters survive decoding because each span is decoded on its own. A one-letter span such as `м` has no Azerbaijani or Russian score, so it stays Cyrillic. Real strings from `9335 MH.pdf` page 20: `4.Haмarlayıcı seмenт-quм мəhlulu - 27 мм`, `Yüngül beтon qatı (B 7.5 marкalı)`. Across the package: 95 mixed words in PDFs (`Lyuк`, `Meтal`, `кonsтruкsiyası`, `yerləşмə`) and 75 in DXF text (`КÜTLƏSİ`, `оlan`, `аd`).

`fold_key("seмenт")` does not equal `fold_key("sement")`, so these rows never share a keyword with the bill. Fix: after joining the spans of a line (PDF) or the runs of an MTEXT (DXF), fold every word that mixes Latin and Cyrillic letters through the default legacy table. Keep the raw text.

```python
# text/legacy.py
_MIXED_WORD = re.compile(r"[\wƏəÖöÜüÇçŞşĞğİı\u0400-\u04FF]+")
_LATIN = re.compile(r"[A-Za-zƏəÖöÜüÇçŞşĞğİı]")

def fold_mixed_words(text: str) -> str:
    """A word that mixes scripts is one word drawn with two fonts: 'seмenт' is 'sement'."""
    def fix(m):
        w = m.group(0)
        if _CYR.search(w) and _LATIN.search(w):
            return decode_with_family(w, DEFAULT_FAMILY).text
        return w
    return _MIXED_WORD.sub(fix, text)
```

Call it in `pdf/read.py` after `text = re.sub(...)` and in `text/mtext.py::decode_mtext` on `decoded`. The unit and thickness regexes must also accept Cyrillic `мм`, `м²`, `м3` (page 20 prints `- 27 мм` and `-30 мм`).

Test fixtures: `Haмarlayıcı seмenт-quм мəhlulu - 27 мм` becomes `Hamarlayıcı sement-qum məhlulu - 27 mm`; `ГОСТ 5781-82*` stays unchanged; `А500C` still folds through the homoglyph path.

### B16. LWPOLYLINE geometry is truncated and loses its arcs

`dwg/read.py`: `pts if len(pts) <= 400 else pts[:400]` cuts long outlines (site boundaries, roads, contours). `e.get_points("xy")` drops bulges, so arcs become chords. Any area or length computed later from `polys` is wrong for exactly the shapes that matter (curved kerbs, round tanks, site outline). Fix in section 2.4.

---

## 2. Readers: data the package has but the reader throws away

Counted in the depot DK DXF (`9335 Xocavend yangin deposu dk son.dwg`): 143 `ACAD_TABLE`, 435 `MULTILEADER`, 1,025 `LEADER`, 3,656 `HATCH`, 27,081 `LINE` (30 kept), 6,611 `LWPOLYLINE`, 4,291 `CIRCLE`, 1,198 `SPLINE`, 2,640 `ELLIPSE`. The dumper (`Dumper.visit`) handles `TEXT`, `MTEXT`, `ATTRIB`, `DIMENSION`, `INSERT`, `LINE` (table and frame layers only) and `LWPOLYLINE` (some roles only). Everything else is dropped without a count.

### R1. ACAD_TABLE: the steel schedules live here

The depot DK's `Polad sərfi cədvəli, kq-la` and `Elementə polad sərfi cədvəli, kq` tables are `ACAD_TABLE` entities. The dump has their titles (plain MTEXT next to the table) and none of their numbers. Example, table handle `3998E7`: `Sütun S-6`, A240 Ø8 64.4 kg, A500C 211.1 kg, total 275.5 kg. Table `3996C5` is the bar schedule (`∅20A500C L=3650mm 8 pcs 9.00 72.01`). Reinforcement is about 17% of the bill value. None of it can be checked today.

ezdxf 1.4.4 has no `acadtable` add-on, but `ACAD_TABLE.virtual_entities()` returns the cell `MTEXT`s and the grid `LINE`s (verified on `3998E7`: 24 MTEXT, 20 LINE). Read the grid, put each cell text in its row and column, and keep the cell address in the locator so the viewer can highlight one cell.

```python
# dwg/read.py, inside Dumper.visit
elif t == "ACAD_TABLE":
    self._table(e, base)
    return  # the table's block is the same content; expanding it again duplicates every cell

def _table(self, e, base):
    ves = list(e.virtual_entities())
    xs, ys = set(), set()
    for v in ves:
        if v.dxftype() == "LINE":
            a, b = v.dxf.start, v.dxf.end
            if abs(a.y - b.y) <= 1e-6:
                ys.add(round(a.y, 3))
            elif abs(a.x - b.x) <= 1e-6:
                xs.add(round(a.x, 3))
    xs, ys = sorted(xs), sorted(ys, reverse=True)

    def band(val, edges):
        for i in range(len(edges) - 1):
            lo, hi = sorted((edges[i], edges[i + 1]))
            if lo - 1e-6 <= val <= hi + 1e-6:
                return i
        return None

    cells = []
    for v in ves:
        if v.dxftype() != "MTEXT":
            continue
        res = decode_mtext(v.text, self._font(v))
        if not res.decoded:
            continue
        p = v.dxf.insert
        r, c = band(p.y, ys), band(p.x, xs)
        cells.append({"r": r, "c": c, "text": res.decoded, "raw": res.plain_raw, "at": _pt(p)})
        # Also a normal text, so the number index and every extractor see it, tagged with its cell.
        self._add_text({**base, "table": base["handle"], "cell": [r, c]}, "MTEXT", p,
                       v.dxf.get("char_height", 0), 0, res)
    self.tables.append({**base, "n_rows": max(len(ys) - 1, 0), "n_cols": max(len(xs) - 1, 0),
                        "bbox": [xs[0], ys[-1], xs[-1], ys[0]] if xs and ys else None, "cells": cells})
```

Edge cases:

- **Merged cells.** A header cell may span columns. Its insert point is in one band; look headers up by x-overlap, not by index.
- **Cells as anonymous blocks.** Some tables store cell content as a block reference (`*T…`). If `virtual_entities()` yields `INSERT`s, expand them once.
- **Legacy-font cells.** Decode them with the cell's own font switch (`\fArial Narrow|…|c204` is Cyrillic). The same `decode_mtext` path already handles this.
- **`CƏ{\f...;Mİ}`.** The word is split across font runs. The run parser joins it, so don't regex the raw string.
- **Red override values.** `{\C1;64.4}` next to `64.4`: the table prints the same number twice (a formula cell and its colour override). De-duplicate equal numbers in one cell.

Number index (`index/numbers.py`): for table cells, set `row_label` from the cells to the left in the same row and add `col_header` from the header cells above in the same column. Take the unit from the header (`kq`, `m³`, `m²`). See R6.

### R2. MULTILEADER text (element marks)

`MULTILEADER` carries its own text (`Mtv`, `Mk-1`, `Md-1`). `LEADER` does not (its MTEXT is a separate entity, already read). Read the mtext content and the text position. Verified on `2646AD`: `get_mtext_content()` returns `{\fTimes New Roman|…;\C7;Mtv}`.

```python
elif t == "MULTILEADER":
    content = e.get_mtext_content() or ""
    ctx = e.context
    at = ctx.mtext.insert if ctx.mtext is not None else ctx.base_point   # confirm the names on ezdxf 1.4.4
    res = decode_mtext(content, None)
    self._add_text({**base, "leader": True}, "MULTILEADER", at, ctx.char_height, 0, res)
    return
```

Marks are how the engine counts elements (B4: `Md-1` walls; columns `S-1`…; lintels). Store the leader's arrow point too (`ctx.leaders[0].lines[0].vertices[0]`) so a count can be de-duplicated by the element it points at, not by the text position.

### R3. HATCH boundary areas

Hatches are the fastest honest source of floor and finish areas: a designer hatches each floor type or material. The dump never reads them. Store the area of every hatch in drawing units² (convert with the region's unit later, never inside the reader), plus its layer, pattern and bbox. Skip hatch-stroke layers (role `hatch`) only for line output, not for hatch entities.

```python
from functools import reduce
from ezdxf import path as ezpath
from shapely.geometry import Polygon

def _hatch(self, e, base):
    rings = []
    for p in ezpath.from_hatch(e):
        pts = [(v.x, v.y) for v in p.flattening(distance=self.flat_tol)]
        if len(pts) >= 3:
            poly = Polygon(pts).buffer(0)
            if not poly.is_empty:
                rings.append(poly)
    if not rings:
        self.dropped["HATCH without a usable boundary"] += 1
        return
    # Hatch islands follow the even-odd rule: each nested ring toggles fill.
    geom = reduce(lambda a, b: a.symmetric_difference(b), sorted(rings, key=lambda g: -g.area))
    c = geom.representative_point()
    self.hatches.append({**base, "pattern": e.dxf.pattern_name, "solid": bool(e.dxf.solid_fill),
                         "area_du2": round(geom.area, 3), "bbox": [round(v, 3) for v in geom.bounds],
                         "rings": len(rings), "at": [round(c.x, 3), round(c.y, 3)]})
```

`flat_tol` must be in drawing units: about 1 mm. Derive it from the extents (`1e-5 × diagonal`), not from `$INSUNITS`, which lies on the site files (plan section 6.3).

### R4. Polylines, lines and curves: complete geometry, kept off the main dump

- Use `ezpath.make_path(e)` for `LWPOLYLINE` and `POLYLINE` (2D and 3D). It honours bulges. Compute `length` and, when closed, `area` from the full flattened path at read time. Store them even when you truncate the vertex list for size.
- Read `LINE`, `ARC`, `CIRCLE` and `ELLIPSE` for every role except `hatch`, `furniture`, `dimension`, `text`, `axis`, `hidden` and `architecture_background`. In the depot DK, 70,299 entities sit on layer `0`. A role-based keep-list sees none of them.
- Write lines to a separate file per drawing (`cache/sheets/<sha12>.geom.json`, compact arrays) so the main dump stays small and the API's region-meta endpoint stays fast.
- Count every dropped entity by type and layer (`self.dropped`) and store it in the dump. The drawing register shows it. A type that is never counted is a silent loss, the same failure the plan calls out for LibreDWG.

### R5. MTEXT position: store the attachment point and width

Row grouping (`locate.rows`, `row_of`, `_row_labels`) compares `t["at"][1]`, the insert point. For MTEXT the insert is the top-left, middle or bottom of the box depending on `attachment_point`, and multi-line cells grow downward. Two cells of one table row can have inserts a full line apart, which is why the fire tank's 9.41 row was not joined (B4). Store `attach`, `width` and line count. Compute a bbox and group by box overlap, not by insert y.

```python
def mtext_bbox(insert, attach: int, width: float, h: float, n_lines: int, line_spacing: float = 1.667):
    """attach: 1 TL, 2 TC, 3 TR, 4 ML, 5 MC, 6 MR, 7 BL, 8 BC, 9 BR (DXF code 71)."""
    total_h = h * (1 + (n_lines - 1) * line_spacing)
    w = width or h * 0.6 * 20   # width 0 means 'no wrap': estimate, and mark the bbox as estimated
    col, row = (attach - 1) % 3, (attach - 1) // 3
    x0 = insert[0] - w * col / 2
    y1 = insert[1] + total_h * row / 2      # top edge
    return [x0, y1 - total_h, x0 + w, y1]
```

Rotation: most schedule text is 0°. Rotate the box when `rot != 0`, or skip rotated text in table reading and log it.

### R6. Tables from positioned text (PDF pages and DXF line-grid tables)

Most schedules are not `ACAD_TABLE`. In PDFs they are text spans plus ruling lines. In DXF they are MTEXT on a line grid (`cedvel 0.09` layers), as the plan says (section 10). `schedules/dxf_tables.py` and `pdf_tables.py` from the plan do not exist yet. Build one table reader that takes text boxes and ruling lines from either source:

1. **Ruling lines.** PDF: `page.get_drawings()` gives every line and rectangle; keep horizontal and vertical segments. DXF: lines on table layers, or the `ACAD_TABLE` grid. The PDF dumper does not keep drawings today: add them.
2. **Table instances.** One page can hold two tables side by side. Page 20 has `Döşəmələrin eksplikasiyası` twice (x ≈ 60–530 and x ≈ 680–1160). Split by repeated header keywords and by gaps in the vertical rules.
3. **Columns** come from header cells (`Otaqların adı və ya nömrəsi`, `Döşəmənin tipi`, `Döşəmə elementlərinin göstəriciləri`, `Sahə` / `m²`, `Mövqe`, `Ölçülər B H`, `Mərtəbə sayı Tex.zir. 1 2 Cəmi`). Headers are split over several lines (`Sahə` above `m²`): join header cells by column band.
4. **Unit of a column** comes from its header (`m²`, `m³`, `kq`, `ədəd`, `(mm)`). Every number in the column inherits it. This alone turns the room-area hits (665.30 next to `1 Qaraj`, 160.00 next to `23 Dəhliz`) from weak into strong.
5. **Rows** come from the horizontal rules. Without rules, a new row starts at each non-empty cell of the key column (type number, mark, room number), and a cell's text is every box whose centre lies in the band.
6. **Section rows** inside a table (`Texniki döşəməaltı mərtəbəsinin planı`, `1-ci mərtəbə`, `2-ci mərtəbə`) are a floor heading for the rows below them, not data.
7. **Merged digits.** PyMuPDF joins adjacent room-number cells into one token: `1213` (rooms 12 and 13), `1617`, `2526`, `161819` (16, 18, 19). Split them first by character gaps (`page.get_text("rawdict")` gives char boxes), then, if needed, by the known room numbers of that floor with the rule "room lists ascend". Keep the token raw and mark it `review` if the split is ambiguous.

```python
def split_room_run(token: str, known: set[str], prev: int | None) -> list[str] | None:
    """'161819' after '15' -> ['16', '18', '19']. None when more than one split fits."""
    sols = []

    def walk(i, acc):
        if i == len(token):
            sols.append(acc)
            return
        for n in (2, 1, 3):
            part = token[i:i + n]
            if len(part) == n and part[0] != "0" and part in known:
                last = int(acc[-1]) if acc else prev
                if last is None or int(part) >= last:
                    walk(i + n, acc + [part])

    walk(0, [])
    return sols[0] if len(sols) == 1 else None
```

The output of a table read is a list of rows. Each cell is a `Source` (file, page or region, bbox or handle, raw and decoded text), so each number taken from it becomes a `Value(method=SCHEDULE)` with exactly that source.

### R7. Layer names with codepage mojibake

`àğìà 0.25` (depot DK, 736 entities) and two layers in the tower DK are Cyrillic `арма…` written in cp1251 and read back as cp1254. The role table cannot match them, so they stay `unclassified`. Repair the name for classification only (keep the raw name), then run the normal legacy decoder on the result.

```python
_NOT_AZ_LATIN = re.compile(r"[àáâãåæèéêëìíîïðñòóôõøùúûýþÿÀÁÂÃÅÆÈÉÊËÌÍÎÏÐÑÒÓÔÕØÙÚÛÝÞ]")

def fix_mojibake(name: str) -> str:
    # Azerbaijani Latin never uses à, ì, ð, ÿ ...; real names like 'Ölçülər' must not be touched.
    if not _NOT_AZ_LATIN.search(name) or "ə" in name or "Ə" in name:
        return name
    for wrong in ("cp1254", "cp1252"):
        try:
            cand = name.encode(wrong).decode("cp1251")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if re.search(r"[\u0400-\u04FF]", cand) and not _NOT_AZ_LATIN.search(cand):
            return cand
    return name
```

Do not include `Ø` in the trigger set: it is a real diameter sign in hundreds of texts.

### R8. Layer roles: grow the table from the data, per file

`layer_roles.yaml` has 26 patterns. `(SON).dwg` leaves 191,799 entity visits unclassified, the depot DK 79,603 and the fence DK 54,535. Known gaps seen in this audit: `BERKITME DIVARI` (retaining wall), `Beams_…`, `Xamut` (stirrups), `Ishare xetleri` (mark lines), `KON cedvel` (already table), `APS_MADEIRA`, `Layer2`, `nadpisi` (Russian `надписи` written in Latin: text). Generate a per-file "unclassified layers by entity count" list and classify the top layers of each file by hand in `layer_roles.yaml`, with the file in the citation. Add a `files:` scope to a pattern when a stem means different things in different files.

Also fix two over-broad patterns: `dam` matches any layer containing those letters, and `arm` matches any `…arm…`. Anchor them (`\bdam\b|^dam`, `^arm|armatur`).

---

## 3. Sheet identity: copies for other orders, independence, building mapping

### 3.1 Sheet families and the canonical copy

Group regions (DWG) and pages (PDF) that are the same sheet for different orders. Keep the 9335 member (9526 for the substation) as canonical. Mark the rest `copy_of`. If a family has no 9335 member, keep the one copy, flag it ("only copy carries order 9336; possibly a typo") and keep its values at `REVIEW`.

```python
# sheets.py, after detect_regions for one file
def assign_families(regions: list[dict]) -> None:
    fams: dict[tuple, list[dict]] = {}
    for r in regions:
        n = r.get("number") or {}
        key = (n.get("mark"), n.get("discipline_mark"), fold_key(r.get("title") or "")[:60])
        if key[0] is None:
            continue
        fams.setdefault(key, []).append(r)
    for members in fams.values():
        canon = [r for r in members if (r["number"] or {}).get("order") in ("9335", "9526")]
        keep = canon[0] if canon else members[0]
        for r in members:
            r["family"] = keep["id"]
            if r is not keep:
                r["copy_of"] = keep["id"]
        if not canon:
            keep["only_other_order"] = True
```

Use it everywhere:

- `engine/locate.py::texts_in`: skip texts in regions with `copy_of`.
- `index/numbers.py`: mark entries from copies `copy: True`. The finder skips them, and the inspector can still show "also printed on the 9336 copy".
- A new check compares each copy's numbers with the canonical sheet. Any difference is a finding for the Conflicts screen ("the 9337 copy of 9335-04-MT shows S dam = 27.64; the 9335 sheet shows …").

### 3.2 Independence: what may make a value VERIFIED

```python
def lineage(src: Source, regions_by_id: dict, files: dict) -> tuple:
    """Two sources confirm each other only when they are different drawings of the fact."""
    loc = src.locator
    if loc.get("kind") == "rule":
        return ("rule", loc.get("rule_id"))
    f = files[src.file_id]
    region = regions_by_id.get((src.file_id, loc.get("region"))) if loc.get("region") else None
    num = (region or {}).get("number") or {}
    if loc.get("kind") == "pdf_span":
        num = (pdf_page_info(src.file_id, loc["page"]) or {}).get("number") or {}
    sheet = (num.get("mark"), num.get("discipline_mark")) if num else (f.get("building"), f.get("discipline"))
    # A copy of the architecture inside an MEP drawing is still the architecture.
    if loc.get("layer") and layer_role(loc["layer"]) == "architecture_background":
        sheet = ("architecture", f.get("building"))
    table = loc.get("table") or loc.get("schedule")   # two different tables on one sheet are two readings
    return ("sheet", sheet, table)
```

`VERIFIED` requires two distinct lineages, for example the room schedule and the floor-type schedule, or a schedule and a geometry sum. A DWG region and its PDF plot share a sheet number, so they share a lineage: the plot confirms the reading, not the fact. Show that as "read twice (DWG and its plot)".

### 3.3 Section to building

Covered in B11. Add a test: every section with `building_no = 9` maps to `heating_point`, and section 24 maps to `sand_pit`.

---

## 4. The area engine: schedules first, geometry second

The user's requirement is that the area takeoff be right. On this package that means reading the designer's schedules completely, deriving the layer quantities from them with the thicknesses the schedules print, and measuring geometry only where no schedule exists. Every area gets a formula with each input traced to a cell.

### 4.1 What the depot schedules give (all in `9335 MH.pdf`, sheet 9335-01-MH)

**Page 20, `Döşəmələrin eksplikasiyası` (floor types).** Rows give rooms, type, layer build-up (with thicknesses) and area m²:

| Floor | Type | Rooms | Layers (from the cell text) | Area m² |
|---|---|---|---|---:|
| Basement (`Texniki döşəməaltı`) | 1 | 1–13 | concrete topping 50, concrete B10 100 | 1344.00 |
| Basement | 2 | 8, 11, 12 | ceramic 10, adhesive 5, screed 20, 2 × waterproofing, screed with mesh 30, keramzit 35, RC slab | 43.8 |
| 1st floor | 1 | 1 | mosaic concrete B25 50 | **658.30** |
| 1st floor | 2 | 5, 6, 12, 12* | timber floor 37, joists 100×50 (50), polystyrene 70, 2 × tol 13 | 129.0 |
| 1st floor | 3 | 3, 4, 13–17, 19, 20 | laminate 10, plywood 20, joists 50, polystyrene 70, tol 20 | 230.6 |
| 1st floor | 4 | 18, 25 | porcelain 10, adhesive 15, screed with mesh 40 (`Ø 4, BR1, ad 150x150mm, 1m2 - 1.35kq`), polystyrene 70 | 104.6 |
| 1st floor | 5 | 7–11, 21–24 | ceramic 10, adhesive 5, screed 20, 2 × waterproofing, screed with mesh 30, polystyrene 70 | 188.2 |
| 1st floor | 6 | 26 (× 2) | artificial marble 20, screed 30, RC stair | 39.00 |
| 1st floor | 7 | 2 | ceramic 10, adhesive 15, screed with mesh 40, polystyrene 70 | 21.0 |
| 2nd floor | 1 | 1–5, 7–16, 18, 19 | laminate 15, light concrete B7.5 50, polystyrene 70, screed 27 | 538.4 |
| 2nd floor | 2 | 6, 17, 20–22 | ceramic, adhesive, screed, waterproofing, screed with mesh 30, polystyrene 70 | 39.0 |
| 2nd floor | 3 | 23 | porcelain 10, screed with mesh 30, adhesive 5, polystyrene 70 | 160.0 |
| 2nd floor | 4 | 24 | artificial marble 20, screed 30, RC stair | 35.40 |
| External (`Artırma 1,2,3`) | 1 | | artificial marble 10, adhesive 10, screed 30, concrete | 24.6 |

**Page 21, `Yerləşkələrin bəzənməsi cədvəli` (finishes).** Ceiling and wall areas per floor:

| Floor | Rooms | Ceiling | m² | Walls | m² |
|---|---|---|---:|---|---:|
| Basement | 1–13 | lime whitewash | 1368.7 | plaster + whitewash | 3380.0 |
| 1st | 1 (garage) | smoothed, emulsion paint | 665.3 | plaster + emulsion | 375.7 |
| 1st | 3–6, 9–20, 22–26 | smoothed, emulsion paint | 686.7 | plaster + emulsion | 1602.0 |
| 1st | 7, 8, 21 | metal suspended | 32.0 | ceramic tiles | 190.0 |
| 2nd | 1–5, 7–9, 11–16, 18–20, 23, 24 | smoothed, emulsion paint | 653.6 | plaster + emulsion | 1915.0 |
| 2nd | 10 | plasterboard suspended | 96.0 | plaster + emulsion | |
| 2nd | 17, 21, 22 | metal suspended | 29.4 | ceramic tiles | 180.0 |

**Page 21, `Qapı-pəncərə və pəncərələrin təsnifatı` (windows).** Mark, B × H in mm, count per floor (`Tex.zir.`, 1, 2) and total. Also the window sills Pa-1 to Pa-5 (`1200x400x30(h)` …) with counts:

| Mark | B | H | Total | Sill | Sill size | Sill count |
|---|---:|---:|---:|---|---|---:|
| P-1 | 1200 | 2700 | 62 (29 + 33) | Pa-1 | 1200 × 400 | 62 |
| P-2 | 1200 | 900 | 9 (basement) | | | |
| P-3 | 1800 | 3020 | 6 (1 + 5) | Pa-3 | 1800 × 400 | 6 |
| P-4 | 3000 | 3020 | 1 | Pa-4 | 3000 × 400 | 1 |
| P-5 | 1600 | 1800 | 1 | Pa-2 | 2000 × 400 | 1 |
| QP-1 | 5400 | 3020 | 1 | Pa-5 | 3600 × 400 | 1 |
| QP-2 | 1600 | 2700 | 3 | | | |
| QP-3 | 1200 | 2700 | 3 | | | |

**Page 22**: doors and roller gates (same layout). **Page 19**: `Dam pəncərəsi DP - 1 (9 əd)`. **Page 16**: gutter and downpipe totals (B6). **Pages 4–6**: room schedules `Yerləşkələrin eksplikasiyası` per floor (room number, name, area, `Cəmi`).

Most of these are printed in the DWG too (`(SON).dwg`). Read both. They are one lineage (3.2), so they confirm the reading, not the fact.

### 4.2 Each schedule row becomes takeoff items with inputs

A schedule area is already a `Value(SCHEDULE)`. A quantity computed from schedule cells is a `derive()` whose inputs are those cells, so the inspector can show each factor and where it was printed. Example for window openings (bill 2.6.7: 252 m²; 2.6.6 text: `(252,28 m²)`):

```python
def openings_area(item_id: str, rows: list[dict], marks: list[str]) -> Value:
    """Sum of B × H × count over schedule rows. Every factor is a cell Value with its own source."""
    inputs, terms, keys = {}, [], []
    for row in rows:
        if row["mark"].value_text not in marks:
            continue
        k = re.sub(r"\W", "", row["mark"].value_text)            # 'P-1' -> 'P1'
        inputs[f"{k}_B_mm"], inputs[f"{k}_H_mm"], inputs[f"{k}_n"] = row["B"], row["H"], row["total"]
        terms.append(f"{k}_B_mm × {k}_H_mm × {k}_n")
        keys.append(k)
    if not keys:
        return blocked("m²", [item_id], [rows[0]["_table_label"]] if rows else [], "no row with these marks")
    return derive("m²", " + ".join(terms) + " ÷ 10⁶",
                  lambda **kw: sum(kw[f"{k}_B_mm"] * kw[f"{k}_H_mm"] * kw[f"{k}_n"] for k in keys) / 1e6,
                  **inputs)
```

Checks inside a schedule, each producing a conflict when it fails (never a silent pick):

- per-floor counts add up to the total (P-1: 29 + 33 = 62);
- room areas of a floor add up to the printed `Cəmi` (pages 4–6; the plan already noted 1,360.80 against the note's 1,360.20);
- the same room's area agrees across schedules: garage room 1 is 665.30 in the room schedule, 665.3 in the finish schedule, and **658.30** in the floor-type schedule. That is a conflict inside the design, and it decides bill 2.7.12 and 2.7.13 (665.3).

### 4.3 Which bill lines each schedule feeds

Grouped by building + floor + element + material + unit (the plan's match key, section 12 of the plan). The classifier in section 5.1 assigns each bill line its element and material.

| Element | Source | Bill lines (depot) |
|---|---|---|
| Floor build-up per type | page 20 area of the type | 2.7.x lines of that floor and type |
| Layer volume (m³) | type area × layer thickness from the same row | e.g. 2.7.3 keramzit 35 mm, the polystyrene 70 mm lines |
| Mesh steel (t) | type area × kg/m² printed in the layer text | 2.7.31 / 2.7.32, 2.7.38 / 2.7.39 |
| Ceiling finish | page 21 ceiling area, by ceiling type and floor | 2.8.1–2.8.6 |
| Wall finish | page 21 wall area, by finish and floor | 2.8.7–2.8.12 |
| Window and door openings | Σ B × H × n per type | 2.6.x |
| Window sills | Σ L × 0.4 × n | 2.6.11 |
| Roof windows | DP-1 count | 2.5.19 |
| Gutters, downpipes | note totals plus itemised lengths | 2.5.13, 2.5.14 |

### 4.4 Build-up derivation: thicknesses and mesh weights from the layer text

The m³ and t lines in a floor build-up are the parent area times a thickness or a unit weight. Section 2.7 shows it on almost every group:

| Line | Bill | Arithmetic | Factor printed on page 20 |
|---|---:|---|---|
| 2.7.3 | 1.533 m³ | 43.8 × 0.035 | `keramzit çınqılı-35 mm` (basement type 2) |
| 2.7.30 | 7.322 m³ | 104.6 × 0.070 | `penopolisterol )-70mm` (1st type 4) |
| 2.7.37 | 13.174 m³ | 188.2 × 0.070 | `penopolisterol )-70mm` (1st type 5) |
| 2.7.31, 2.7.32 | 0.141 t | 104.6 × 1.35 / 1000 | `1m2 -1.35kq` (1st type 4) |
| 2.7.38, 2.7.39 | 0.254 t | 188.2 × 1.35 / 1000 | 1.35 kg/m² printed only on types 4 and 7 |
| 2.5.4 | 106.1 m³ | 1414.2 × 0.075 | thickness from the roof section (75 mm polystyrene) |

Layer-text edge cases (all real, page 20):

- `B10-100mm`: the class number (10) is not the thickness (100).
- `150x150mm` is mesh spacing; the thickness is the last plain `<n> mm`: `(Ø 4, BR1,ad -150x150mm,1m2 -1.35kq)- 40mm` → 40.
- Cyrillic units: `- 27 мм`, `-30 мм`.
- A layer can continue on the next line without a number: `5."150"markalı sement-qum məhlulu` + `1 qat torlu -30 mm`.
- `Laqa taxta 100 X 50 (h) - 50 mm` → 50 (not 100 or 50 from the section size).

```python
THICK = re.compile(r"(?<![x×X\d.,])(\d+(?:[.,]\d+)?)\s*(?:mm|мм)(?![\w²³])", re.I)
KG_PER_M2 = re.compile(r"1\s*m\s*2?\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:kq|kg|кг)", re.I)
LAYER_START = re.compile(r"^\s*(\d{1,2})\s*[.)]")

def layers_of(cell_lines: list[str]) -> list[dict]:
    """Numbered layers; an unnumbered line continues the layer above it."""
    out = []
    for line in cell_lines:
        line = fold_mixed_words(line)
        if LAYER_START.match(line) or not out:
            out.append({"text": line})
        else:
            out[-1]["text"] += " " + line
    for layer in out:
        hits = [m for m in THICK.finditer(layer["text"])
                if not re.search(r"\d\s*[x×X]\s*$", layer["text"][:m.start()])]
        layer["thickness_mm"] = float(hits[-1].group(1).replace(",", ".")) if hits else None
        kg = KG_PER_M2.search(layer["text"])
        layer["kg_per_m2"] = float(kg.group(1).replace(",", ".")) if kg else None
    return out
```

Rules for using a factor:

- The factor comes from the same schedule row as the parent area. That is a drawing source (`SCHEDULE`) and the line is `derived` and checked.
- The factor is printed on another row of the same schedule (1.35 kg/m² reused for type 5): still a drawing source, but say so in the note ("weight per m² printed for type 4, applied to type 5's mesh layer").
- The factor only appears in the bill line's own text (`qalınlığı 30 mm`, `(250 mm)` on 21.1.1): record `factor_source = "bill_text"`. The line is consistent with a checked parent, but the factor is not on a drawing. List these separately in the report summary and never call them measured.
- A constant ratio with no printed factor: 2.7.15 (104 = 130 × 0.8) and 2.7.23 (184.5 = 230.6 × 0.8) look like insulation between joists at 80% coverage. That is an estimator's factor. Show it as a hint ("0.8 × parent, the same ratio as 2.7.23"), status `review`, never `derived`.

### 4.5 Per-element tables need a count

`material sərfi` and `polad sərfi` tables are often "for one element" (`Bir element üçün`, `1 ədəd üçün hesablanmışdır`; NƏZARƏT.dwg regions R32–R34 are titled `Materialların təsnifatı 1 ədəd üçün hesablanmışdır`). The engine must:

1. Detect the per-element wording in the table title or the region title.
2. Find the count: element marks on the plan (R2), a `N ədəd` note, or a count column.
3. Multiply, with the count as a named input `Value`.
4. If no count is found, `BLOCKED`. B4 is the worked example.

### 4.6 Geometry when no schedule exists

Several large depot parents are printed nowhere in the package. Searched in the number index: 1414.2 (roof build-up), 1992 (profiled sheet), 50.4 m³ (rafters), 1333.6, 1983.9, 3260, 3647, 474.2, 86.6 (finishes), 628.3 / 223 / 551 (limestone walls), 1201.7 (brick walls), 196.8 (partitions), and the depot concrete volumes (676.97, 146.87, 279.74, 133.52). For each one, the engine either measures it or says `not_found` with what it searched.

Order of methods:

1. **Hatch areas** (R3) on the plan region of that floor, grouped by layer and pattern. Floor and roof finishes are usually hatched.
2. **Closed polylines** on slab, roof and zone layers (`Элемент модели - Зона` exists in `(SON).dwg`: 83 entities). Room zones from ArchiCAD are room polygons.
3. **Wall pairing** for wall areas: parallel lines at 400 / 200 / 500 mm on wall layers, centreline length minus openings (from the window and door schedules), times storey height. This is the blocked `wall_length_depot` item. It needs R4 (lines kept) before it can start.
4. **Roof slope.** The roof plan prints slopes of 42.4% and 14.1% (page 16). Sloped area = plan area × √(1 + i²), per roof plane. The profiled-sheet lines (1,660 and 1,992 m²) follow the slope; the screed lines (1,414.2) may not. Do not decide which one the bill used. Compute both, show both, and let the matcher compare.

Every geometry result is checked against a schedule total where one exists (a floor's polygon sum against its room-schedule `Cəmi`, within 3%). The scale and units come from the region (plan section 6.3), never from `$INSUNITS` alone.

### 4.7 Retaining walls İD-1 to İD-13 (section 25, about 460,000 AZN)

After B10, each bill sub-section is one wall `İD-n` with a fixed 7-line build-up. The fence DK has the same marks on its plan (region R8 `Baş plan.`) and in detail regions (R63, R67, R71, R74 …). Read, per wall type, the cross-section dimensions (footing width × depth, wall thickness × height) and the stretch length from the plan, then derive: crushed stone, B7.5 prep, footing concrete, wall concrete. Reinforcement comes from the wall type's steel table (R1 / R6). Read the `İD-n` labels' layer as `fence` (R8). Investigate first how the fence DK states lengths: dimension chains, `L=` notes, or a stretch table.

### 4.8 Consistency checks inside the drawings (they produce conflicts, not values)

| Check | Real case |
|---|---|
| Room areas of a floor add up to `Cəmi` | room schedules pages 4–6 |
| Same room, same area in every schedule | garage 665.30 / 665.3 / 658.30 |
| Note total equals the itemised parts | downpipes 154.2 against 64.9 |
| Per-floor counts add up to the total | windows P-1 29 + 33 = 62 |
| A copy for another order equals the canonical sheet | NƏZARƏT.dwg 9335 / 9336 / 9337 |
| DWG region equals its PDF plot | `(SON).dwg` against `9335 MH.pdf` |

Put them on the Conflicts screen next to the document conflicts, with both sources and a suggested side.

---

## 5. Matcher: from "printed somewhere" to matched or different

### 5.1 Keyed matching with an element classifier

Today a line gets a drawing value only through 15 hand-written `bill_map.yaml` entries or an exact printed number. Add the plan's keyed matcher: building + floor + element + material + unit.

- **Element and material for bill lines**, from the description with a keyword table in `demo_rules/bill_elements.yaml` (cited to example lines): `tavan` → ceiling; `divar` + `suva` → wall plaster; `keramik` + `divar` → wall tiles; `mozaik`, `terraso` → terrazzo floor; `laminat` → laminate floor; `keramoqranit` → porcelain floor; `penopolistrol` → polystyrene layer; `armatur məftil`, `döşənək ... armaturlanması` → mesh; `pəncərə` → window; `qapı` → door; `pəncərəaltı` → sill; `nov` → gutter; `su axıdıcı`, `novalça` → downpipe. The type tags in descriptions are strong keys: `(1-ci mərtəbə Tip-4)`, `(Zirzəmi)`, `(zirzəmi tavan)`.
- **The same classifier for drawing items**, from schedule row text, table titles and note subjects.
- **Candidates**: items with the same building, floor (or floor unknown), element and unit. If several fit, pick none automatically. Show them all as candidates and let a person confirm (section 6).
- **Result**: `matched` within tolerance (B13), otherwise `different` with gap, percentage and money (gap × rate). This is how the finish lines come out:

| Line | Bill | Drawing | Expected |
|---|---:|---|---|
| 2.8.1 basement ceiling whitewash | 1333.6 | 1368.7 | different, −35.1 |
| 2.8.2, 2.8.3 ceilings plaster + paint | 1983.9 | 665.3 + 686.7 + 653.6 = 2005.6 | different, −21.7 |
| 2.8.4, 2.8.5 plasterboard ceiling | 96 | 96.0 (room 10) | matched |
| 2.8.6 aluminium suspended ceiling | 86.6 | 32.0 + 29.4 = 61.4 | different (confirm no other metal ceiling) |
| 2.8.7, 2.8.8 basement walls | 3260 | 3380.0 | different, −120 |
| 2.8.9, 2.8.10 walls improved plaster + paint | 3647 | 375.7 + 1602.0 + 1915.0 = 3892.7 | different, −245.7 |
| 2.8.11, 2.8.12 | 474.2 | ceramic walls 190.0 + 180.0 = 370.0 | candidate only, confirm the mapping |

The gap sign convention (bill − drawing) must be the same in the report, the UI and the exports.

### 5.2 The evidence finder needs table context

With R6, index entries from tables carry `col_header` and the column unit. The finder then accepts `665.30` next to `1 Qaraj` under `Sahə m²` as a strong m² hit. It still needs the B6 label check: a room area hit for a floor-finish line is a match only through the floor-type link (room 1 → type 1 → 658.30), otherwise it is a candidate. Never "search all files for small integers" (plan 5.3). Keep the weak rule for 1–2 significant digits.

### 5.3 Build-up groups

A build-up group is a contiguous run of lines in one section:

- it starts at an m² line with quantity Q;
- it continues while lines are m² with quantity Q (copies), m³ ≈ Q × t, or t ≈ Q × k / 1000, with t and k found as in 4.4;
- it ends at the next m² line with a different quantity, or at a unit that fits none of these.

Status, floor (B14) and the matched drawing item propagate across the group. The report shows the group as one parent with children, which also makes "parents and leaves are scored, layer copies are not" (plan section 12) possible in the summary.

### 5.4 Quantities written inside bill descriptions

Descriptions state parent quantities: `(252,28 m²)` on 2.6.6, `(1201,7 m², qal=20 sm)` on 2.4.4 (240.34 m³ = 1,201.7 × 0.20), section titles `383,7 m²`, `1021 m²`, `1437,8 m²`, `TİP1-16m²`. Parse them in the match stage only. They tell the matcher which drawing number to look for, and they give a self-consistency check ("240.34 = 1,201.7 × 0.20, as the line itself says"). They never count as drawing evidence, and the takeoff never sees them.

### 5.5 Reviewer comments

`_reviewer` handles `a-b=c` and `N m2 az`. Keep both. Also show the parsed result next to the drawing value in the inspector, so a person sees bill, reviewer and drawing side by side (plan section 12).

---

## 6. Source inspector and editing in the frontend (ideas taken from Constech's UI)

This section takes interaction patterns from Constech's UI (`ElementInspector.tsx`, `BillInspector.tsx`, `QuantityRow.tsx`, `FormulaEditor.tsx`, `EvidenceCrop.tsx`) and no data. Today AZ-BOQ shows a Takeoff "Why this number" panel and a Bill line drawer, both read-only. The API has no write endpoint, and `Method.MANUAL` exists but nothing produces it.

### 6.1 What to build

**Line inspector (Bill screen), three tabs.**

1. *Sources*: every source grouped by sheet. Each source is a card with an evidence crop (6.4) cut from the PDF page raster or the DWG region tile and centred on the cell or text. Click it to open the viewer at that spot. A "Highlight all on the drawings" button opens the viewer with every source of the line marked. Copies and plots from other lineages appear greyed under "also printed on".
2. *Calculation*: the formula rendered as math (`Σ B × H × n ÷ 10⁶`). Each variable is a chip showing its value, unit and method; hovering a chip shows its crop. For a schedule sum, a breakdown table with one row per schedule row (P-1: 1200 × 2700 × 62 = 200.88). Below that: tolerance used, gap, percentage, money impact, "looked in" and "rejected candidates".
3. *History*: every review action on this line (6.2), newest first, with author, reason and the value before and after.

**Item inspector (Takeoff screen).** The same tabs, plus the input tree that already exists. Every leaf input gets an edit button.

**Editing, always with a reason (Constech's `QuantityRow` pattern).** Every edit keeps the engine value next to the override ("engine 252.28") and has a one-click reset. A reason is required and stored. The edit kinds:

- *Override a quantity* with an expression over named variables (`P1_B_mm * P1_H_mm * 62 / 1e6`). The result is a `Value(method=MANUAL)` whose inputs are the variables. Each variable is either picked from an existing source or typed in, with the reason as its source.
- *Set a missing input*: `Md-1 wall count = 4`, from a person who counted the plan. It unblocks the dependent items, which then show "depends on a manual input".
- *Accept or reject a candidate*: a weak hit or a keyed-match candidate becomes the line's source (status `matched` or `different`, method of the source, note "confirmed by <name>"), or is rejected with a reason and never offered again.
- *Map a line to an item*: pick the takeoff item for a bill line. It replaces editing `bill_map.yaml` by hand for the demo. Export the accepted mappings to `bill_map.yaml` with a button for the developer.
- *Decide a conflict*: choose a side on the Conflicts screen. Record who, when and why. The other side stays visible.

**Review queue.** Previous and next through the filtered list (keys N and P), "mark reviewed" (R), and a progress count ("212 of 2,175 lines reviewed") on Home.

**Area book screen (new).** Buildings → floors → rooms: room number and name, area, floor type, ceiling type, wall finish, with each value's source and the `Cəmi` checks from 4.8. Under each floor type: its layer build-up, the thickness and kg/m² read from it, and the bill lines that use it with their status. This is the screen that shows the area takeoff to the client.

**Labels the UI must get right.**

- A `printed` line shows "Printed value", not "Ours".
- A `derived` line shows the formula and its parent.
- `factor_source = bill_text` shows "factor from the bill's own text".
- `MANUAL` values show "entered by <name>: <reason>", always distinct from measured values. This is the plan's observability rule applied to people.

### 6.2 Backend: a reviews table, applied as its own stage

The API must not measure at request time (plan section 4). Applying review actions and re-running the matcher is not measuring: it is a pure function of stored stages plus the reviews. Cache the `Finder` (it loads a 34 MB index) in the API process.

```python
# azboq/reviews.py
SCHEMA = """create table if not exists review (
    id integer primary key autoincrement,
    target_kind text not null,        -- line | item | input | candidate | mapping | conflict
    target_id text not null,
    action text not null,             -- override | set_input | accept | reject | map | decide | reset
    payload text not null,            -- json: expression, variables, value, unit, source ref, side
    reason text not null check (length(trim(reason)) > 0),
    author text not null,
    created_at real not null,
    superseded_by integer references review(id)
)"""

def manual_value(payload: dict, reason: str, author: str, review_id: int) -> Value:
    src = Source("manual", f"review #{review_id}", {"kind": "manual", "review_id": review_id, "author": author},
                 None, reason)
    inputs = {k: Value.from_dict(v) if isinstance(v, dict) else
              Value(float(v), payload["units"].get(k, ""), Method.MANUAL, Status.REVIEW, sources=(src,))
              for k, v in payload.get("variables", {}).items()}
    result = evaluate(payload["expression"], {k: iv.value for k, iv in inputs.items()})  # safe parser, no eval()
    return Value(float(result), payload["unit"], Method.MANUAL, Status.REVIEW, sources=(src,),
                 formula=payload["expression"], inputs=inputs, note=f"{author}: {reason}")
```

- `POST /api/review` validates, inserts, runs `apply_reviews()` + match + floors, and returns the changed lines. `DELETE /api/review/{id}` marks it superseded (never deletes) and re-runs.
- `apply_reviews()` runs after `takeoff` and before `match`. It replaces item values and inputs, adds mappings, and records decisions. It never edits `demo_rules/*.yaml`.
- The run manifest records the review ids applied. Exports put "manual" in the Evidence sheet's method column.
- The expression evaluator must be a small parser (numbers, variables, + − × ÷, parentheses, `sum`, `round`), never Python `eval`.

### 6.3 Constech habits not to copy

Constech's override edits the line total directly ("Applies to the whole line"). Here the preferred edit is at the input (count, thickness, area of one schedule row), so the change propagates to every line that uses that input and stays explainable. Keep the line-level override, but label it as the last resort, like Constech does.

### 6.4 Evidence crop coordinates (easy to get wrong)

PDF bboxes from PyMuPDF `get_text("dict")` are in points with the origin at the top left. The page PNG is rendered at 110 dpi (`api/app.py::pdf_page_png`). DXF coordinates have y pointing up; image rows go down.

```ts
// PDF span bbox [x0, y0, x1, y1] in points -> pixel box on the 110-dpi page PNG
const PDF_DPI = 110
export const pdfToPx = (b: number[]) => b.map((v) => (v * PDF_DPI) / 72)

// DXF world point -> pixel on a region tile. Region bbox [X0, Y0, X1, Y1] is in drawing units, y up.
export function dxfToPx([x, y]: number[], [X0, Y0, X1, Y1]: number[], pngW: number, pngH: number) {
  const s = Math.min(pngW / (X1 - X0), pngH / (Y1 - Y0))   // must equal the scale render.py used
  return [(x - X0) * s, (Y1 - y) * s]                      // flip y
}
```

Take the scale from the region-meta response (`render_region` should return the transform it used), not from a re-derivation in the browser. If the tile has a margin or is letterboxed, the transform must include the offset.

---

## 7. Smaller issues (P2)

1. `export/client_bill.py::excel_finish` accepts `timeout_s` and never uses it. The plan wants a timeout and a kill of `EXCEL.EXE` on hang. Run Excel in a worker with `win32process` and kill it by pid on timeout.
2. `floor_bill.py` and `generated_bill.py` delete everything below row 10, including the helper columns AX–AZ that the plan says to preserve. That is acceptable for these two exports only if documented in the export notes.
3. `dimension_extreme` takes the largest repeated dimension in range. A site or roof-overhang dimension repeated twice in a depot region would beat 45200. Restrict to plan regions (title `planı`, not `Fasad`, `Kəsim`, `Baş plan`) and to dimension layers.
4. `slab_level_step` and `floor_level_depth` read `rule["building"]` texts, but in `(SON).dwg` two regions are the tower. They are filtered by building today. Keep a test that injects a tower level and checks the depot gate does not move.
5. `_pdf_confirms` searches every line of `9335 MH.pdf` when a rule has no PDF. Any equal number anywhere confirms. Restrict it to pages of the same building and sheet family.
6. `_project_conflicts` searches with `str.lower()`, which is wrong for `İ`/`ı` (plan trap 21). Use `fold_key`.
7. `sheets.py::TITLE_RE` matches `plan\b` inside `Baş plan` and `planlaşdırma` sentences, so region titles are sometimes a note. Prefer the largest text inside the stamp's title cell.
8. `locate.dwg_files(name_contains)` matches by substring of the folded file path. `"(SON)"` works, but `"yangin su anbari dk"` would also match a future `...anbari dk 2.dwg`. Match by sha in `extractors.yaml` once the files are fixed.
9. `parse_bill` keeps `unit_raw` but the generated and floor bills write it back as the unit. Fine. But `FF` (row 2330) must keep its warning in every export.
10. The number index stores `context` as the first 200 characters. A long note loses the sentence with the number. Store the sentence around the match (±120 characters) instead.
11. `Finder.direct` skips three-decimal values under 100 unless the unit is m³ or t (level marks). Real tonnages like `0.141` pass, but `13.174` m³ also passes. Keep it, but also reject when the text has a `±` or a level symbol next to it.
12. The source map (`sourcemap.py`) is not read by the resolvers. The plan wants "looked in" lists to come from it. Wire `_searched()` to the source map cell for (building, trade).

---

## 8. Acceptance table: what the engine must return after the fixes

Use these as tests (`tests/test_acceptance_depot.py`, skipped when the caches are missing). "Expected" is the engine's output, not a claim about which document is right.

| Line | Bill | Expected engine result | Source |
|---|---:|---|---|
| 2.5.13 gutters | 154.2 m | different: the drawing gives 154.2 to downpipes, gutters are 190.5 | MH p16 note |
| 2.5.14 drain pipes | 190.5 m | different: 190.5 is the gutter total | MH p16 note |
| 2.5.19 roof windows | 9 | matched | MH p19 `DP - 1 (9 əd)` |
| 2.6.7 window glass | 252 m² | matched at 0 decimals: Σ P-1..P-4 = 252.276 | MH p21 window schedule |
| 2.6.8 PVC window | 2.88 m² | matched: P-5 1.6 × 1.8 × 1 | MH p21 |
| 2.6.10 glazed doors | 39 m² | matched at 0 decimals: Σ QP-1..QP-3 = 38.988 | MH p21 |
| 2.6.11 window sills | 37.52 m² | matched: Σ L × 0.4 × n = 37.52 | MH p21 sills |
| 2.7.1, 2.7.2 | 1344 m² | matched, floor basement (both lines) | MH p20 type 1 |
| 2.7.3 keramzit | 1.533 m³ | derived: 43.8 × 0.035 | MH p20 basement type 2 |
| 2.7.6–2.7.11 | 43.8 m² | matched, floor basement | MH p20 basement type 2 |
| 2.7.12, 2.7.13 terrazzo | 665.3 m² | review: room and finish schedules say 665.3, floor-type schedule says 658.30 (conflict) | MH p4–6, p20, p21 |
| 2.7.14–2.7.21 timber floor group | 130 m² | different: drawing 129.0 | MH p20 1st type 2 |
| 2.7.22–2.7.28 laminate group | 230.6 m² | matched, floor 1st | MH p20 1st type 3 |
| 2.7.29–2.7.35 porcelain group | 104.6 m² | matched; 2.7.30 derived 104.6 × 0.07; 2.7.31, 2.7.32 derived 104.6 × 1.35 kg | MH p20 1st type 4 |
| 2.7.36–2.7.45 ceramic group | 188.2 m² | matched; 2.7.37 derived × 0.07; 2.7.38, 2.7.39 derived × 1.35 kg (factor from type 4, noted) | MH p20 1st type 5 |
| 2.7.46–2.7.48 stairs | 39 m² | matched | MH p20 1st type 6 |
| 2.7.56–2.7.61 2nd floor laminate | 538.4 m² | matched, floor 2nd | MH p20 2nd type 1 |
| 2.7.65–2.7.71 | 39 m² | matched, floor 2nd | MH p20 2nd type 2 |
| 2.7.75–2.7.77 | 160 m² | matched, floor 2nd | MH p20 2nd type 3 |
| 2.7.78–2.7.80 | 35.4 m² | matched, floor 2nd | MH p20 2nd type 4 |
| 2.8.1 | 1333.6 m² | different, drawing 1368.7 | MH p21 |
| 2.8.4, 2.8.5 | 96 m² | matched | MH p21 room 10 |
| 2.8.7, 2.8.8 | 3260 m² | different, drawing 3380.0 | MH p21 |
| 10.1.24, 11.1.24 tank cover | 4.13 m³ | matched | fire-tank DK R1 |
| 10.1.15, 11.1.15 walls and bottom | 27.73 m³ | blocked until the Md-1 count is found; matched as 9.41 + 4 × 4.58 when it is | fire-tank DK R1 |
| 12.1.13, 13.1.13 | 14.49 m³ | matched: 3.89 + 10.60, no multiplier | drinking-tank DK R1 |
| 19.1.3 / 20.1.3 | 383.7 / 216 m² | matched as a group; each line's `our_qty` is its own quantity, never 599.7 | Vertikalka note |
| 3.5.7 | 12.8 m | not from sheet 9336-08-MT; only the 9335 sheet may supply it | NƏZARƏT.dwg |
| 25.1.x (after B10) | | 13 sub-sections İD-1 … İD-13, each with 7 lines, trade fence / reinforced concrete | bill rows 2099–2202 |

Global invariants to add to `tests/test_boundaries_and_invariants.py`:

- No two lines carry the same `group` total as their own `our_qty` (B1).
- `our_qty` never equals the bill quantity by assignment: every non-null `our_qty` has a source that is not the bill (B2).
- The floor bill totals 3,811,193.36 (B3).
- No source of a `matched`, `printed` or `derived` line lies in a region with `copy_of` (B7).
- Every `VERIFIED` value has sources from two lineages (B8).
- The dump of every DXF reports zero entity types read as "unknown" without a count (R4).

---

## 9. Order of work

1. **P0 bugs that corrupt numbers**: B1, B2, B3, B10, B11, B13. Small changes, high trust impact. Add the invariants from section 8 first, watch them fail, then fix.
2. **Reader completeness**: R4 (dropped-entity counts first, so you can see what is lost), R1, R2, R3, R5, R7. Re-run `read`, `sheets` and `index`.
3. **Sheet identity**: 3.1 families, 3.2 lineage, B9. Re-run `takeoff`.
4. **Tables**: R6 on `9335 MH.pdf` pages 20, 21, 22, then the DXF line-grid tables, then `ACAD_TABLE` steel schedules in the depot DK.
5. **Area engine**: 4.2 schedule items, 4.4 build-up derivation, 4.5 per-element counts (fixes B4), 4.8 consistency checks.
6. **Matcher**: 5.1 classifier and keyed matching, 5.3 build-up groups (with B12, B14), B6 label check, B15.
7. **Inspector and editing**: 6.2 backend reviews first, then the line inspector tabs, crops, the Area book.
8. **Geometry** for what has no schedule: 4.6 roof, walls, then 4.7 retaining walls.

Done when the acceptance table in section 8 passes, the Home counts show the `different` list populated from the finish and floor schedules, and every quantity in the inspector opens a crop of the cell it came from.
