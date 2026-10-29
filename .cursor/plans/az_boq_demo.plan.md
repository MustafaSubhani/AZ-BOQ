---
name: AZ-BOQ demo, drawing-to-bill check
overview: Build a web demo that reads the Hadrut drawing package (DWG, PDF, scans, Azerbaijani text), measures quantities with a source for every number, compares them with BOQ-Hadrut.xlsx, and exports the client's bill in its exact visual format plus a discrepancy report. FastAPI + React/Vite + SQLite. ODA converts DWG offline, LibreDWG cross-checks it. OpenAI translates in the display layer only. No value may appear without a source, and no missing value may be replaced silently.
todos:
  - id: m0-setup
    content: "M0: repo scaffold (backend FastAPI, frontend React/Vite/TS, SQLite), install ODA File Converter, Tesseract (aze, aze_cyrl, rus) and LibreOffice (fallback); pywin32 for Excel automation; UTF-8 everywhere, run manifest, no-silent-default test in CI from day one"
    status: completed
  - id: w1-spikes
    content: "Week-1 spikes (section 19.4): ODA on all 34 DWGs, legacy font tables from embedded PDF fonts, depot 45.2 x 34.6 m gate from (SON).dwg, filled bill through openpyxl + Excel fingerprint and print"
    status: completed
  - id: m1-ingest
    content: "M1: file register for the 84 files: sha256, kind, discipline, building, order, DWG version; drop junk, group duplicates by hash; Drawings screen"
    status: completed
  - id: m2-bill
    content: "M2: bill parser from cached values (all cells are external-link formulas), section code repair, units, comments, totals reproduced to the cent; Bill screen"
    status: completed
  - id: m3-text
    content: "M3: text pipeline (MTEXT runs with fonts, legacy Azerbaijani font decoding, homoglyph folding, normalisation keys) and display-layer translation with OpenAI, glossary, guards and a persisted cache; AZ / EN / both toggle"
    status: completed
  - id: m4-dwg
    content: "M4: ODA conversion offline to a DXF cache, LibreDWG second-reader cross-check, sheet regions and scale in model space, layer normaliser, drawing viewer (raster tiles + evidence overlay)"
    status: completed
  - id: m5-schedules
    content: "M5: schedule readers (DXF line-grid tables, PDF tables with font-aware decoding, OpenAI vision on scans as review-only); guard roof 9.6 m2 and 0.23 m3 exact"
    status: completed
  - id: m6-geometry
    content: "M6: geometry takeoff; 45.200 x 34.600 m gate first; depot parent areas and layer copies; tanks; roads; every height and thickness from a cited source or BLOCKED"
    status: completed
  - id: m4b-source-map
    content: "M4b: sheet-level classification (fuzzy sheet numbers), source map per building x trade, number index over all decoded text and notes, Coverage screen"
    status: completed
  - id: m7-match-report
    content: "M7: evidence finder (printed numbers + simple derivations), derived-line analysis, matcher (building + material + unit), statuses with reasons, reviewer-adjusted quantities, discrepancy report, Inputs ledger, Conflicts with suggestions"
    status: completed
  - id: m8-exports
    content: "M8: filled client bill in the original template with a cell-style fingerprint test and a print test (63 A3 pages), report export Excel and PDF"
    status: completed
  - id: m9-generated-bill
    content: "M9: generated bill (our own lines) laid out with the client's template styles, row heights computed for wrapped text"
    status: completed
  - id: m10-polish
    content: "M10: Home counts, search with Azerbaijani folding, dark mode, performance on the 166k-entity DWG, HARDCODED.md generated from demo_rules, demo script"
    status: in_progress
  - id: m11-operations
    content: "M11 (later): thin module-2 registers seeded from real data (drawing register, contract bill, codes); fraud rules only once deliveries or invoices exist"
    status: completed
isProject: false
---

# AZ-BOQ demo: drawing-to-bill check on the Hadrut package

## 0. How to use this plan

Read in this order: this file, then `CONTEXT-FOR-PLAN.md` (the data brief), then `Hadrut-geometry-extraction.md`. Where this file corrects the brief (section 2 below), this file wins. Everything marked **Verified 29 Oct 2026** was checked against the real files, not taken from earlier notes.

`D:\Constech` is a previous, similar project. You may read its code for patterns. Do not copy any data, outputs, rates, rules or measurements from it into this project. Section 3 lists the Constech mistakes this plan exists to prevent.

The single most important rule is in section 3. If you only remember one thing: **no number without a source, and no missing value replaced silently.**

## 1. Decisions taken

| Topic | Decision |
|---|---|
| Stack | Python 3.12+ FastAPI backend, React + Vite + TypeScript frontend, SQLite. Geometry in Python (ezdxf, shapely, PyMuPDF, openpyxl). Python 3.14 is installed on the dev machine and the core packages import on it; pin versions and fall back to a 3.12 venv if a wheel is missing |
| Scope | Module 1 first (drawing-to-bill check). Module 2 is a later thin slice (M11) |
| BOQ generation | Both. First a **filled client bill**: the client's 2,175 lines and descriptions unchanged, our measured quantity written where we have one, with evidence. Then, as a stretch, a **generated bill** of our own lines in the client's visual format |
| DWG conversion | ODA File Converter installed locally, all 34 DWGs converted **once, offline**, DXF cache shipped with the demo. LibreDWG runs as an independent second reader to catch silent drops. Reason: the free ODA converter is licensed for non-commercial use only, and a hosted platform needs a paid ODA tier (Sustaining, about 7,500 USD in year one). The demo never calls ODA at request time |
| LLM | OpenAI, model names in environment variables. Used for display translation and for reading tables on scanned pages. Never used as the source of a quantity that is scored automatically |
| Rates | Stored, exported, never scored |
| Excel export | openpyxl writes values into the original template, then Microsoft Excel (installed on the dev machine) recalculates, saves and prints the PDF through automation. LibreOffice is the fallback |
| Evidence | Every bill line is checked two ways where possible: a printed number in the drawings (evidence finder, 5.3) and our own measurement (takeoff) |
| Hardcoding | Allowed for the demo, only in `backend/demo_rules/*.yaml` with a citation, and reported to the developer in `HARDCODED.md`. Not labelled "hardcoded" in the UI (section 16) |

## 2. Corrections to the brief (Verified 29 Oct 2026)

1. **The 700,000 AZN gap is explained by the workbook's own formulas.** It is not unexplained.
   - Line sum `SUM(F11:F2330)` = 3,110,505.89
   - Row 2331, temporary buildings 1.8% (`Müvəqqəti bina və qurğular`): `=SUM(F11:F2330)*1.8%` = 55,989.11
   - Row 2332, contingency 2% (`Nəzərdə tutulmayan xərclər`): `=SUM(F11:F2331)*2%` = 63,329.90
   - Row 2333, subtotal `Cəmi`: `=SUM(F11:F2332)-0.02` = 3,229,824.88. The `-0.02` is a manual rounding fudge in the formula. Reproduce it in the client copy.
   - Row 2334, VAT `ƏDV 18%`: `=F2333*18%` = 581,368.48
   - Row 2335, total `Yekun`: `=F2333+F2334` = **3,811,193.36**. Cell `C5` (contract price) is `=F2335`.

   Open decision 4 in the brief can be closed, pending a one-line confirmation from the lead.
2. **Almost every cell in the bill is a formula into another workbook that is not in the package.** Columns A–E of the line rows are formulas like `=[6]Лист1!B11`. Columns J and L come from `='[6]Forma 2'!J19`. External link `[6]` points to `/Users/Z BOOK/Desktop/Hadrut CMOS-PROJECT/Hadrut Smeta(AutoRecovered).xlsx000.xlsx`. Five other external links point to unrelated templates. The **cached values are the only data**. Read with `data_only=True`, never recalculate the original, and never save it.
3. **Progress cells are not all zero.** `L2329` = 4.08, `L2330` = 1, `L2331` = 55,989.11, `L2332` = 63,329.90. `H2335` shows 140,802.40 AZN of progress including VAT. Parse these values and show them, but do not score them.
4. **The bill has 10 reviewer comments** by Ilaha N. Amiraslanova. They are on `B1185`, `B1188`, `B1216`, `B1217`, `B1228`, `B1266`, `B1596`, `B1797`, `B2001` and `B2202`, and most cite "addendum 15" reductions. Example: `addendum 15 beton 115 azn 552-460 = 92 m3 460 burda eksik verlib`. These lines' bill quantities are known to be under revision. Attach each comment to its line as evidence and show it in the report.
5. **Basement area conflict.** The depot plan PDF room schedule (page index 4 of `9335 MH.pdf`) prints `Cəmi 1360.80`. The brief quotes 1,360.20 from the general note. Add this to the Conflicts screen. Do not pick one.
6. **Legacy Azerbaijani fonts** encode Latin Azerbaijani letters at Cyrillic code points, and **Cyrillic look-alike letters** appear inside codes (section 8). Neither is mentioned in the brief, and both break matching and translation.
7. **Bill structure facts**: 132 section headers and 2,175 lines, all with quantity > 0. Raw unit counts are `ədəd` 728, `m` 399, `m(3)` 313, `m2` 100, `m(2)` 257, `ton` 241, `m3` 57, `dəst` 56, `km` 10, `kg` 8, `pagon metr` 3, `p/m` 2 and `FF` 1. `FF` is the last line of section 27 (row 2330) and should be flagged as an unknown unit. Header codes are floats (2.10 stored as 2.1, as the brief says).
8. **Architecture DWGs exist.** The brief and the file inventory treat them as copies or supervision files.
   - `YRS - VM - Xocavənd\YRS - VN -9335 hadrut xocevend (SON).dwg` is the **depot architecture**: floor plans, section 1-1, elevations A-G / G-A / 1-10, roof plan, room schedule `Yerləşkələrin eksplikasiyası`. It also holds the **depot fire alarm, CCTV, telephone and public-address plans** and the **tower** plans and fire-alarm schedule (sheet `9335-6-YS`).
   - `YRS - VM - XOCAVEND-NƏZARƏT.dwg` is the **guard-room architecture**, plus other small buildings. It contains the pump-station floor schedule on sheet `9336-04-MT`; note the typo, 9336 instead of 9335.
   - It has floor, finish, door/window and lintel schedules and stated areas such as `S= 63.40`, `1.45 m²` and `2.91 m²`.
9. **The "not found" depot systems are mostly found.**
   - Fire alarm, CCTV and communications (bill 2.24–2.29) are in `(SON).dwg`.
   - Internal power and lighting (bill 2.22–2.23) are in `9335 hadrut xocevend elektrik.dwg`: plans per floor, equipment schedules, and the 142 kW load note.
   - The tower fire-alarm schedule gives smoke detectors 12, manual call points 5 and cable 110 m (bill 4.12).
10. **Cut and fill is a printed table, not a surface to rebuild.** `Vertikalka.dwg` has `TORPAQ KÜTLƏSİNİN BALANSI` (earth-mass balance): fill 12,996 m³, cut 3,167 m³, road and pavement corrections (`1021.0 x 0.62`, `599.7 x 0.52`, `1437.8 x 0.14`), topsoil 522 m³, totals 13,518 / 4,835, shortfall 8,683 m³. Every quantity in bill section 18 comes from this table:
    - 12,996 is the fill
    - 8,683 is the shortfall
    - 522 is the topsoil
    - 4,313 = 4,835 − 522
    - 15,195.25 t = 8,683 × 1.75
    - 626.4 t = 522 × 1.2
11. **The demolition volume is stated.** A note in `Depo  Hadrut BP\9335 Xocavənd  rayon   DYNX.dwg` reads `Ərazidəki mövcud tikililər sökülməlidir. Söküntünün həcmi V=7625.40m³`, and the legend has a `Sökülən binalar` (buildings to be demolished) entry. Bill line 1.1.1 (7,625.4 m³) is a `STATED` match, not "impossible".
12. **Site DWGs declare the wrong units.** `Baş plan`, both `DYNX` files, `Vertikalka` and `POS` have `INSUNITS = 2` (feet). A note in the same files says `Bütün ölçülər metrlə verilib` ("all dimensions are in metres"), and the coordinates (x ≈ 686,669, y ≈ 4,375,220) are UTM-style metres.
13. **35% of the bill's line value is printed somewhere in the package.** On 29 Oct 2026, 794 of 2,175 bill quantities (non-trivial values only) appeared as a printed number in a DWG or PDF. Some of these are coincidences (round numbers like 110), but most strong hits are real: `1660`, `1344.0`, `665.3` and `230.5` m² in `9335 MH.pdf`, and `7625.4` in `DYNX`. Section 5.3 turns this into the evidence finder.
14. **The legacy font table can be derived exactly** from the fonts embedded in the PDFs (section 8.2). It does not have to be guessed.

## 3. The non-negotiable rule: no silent values

### 3.1 What went wrong in Constech

In `D:\Constech\backend\structural_boq\structure.py` (around line 1697):

```python
tank_height = (levels.get(above_ground) or 0.0) - (levels.get(ground_floor) or 0.0)
if tank_height < 0:
    tank_height = pit_height
```

The level was missing, so `or 0.0` invented zero, the result went negative, and the code quietly substituted the pit height. The tank height printed on the drawing was never used. The review screen showed a normal-looking quantity because the substitution left no record. Constech did have an inputs register, but this code bypassed it. A second Constech habit to avoid: `dwg_dump/dump.mjs` `cleanText()` deletes MTEXT font switches (`\f...;`). For this project those switches are what identify legacy-encoded text (section 8).

### 3.2 The data model that makes this impossible

Every number the engine uses or produces is a `Value`, never a bare float.

```python
class Method(str, Enum):
    SCHEDULE = "schedule"        # read from a table the designer printed
    STATED = "stated"            # a number written in text ("1395.80", "TİP1-16m²", "383,7 m²")
    GEOMETRY = "geometry"        # measured from DXF entities
    DERIVED = "derived"          # formula over other Values
    VISION = "vision"            # read from a scan by a vision model; always REVIEW
    RULE = "rule"                # demo_rules/*.yaml entry, must carry a citation
    MANUAL = "manual"            # entered by a person in the UI, with a reason

class Status(str, Enum):
    VERIFIED = "verified"        # two independent sources agree within tolerance
    EXTRACTED = "extracted"      # one source, no contradiction
    REVIEW = "review"            # vision, reader disagreement, low decode confidence, conflict
    BLOCKED = "blocked"          # a required input is missing; there is NO number

@dataclass(frozen=True)
class Source:
    file_id: str                 # sha256 of the file
    file_name: str
    locator: dict                # {"kind":"dxf_entity","handle":"2F1A","layer":"...","region":"R3"}
                                 # {"kind":"pdf_span","page":4,"bbox":[...]}
                                 # {"kind":"xlsx_cell","sheet":"BOQ","cell":"D16"}
                                 # {"kind":"rule","rule_id":"R-012"}
    raw_text: str | None         # exactly as read, before decoding
    decoded_text: str | None

@dataclass(frozen=True)
class Value:
    value: float | None          # None only when status is BLOCKED
    unit: str
    method: Method
    status: Status
    sources: tuple[Source, ...]  # at least one, unless BLOCKED
    formula: str | None = None   # for DERIVED, e.g. "length_m * height_m * thickness_m"
    inputs: dict[str, "Value"] = field(default_factory=dict)
    searched: tuple[str, ...] = ()   # where the resolver looked, kept even on success
    rejected: tuple[dict, ...] = ()  # other candidates found and why they lost
    conflicts: tuple[dict, ...] = () # candidates that disagree beyond tolerance
```

Rules:

1. One function per attribute resolves inputs: `resolve_tank_height(tank) -> Value`. It tries sources in a declared order (schedule, stated text on the section, geometry, rule). It records every place it looked in `searched`. It returns `BLOCKED` with `value=None` if nothing is found.
2. A `DERIVED` value whose input is `BLOCKED` is itself `BLOCKED`, and lists the missing input names. Arithmetic on `None` must raise, never coerce.
3. When the drawings lack a value the demo needs, the value comes from a `RULE` with a citation (a file plus a page, region or handle, or a brief section). A rule without a citation fails validation at startup.
4. Two sources that disagree beyond tolerance produce a `conflicts` entry and status `REVIEW`. The engine never averages them and never picks silently. The declared source order only decides which value is shown first.
5. The takeoff stage has **no access to the bill**. It cannot import the bill module or read `BOQ-Hadrut.xlsx`. The matcher joins the two afterwards. This stops anyone, human or agent, from "measuring" a quantity by copying it from the answer key. Enforce this with an import-boundary test.

### 3.3 Enforcement that runs in CI

- `tests/test_no_silent_defaults.py`: an AST scan of `backend/engine/**` that fails on:
  - `x or <number>`
  - `dict.get(k, <number>)`
  - `getattr(o, n, <number>)`
  - a numeric assignment inside `except`
  - `max(x, 0)` or `min(...)` used to clamp a quantity

  An explicit allow-comment `# allow-default: <reason>` is reviewed in code review and listed in the run manifest.
- `tests/test_run_invariants.py`: after a full run, every exported quantity has at least one source. No `BLOCKED` value carries a number. Every bill line has exactly one report status and a non-empty reason.
- The run summary counts values by method and status, and the Home screen shows "inputs missing" and "values from project rules" as numbers that open their lists.

### 3.4 What the reviewer sees

Clicking any quantity opens an **input tree**. It shows the formula, then each input with its method, value and source. Each source is a link that opens the drawing at that entity, or the PDF at that span, or the cell. The tree also shows "looked in" and "rejected candidates". For a Hadrut tank, a missing wall height would read like this:

> Tank wall height: **not found**, quantity blocked. Looked in: `9335 Xocevend yangin su anbari dk.dwg` section regions (dimension text on `razmer` layers), `Xocavend Yangin su anbari.pdf` sections page 2, `material sərfi` table.

The dedicated **Inputs ledger** screen lists every input in the run. Filters: not from a drawing, conflicts, missing.

## 4. Architecture and repository layout

```text
d:\AZ-BOQ\
  data\                         client files, read-only, never written
  cache\                        not in git: dxf\, libredwg\, tiles\, translations.sqlite (shipped as a zip with the demo)
  backend\
    azboq\
      api\                      FastAPI routers
      ingest\                   file register, hashing, classification
      dwg\                      oda.py, libredwg_check (calls node tool), regions.py, layers.py, entities.py, render.py
      text\                     mtext.py, legacy_fonts.py, homoglyphs.py, normalise.py, translate.py, glossary.az-en.yaml
      bill\                     parse.py, codes.py, units.py, sections.py
      schedules\                dxf_tables.py, pdf_tables.py, vision.py
      engine\                   values.py (section 3), resolvers\, takeoff\ (per building), checks.py (acceptance)
      match\                    matcher.py, report.py
      export\                   client_bill.py, generated_bill.py, report_xlsx.py, report_pdf.py, fidelity.py
      runs\                     run manifest, structured logs, stage invariants
    demo_rules\                 YAML rules with citations (section 16)
    tools\libredwg\             Node script, one process per DWG
    tests\
  frontend\                     React + Vite + TypeScript
  HARDCODED.md                  generated from demo_rules, for the developer only
```

Processing is offline and staged. `python -m azboq run --project hadrut` executes ingest, convert, read, decode, schedules, takeoff, match and report. Each stage writes its output and a stage log into SQLite, keyed by input hashes and engine version, so a stage reruns only when its inputs change. The API serves results and never converts or measures at request time. That keeps the demo fast and deterministic.

## 5. Ingest and file register

- Hash every file with sha256. Group exact duplicates and keep one canonical file per group, listing the copies. Duplicate groups in this package: the KTM PDF stored twice, DYNX twice, POS twice, and the title DOC twice.
- Drop junk on ingest and show a count of hidden files: the zip, `.bak` files, `plot.log` and `hardcopy.log`, and `~$Titul.doc`.
- Classify from the title block or stamp first, the folder name second. Record order (9335 / 9526), building mark, discipline mark (BP, MH, DK, SK, İV, E/EE/EİA, POS) and document class. The DWG version comes from the first 6 bytes (`AC1021` = R2007, `AC1024` = R2010, `AC1027` = R2013).
- Filenames contain `ə`, `İ`, `³`, double spaces and trailing dots (`anbarı..dwg`). Store the original name for display. Use `<sha8>.<ext>` for every temporary or tool path. Normalise displayed names to NFC.
- Acceptance: the register reproduces the 84-file inventory by kind without a person renaming anything.

### 5.1 Classify sheets, not files

One file can hold several buildings and disciplines. `(SON).dwg` contains the depot architecture, the depot low-current systems and tower sheets. `NƏZARƏT.dwg` contains the guard room and the pump station. A file-level label hides most of what a file contains.

- After region detection (6.4), classify **each sheet region** from its title block: order, building, discipline, sheet number, title.
- Parse sheet numbers fuzzily. Real examples are `9335-01-MH`, `9335- 6 - YS`, `9335-8-EİA`, and the typo `9336-04-MT`. Record the raw text and the parsed fields, and flag a mismatch such as an order of 9336 inside a 9335 package.
- The building is identified by its stamp name (`Qüllə`, `Nəzarətçi otağı`, `Su nasos stansiyası`). The stamp may be in a legacy font, for example `Гцллянин сявиййяляр цзря планлары` = `Qüllənin səviyyələr üzrə planları`, so decode it first.

### 5.2 Source map: where each fact lives

The information is scattered. For the depot, plan size and room areas come from the architecture DWG and PDF, concrete and steel from the DK DWG, pipes from the SK DWG, ducts from the İV DWG, power and lighting from the electrical DWG, low-current systems from `(SON).dwg`, insulation from a PDF, and soil group from a Word file. Build this map explicitly, right after ingest:

- One row per **building × trade**. Columns: sheet regions found (with file), schedules found, stated values found, and status. Status is one of: schedule available, geometry only, scan only, nothing.
- The resolvers in section 3.2 read this map to know where to look, so the "looked in" list on every value comes from it.
- Show it as the **Coverage** screen: buildings down, trades across. Each cell is coloured with a word label and opens the sources. The demo audience then sees at a glance what is checkable and why.
- The map is generated from the sheet classification. Corrections go into `demo_rules/source_map.yaml` with citations.

### 5.3 Number index and evidence finder

The estimator built the bill from printed tables plus simple arithmetic (section 2, items 10, 11 and 13). The fastest honest way to trace a bill quantity is to find where it is printed.

- **Index every number** in every decoded text: DXF text, PDF spans, OCR of scans, the general note. Each entry stores the value, its unit if one is adjacent (`m²`, `m³`, `m`, `ədəd`, `kq`, `t`), and 5–10 words of context. It also stores the file, sheet region, handle or bbox, and the building from the sheet classification.
- **For each bill line**, search the index for its quantity within that building's sheets (from the source map), in this order:
  1. Exact value with a compatible unit or context.
  2. A simple derivation shown on the sheet itself, such as `1021.0 x 0.62 = 633.0`.
  3. Sum or difference of two or three indexed values from the same table (4,313 = 4,835 − 522).
  4. Value × factor, where the factor is recorded as a rule (soil densities 1.75 and 1.2, cited to the bill line pairs).
- **Strength**:
  - Strong: four or more significant digits or a decimal value, the same building, and a matching unit or context word.
  - Weak: round or small numbers (110, 130, 12) or no unit context. These are shown as "candidate", never as a match.
  - **Never** search all files for small integers. That produces false hits everywhere.
- **What it produces**: a `found_in_drawing` link from the bill line to the printed number. Status is `STATED`, or `SCHEDULE` if the number sits in a table. This is a legitimate verification of the bill against the drawings. It does not replace measurement. It is not the takeoff stage, so the import boundary in 3.2 still holds: the takeoff never reads the bill, and the evidence finder lives in the matching stage.
- **It also builds the bill map** (12) automatically. A strong hit proposes "bill line 18.1.5 ← `Vertikalka.dwg`, earth balance table, row 'Sahənin planlaşdırılması', column `Tökmə`". You confirm it once in `bill_map.yaml`, which makes the curated mapping much smaller.

### 5.4 Derived bill lines

Many bill lines are arithmetic on other lines in the same section, not separate measurements:

- tonnes = m³ × density (section 18: 1.75 and 1.2)
- "each next 10 m" or "extra 5 m" lines repeat the parent quantity
- material-layer copies repeat the parent area (11.3)

Detect them per section: pairs with the same quantity, or with a constant ratio, next to each other, where the description says "əlavə" (extra) or "hər növbəti" (each next). Label them `derived from line X`. Check them through their parent, not on their own, and show the relation in the report. This makes far fewer lines need an independent source, and explains numbers the drawings never print.

## 6. DWG pipeline

### 6.1 Conversion with ODA (offline, once)

- Install ODA File Converter on the dev machine. It is not installed today. On Windows the GUI is suppressed when it runs from the command line. You can drive it through `ezdxf.addons.odafc` by setting `win_exec_path` in the ezdxf config, or call it directly:
  `ODAFileConverter.exe "<in_dir>" "<out_dir>" ACAD2018 DXF 0 1 "<sha8>.dwg"`
  The arguments are input folder, output folder, version, format, recurse, audit and filter. The tool works on folders, so give each file its own temporary input and output folders with ASCII names.
- **The exit code is advisory.** ODA returns 0 even when a file failed. Verify that the DXF exists, is not empty, and opens with `ezdxf.readfile`. If that fails, try `ezdxf.recover.readfile` and store the auditor errors. Set a 600 s timeout per file.
- Output is ACAD2018 DXF, which keeps text as Unicode. Store the ODA version, timestamp and both hashes in a conversion manifest.
- The 26.9 MB `YRS - VN -9335 hadrut xocevend (SON).dwg` holds 166,117 top-level entities, so expect a large DXF. Keep `cache/dxf/` out of git and ship it as a zip with the demo.

### 6.2 Second reader: LibreDWG cross-check

LibreDWG (`@mlightcad/libredwg-web`, Node) was run on all 34 DWGs on 29 Oct 2026:

| Result | File |
|---|---|
| Read, with content | 31 files (warning code 68 is normal and non-fatal) |
| Crash: "memory access out of bounds" | `9335-13 -SK-2 yerlik ayaqyolu.dwg` (21.4 MB, R2010) |
| **Reported success, returned 0 entities** | `9335 Xocavend istilik menteqesi.dwg` (21.6 MB, R2007) |
| Crash only when read as the second file in the same process | `9335-3,3a-SK-81m³ Yanğın su anbarı..dwg` (reads fine alone) |
| 0 proxy objects reported | including `Baş plan`, `DYNX` and `POS`, which contain Civil 3D objects. LibreDWG probably drops them silently |

What to build:

- Run one Node process per DWG with a 120 s timeout. Record per-layer and per-type counts of top-level entities in model space and in each layout.
- Count the same thing with ezdxf on the ODA DXF. Count top-level entities, not expanded blocks, so like is compared with like.
- If total entities differ by more than 2%, or any layer with 10 or more entities differs by more than 5%, mark the file **reader disagreement**. Every quantity from that file is `REVIEW`, and the drawing register shows the per-layer table.
- A file where either reader returns 0 entities is never "read". It is "failed", in red, with a reason.

### 6.3 Units and scale

- Read `$INSUNITS` (the guard-room DK file says 4, millimetres), then **confirm** it with a known dimension. The depot must measure 45,200 × 34,600 drawing units. If that fails, nothing from the file is trusted.
- `INSUNITS` is wrong on the site files: they say feet (2), while their own note says metres and the coordinates are UTM metres. Decide units from evidence in this order:
  1. A unit note on the sheet (`Bütün ölçülər metrlə verilib`, `ölçülər mm-lə`).
  2. A known stated area or length that the geometry must reproduce: roads 1,021 m², pavements 1,437.8 m², `S=1620.70m²` under roads in `Vertikalka`, the depot 45.2 m.
  3. Coordinate magnitude (UTM metres around 686,000 / 4,375,000).
  4. `INSUNITS`, only as a tiebreaker.

  Record the chosen unit as a `Value` with its evidence.
- For each `DIMENSION`, compare `get_measurement()` with the displayed text (`<>` means "show the measured value"). An override like `6000` over a 5,980 line is common. Record both, and use the ratio to detect detail scale (next section).

### 6.4 Sheets live side by side in model space

The guard-room DK file's model-space extents span about **42 m × 215 m in millimetres** for a 2 × 2 m building. All sheets, plus enlarged details, are laid out in model space. This is normal Russian/Azerbaijani (SPDS) practice. Without region detection, wall lengths from a 1:20 detail get added to the 1:100 plan.

- Detect sheet frames. Look for closed rectangles whose size is a paper format (A4 210×297, A3 297×420, A2 420×594, A1 594×841, in either orientation) times a standard scale (1, 10, 20, 25, 50, 100, 200). Also look for frame or stamp block inserts (names like `A3`, `Формат`, `ramka`, `ştamp`).
- Each region gets a frame box, a nominal scale, the sheet number read from the title-block text (`9335-01-MH`), and a sheet title.
- Inside a region, a detail may be drawn enlarged. Cluster dimension ratios (`measurement / text value`) to find sub-areas with a different local scale. Exclude those sub-areas from plan measurement unless a takeoff explicitly targets a detail.
- If paper-space layouts with viewports exist, use the viewport scale and clip boundary, and record which method produced the region.
- If automatic detection fails for a file, a `RULE` in `demo_rules/regions.yaml` may define the frames by coordinates, citing the file and the visible sheet number.

### 6.5 Entity handling

| Entity | Handling |
|---|---|
| `INSERT` | Expand through `virtual_entities()`, including nested, mirrored (negative scale) and `MINSERT` arrays. Use the effective name for dynamic blocks (`*U...`). Do not count block definitions that are never inserted |
| `ATTRIB` | Title-block attributes carry the sheet number and name. Read them |
| `LWPOLYLINE`, `POLYLINE` | Bulges are arcs. Use ezdxf path flattening for length and area, never straight vertex-to-vertex |
| `HATCH` | Boundary paths give areas (floors, finishes). Pattern strokes are not geometry |
| `MTEXT`, `TEXT`, `MLEADER`, `LEADER` | Through the text pipeline in section 8. Marks such as `Mtv-1`, `Mk-1` and `Atm-1` come from leaders |
| `DIMENSION` | Measurement plus text, section 6.3 |
| `ACAD_PROXY_ENTITY` | Count it and log it by handle. Render its proxy graphic greyed out. Never measure it |
| XREF block definitions | List referenced files that are not in the package as "missing reference" |
| Frozen or off layers | Keep but mark. Never measure them by default. `9335-1-SK ... depo 2-ci variant.dwg` ("second variant") may hold old variants on hidden layers |

Before summing lengths, remove duplicate overlapping segments. CAD files often contain identical lines on top of each other.

### 6.6 Layer normaliser

- Strip the plot suffixes `_Ном. пера__N` and `_Pen_No__N`. Strip trailing lineweight tags as seen in real names: `cedvel  0.09`, `razmer   0.09`, `ИЧ  РАЗМЕР  0.09`. Then apply NFC and homoglyph folding (section 8.3).
- Map the stem to a role (wall, partition, column, slab, door, window, roof, zone, pipe system, dimension, table grid, text, hatch, furniture, hidden, axis). The brief's dictionary is the starting point. Layers seen in the guard-room DK file include `Х - диварлар.`, `STENA`, `divarlar`, `ara divarlar`, `аракясмя` (a legacy-encoded `arakəsmə`), `kalonlar`, `РАЗМЕРЫ`, `razmer 0.09`, `Olchu`, `Ölçülər`, `cedvel 0.09`, `arm1`, `ARMATUR`, `Ox xetti` and `yazilar`.
- Unknown layers go to an "unclassified layers" list with entity counts on the drawing page. They are never silently dropped.
- Exploded hatches dominate some files. In `(SON).dwg`, 120,726 of 166,117 entities (73%) are on `M-2 keramitin shtrixi_...`, the strokes of a ceramic-tile hatch. In `elektrik.dwg`, 31,537 entities are on `memar` (the architectural background under the electrical plans). Classify these layers as hatch or background. Exclude them from measurement and draw them faint in the viewer; otherwise both measurement and rendering slow to a crawl.
- An architectural background inside an MEP file (`memar` in electrical, room names in SK and İV) is a **second copy of the architecture**. Use it as a cross-check of room names and outlines, never as an additional measurement.

## 7. Visual layer: why converted DXF "looks ruined", and what to show instead

### 7.1 Causes, specific to this package

1. **Missing fonts.** Text styles reference `A3TI(LA).TTF` and `A2TI(LA).TTF`, which are legacy Azerbaijani Latin fonts, plus `ARIALN.TTF`, `romans.shx`, `isocp.shx` and `txt.shx`. None of these are in the package. Substitutes change text width and spacing, and legacy-encoded text renders as Cyrillic.
2. **Proxy objects.** Civil 3D objects in `Baş plan`, `DYNX` and `POS` show up as boxes or vanish.
3. **No plot style.** The CTB file is not in the package, so the drawing shows screen colours instead of black lines with pen weights.
4. **Model space shows everything.** All sheets, construction lines, frozen variants and enlarged details appear together.
5. **Hatch patterns and linetype scale** (`LTSCALE`, `PSLTSCALE`) render heavy or as solid lines.
6. **Huge coordinates** (x around 1,600,000 mm) cause floating-point jitter in browser renderers.

### 7.2 Decision: measurement and looks are separate

- **Measurement always uses the DXF.** None of the visual problems above affect coordinates.
- **The look**, in order of preference:
  1. **The designer's own vector PDF plot**, where one exists (folder `9335`, `Elektrik`). This is the true appearance. Fit a DWG-to-PDF transform from text that appears in both (sheet numbers, axis letters, room names, marks) and store the RMS residual. If the residual is too large, show the two side by side instead of overlaying.
  2. **ezdxf render of a single region** for DWGs without a plot (DK, SK, site). Hide frozen and off layers. Use monochrome output with lineweights from the layer (a CTB built in code). Decode legacy text to Unicode before rendering. Map fonts to installed TTFs (Times New Roman, Arial Narrow are on the dev machine). Use ezdxf's SHX support if SHX files are provided. Draw hatches light.
  3. Proxy graphics greyed out, with a "proxy" marker.
- Rendering format: pre-render at ingest a **tile pyramid** of PNGs per region (three zoom levels). Draw evidence entities as an SVG overlay on top, in region-local coordinates. A single SVG of the 166k-entity file will freeze the browser.
- Ask the client for their font folder and CTB file (section 20). With the real fonts, ezdxf renders match far better. Until then the font mapping lives in `demo_rules/fonts.yaml`.
- **Decode before render fixes most of the "ruined" look without the client's fonts.** The legacy fonts are Arial and Times clones with Azerbaijani glyphs placed at Cyrillic slots (section 8.2). Once the text is decoded to real Unicode (`Ə`, `ü`, `ş`), render it with the installed Arial, Arial Narrow and Times New Roman, and the sheet looks right: same letter shapes, correct letters. What stays imperfect is spacing, by a few percent.
- **Optional high-fidelity path, offline**: Autodesk DWG TrueView is free and plots with Autodesk's own engine. It ships the standard SHX fonts, and the free Civil 3D Object Enabler makes proxies visible. It can batch-plot model-space frames or layouts to PDF once, during demo preparation. Then every DWG has a designer-like PDF for the viewer, aligned to the DXF through shared text anchors as in option 1. It needs manual setup per file. Use it only for the sheets shown in the demo, and record which PDFs were made this way.
- Acceptance: the guard-room DK region renders legibly, with Azerbaijani letters correct and the `Spesifikasiya` table readable. You (the developer) compare it by eye with the matching PDF page and record the result in the run notes.

## 8. Text: decode first, translate second

Pipeline per text: **raw, then runs, then decoded, then normalised (for matching), then translated (for display only)**. Store raw and decoded forever. Never overwrite raw.

### 8.1 MTEXT runs

Real strings from the guard-room DK file show fonts switching inside words and inside numbers:

```text
{\fArial Narrow|b0|i0|c238|p34;Kütl\fTimes New Roman|b0|i0|c238|p18;ə}          -> "Kütlə"
{\C0;8\fArial Narrow|b0|i0|c238|p34;3\fArial Narrow|b0|i0|c204|p34;.\fArial Narrow|b0|i0|c238|p34;10}   -> "83.10"
6{\fArial Narrow|b0|i0|c238|p34;%%C14 A500C}                                        -> "6Ø14 A500C"
```

- Tokenise MTEXT with ezdxf's MTEXT parser, or a tokenizer that **keeps** each run's font name and charset (`c238` Central European, `c204` Cyrillic, `c186` Baltic, `c0` ANSI). Decode each run by its font, then join the runs into one logical string. Never split a number at a run boundary.
- Handle `\P` (paragraph), `\~`, `\S` (stacked fractions), `\U+XXXX`, `%%c` = Ø, `%%d` = °, `%%p` = ±, `\L`, `\A`, `\pt...;`, `\H...x;`, `\C...;`.
- In PDFs, read spans with `page.get_text("dict")`, which gives the font name per span. Decode per span.

### 8.2 Legacy Azerbaijani fonts (critical, easy to miss)

Old Azerbaijani CAD and Word fonts (`A3TI(LA)`, `A3TimesAzLatNormal`, `A3ArialAzLatNormal`, `ArialAzeriLat`, `ArialAzLat`, `ArialCyrMT`) place Azerbaijani letters at Cyrillic code points. Text extraction "succeeds" and returns Cyrillic that is neither Russian nor readable. A translator will produce nonsense, and a matcher will never match. Real examples from this package:

| Extracted | Means | Where |
|---|---|---|
| `ЙЕРЛЯШЭЯЛЯРИН ЕКСПЛИКАСИЙАСЫ` | `YERLƏŞMƏLƏRİN EKSPLİKASİYASI` (room schedule) | `9335 MH.pdf` page index 4 |
| `Tяmizlik lяvazimatlarının` | `Təmizlik ləvazimatlarının` | `9335 MH.pdf` page index 5 |
| `Юлчц ващиди`, `ГЕЙД`, `МИГДАРЫ` | `Ölçü vahidi`, `QEYD`, `MİQDARI` | `Elektrik/Generator/1.pdf` |
| `ЭЮСТЯРИЪИЛЯРИ` | `GÖSTƏRİCİLƏRİ` | same |
| `Имза вя тарих`, `Яслин инв.№` | `İmza və tarix`, `Əslin inv.№` | guard-room PDF title block |
| `NYY типли elastik кабел ен кясийи` | `NYY tipli elastik kabel en kəsiyi` | `Elektrik/qülle/AT.pdf` |

**What these fonts really are (Verified 29 Oct 2026).** They are Latin Arial or Times fonts whose glyphs sit at Cyrillic code points: the code point says `я`, the font draws `ə`. This was proven by extracting the embedded subset fonts from `Elektrik/Generator/1.pdf` (`A3ArialAzLatNormal`, `A3TimesAzLatNormal`) with PyMuPDF and rendering each Cyrillic-slot glyph. The observed table:

| Slot | Draws | Slot | Draws | Slot | Draws |
|---|---|---|---|---|---|
| А а | A a | Л л | L l | Ц ц | Ü ü |
| Б б | B b | М м | M m | Ч ч | Ç ç |
| В в | V v | Н н | N n | Ш ш | Ş ş |
| Г г | Q q | О о | O o | Щ щ | H h |
| Д д | D d | П п | P p | Ъ ъ | C c |
| Е е | E e | Р р | R r | Ы ы | I ı |
| З з | Z z | С с | S s | Э э | G g |
| И и | İ i | Т т | T t | Ю ю | Ö ö |
| Й й | Y y | У у | U u | Я я | Ə ə |
| К к | K k | Ф ф | F f | Х х | X x |

`ж` (seen in `эцжц` = `gücü`) was not in these subsets. The text suggests it draws `c`. Confirm it from another embedded font before relying on it. Letters for `Ğ`, `J` and `Ş` capitals may sit at other slots (`Ь`, `Ж`, `Ш`). Complete the table the same way.

**How to build the table automatically, per font family:**

1. For every embedded PDF font whose name matches the legacy pattern, extract it (`doc.extract_font(xref)`).
2. Render each glyph at a Cyrillic slot to a small image.
3. Render candidate Latin and Azerbaijani letters with the matching standard font (Arial for `*Arial*`, Times New Roman for `*Times*`). Pick the best pixel match (IoU) for each slot.
4. Write `text/legacy_fonts/<family>.json` with slot → letter and a match score. Generate one contact sheet image per font, like the one used to verify this table, so you can check it by eye in a minute.
5. DWG text styles do not embed fonts. Map the style's font file to the same family by name (`A3TI(LA).TTF` → `A3TimesAzLatNormal`, `A2TI(LA).TTF` → the A2 Times family) and use that family's table.

Two patterns appear in the data:

- **Whole run in a legacy font**, for example `ЙЕРЛЯШЭЯЛЯРИН` → `YERLƏŞMƏLƏRİN`. Apply the font table to the run.
- **Mixed inside one string**, where the font changed mid-sentence. Examples: `Tяmizlik`, and `Лайищя комплексиндя Yanğın siqnalizasiya шябякяси нязярдя тутулуб` = `Layihə kompleksində Yanğın siqnalizasiya şəbəkəsi nəzərdə tutulub`. In DXF, MTEXT font switches tell you exactly which run is which. In PDFs, the span font name does. Where the font information is lost (plain `TEXT` with a legacy style, or a flattened string), decode **per word**: convert a word only if it is entirely Cyrillic and the decoded word scores better as Azerbaijani than the raw word scores as Russian.

**Codes inside legacy runs need extra care.** `Тцстц хябярверичи | МЭ-2100 | яд | 12` decodes to `Tüstü xəbərverici | MG-2100 | əd | 12`. `МЭ-2100` is a product code, and `MG-2100` may or may not be what the designer meant. For tokens that look like codes, keep both raw and decoded, mark them `code_uncertain`, and never use them as a match key unless they also appear in a non-legacy font somewhere.

How to implement:

- Trigger decoding per run, by font name (regex on `AzLat|AzeriLat|\(LA\)|A3Ti|A2Ti|A3Times|A3Arial|AzCyr|ArialCyr`, plus the text style's font file) and by content.
- **Genuine Russian must stay Russian**: `ГОСТ 34028-2016`, norm titles, layer names like `РАЗМЕРЫ`, and Russian block names (`Унитаз`, `Умывальник`, `Ворота гаражные подъемные`). Score raw-as-Russian against decoded-as-Azerbaijani with word lists. For Azerbaijani, the best domain word list is free and already here: the vocabulary of the 1,079 distinct bill sentences plus every Unicode Azerbaijani string in the drawings. For Russian, use hunspell `ru_RU`. Add letter-bigram statistics. Keep the higher score. If both are low, keep the raw text with status `undecoded`.
- Store `decode_scheme` and `decode_confidence`. The UI shows decoded text with a small marker, and hovering shows the raw text.
- Unicode and legacy text coexist **inside one MTEXT**. The guard-room DK file writes `ə` as real Unicode in Times New Roman runs next to legacy-styled runs.
- Tests use the real strings above as fixtures.

### 8.3 Cyrillic look-alikes in codes (homoglyphs)

The guard-room DK file writes rebar class `А500C` and `А240C` with a **Cyrillic А**, the mark `Мtv-1` with a Cyrillic М, and `аd:` with a Cyrillic а. To the eye they are identical to Latin. As strings they will never match `A500C` in a schedule or the bill. For **code-like tokens only** (letters mixed with digits, or known mark patterns), fold Cyrillic А В Е К М Н О Р С Т Х а е о р с х to Latin. Do not fold genuine Cyrillic words.

Equivalence table for rebar classes (a rule with citation): A240 = A-I = A-1, and A500C ≈ A-III = A-3, as the bill writes them. The bill prices A-I and A-III separately.

### 8.4 Normalisation keys (matching and search only)

- Use NFC. Lowercase with Azerbaijani rules: `İ`→`i` and `I`→`ı`. Python's `.lower()` and `.upper()` are wrong for Azerbaijani (`"i".upper()` gives `I`, not `İ`). Write `az_lower` and `az_upper` helpers and use them everywhere.
- Fold `ä`→`ə`. The 1991–92 Azerbaijani Latin alphabet used `ä`.
- The fuzzy search key additionally folds ə→e, ı→i, ö→o, ü→u, ş→s, ç→c, ğ→g. Display text keeps every diacritic.
- Units map to canonical forms:
  - `m(3)`, `m3`, `m³`, `м3` → m³
  - `m(2)`, `m2`, `m²` → m²
  - `p/m`, `pagon metr`, `p.m`, `pm.` → m
  - `ədəd`, `əd`, `əd.`, `ed` → each
  - `dəst`, `komplekt`, `компл` → set
  - `ton`, `t` → t
  - `kq`, `kg` → kg
  - `FF` → unknown, flagged
- Decimal comma: `0,5`, `383,7` and `+0,300` appear in descriptions and drawings, while bill cells use a dot. Parse both, and do not confuse a thousands separator with a decimal.
- Reviewer comments are typed without Azerbaijani letters (`haz;rl;q` for `hazırlıq`). Do not auto-correct stored text. Translation must tolerate it.
- In the frontend, set `lang="az"` on Azerbaijani content and use `toLocaleUpperCase('az')` and `Intl.Collator('az')`. CSS `text-transform: uppercase` without `lang="az"` produces `I` instead of `İ`.

### 8.5 Translation in the display layer (OpenAI)

Your instinct is right: never translate the stored data or the files. Translate only what the screen shows, and cache it.

- **What gets translated**: distinct decoded strings, namely bill descriptions (1,079 distinct), 132 section titles, drawing texts, layer names, file titles and reviewer comments. Never translate pure numbers, codes or units.
- **When**: pre-warm at ingest as a background job, never on page load. The cache is a SQLite table `translation(source_hash, source_text, lang, text, origin[llm|human], model, prompt_version, glossary_version, checks, created_at)`. Ship it with the demo so the demo works offline. The UI shows the Azerbaijani text until an English one exists, and never blocks waiting for it.
- **Glossary** (`text/glossary.az-en.yaml`), versioned and enforced:
  - Seed it from the bill's own bilingual headers: İşin adı = Description, Ölçü vahidi = Unit, Həcmi = Quantity, Sifarişçi = Employer, Podratçı = Contractor, Cəmi = Subtotal, Yekun = Total, ƏDV = VAT.
  - Add terms from the drawings: bünövrə = foundation, hörgü = masonry, arakəsmə = partition, döşəmə = floor, dam örtüyü = roof covering, tava = slab, sütun / kalon = column, D/b = reinforced concrete, material sərfi = material consumption, spesifikasiya = specification, eksplikasiya = room schedule, təsnifat = schedule, su anbarı = water tank, nəzarətçi otağı = guard room, qüllə = drill tower, söhbətgah = gazebo, şaquli planlaşdırma = vertical grading, səki = pavement, qırma daş = crushed stone, çınqıl = gravel.
- **Request**: batches of about 50 strings, JSON-schema structured output `{id, en}`, temperature 0. The system prompt says: technical translator for Azerbaijani construction bills; keep numbers, units, codes, standard names (SNiP, GOST, AzDTN) and marks verbatim; use the glossary. Model name comes from `OPENAI_TRANSLATION_MODEL`.
- **Guards after every answer**:
  1. The multiset of numbers and code tokens in the source must equal the one in the translation. Otherwise retry once, then mark `needs check` and display the Azerbaijani text.
  2. Every glossary term present in the source must appear in its approved English form.
  3. A length-ratio sanity check.
- **UI**: AZ / EN / both toggle in the header. In "both", the English sits under the Azerbaijani in muted text. Every English string shows the Azerbaijani source and "machine translation" on hover. A small Translations screen lets you correct a string; corrections are stored as `human` and win over the model.
- **Drawings**: never repaint drawing text in English, because the layout breaks. Show the English as a tooltip over each text entity (invisible hit-boxes in the overlay) and in a side list "Text on this sheet (AZ | EN)".
- **Exports keep Azerbaijani exactly.** The discrepancy report may add an English column.
- Log tokens and cost per batch in the run log.

## 9. Reading the bill

- Load twice: `data_only=True` for the cached values, and the default mode for the formulas (to know which cells are formulas). Never save either workbook object.
- Row layout: rows 1–5 are the header block (C5 = contract price formula), rows 7–9 the column headers (print titles), and rows 10–2330 the sections and lines. Rows 2331–2335 are the overheads and totals (section 2). Row 2337 holds the signatures. Columns AX–AZ near the end are helper columns: ignore them, but preserve them in the export.
- A header row has a float in A, a title in B, and no unit or quantity. A line row has a unit in C and a quantity in D. Expected counts are 132 headers and 2,175 lines.
- **Code repair**: give the k-th header within building N the code `N.k` as text. Check that `float("N.k") == A` (2.10 → 2.1 passes), and flag any mismatch. Line id = `{section}.{item}`, for example `2.10.3`. Store codes as text everywhere.
- Section to building: map the title prefix to a building with a rule table (`demo_rules/sections.yaml`, citing the header row). Examples: `4 çıxışlı Yanğın Deposu binası` → depot; `Nəzarətçi otağı` → guard room; `Qüllə` → tower; `V=81 m3-luq ... 1-ci su anbarı` → tank 3; `... 2-ci` → tank 3a. Sections 5–8 and 17–27 are site-wide.
- Trade comes from the parentheses in the title, matched fuzzily because the bill has typos: `konsturksiyalar`, `kostruksiyalar`, `işqılanması`, `itehsalat`, `yerliq`.
- Acceptance: line sum 3,110,505.89, and the chain in section 2 reproduces 3,811,193.36 to the cent.

## 10. Schedules and stated values

The designer has already done much of the takeoff. Read the tables before measuring anything.

- **DXF tables** are a line grid on a table layer (`cedvel 0.09`) with one MTEXT per cell, not `TABLE` entities.
  - Collect horizontal and vertical lines inside the region, cluster their coordinates, build cells, and assign text by its centre point.
  - Find the header row with decoded keywords: `Mövqe`, `İşarə`, `Adı`, `Miq.`/`Miqdarı`, `Kütlə`, `Qeyd`, `Spesifikasiya`, `Material sərfi`, `Ölçü vahidi`, `Sayı`, `Markası`, `Elementin markası`, `Armaturun sinfi`, `Cəmi`, `Yekun`.
  - Real cells in the guard-room DK file include `Monolit örtük tavası Mtv-1`, `5.76 m²`, `1.92 m³`, `0.86 m³`, `Beton B20`, and bar lines like `Ø16 А500C L=1350`.
- **PDF tables** (AT equipment schedules, door and window schedules, room schedules): decode spans by font (section 8.2). Use `page.find_tables()` first, then position clustering as a fallback.
- **Stated numbers inside text** are `STATED` values: `383,7 m²` in the section 19 title, `TİP1-16m²`, `1395.80` printed on the plan, and the tower's `65.20 / 127.14 / 790.80`.
- **Scans** (order 9526 set, the 56-page general note): an OpenAI vision model returns a JSON table with cell boxes. The status is always `REVIEW`, the page crop is kept as evidence, and nothing is auto-matched until a person accepts it. If vision is unreliable for the road course thicknesses in the general note, enter them as a `RULE` citing the page.
- **Two readers for scans, same principle as DWG.** Run a local OCR as well: Tesseract with `aze`, `aze_cyrl` and `rus` language data; it is not installed today. Compare it number by number with the vision output.
  - Agreement on a number raises the status to `EXTRACTED`, still shown as "read from a scan".
  - Disagreement stays `REVIEW`, with both readings shown.
  - Also check scanned numbers against the same fact elsewhere. Road areas 1,021 and 1,437.8 m² appear in `Vertikalka.dwg`, the bill titles and the general note. A scanned value that matches a vector-text value is far more trustworthy.
- **Notes are data.** Plain-text notes carry quantities: `Söküntünün həcmi V=7625.40m³`, `S=1620.70m² (yol altı)`, `3482.3 x 0.15 = 522.0m³`, `S= 63.40`. Pattern-extract `V=`, `S=`, `L=`, `H=`, `h=`, `x … =` expressions with their units into the number index as `STATED` values, with the whole sentence as context.

## 11. Geometry takeoff

The formulas and acceptance checks are in the brief (sections 5–6) and `Hadrut-geometry-extraction.md`. This plan adds these implementation rules:

1. **Gate first.** Depot 45.200 × 34.600 m within 50 mm, bay 6.000 m within 20 mm. If the gate fails, geometry from that file stops and the drawing register shows why.
2. **Heights and thicknesses** (2.70 m and 3.30 m storeys, 400, 200 and 500 mm walls, slab thickness, tank wall height) each come from a resolver with a cited source: section dimension text, a note, or a schedule. If none is found the value is `BLOCKED`. A `RULE` is the last resort and must cite the sheet.
3. **Parent area once, copied to layers.** A parent takeoff item (for example the depot roof, 1,414.2 m²) owns the measurement. Child bill lines for each material layer reference the parent and are not independent hits. The parent-to-lines table is `demo_rules/buildups.yaml`, and the brief's tables are the seed.
4. **Identical pairs** (tanks 3/3a, 5/5a): measure once, copy, name separately. Check that the two bill sections agree with each other.
5. **Never measure all vectors.** Use role layers only, inside the sheet's region, at its scale, after removing duplicates.
6. **Rounding.** Store the full precision, and report at the bill's own decimals for that line.

Demo depth, in order:

- **Tier 1, automatic end to end**:
  - depot structure, floors and roof parent areas
  - guard-room roof schedule
  - tanks from `material sərfi`
  - road and pavement stated areas (sections 19–22)
  - **section 18 grading from the earth-balance table, including the derived tonne lines**
  - **section 1 demolition volume from the `DYNX` note**
  - electrical AT counts for the tower, guard room and pump station
  - **tower fire-alarm schedule**
- **Tier 2**:
  - fence and retaining-wall lengths by lettered stretch (section 25)
  - the tower
  - **depot power, lighting and low-current counts** from schedules in `elektrik.dwg` and `(SON).dwg`
  - **the evidence finder over all sections**, as candidates you confirm
- **Everything else** is "not found" or `BLOCKED` with a reason. That is an honest result, not a failure.

## 12. Matching and the discrepancy report

- Match key: building + material/element + canonical unit. Never match on the description alone. The A-III rebar sentence repeats 94 times and A-I 76 times.
- Mapping from bill lines to takeoff items: automatic suggestions from the evidence finder (5.3), the derived-line analysis (5.4), the section building, the unit, and description keywords after normalisation. Confirmed in `demo_rules/bill_map.yaml` for the demo sections.
- Every bill line can carry two independent confirmations: a **printed number** (evidence finder) and a **measurement** (takeoff). The strongest result is both agreeing. Show which of the two exist on every row. When a printed number exists, measurement disagrees, and the bill equals the printed number, the report says so. It means the bill copied the designer's table, and our measurement questions the table, not the bill.
- **Reviewer comments carry numbers.** For example `552-460 = 92 m3` and `152 m2 az verilmelidir` ("152 m² should be less"). Parse the arithmetic into a "reviewer-adjusted quantity", shown next to the bill quantity as a third column for those 10 lines. Never replace the bill quantity with it.
- Statuses:

  | Status | Meaning |
  |---|---|
  | `matched` | Within tolerance |
  | `different` | Both quantities shown, plus the gap and the percentage |
  | `not found` | No drawing source |
  | `blocked` | A source exists but an input is missing; the row says which |
  | `review` | Vision, reader disagreement or a conflict |
  | `measured, no bill line` | Diagnostic list |

  The client-facing report keeps the brief's three lists. The other statuses are visible in the app.
- Tolerance by method, recorded on every row: schedule copy exact (at the bill's decimals), stated value exact, geometry 1% for scoring (3% for the acceptance checks, as in the brief).
- Score summaries are counted both by line and by share of bill value. Parents and leaves are scored, layer copies are not.
- Reviewer comments from the bill (section 2, item 4) appear on their rows.

## 13. Exports, matching the client's format exactly

### 13.1 What the template is

The template is `BOQ-Hadrut.xlsx`, one sheet `BOQ`:

- Columns A:L. Widths: A 13.0, B 60.8, C 25.6, D 15.6, E 13.4, F 17.6, G 15.9, H 18.0, I 14.6, J 17.6, K 14.6, L 16.1.
- Times New Roman: 12 pt for headers and numbers, 11 pt for descriptions, 14 pt bold for section codes.
- Number format `#,##0.00`, thin borders, 16 merged ranges (rows 7–9 header), 141 cell styles.
- Print setup: area `A1:L2339`, print titles rows 7:9, A3 landscape (paperSize 8), fit to page, left and right margins 0.
- Freeze pane at `A217`. It is odd, but preserve it.
- Two conditional formats, two data validations (one already contains `#REF!`; preserve it), 10 comments.
- The client PDF is 63 A3 landscape pages, using Times New Roman and Tahoma.

### 13.2 Filled client bill (mode A)

- Start from the original file. In rows 10–2330, replace the external formulas in A–E with **literal cached values**. Write our quantity into D where we have a measured or matched value. Keep F `=+E*D`, the overhead rows and the totals formulas exactly, including `-0.02`.
- Remove the six external links (`wb._external_links = []`) only after no formula references `[n]`. Check every defined name (`alcipandi`, `dogrami` and others) for `[n]` references, and remove any that would break. Otherwise Excel shows an "update links" or repair prompt, which looks broken in a demo.
- Set `fullCalcOnLoad`. openpyxl writes formulas **without cached values**, so the in-app preview must use our own computed values, never read back from the file.
- **Microsoft Excel 16 is installed on the dev machine** (`Excel.Application.16`). This is the export path for the demo: openpyxl writes the values, then Excel automation (`pywin32`) opens the file and does the rest. Set `DisplayAlerts = False` and `AskToUpdateLinks = False`, run `CalculateFull()`, and save, which writes real cached values. Then `ExportAsFixedFormat` produces the PDF. This is the same software that produced `BOQ-Hadrut.pdf`, so the print matches it. Run Excel automation in a single worker, with a timeout and a kill of `EXCEL.EXE` on hang. Microsoft does not support server-side automation, which is fine for a local demo but not for production. LibreOffice remains the fallback and the Linux path.
- Lines we did not measure keep the client's quantity. Every changed or unmeasured line gets an Excel comment with the evidence id. Add an extra sheet `Evidence` (line id, status, our quantity, bill quantity, method, source); the `BOQ` sheet's look is unchanged. An optional export toggle, off by default, fills changed cells with colour.
- Section codes: by default keep the original cell values so the sheet prints like the client's. The corrected codes (`2.10`) appear in the report and the Evidence sheet. Ask the lead whether the client copy should print `2.10` instead (section 20).

### 13.3 Generated bill (mode B, stretch)

- Same template. Copy row styles (`cell._style`) from a template row of the same kind: section header, line, overhead, total.
- Each line's description is the client's nearest existing sentence for that building, element and unit (the bill is the phrase and rate library). If no such sentence exists, use a phrase template. The rate is copied from the matched client line.
- Rebuild the SUM ranges for the new row count. Do not carry over the `-0.02`.
- **Row heights**: openpyxl does not auto-fit wrapped text. Estimate each height from text length, column B width (60.8 characters) and the font size. Otherwise long Azerbaijani descriptions are clipped in print.

### 13.4 Fidelity tests (run in CI on the filled bill)

1. **Style fingerprint**: for every cell in A1:L2339, compare font, fill, border, alignment, number format and protection, plus row heights, column widths, merges, print setup, conditional formats and validations, against the original. Zero differences except the intended value changes.
2. **Print test**: export the PDF through Excel automation (13.2). Expect 63 pages, A3 landscape. Pixel-compare pages 1 and 30 with `BOQ-Hadrut.pdf` at 100 dpi; only changed numbers may differ.
   - Fallback without Excel: LibreOffice headless (not installed today). Use a fresh `-env:UserInstallation` profile seeded with `OOXMLRecalcMode=0`; without it, headless LibreOffice silently skips recalculation. LibreOffice text metrics differ slightly from Excel, so page breaks can shift, and a page count of 63 ± 1 is accepted on this path.
   - On Linux, Times New Roman and Tahoma are missing and the layout shifts. Run exports on Windows for the demo.
3. **Values**: re-read the output with our own calculator and confirm the totals chain.

### 13.5 Discrepancy report

Our own Quiet Utility style, not the client's format. Excel and PDF. Contents: counts strip, then the three lists. Each row shows the bill line id, description (Azerbaijani, optional English), unit, bill quantity, our quantity, gap, percentage, method, source sheet and reason. The PDF embeds Noto Sans and must render `Ə ə İ ı Ğ ğ Ş ş Ç ç Ö ö Ü ü`.

## 14. Screens

Use the brief's section 9 layout and Quiet Utility rules. Additions needed for traceability:

| Screen | Purpose |
|---|---|
| Home | Counts strip: open differences, drawings not read, lines with no drawing, **inputs missing**, **reader disagreements**, **values from project rules**. Every count opens its list |
| New check (stepper) | Drawings, Takeoff, Bill, Report |
| Drawings | Register: kind, discipline, building, order, DWG version, reader agreement, regions found, share of text decoded, units gate result. Junk hidden behind a count |
| Drawing viewer | Region list, tiles plus evidence overlay, layer panel with roles and unclassified layers, "Text on this sheet (AZ \| EN)", entity inspector (handle, layer, raw text, decoded text, decode scheme) |
| Takeoff | One row per measured item: building, element, material, unit, quantity, method, status, sheet. Clicking a row opens the input tree (section 3.4) beside the drawing at the entity |
| Bill | Sections and lines as a parent/child table, AZ / EN, comments, repaired codes |
| Report | Three lists plus diagnostics, as in section 12 |
| Inputs ledger | Every input in the run, filterable by method and status |
| Conflicts | Seismic 8 or 9, datum 694.70 / 694.40 / 408.80, substation 10/0.4 or 35/0.4 kV, basement 1,360.20 or 1,360.80, contract sum explanation. Sources side by side, each with a **suggested** side and the reason, never applied without a person choosing. Suggestion heuristics: a later order or date wins (9526 of 2026 over the 2024 note); a drawing sheet wins over narrative text; a passage that names another place (`Zəngilan`) is marked "probably copied from another project"; a value confirmed by a third independent source wins |
| Coverage | The source map (5.2): buildings × trades, what was found where, and what is checkable |
| Run log | Stages, durations, counts, warnings. A warning that only exists in a log is a silent fallback, so every warning also becomes a review item |
| Translations | View and correct cached translations |

## 15. Observability and tests

- **Run manifest** (JSON, stored per run): git sha, engine version, file hashes, ODA and LibreDWG versions, hashes of the rule files, glossary version, translation model, timings.
- **Structured logs** (JSON lines) per stage, with counts in and out.
- **Stage invariants that stop a file or the run**: DXF missing or with 0 entities, reader disagreement (stops automatic status, not the run), units gate failed, a rule without a citation, a `Value` without a source.
- **Tests**:
  - Bill parser: counts, totals chain, code repair, units.
  - Decoding: the real strings from section 8.2 and the homoglyph cases from 8.3.
  - No silent defaults (3.3).
  - Run invariants (3.3).
  - Import boundary: takeoff cannot import the bill.
  - Acceptance checks from the brief.
  - Export fidelity (13.4).
  - Translation guards.
  - **Determinism**: two runs on the same inputs give byte-identical results. Sort everything and never iterate an unordered set into output.

## 16. Hardcoding policy

- Anything too hard for the demo may be hardcoded, but **only** as an entry in `backend/demo_rules/*.yaml`, never as a literal in engine code. Each entry has: `id`, `value`, `unit`, `applies_to`, `citation` (file + page/region/handle, or brief section), `why_hardcoded`, `how_to_automate`.
- `python -m azboq hardcoded-report` generates `HARDCODED.md` from these files for you, the developer. It is never shown in the platform UI.
- In the UI, a rule-backed value shows method "Project rule" and its citation. It is never labelled "hardcoded", and it is never shown as "measured" either. The reviewer can always tell a curated value from a value read off a drawing, which is the observability lesson from Constech.
- Expected demo rules: section-to-building map, trade map, bill-line-to-takeoff map, layer roles per file, region frames where detection fails, font mapping, parent-area build-ups, road course thicknesses from the scanned note, rebar class equivalences, and storey heights only if text extraction fails.
- **Never allowed**: taking any quantity from `BOQ-Hadrut.xlsx` as our measurement. The import-boundary test enforces this.

## 17. Milestones and done criteria

| Milestone | Done when |
|---|---|
| M0 setup | `python -m azboq run` works on an empty project. CI runs the no-silent-default test. ODA and LibreOffice are installed. `PYTHONIOENCODING=utf-8` is set and every file is opened with `encoding="utf-8"` (the Windows console crashed on `İ` during research) |
| Week-1 spikes (before M1) | Four de-risking checks, each with a fallback, listed in section 19.4. Do these before building on them |
| M1 ingest | The register shows 84 files by kind, junk hidden, duplicate groups listed. After M4, sheet-level classification and the source map (5.1, 5.2) are added, and the Coverage screen shows them |
| M2 bill | 132 headers, 2,175 lines, totals chain to the cent, codes repaired, comments attached. The Bill screen renders AZ |
| M3 text | Decoding fixtures pass. The bill and section titles are translated, cached, and guard-checked. The toggle works |
| M4 dwg | 34 DXFs in the cache, the cross-check table stored, the three problem files visibly flagged, regions detected on the guard-room DK and depot DK, the viewer shows tiles plus overlay |
| M5 schedules | Guard roof 9.6 m² and 0.23 m³ exact. Tank `material sərfi` read for both pairs. AT counts for the tower read with sources |
| M6 geometry | Depot gate passes. Depot parent areas within tolerance or explained. Roads exact from stated areas |
| M7 match | Every bill line has one status and a reason. The evidence finder runs, and every section 18 line traces to the earth-balance table. The Inputs ledger and Conflicts screens are populated |
| M8 exports | Fingerprint test zero diffs, 63 pages, the report renders all Azerbaijani letters |
| M9 generated bill | Wrapped text not clipped. Totals rebuilt |
| M10 polish | `HARDCODED.md` generated. A 10-minute demo script runs on the shipped caches without network |

## 18. Traps a smaller agent will miss

1. Reading `BOQ-Hadrut.xlsx` without `data_only=True` gives formula strings like `=[6]Лист1!B11`, not data.
2. Saving the bill with openpyxl strips cached values of external formulas. Never save the original. In exports, replace those formulas with literals first.
3. The "unexplained" 700,000 AZN is overheads plus VAT (section 2). Do not report it as a discrepancy.
4. Header codes are floats: 2.10 equals 2.1. Rebuild them by position.
5. Units are written several ways (`m(3)` and `m3`, `pagon metr` and `p/m`). `FF` is unknown.
6. Matching on description alone fails: the A-III sentence appears 94 times. Use building + material + unit.
7. Layer copies of one parent area are not independent measurements.
8. ODA exits with 0 on failure. LibreDWG can return 0 entities and report success. Verify outputs, and cross-check the two readers.
9. LibreDWG crashes when reading a second file in the same process. Use one process per file.
10. Filenames with `ə`, `³`, double spaces and trailing dots break CLI tools. Stage them under hashed ASCII names.
11. `INSUNITS` can lie. Gate on 45.2 × 34.6 m.
12. Model space contains every sheet and enlarged details side by side. Measure within regions at the region's scale.
13. Dimension text can be overridden. Compare it with the measured value.
14. Bulged polylines are arcs. Flatten them properly.
15. Duplicate overlapping lines inflate lengths.
16. Frozen layers may hold old variants. Do not measure them by default.
17. Proxy (Civil 3D) objects have no measurable geometry.
18. MTEXT switches fonts inside numbers. Tokenise and join, never regex-strip blindly, and never discard font switches (the Constech `cleanText` mistake).
19. Legacy Azerbaijani fonts make Latin text look like Cyrillic. Decode by font, keep genuine Russian as Russian, keep raw text.
20. Cyrillic `А`, `М` and `а` inside codes (`А500C`, `Мtv-1`) look Latin. Fold homoglyphs in code tokens.
21. Python's `.upper()` and `.lower()` are wrong for Azerbaijani `İ`/`ı`, and so is CSS uppercase without `lang="az"`.
22. Decimal commas in descriptions and drawings, dots in cells.
23. The LLM translates only. It must preserve numbers and codes (guard-checked) and never supply a quantity.
24. Translation must be pre-warmed and cached, or the demo becomes slow, costly and dependent on the network.
25. openpyxl does not auto-size wrapped rows. Compute row heights in the generated bill.
26. Headless LibreOffice silently skips recalculation unless `OOXMLRecalcMode=0` is set in a fresh profile.
27. Rendering one SVG of a 166k-entity drawing freezes the browser. Use pre-rendered tiles plus an evidence overlay in region-local coordinates.
28. The Windows console is cp1252. Set UTF-8, or prints crash on `İ`.
29. Any `x or 0`, `.get(k, 0)` or clamp in engine code is a potential tank-height bug. CI forbids it.
30. A warning written only to a log is invisible. Every warning must become a review item in the UI.
31. Scanned pages (9526, general note) give `VISION` values, always `REVIEW`, never auto-matched.
32. The two price systems (9526 smeta in thousand manat, bill in manat) must never be merged.
33. File names lie about content. `(SON).dwg` is the depot architecture and low-current systems; `NƏZARƏT.dwg` is the guard room plus the pump station. Classify by sheet title block, not by file name.
34. One file holds several buildings, so a building label per file is wrong. Classify per sheet region.
35. Sheet numbers have typos (`9336-04-MT` in a 9335 package). Parse fuzzily and flag.
36. Site DWGs say feet while the note says metres. Units come from evidence, not the header.
37. Many bill quantities are printed in a table or note (earth balance, demolition `V=7625.40m³`). Read tables and notes before measuring.
38. Tonne lines are m³ × density, and "each next 10 m" lines copy their parent. Do not look for them on a drawing; check them through their parent.
39. Searching every file for small round numbers finds false matches everywhere. Evidence-finder hits need building, unit and context.
40. A product code inside a legacy font (`МЭ-2100`) may decode wrongly. Never use it as a match key on its own.
41. 73% of the entities in `(SON).dwg` are exploded hatch strokes. Filter them by layer, or rendering and measurement crawl.

## 19. Problems that remain, and how each is handled

### 19.1 No source in the package (show as "not found" with the reason)

| Item | Handling |
|---|---|
| Furniture and loose equipment (computers, chairs, sofas, racks, amplifier) | No schedule has been found yet. `(SON).dwg` has a furniture layer (`Интерьер - Мебель`, 246 entities) and blocks such as `Toshiba 65L9300` (31 inserts). Count blocks by name as **candidates** for the TV, chair and wardrobe lines, status `REVIEW`. Otherwise "not found" |
| Demolition tonnage (2,501 t) | The volume is stated; the tonnage is not. Treat it as a derived line (5.4) if the ratio to the volume is a plausible density, otherwise "not found" |
| Estimator choices in descriptions (machine, soil group, haul) | Not drawn. Never scored |
| Order 9526 substation | Scans only. Vision + OCR, always "read from a scan" |
| Barrier and running track | No bill section. Nothing to compare |

### 19.2 Possible, but not fully reliable (shown in the UI, never silent)

| Problem | Handling |
|---|---|
| Legacy glyphs not present in any embedded subset (some capitals, `ж`) | Unknown slots decode to the raw character with status `undecoded`. The client's font files would complete the table |
| The two DWGs that LibreDWG cannot read | Week-1 spike with ODA. If ODA also fails, the file is `failed` with a reason, and its buildings fall back to the PDF set where one exists |
| Civil 3D proxies on the site drawings | The quantities that matter are in tables and notes (earth balance, stated areas), so measurement barely depends on proxies. The visual uses proxy graphics, or DWG TrueView with the Object Enabler |
| Sheet frames that defeat detection | Frames from `demo_rules/regions.yaml`, with citation |
| Exploded room zones and broken walls | Printed room schedules (`Yerləşkələrin eksplikasiyası`, PDF and DWG) are the source. Geometry is the check |
| Scanned numbers | Two readers plus cross-document checks. Otherwise `REVIEW` |
| Exact print | Excel automation on Windows. LibreOffice fallback with a ±1 page tolerance |
| Translation quality | Glossary, number guard, original text on hover, human corrections |

### 19.3 Not ours to decide

- **Bill quantities that are themselves wrong** (addendum 15). Show the reviewer-adjusted quantity next to the bill quantity, and never pick.
- **Contradictions between documents.** The Conflicts screen suggests a side and gives the reason. A person decides.
- **Generality.** One project cannot prove the engine works on others. The rules are shaped by one design institute's conventions (Azərdövlətsənayelayihə). Keep them in rule files grouped by designer, so a second project from the same institute reuses them and a different designer gets a new profile.
- **Production licensing.** ODA Sustaining tier, Autodesk Platform Services (Design Automation for AutoCAD converts and plots with real AutoCAD in the cloud), or a commercial DWG SDK. LibreDWG is GPL; do not bundle it into a closed product.
- **Fraud checks (module 2).** No purchase orders, deliveries or invoices exist to test against.

### 19.4 Week-1 spikes (do these before building on them)

| Spike | Pass | Fallback |
|---|---|---|
| ODA converts all 34 DWGs, including the two LibreDWG failures, and the entity counts agree with LibreDWG elsewhere | All 34 open in ezdxf with no reader disagreement | Failed files are blocked; use their PDFs |
| Build the legacy font tables from every embedded PDF font and decode all text | 95% of Cyrillic-script runs decode with high confidence, and Russian stays Russian | Unknown slots stay raw; ask the client for the fonts |
| Depot gate 45.200 × 34.600 m from `(SON).dwg` and the depot DK DWG | Within 50 mm on both | Regions and scale from `regions.yaml` |
| Filled bill through openpyxl + Excel: style fingerprint and print | Zero style differences, 63 pages | Patch the sheet XML directly instead of going through openpyxl |

## 20. Open questions (for the lead or the client)

1. Can the client send their **font folder** (`A3TI(LA).TTF`, `A2TI(LA).TTF`, any `.shx`) and **CTB plot style**? This largely fixes drawing appearance.
2. Can the designer re-save `Baş plan`, `DYNX` and `POS` with `PROXYGRAPHICS=1`, or export LandXML for the grading?
3. Confirm the contract-sum chain in section 2 (line sum + 1.8% + 2% − 0.02, then VAT 18%).
4. Is "addendum 15" available? The reviewer comments say several bill quantities are already known to be wrong.
5. Are the progress values in column L (140,802.40 AZN including VAT) real, or a test entry?
6. Should the client-format export print corrected codes (`2.10`) or keep the client's display (`2.1`)?
7. Which document wins each conflict: seismic, datum, substation, basement area?
8. What does the unit `FF` on row 2330 mean?
9. The brief's decisions 1, 2 and 5 are still open (quantity-only check confirmed, exact copy of printed schedule areas, client-side sample checker).
10. Confirm that `YRS - VN -9335 hadrut xocevend (SON).dwg` is the final depot architecture and low-current set, and that `9335 MH.pdf` is a plot of it. If the two differ, which one is current?
11. Is there a separate technology (TX) set for the depot equipment lines (bill 2.30–2.31), or are those lines priced from a list with no drawing?

## 21. Research sources

- ODA File Converter command line and Docker/xvfb notes: [cad-gis-bim-interop.org batch conversion](https://www.cad-gis-bim-interop.org/python-parsing-geometry-extraction/pydwg-integration/batch-converting-dwg-to-dxf-with-oda-file-converter/), [ezdxf odafc add-on](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html), [ODA File Converter page](https://www.opendesign.com/guestfiles/oda_file_Converter)
- ODA licensing: [ODA FAQ on File Converter](https://www.opendesign.com/faq/question/what-are-oda-viewer-and-oda-file-converter), [membership levels](https://www.opendesign.com/oda-membership), [membership FAQ (SaaS)](https://www.opendesign.com/faq/membership)
- Proxy entities and Civil 3D: [handling DWG proxy entities](https://www.cad-gis-bim-interop.org/core-format-fundamentals-schema-mapping/dwg-proprietary-limitations/handling-dwg-proxy-entities-during-conversion/), [ezdxf issue 495](https://github.com/mozman/ezdxf/issues/495), [Land F/X on PROXYGRAPHICS](https://www.landfx.com/kb/autocad-fxcad/view/1820-topo)
- ezdxf rendering and fonts: [drawing add-on](https://ezdxf.readthedocs.io/en/stable/addons/drawing.html), [fonts and SHX](https://ezdxf.readthedocs.io/en/stable/howto/fonts.html)
- Browser DWG viewer (LibreDWG is GPL, limited coverage): [mlightcad/cad-viewer](https://github.com/mlightcad/cad-viewer)
- Azerbaijani Cyrillic to Latin table: [ICU Azerbaijani_Latin_BGN](https://www.dre.vanderbilt.edu/~schmidt/android/android-4.0/external/icu4c/data/translit/Azerbaijani_Latin_BGN.txt)
- Translation with glossaries: [DeepL glossaries](https://developers.deepl.com/docs/customize/managing-glossaries), [Intento 2026 glossary routes](https://inten.to/state-of-translation-automation/harnesses/five-glossary-delivery-routes-probed/)
- openpyxl and LibreOffice recalculation: [openpyxl tutorial (keep_links)](https://openpyxl.readthedocs.io/en/3.1/tutorial.html), [headless recalc pitfall](https://shahathir.me/til/recalculating-spreadsheets-headless), [Anthropic xlsx skill notes on external links](https://github.com/anthropics/skills/blob/main/skills/xlsx/SKILL.md)
