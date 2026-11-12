# Data Requirements for BOQ Generation

Minimum data per project for automatic Bill of Quantities generation on building projects (villas, mid-rise, towers, industrial and depot buildings): files, formats, counts and fields.

## 1. Package conditions and file content

| Item | Requirement |
|---|---|
| Project unit | One project = one package from one coordinated issue (same revision for drawings, schedules, specification, BOQ and rates) |
| Revision | Revision letter and date on every sheet; revision log or drawing register included |
| Format | DWG (or DXF) plus the matching PDF for every sheet that carries quantities |
| Scale and units | Scale printed on each sheet or in a scale schedule; units stated per file (mm, m) and per BOQ line (m, m², m³, kg, t, no.) |
| Language and naming | Original language kept (Azerbaijani, Arabic, English); sheet number, title, discipline and floor identifiable from file name or title block |
| Geometry | Model-space entities at true size; closed polylines or hatches for areas; CAD units set correctly (INSUNITS matches real units) |
| Layers and blocks | Layer names kept (S-COL, S-BEAM, A-WALL); block definitions and xrefs included |
| Text and dimensions | Real text (not outlines), MTEXT for schedules and notes; dimension entities and level marks kept; non-standard language fonts embedded or supplied |
| Tags and title block | Element marks (C1, B2, F3) on plans match the schedules; title block has sheet number, title, scale, revision, date; one layout per sheet |

## 2. Drawings by discipline

Format: **D** = DWG, **P** = PDF, **X** = Excel. Minimum is per project.

### 2.1 General, site and landscape

| Sheet / document | Format | Minimum | Gives |
|---|---|---|---|
| Cover sheet, drawing index, legends and symbols, general notes, area / GFA statement, location plan | P / X; D + P for legends and notes | 1 each (legends and notes: 1 per discipline) | Sheet list, revisions, symbol and hatch meaning, thickness / cover / grade / finish rules, floor and room areas, site context |
| Site plan, setting-out plan, topographic survey, grading and finished levels plan | D + P | 1 each | Building positions, coordinates, existing and finished levels |
| Cut-and-fill table or sections; road plan, long sections, cross sections | D / P | 1 set | Earthwork volumes; road, kerb and pavement quantities |
| Storm, sewer, water and utility network plans | D + P | 1 per network | Pipe lengths, manholes, fittings |
| Retaining walls, fences, gates; demolition plan or note | D + P | All issued / if any | Length, height, section; demolition volume |
| Geotechnical / soil report | P | 1 | Soil group, bearing capacity |
| Landscape hardscape plan, softscape / planting plan with plant schedule | D + P (+ X) | 1 each | Paving area, edging, steps, plant counts, turf area |
| Irrigation plan, site furniture, pool and water feature details | D + P | If any | Pipe and head counts, furniture counts, volumes, finishes |

### 2.2 Architecture and interior

| Sheet / document | Format | Minimum | Gives |
|---|---|---|---|
| Floor plans (basement, ground, mezzanine, typical, upper, roof, top roof) and setting-out / dimension plans | D + P | 1 per unique floor | Walls, rooms, areas, openings, wall lengths, grid |
| Elevations (north, south, east, west, internal) | D + P | All sides | Facade area, cladding, openings, heights |
| Building sections; wall sections and facade details | D + P | At least 2 sections; all details | Floor levels, ceiling heights, build-ups, cladding, insulation |
| Reflected ceiling plans, floor finish plans | D + P | 1 per unique floor | Ceiling type and area, floor finish zones |
| Wall finish plans / interior elevations; toilet, bathroom, kitchen enlarged plans and elevations | D + P | 1 per room type | Wall finish, tile height, fixtures, fittings |
| Roof plan, roof drainage, roof details | D + P | 1 each | Roof area, slope, waterproofing, insulation |
| Stair, lift and ramp details | D + P | All issued | Steps, balustrades, finishes |
| Partition / wall type schedule | D + P | 1 | Wall layers per type |
| Door and window schedules and types | X / D / P | 1 each | Count, size, material, glass, frame, hardware |
| Louvres, curtain wall, cladding, canopy; waterproofing, expansion joint, parking and miscellaneous details | D + P | All issued | Facade systems, detail items |
| Finish schedule / room data sheet; ironmongery / hardware schedule | X / P | 1 each | Floor, wall, ceiling finish per room; hardware |
| Fire egress and fire-rated wall plans; signage and wayfinding plans | D + P | If any | Fire-rated wall length and type; sign counts and types |
| Interior: furniture layout, ceiling and lighting plans | D + P | 1 per unique floor | FF&E counts, ceiling and fixture counts |
| Interior: joinery / millwork details, interior wall elevations | D + P | All issued; 1 per room type | Cabinet, panel, counter quantities, wall finish area |
| Interior: FF&E, sanitary and fixture schedules | X / P | 1 each | Item counts, specs |

### 2.3 Structure

| Sheet / document | Format | Minimum | Gives |
|---|---|---|---|
| General notes; typical details (laps, hooks, openings, stirrups); sections | D + P | 1 set; all issued; at least 2 sections | Concrete grade, cover, blinding, lap rules, steel assumptions, levels, depths |
| Foundation plan (footings, raft, piles, pile caps); footing / pile cap / raft schedule | D + P; D / X | 1 each | Foundation geometry, size, depth, bars |
| Column layout plan; column schedule | D + P; D / X | 1 each | Column positions; size and bars per floor band |
| Ground beam and slab-on-grade plan | D + P | 1 | Beams, slab area and thickness |
| Framing / slab plans; beam schedule | D + P; D / X | 1 per unique level; 1 | Slabs, beams, openings; size and bars |
| Slab reinforcement plans | D + P | 1 per unique level | Slab steel |
| Shear wall, core wall, lift pit, stair and ramp details; tank, retaining wall and special elements | D + P | All issued | Wall length, height, thickness, concrete and steel, volumes |
| Post-tensioned slab plans (tendon layout, TOC levels) | D + P | If any | Slab thickness, tendons |
| Bar bending schedule | X / P | If issued | Steel by bar mark |
| Steel structure member and connection schedules | D / X | If any | Member lengths, weights, bolts |

### 2.4 MEP

| Discipline | Sheet / document | Format | Minimum | Gives |
|---|---|---|---|---|
| Electrical | Lighting layout; power / small-power layout; cable tray / containment layout | D + P | 1 per floor | Fixture, socket and outlet counts; tray and conduit lengths |
| | Single-line diagram; earthing and lightning protection | D + P | 1 | Panels, breakers, cables, conductors, rods |
| | Panel and load schedules; fixture and device schedule | X / P | 1 per panel; 1 | Circuits, ratings, item specs |
| | External lighting, substation, generator | D + P | If any | Equipment and cable |
| HVAC | Duct and pipe layouts | D + P | 1 per floor | Duct and pipe lengths |
| | Equipment schedule (AHU, FCU, chiller, fan) | X / P | 1 | Equipment counts and capacity |
| | Risers, schematics, control diagrams; ventilation and smoke management; BMS I/O point list | D + P / X | 1; if any | Riser lengths, controls, fans, dampers, control points |
| Plumbing | Water supply layout and risers; drainage, storm and condensate layouts | D + P | 1 per floor | Pipe lengths, fittings, manholes |
| | Fixture schedule | X / P | 1 | Sanitary counts |
| | Pump rooms, tanks, pool, irrigation, gas | D + P | If any | Equipment and pipe |
| Fire | Firefighting / sprinkler layout; fire pump and hydrant layout | D + P | 1 per floor; if any | Heads, pipe lengths, equipment |
| | Fire alarm layout and device schedule | D + P + X | 1 each | Detector and panel counts |
| ELV / ICT | Data, telephone, CCTV, access control, PA, TV | D + P | 1 per system and floor | Outlets, cameras, cabling |
| Vertical transport | Lift / escalator layouts and specification | P | If any | Unit counts, stops |

### 2.5 Specifications, supporting documents and BIM

| Document | Format | Minimum | Gives |
|---|---|---|---|
| Technical specification (concrete, masonry, plaster, finishes, MEP) | P / Word | Relevant sections | Materials, grades, methods |
| Material submittals and approved brands; door, window and ironmongery data sheets | P / X | If any | Material identity, product specs |
| Sustainability, acoustic, energy reports; site photos | P / X / JPG | If any | Material requirements, context |
| BIM model and its quantity export | IFC / RVT; X | If available | Element quantities, check data |

### 2.6 Typical drawing volume

| Project type | Sheets | Example in our data |
|---|---|---|
| Villa | 30–60 | Khanna Villa, 29 structural DWG |
| Mid-rise (G+4) | 100–150 | Y-911 G+4, 117 PDFs |
| Industrial / depot complex | 50–100 | Hadrut depot, 34 DWG + 23 PDF + 4 scans |
| Tower / mixed use | 500–1,000+ | ADICC Volume 4, 1,100+ PDFs and 190+ DWGs |

## 3. The BOQ

**Line fields**

| Field | Example | Required |
|---|---|---|
| Item code | `2.2.4` (stored as text) | Yes |
| Section / trade; building / zone | Structure, Masonry, Finishes, MEP; Main building, Guard room | Yes; zone if more than one |
| Description | "Reinforced concrete C30/37 in footings" | Yes |
| Unit, quantity | m³, 67.00 | Yes |
| Unit rate, amount | 120.00, 8,040.00 | Yes |
| Reviewer comments; progress columns (executed to date, this month) | "Includes formwork" | If any; if a payment certificate |

**BOQ files**

| File | Format | Minimum | Gives |
|---|---|---|---|
| Full BOQ with line quantities; summary / collection page; preliminaries and general items | X | 1 each | Baseline and output template, section and grand totals, site setup, supervision, insurance |
| Provisional and prime cost sums; bill preambles and notes | X / P | If any | Allowances, inclusions, measurement notes |
| QS takeoff / calculation sheets | X | Recommended | Human measurement per line |
| Verified sample calculation per trade | X / P | 1 per trade | Ground truth |

**Measurement rules** (one written set): standard (CESMM, POMI, SMM7 or local norm); openings net or gross and deduction threshold; repeated layers measured once or per layer; finishes measured to wall face or to structure; comparison tolerance per trade.

## 4. Materials and rates

| Data | Fields | Example |
|---|---|---|
| Material price list | Name, specification / grade / brand, unit, rate, currency, price date / base, location / supplier, VAT included, delivery included | Ready-mix concrete, C30/37, m³, 95.00 AED, 1 Sep 2022, Baku, VAT yes |
| Labour | Trade, unit (hour / day), rate | Mason, 12/hour |
| Plant | Machine, unit, rate, operator and fuel included | Excavator, 80/hour |
| Subcontract; transport / haul | Work type, unit, all-in rate; distance, unit, rate | Waterproofing 15/m²; haul 10 km, 4/m³ |
| Rate analysis (per bill line) | Bill code or description; material rows with quantity per one unit of work and waste %; labour rows; plant rows; overhead and profit %; resulting unit rate | Block wall 200 mm per m²: block 12.5 no. (5% waste), mortar 0.03 m³ (10%), mason 0.5 h, mixer 0.1 h, overhead 10% + profit 8% |
| Price base and mark-ups | Price date, region, norm book or quote; escalation rate and period; temporary buildings %; contingency % and base; overheads and profit % and order; VAT / duties %; currency, decimals, conversion rate | Work lines, + temporary buildings %, + contingency %, + VAT % (written in calculation order so the BOQ header total can be rebuilt from the lines) |

Also record whether the bill amount equals the sum of the analysis rows, how waste is written (percentage, separate row, none), and whether the bill quantity is before or after waste.

**Quantities that need extra data**

| Item | Extra file |
|---|---|
| Reinforcement (kg, t) | Bar bending schedule or count per bar mark |
| Earthwork | Cut-and-fill table or survey, soil group, haul distance |
| MEP items | Equipment schedules, counts per system |
| Technology, furniture, communications | Own drawing set or equipment list |
| Demolition | Demolition drawing or stated volume |

## 5. Site and commercial records

Each record points to a bill code, a material row or a month.

| Record | Fields | Minimum |
|---|---|---|
| Delivery notes | Date, supplier, material, quantity, unit, note number, bill code | 1 sample, then 1 month |
| Site measurements | Month, bill code, quantity done | 1 month |
| Monthly payment certificate | Bill line, quantity this month, to date, amount | 1 sample |
| Invoices | Date, supplier, item, quantity, rate, amount, bill code | 1 sample |
| Variation orders; material approvals | Item, reason, quantity or rate change; material, brand, approval status | If any |

## 6. Dataset size and variety

| Item | Minimum / range |
|---|---|
| Method validation | 3–4 projects, each with BOQ, rate sheet and verified calculation |
| New drawing offices | 10–15 projects from at least 5 offices or CAD conventions |
| Rate coverage | A rate for at least 90% of BOQ lines by value |
| Rate analyses | One per distinct work type (about 30–60 for a typical building) |
| Labelled drawing sheets (walls, rooms, symbols) | 50–70 sheets per drawing style, at least 3 styles |
| Building type | Villa, mid-rise, high-rise, industrial or depot, fit-out |
| Structure | RC frame, raft, pile caps, post-tensioned slab, steel |
| Line style and detail level | Clean CAD, thin-line ink, scanned or flattened; tender set and construction set |
| Language and units | English and local language, mm and m |
| Bill style and price base | At least 3 consultant bill formats; at least 2 currencies or price dates |
| Trades | Concrete, masonry, plaster, finishes, MEP, external works |

## 7. File types and ground truth

| Type | Data quality | Notes |
|---|---|---|
| DWG / DXF | Best | Exact geometry, layers, text |
| IFC / RVT | Best, if available | Classified elements |
| Excel | Best for tables | BOQ, rates, schedules |
| Vector PDF (real text) | Good | Text readable, geometry limited |
| Word | Good | Specifications, notes |
| Scanned or flattened PDF, images | Weak | No text or closed shapes |
| Backups and logs (`.bak`, `.log`, duplicate zips) | Exclude | |

| Ground truth | Content |
|---|---|
| Quantities | Consultant BOQ plus QS-verified calculation, per project and per trade |
| Bill-to-drawing link | Sheet and element for each quantity (sample of lines) |
| Bill-to-rate link | Each BOQ line matched to a rate or rate analysis |
| Drawing labels | Wall polygons in one consistent style per sheet |
| Conflicts | Both values kept when documents disagree, with the chosen one marked |

## 8. Package is incomplete if

Bill and drawings are from different revisions; scale or units are not stated; the bill has totals only; the bill has no rates and there is no rate sheet; price base, currency or mark-up chain is unknown; all drawings are scans with no DWG or text PDF; schedules are referenced but not supplied; measurement rules are not written.

## 9. Minimum package to request

For 3–4 projects, each from one coordinated issue: the consultant BOQ in Excel (with summary, preliminaries and notes); all drawing types in section 2 for the agreed scope, in DWG and PDF; schedules (doors, windows, finishes, columns, beams, footings, bar bending, equipment); specification sections; material prices, labour and plant rates and rate analyses with price date and currency; mark-up and tax rules in calculation order; measurement rules; one verified QS calculation per trade; and, if cost control is in scope, delivery note, site measurement, payment certificate and invoice samples.
