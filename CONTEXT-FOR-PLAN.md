# Context for planning

This file is the brief for an agent that will write an implementation plan. It is self-contained. Deeper evidence is in the files named at the end. Do not treat the 16-folder tree as a request to build 180 screens.

The client data is a real Azerbaijani fire-station design. The Excel bill is the test. The drawings are the input. Nothing in this repository is the application yet.

## 1. What the lead asked for

Sagar defined two products. They share a company and a project. They do not share a first build.

**Module 1. Drawing-to-bill check** (his words: AI BOQ verification, drawing-to-BOQ validation engine)

Read CAD and PDF drawings, extract quantities, compare them with the client's Excel bill, and write a discrepancy report that shows where each number came from.

**Module 2. Construction operations and fraud checks** (his words: construction business automation, operations and fraud intelligence)

Digitise the company's departments, record material and money movements, and flag a quantity, a rate, or a payment that does not match the register next to it.

His first message was a folder tree of 16 Excel workbooks (`PJ_00` to `PJ_16`), each tab named in Azerbaijani and English. That tree is the information model for module 2. It is not the screen list for version 1.

A later readiness table said most of those department groups can be started as empty frameworks, and that the rules (who approves, which form, which code) are still missing. Those rules are not blockers for module 1.

## 2. What to build, and in what order

**First release is module 1 only**, proved on the Hadrut package.

The user-facing job has four steps:

1. Drawings. Upload the package. Classify each file. Hide backups, plot logs, and the zip.
2. Takeoff. One row per measured surface: building, material, unit, quantity, and the sheet it came from.
3. Bill. Read `BOQ-Hadrut.xlsx`: description, unit, quantity. Keep the rate in the file. Do not score it.
4. Report. Three lists: matched, different, not found on a drawing. Different rows show both quantities and the gap. One export, Excel or PDF.

**Second release is a thin slice of module 2**, not the whole tree. Build only the registers a quantity or a payment can be checked against:

| Workbook in the tree | Tabs that matter first | Why |
|---|---|---|
| `PJ_00` Command center | Home, project health, alerts | Counts of open differences, and the list under them |
| `PJ_02` Tender | Master bill, bill mapping | Where the checked bill and the match live |
| `PJ_04` Engineering | Drawing register, revisions | Which file a quantity came from |
| `PJ_08` Materials | Receiving, stock, bill vs actual, waste | Later, once deliveries exist |
| `PJ_12` Commercial | Contract bill, reconciliation, measurement | Measured site quantity against the contract line |
| `PJ_13` Finance | Invoices, payments | Later, once invoices exist |
| `PJ_16` Master data | Company, project, materials, codes | Shared names so rows can match |

Fraud checks are rules on those registers, not a third app. Examples: delivered quantity above the bill line, invoice above the measured quantity, the same delivery entered twice. The Hadrut package has drawings and one bill. It has no purchase orders, deliveries, or payments, so fraud rules cannot be tested on it.

Leave programme, quality forms, safety, handover, the organisation chart, and the other workbooks until a live job is being run. The tree can stay as the later map.

## 3. The Hadrut project the test is about

| | |
|---|---|
| Language | Azerbaijani in Latin script. Older Word files and some CAD text are Cyrillic Azerbaijani. Norm titles (SNiP, GOST, AzDTN) stay in Russian. The commercial bill is bilingual English / Azerbaijani |
| Client | Ministry of Emergency Situations of Azerbaijan (FHN), Capital Construction Department |
| Designer | Azərdövlətsənayelayihə State Design Institute |
| Main order | **9335**, Baku, 2024. Chief engineer G.A. Feyzullayev |
| Later order | **9526**, Baku, 2026. External power only |
| Object | State fire station in Hadrut settlement, Xocavənd district. A 4-bay depot for 8 fire vehicles, plus yard buildings |
| Site | 0.842 ha = 8,242.50 m². Stated buildable area 1,881.70 m². Greenery 3,482.30 m² |
| Main building | 2 storeys plus basement. Plan **45.2 m × 34.6 m**. Basement area stated as 1,360.20 m². First floor stated as 1,395.80 m² |
| Structure | Monolithic reinforced-concrete frame. External walls of sawn limestone, mark M50, about 400 mm. Concrete B25. Reinforcement A240 and A500C. Seismic **8 points** on the structural note, soil class II |
| Power | 2024 note: demand 142 kW, adopted 250 kVA at **10/0.4 kV**. 2026 drawings: **1×250 kVA, 35/0.4 kV**. These disagree. See section 8 |

Buildings named on the master plan and in the bill:

| Mark | Element | Bill section |
|---|---|---|
| 1 | 4-bay fire station, basement + 2 floors | 2. About 1.84 million AZN of the line total |
| 3, 3a | Two fire-water tanks, 81 m³ each | 10 and 11 |
| 4 | Pump station | 14 |
| 5, 5a | Two drinking-water tanks, 27 m³ each | 12 and 13 |
| 6 | Drill / hose tower | 4. Drawing states footprint 65.20 m², total area 127.14 m², volume 790.80 m³ |
| 7 | Guard room | 3 |
| 8 | Transformer substation | Separate order 9526, not fully inside the 3.81 million header |
| 9 | Vehicle wash | 15 |
| 12 | Sand training pit | 24 |
| 13 | Gazebo | 26 |
| 16 | Diesel generator, about 50 kVA / 40 kW | 6 |
| 17 | Heating point and heating network. One sheet sizes the building at 6.00 × 4.00 m | 9 |
| 18 | Fence, and the note also uses 18 for a waste point | 25. Retaining wall and stone fence, about 0.46 million AZN of line value |
| — | Two-seat toilet | 16 |
| — | Roads, pavements, grading, landscaping, external lighting, site water, 0.4 kV, site fire-alarm cable, site CCTV | 5, 7, 8, 17–23, 27 |
| — | Demolition of existing buildings | 1. About 74,000 AZN. No measured drawing in the package |

The barrier (`şlaqbaum`) and the running track are named on the master plan and do not have their own bill sections.

## 4. The 84 files

Recounted from `data` on 23 October 2026. Each file is in one row. Counts add up to 84. Full wording is also in `Hadrut-file-inventory.md`.

| Kind | Files | What an extractor should do with them |
|---|---:|---|
| Contract bill | 2 | `data/BOQ-Hadrut.xlsx` and the 63-page PDF of the same sheet. This is the test. Read the Excel, not the PDF |
| Official estimate | 1 | `SMETA.pdf`, order 9526 only. 436,712 AZN for external power. Scanned. A different price system from the Excel bill. Do not merge the two templates |
| Architecture | 7 | Plans, sections, elevations, floor types, doors and windows. Depot, guard room, tower, pump station, heating point, toilet, and the 9526 substation |
| Reinforced concrete | 16 | 13 DWG, 2 tank PDFs, 1 substation PDF. Footings, frames, tanks, fence. Concrete m³ and steel tonnes are already totalled on the sheets as `material sərfi` |
| Water and sewerage | 9 | DWG. Depot, both tank pairs, pump station, heating point, tower, vehicle wash, toilet |
| Electrical | 13 | 1 DWG and 12 PDFs. 0.4 kV cables, external lighting, generator, pump station, guard room, tower, 250 kVA substation. Several `AT` sheets already list mark, name, quantity, and unit |
| Heating and ventilation | 5 | 1 DWG and 4 PDFs. Ducts and pipes, heat-loss areas, insulation thickness, energy class A–E |
| Site, roads, construction plan | 11 | 10 DWG and 1 PDF. Site layout, vertical grading, roads, landscaping, heating network, construction site plan, substation master plan. Includes `Xocavənd DQT.dwg`, whose title could not be read |
| General note and title pages | 3 | 56-page scanned note (building list, areas, road layer thicknesses) plus 2 cover sheets |
| Construction organisation | 1 | Word. Duration 16.5 months, plant, temporary fence 249.1 m. Preliminaries, not permanent quantities |
| Ecology | 1 | Word. Soil, air, water, noise, waste. Not a quantity source for the bill |
| Geology and climate | 3 | Word. Boreholes, soil layers, strength, temperature, rain, snow. Chooses the soil-group sentence. Does not give trench volume |
| Substation explanatory note | 1 | Scanned PDF, order 9526 |
| Structural calculation | 1 | `Xocavend transformator.lir`, LIRA-SAPR 2013. An analysis model. Do not take quantities from it |
| Copies and junk | 10 | 1 zip of the same folder, 2 AutoCAD `.bak`, 6 plot logs, 1 Word lock file `~$Titul.doc`. Drop these on ingest |

## 5. How the bill is actually built

`BOQ-Hadrut.xlsx` is one sheet named `BOQ`. It is a contract bill and an interim payment certificate (the sheet says PPC / `AKT`). All progress cells are zero, so this copy is the contract bill, not a filled monthly certificate.

Columns: bill code, description (`İşin adı`), unit, quantity, unit rate in AZN, line total, then progress to date, previous period, and this month.

| | |
|---|---|
| Priced work lines | 2,175 |
| Subsections | 132 |
| Distinct description texts | 1,079. The same sentence is reused across buildings |
| Header on the sheet and on the PDF | **3,811,193.36 AZN** |
| Sum of the line-total column | **about 3,110,506 AZN** |
| Gap | about 700,000 AZN. Unexplained. Do not call either figure the contract sum until the client says what the gap is |

Line value by unit:

| Unit | Lines | Value, AZN | Share |
|---|---:|---:|---:|
| m³ (`m3` and `m(3)`) | 370 | 1,085,795 | 35% |
| tonne | 241 | 536,988 | 17% |
| m² (`m2` and `m(2)`) | 357 | 771,610 | 25% |
| each (`ədəd`) | 728 | 437,445 | 14% |
| metre | 399 | 231,420 | 7% |
| set, km, kg, and a few odd units | 80 | 47,249 | 2% |

The Excel file damaged subsection codes. `2.10`, `2.20`, `2.30`, `3.10`, `4.10`, `9.10`, and `14.10` were stored as numbers, so `2.10` became `2.1` and now collides with the real section 2.1. Store codes as text.

Class A-3 reinforcement is the same sentence **94 times**. Class A-1 is the same sentence **76 times**. A match on description must survive that repetition. Match on building + description + unit, not on description alone.

The wording of the lines is the wording of Azerbaijani construction norms: excavator bucket size, soil group, haul distance, footing width, reinforcement class, wall thickness. About 70 lines name the machine, about 130 name the soil group, and about 30 name a haul of 5 km in a 17-tonne truck. The drawing shows a trench. It does not show which machine the estimator chose. A quantity can be right while the sentence is a different bill line.

There is a second price system. The 9526 `SMETA.pdf` is an official estimate in **thousand manat**, on the price base of 1 September 2022, split into construction / installation / equipment / other. The Excel bill is unit rates in manat. Do not train one layout on the other.

### The area rule that makes or breaks the match

A floor, a wall, or a roof is **one area**. The bill repeats that area once per material layer. The engine measures the parent once, reads the schedule for the build-up, and writes one line per material with the same quantity. An "extra 5 mm" or "extra 1 mm" line is not a new measurement. It inherits the parent.

Worked example, depot roof. One surface is **1,414.2 m²**, written eight times: 15 mm screed, extra 1 mm, 75 mm polystyrene, mesh, glass mesh, and the screed again. The profiled metal sheet is a second area, **1,660 m²** and **1,992 m²**, because the sheet follows the slope.

Floors, same pattern:

| Parent area | What it is | Copied onto |
|---|---|---|
| 1,344.0 m² | Basement concrete floor | 30 mm layer and an extra 5 mm |
| 665.3 m² | First-floor terrazzo | The 20 mm layer and an extra 5 mm |
| 538.4 m² | Second-floor laminate | Screed, extra 5 mm, lightweight concrete, and the laminate |
| 188.2 m² | First-floor ceramic wet rooms | Insulation, screeds, two waterproof layers, and the tile |
| 104.6 m² | First-floor porcelain tile, type 4 | Insulation, screeds, and the tile |

Roads and landscaping, the area is already stated and then repeated per course:

| Area | Where it is stated | Repeated for |
|---|---|---|
| 383.7 m² | Internal asphalt, bill section 19 | Six course lines |
| 216 m² | External asphalt, section 20 | Six course lines |
| 1,021 m² | Reinforced-concrete roads, section 21, also written in the section title | Six course lines |
| 1,437.8 m² | Pavements, section 22, also in the section title | Two lines |
| 3,482.30 m² | Greenery, also in the construction-organisation note | Grading and setting-out |

Layer thicknesses for roads, from the general note, turn those areas into volumes: pavement asphalt 40 mm on 100 mm gravel; asphalt road 50 + 70 mm asphalt, 150 mm crushed stone, 250 mm gravel; concrete road 50 + 70 mm asphalt on 150 mm concrete B15 with mesh.

There are 357 m² lines and only 166 distinct quantities. Most lines are copies of a parent. Scoring 357 independent measurements will fail a correct takeoff.

## 6. Where each quantity actually sits

Use the first source that exists. Do not average them.

| Order | Source | Returns |
|---|---|---|
| 1 | A schedule already on the sheet | The designer's count, in the bill's unit. Doors, windows, luminaires, cables, fans, reinforcement, timber, tank concrete |
| 2 | DWG model space, after conversion to DXF | True lengths and areas for walls, slabs, trenches, roads, fences, and pipes when no schedule exists |
| 3 | Vector PDF of an order 9335 plot, calibrated per viewport | A check on the DXF takeoff. The plot is on A3 paper. A line length in points is not metres until a dimension text is used as the scale |
| 4 | Vision on a scan | Order 9526 and the 56-page general note have no text layer. Read tables and isolated dimensions only |

Numbers already printed, which the takeoff must hit:

| Printed figure | Where | Means |
|---|---|---|
| 45200 × 34600 | Depot plan, `9335 MH.pdf` | 45.200 m × 34.600 m. Linear dimensions are millimetres. The bay chain is 1600 + 6000 × 7 + 1600 = 45200 |
| 2700 and 3300 | Depot sections | Basement height 2.70 m, upper storeys 3.30 m |
| 1395.80 | Depot first-floor sheet, and the general note | First-floor area, m² |
| 1360 | Depot sheet and the note | Basement area, about 1,360.20 m² |
| 9.6 m² and 0.23 m³ | Guard-room roof schedule | Metal tile area and timber volume. The bill uses 9.6 |
| 29.71 and 118.76 | Tower floor text in the bill, and tower PDF page 9 | Floor types `Tip1` and `TİP2`. The area is inside the description |
| 16 m² | Pump-station floor text | `TİP1-16m²` |
| 5000 | Fire-tank sheets | 5.00 m plan size. Wall and slab thicknesses 300, 250, 125 mm |
| 2000 × 2000 | Guard-room plan | 2.00 m grid |
| 694.4 to 694.7 | Spot levels on depot and tank sheets | Absolute metres. Do not mix with the 408.80 figure. See section 8 |

Drawing units inside a DWG must be checked against the coordinate range. If the long side spans about 45,000, the file is in millimetres. If it spans about 45, it is in metres.

### What the geometry actually is

These are **2D working drawings**, not a BIM model and not solids. Volume is always an area times a thickness or a storey height taken from another view.

- 34 DWG files. AutoCAD **2007** (the structural set, vertical grading, construction plan), **2010** (most site, water, and electrical), **2013** (depot plumbing and the HVAC drawing). The entity bodies are compressed. Convert to DXF before reading entities. ODA File Converter is the conversion path. ezdxf can then read the DXF.
- Order 9335 drawing PDFs are vector plots on A3 landscape (1191 × 842 pt). `9335 MH.pdf` still carries the original CAD layers as optional content groups. Plotting duplicated every layer once per pen. `стены_Ном. пера__21` and `стены` are the same layer. Strip the suffixes `_Ном. пера__N` and `_Pen_No__N`, then merge.
- The longest line on the depot plan page is 1190 pt, which is the sheet border. Calibrate each viewport from a dimension whose text is known (`6000` mm over the paper length of that dimension line). A plan and a detail on the same sheet have different scales. Do not mix them.
- One toilet sheet has **354,986 line segments**. Those are hatch and bar strokes. Never measure every vector. Drop hatch, furniture, axes, dimension lines, hidden layers, and the title block. Read dimension **text**. Trace reinforcement only if the `material sərfi` table is missing.
- Walls come in known thicknesses: limestone about 400 mm, concrete walls 200 mm and 500 mm. Pair parallel lines at that spacing. Wall area for the limestone basement is billed in m², not m³. Concrete wall volume is net length × height × thickness, split by thickness because the bill prices them as different lines.
- Reinforcement tonnes come from the schedule, split A240 / A-I and A500C / A-III. The bill prices the classes separately.
- `Vertikalka.dwg` is AutoCAD 2007 and contains **no Civil 3D surface**. Cut and fill has to be rebuilt from contours and spot levels. Some other site files (`Baş plan`, `DYNX`, the POS drawing) do contain Civil 3D objects (`AeccDb`: parcels, alignments, section labels). No TIN surface name was found in clear text. If conversion drops the Civil object, use the visible linework.
- The depot architecture was drawn in ArchiCAD and AutoCAD SPDS, then flattened. A zone layer (`Элемент модели - Зона`) can be a room polygon with a name and an area. Where zones were exploded, build rooms from the wall centreline.
- Pipe and cable layers already use the bill's system codes: `-S0`, `-K1`, `-K3`. Length is polyline length split by the nearest diameter text. Vertical drops are on the schematic, not the plan.
- Fan duties are already a table in the general note: S1 sanitary K 200 L 400 L/s, S2/S3 dining OV 2E 200 300 L/s, S4 drying 400 L/s, S5 showers 375 L/s, S6 sanitary 350 L/s, S7/S8 garage CT 315-4 3,000 L/s.

Layer stems worth keeping, after the pen suffix is removed:

| Stem | Use |
|---|---|
| `Xarici divarlar`, `Exterior walls`, `стены`, `дивар`, `DIVAR2` | External wall |
| `перегородка`, `Arakesmelerin xətti`, `аракəсмə` | Partition, separate from the external wall |
| `колонна`, `Kalonlar` | Column |
| `ДВЕРИ`, `Двери ArchiCAD` | Door |
| `окна` | Window |
| `Demir-beton tava`, `DOSEME` | Slab |
| `Оболочка - Крыша`, `Metal kiremit` | Roof |
| `Элемент модели - Зона` | Room polygon |
| `-S0`, `-K1`, `-K3` | Pipe system |
| `размер`, `Olculer daxili`, `Olculer xarici`, `Dimensioning` | Read the text. Ignore the dimension lines |
| `Fills`, `shtrix`, `Тонкий`, `Мебель`, `невидимка` | Drop |

### Acceptance checks for a takeoff run

| Check | Expected | Tolerance |
|---|---|---|
| Depot long side | 45.200 m | 50 mm |
| Depot short side | 34.600 m | 50 mm |
| Bay module | 6.000 m | 20 mm |
| Basement height | 2.70 m | 20 mm |
| Upper storey height | 3.30 m | 20 mm |
| First-floor area | 1,395.80 m² | polygon sum within 3%, or exact if the printed label is read |
| Guard roof | 9.6 m² and 0.23 m³ | exact, from the schedule |
| Fire-tank plan | 5.00 m | 20 mm |
| Two 81 m³ tanks | equal quantities | they must match each other |
| Two 27 m³ tanks | equal quantities | they must match each other |
| Roads and pavements | 383.7, 216, 1,021, 1,437.8 m² | 3% if remeasured, exact if the stated area is read |

Run the 45.200 × 34.600 m check first. If it fails, units or scale are wrong and nothing else should be trusted.

### Score against the Excel bill

Match on building, material, and unit.

- Quantity copied from a schedule cell: exact.
- Quantity calculated from geometry: within 1%.
- Rates, machine names, haul distance, and soil-group wording: not scored.
- A line with no drawing stays "not found". Do not invent it.
- Do not score "2,175 identical sentences". The estimator's machine and product choices are part of the text. Score the parent quantities and the layer copies.

## 7. Bill lines with no drawing to measure

Furniture and loose equipment are in the bill. No furniture schedule was found. Examples from the technology sections of the fire station:

| Line | About |
|---|---|
| Computer and monitor set | about 19,100 AZN, and a second line about 6,800 AZN |
| Hall chairs | about 17,500 AZN |
| Wardrobe 800×500×1800 | about 6,300 AZN |
| Three-seat sofa | about 5,700 AZN |
| Four-shelf rack | about 4,500 AZN |
| Sound amplifier 360 W | about 6,400 AZN |

`ədəd` is 728 lines. Most of those are fittings that do have schedules (lamps, cables, fans, valves). The furniture lines are the part with no schedule.

The depot sheet index names three sets that were not found as their own files: `TX` technology, `RI` communications, `YS` fire alarm. They may be inside a combined DWG. They are not separate PDFs the way the guard room, the tanks, and the electrical schedules are. Leave those bill lines as "not found" until a drawing is tied to them.

Demolition, bill section 1, is about 7,625.4 m³ of masonry and 2,501 t of rubble. There is no existing-building drawing.

## 8. Conflicts the engine must surface, not pick

| Topic | What the documents say |
|---|---|
| Seismic | Structural chapter, geology, and the construction note: **8 points**. Architecture chapter: **9 points**, and that chapter names **Zəngilan**, a different district. Treat the architecture passage as copied from another job until the client says otherwise |
| Datum of level 0.000 | Structural chapter: **694.70 m**. Tower sheet: **694.40**. Architecture chapter: **408.80**, in the same copied passage. Excavation depth uses 694.7 unless the client says otherwise |
| Substation | 2024 note: 142 kW demand, KTY-250 at **10/0.4 kV**, and a heading that still says KTY-160. Order 9526: **1×250 kVA, 35/0.4 kV**, with its own estimate. The 2026 set is the later document |
| Floor areas | Note page 6: basement 1,360.20 m², first floor 1,395.80 m². A later brief page: total area 3,672.10 m², construction area 1,612.70 m², volume 18,570.40 m³, and it uses the acronym DYMX. Treat the later page as a brief until it is checked against the floor plans |
| Contract sum | Header 3,811,193.36 AZN. Line sum about 3,110,506 AZN |
| Bill codes | `2.10` stored as `2.1` |

## 9. How the screens should be organised

One shell, two entries. Do not show 16 folders in the sidebar.

Top bar: search, project name, language switch (AZ / EN / both), theme switch. One solid primary button per screen.

Left bar, two groups:

| Group | Items |
|---|---|
| Bill check | New check, Checks, Discrepancy report |
| Operations | Home, Drawings, Bill, Materials, Measurements, Invoices, Codes |

Home is a strip of counts (open differences, drawings not read, lines with no drawing) and the latest rows. Each count opens the list it came from. One chart under the strip. No greeting, no photo banner, no card around every number.

Bill check is the four steps in section 2, shown as a line of steps across the top. Click a takeoff row and the source sheet opens beside it.

Every operations screen is the same register: title, one New button, search and a few filters, counts that are also filters, then a table of hairline rows. Status is a small dot plus a word, not a filled pill on every row.

Visual rules already agreed, under the name Quiet Utility. Reference screenshots are in `app/docs/design-references/` (Plausible for the KPI strip, Odoo Purchase for a real ERP register, Odoo Dashboards for the chart-and-ranked-list, OpenProject for a parent/child quantity table).

- KPIs are one strip inside one card. No icon-in-a-box tiles.
- One card level. Lists are rows, not stacks of cards.
- Radius 6 px on controls, 8 px on cards. No shadows. 1 px borders.
- Table text 13 px. Rows 36–40 px. Numbers use tabular figures.
- Near-monochrome. One solid accent for the primary button, links, and focus. Status colours always come with text.
- Sidebar is a neutral surface, not a saturated brand colour.
- The Azerbaijani letters `Ə ə İ ı Ğ ğ Ş ş Ç ç Ö ö Ü ü` must render in the UI and in PDF. Set `lang="az"` or CSS uppercase will turn `i` into `I` instead of `İ`. Embed a font in the PDF. Noto Sans is the known fallback.
- AZ + EN doubles titles. Truncate with a tooltip. Long tab names in the tree are the stress test.
- Empty lists say what belongs there and offer New. A missing value is a dash, never `NaN`.

## 10. Decisions already made

- The application is a web platform, not a set of Excel workbooks. Excel and PDF are exports.
- Language switch and light/dark theme are both required. They sit in the header.
- Module 1 is the first build. The Hadrut package is the test set.
- Rates are stored and not scored.
- Parent area is measured once and copied onto every layer in that build-up.
- Identical pairs (two 81 m³ tanks, two 27 m³ tanks) are measured once and copied, then named separately.
- Junk files are dropped on ingest.
- The LIRA file, the ecology volume, and the construction-organisation narrative are not quantity sources.
- The official 9526 smeta is a different document type from the Excel bill.

## 11. Decisions still open

These change the plan. Do not invent answers.

1. Confirm the first delivery is a quantity check (description, unit, quantity, material, source), with rates not scored.
2. Confirm a printed schedule area is used exactly and copied onto every layer.
3. Which document wins when they disagree: seismic 8 or 9, datum 694.70 m or 408.80 m, substation 10/0.4 kV or 35/0.4 kV.
4. What the 700,000 AZN gap between the header and the line sum is.
5. Who on the client side will check a sample of areas against the drawings.

## 12. Files a planner should read

| File | Use it for |
|---|---|
| `CONTEXT-FOR-PLAN.md` | This brief |
| `Hadrut-file-inventory.md` | The 84-file count by kind |
| `Hadrut-client-data-analysis.md` | File-by-file reading of the package, bill sections, and the first geometry notes. Written before the area-rule and the two-module split were settled. Where it disagrees with this brief, this brief wins |
| `Hadrut-geometry-extraction.md` | How to convert DWG, which layers to keep, and the acceptance checks |
| `app/docs/design-references/README.md` | The five screenshots and what to copy from each |
| `data/BOQ-Hadrut.xlsx` | The test bill. Do not parse the PDF for quantities |
| `data/Hadrut DEPO/` | The drawings. Skip `.bak`, `.log`, `~$`, and the zip |

Do not start from the old plan `bilingual_pm_platform_skeleton.plan.md` as if it were the scope. That plan was an all-16-modules skeleton. The scope in section 2 of this file replaces it.
