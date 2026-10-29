# How geometry will be extracted from the Hadrut drawings

This report covers measurement only: lengths, areas, counts and volumes. Prices stay in `BOQ-Hadrut.xlsx`. File identities are in `Hadrut-client-data-analysis.md`.

The short version: these are **2D working drawings in millimetres**, not a 3D model. Real lengths are written on the sheets as dimension text (`45200` means 45.200 m). The lines underneath are the geometry we measure, but only after the drawing is split by layer. Hatches, furniture, axes and dimension graphics are not building elements, and on some sheets they are most of the vectors.

---

## 1. What was checked

| Check | Result |
|---|---|
| 34 DWG files | AutoCAD **2007** (structural set, vertical grading, construction plan), **2010** (most site, water and electrical drawings), **2013** (depot plumbing and the HVAC drawing). Bodies are compressed, so entities cannot be read by scanning the file as text. They have to be converted to DXF first |
| Order 9335 drawing PDFs | Vector plots on **A3 landscape** (1191 ? 842 pt). Text and lines both exist. One depot architecture file carries the original CAD layers inside the PDF |
| Order 9526 PDFs and the 56-page general note | **Scans**. No vectors. Geometry cannot be measured from those pages; a vision read can only lift dimensions and tables |
| Depot plan, `9335 MH.pdf` page 5 | Overall dimensions **45200 ? 34600**, which is the stated 45.2 m ? 34.6 m building. Bay chain on the same side: 1600 + 6000 ? 7 + 1600 = 45200. Linear dimensions are **millimetres** |
| Same file, section sheets | Storey heights appear as **2700** and **3300** mm. That matches the written brief: basement 2.70 m, floors 3.30 m |
| Same file, first-floor sheet | The number **1395.80** is printed on the plan. That is the stated first-floor area in m?. Areas on the sheet are square metres; lengths are millimetres |
| Longest line on that plan page | 1190 pt, which is the **paper border**, not the building. A PDF line length is a paper length until a scale is applied |
| Fire-tank sheets | Repeated dimension **5000** mm (5.00 m tank). Wall and cover thickness shown as 300, 250, 125 mm |
| Guard room | Plan grid **2000 ? 2000** mm, which matches the roof plan already read |
| Toilet structural sheet | **354,986 line segments on one page**. Those are hatch and bar strokes. Measuring every line would invent a huge length that is not a wall |
| `Vertikalka.dwg` | AutoCAD 2007. **No Civil 3D surface** stored in the file. Cut and fill is drawn as ordinary contours and level text. A volume has to be built from those points |
| Master-plan / utilities DWGs (`Ba? plan`, `DYNX`, POS) | Contain Civil 3D objects (`AeccDb`: parcels, alignments, section labels). No TIN surface name was found in clear text. After conversion, use the visible linework if the Civil object does not survive |

The architecture PDF also shows where the drawings were produced. Layer names inside `9335 MH.pdf` come from **ArchiCAD** (`���� ArchiCAD`, `����� ArchiCAD`, zones, fills) and from **AutoCAD SPDS** (`��� ����`), then a plot that duplicated every layer once per pen. The building was flattened to 2D before it reached us. There is no solid to ask for a volume.

---

## 2. Three sources, used in this order

Use the first source that exists for that element. Do not average them.

| Order | Source | When it is the right one | What it returns |
|---|---|---|---|
| 1 | A schedule already on the sheet | Doors, windows, luminaires, cables, fans, reinforcement, timber, tank concrete | The designer�s own count, in the bill�s unit. This is not geometry, and it is more reliable than tracing |
| 2 | DWG model space, after conversion to DXF | Walls, slabs, trenches, roads, fence, pipes, when the native file exists | True lengths and areas in drawing units, one coordinate system per file |
| 3 | Vector PDF, calibrated per viewport | The 9335 plots, as a check, and for any sheet whose DWG was not sent | Same elements, but the scale must be recovered from a dimension |
| 4 | Vision on a scan | Order 9526 (no DWG at all) and the general note | Individual written dimensions and tables. Not a closed polygon of a wall |

`BOQ-Hadrut.xlsx` is the score sheet, not an input to measurement. After a takeoff, the quantity is compared with the matching bill line.

---

## 3. The extraction pipeline

```text
DWG 2007 / 2010 / 2013
        ?
        ?
ODA File Converter  ?  DXF (one model, units kept)
        ?
        ?
ezdxf
  � drop paper space, title block, viewports
  � read INSUNITS
  � if the plan spans about 45,000, units are mm
  � if it spans about 45, units are m
        ?
        ?
layer normaliser
  � cut the plot suffixes  _���. ����__N   and  _Pen_No__N
  � merge what is left into the dictionary in section 5
        ?
        ?
keep only element layers
  walls, partitions, columns, slabs, doors, windows,
  pipes, cables, roads, fence, contours
  drop: dimensions, axes, hatch, furniture, text, hidden, stamp
        ?
        ?
heal
  � join collinear segments into polylines (gap tolerance 5 mm)
  � drop segments shorter than 50 mm (hatch debris)
  � pair parallel wall lines at the known thickness
        ?
        ?
measure
  � length, area, count
  � height and thickness from the section or the note
  � volume = area ? thickness, or plan area ? storey height
        ?
        ?
record
  file, layout, layer, method, raw value, unit, bill section
```

PDF plots of the same 9335 sheets follow the same filter, with one extra step. The plot is on paper. Each viewport is calibrated from a dimension whose text we can read:

- find the text `6000` sitting on a dimension layer
- measure the paper length of the dimension line under it
- scale = 6000 mm / that paper length
- apply that scale only inside that viewport

A typical A3 sheet has a plan at one scale and a detail at another. Mixing them turns a 400 mm wall into a nonsense length. The overall `45200` on the depot plan is the calibration check: after scaling, the long side must come back as 45.200 m � 0.05 m.

Scanned pages (9526, the general note) stop before this pipeline. They go to a vision reader for tables and for isolated dimensions such as footing size and layer thickness.

---

## 4. How each bill quantity is computed

Heights below are the ones printed on the depot sections (`2700`, `3300`) or in the note. Thicknesses are the ones stated in the structural chapter and on the small-building sheets. Every formula is applied **per building**, then mapped to that building�s section of the bill.

### 4.1 Walls and partitions (the large money in section 2)

External wall is sawn limestone, about **400 mm**. Concrete walls on the bill are **200 mm** and **500 mm**.

1. Take centreline length from a closed wall polyline, or from a pair of parallel lines 400 mm apart (200 or 500 mm for the concrete walls).
2. Subtract door and window widths. Those widths are on the door/window schedule; the opening polylines on layers `�����` and `����` are the fallback.
3. Wall area (m?) = net length ? storey height. The bill measures the limestone basement wall in **m?**, so this area is the quantity, not the volume.
4. Concrete wall volume (m?) = net length ? height ? thickness. Split 200 mm and 500 mm because they are different bill lines.
5. Do not count hatch lines inside the wall. They are the stone pattern.

Partitions (`arak?sm?`, `�����������`) are a separate layer and a separate bill line. They are thinner and must not be added to the external wall.

### 4.2 Columns, beams, slabs

These are 2D outlines, so the third dimension comes from the section or from the member label.

| Member | Plan geometry | Third dimension | Bill unit |
|---|---|---|---|
| Column | Closed rectangle on `�������` / `Kalonlar`, or a block | Height from underside of beam to floor, read on the section | m? of concrete, then tonnes of steel from the bar schedule |
| Beam | Two parallel lines, or a labelled width | Width ? depth from the section; length along the grid | m?, split from the slab |
| Slab | Closed outline on `Demir-beton tava` / `DOSEME`, one per level | Thickness from the section (the note and the bill use up to 200 mm for the flat slab) | m? = outline area ? thickness, minus stair and duct openings |
| Strip footing | Closed band, or two lines. Depot footing in the note is **1000 ? 500 mm**. Toilet footing on its sheet is **500 ? 400 mm** | Depth is the section depth, not the plan width | m? = centreline ? width ? depth. Blinding and gravel underneath are extra layers, each with its own thickness from the section |

Reinforcement is **not** traced. A tank sheet and the toilet sheet show why: one page can hold hundreds of thousands of bar strokes. The quantity is the `material s?rfi` table beside the bar detail, in tonnes, split A240 / A-I and A500C / A-III. The geometry is only a check that a schedule exists for every member mark.

### 4.3 Floors, finishes, roof

Room area is the best-case read. The depot PDF has an ArchiCAD zone layer (`������� ������ - ����`). A zone polyline is the room polygon, and its label is the room name and often the area. Where zones were exploded, build the rooms by polygonising the wall centreline and attaching the nearest room-name text.

Floor quantity (m?) = room polygons grouped by the floor-type schedule (`d???m? eksplikasiyas?`), not one number for the whole storey. The bill splits laminate, ceramic, concrete and screed.

Finish area (m?) = net wall area of those rooms, by finish type, from the same schedule. Wall area already excludes openings.

Roof:

- Plan area from the roof outline.
- Slope from the section. The guard-room sheet shows **25�** and a metal-tile area already totalled as **9.6 m?**. Prefer that table.
- Timber is the piece schedule (size, length, count, volume), as on the guard-room rafter table. Summing those rows is the quantity. Tracing rafter lines is the fallback.

### 4.4 Tanks (sections 10�13)

Each tank is a box. The fire-tank sheets print **5000 mm** as the main plan size and wall/slab thicknesses of **300, 250 and 125 mm**.

- Floor slab m? = internal length ? internal width ? slab thickness
- Walls m? = centreline perimeter ? height ? wall thickness
- Cover m? = same as the floor, with its own thickness
- Excavation m? = outside footprint ? depth, plus the working space shown on the section
- Two identical tanks stay as two bill sections. Measure one, copy, and name them 3 and 3a, or 5 and 5a

The sheet�s own material total is source 1. The formula is the check.

### 4.5 Pipes, ducts, cables

System codes are already layer names on the depot PDF: **`-S0`**, **`-K1`**, **`-K3`**, and the HVAC drawing is mark ?V. The bill uses the same codes (S0, ?S3, ?S4, K1, K1T, K3, K3T).

- Length (m) = polyline length on that layer, split by the diameter text nearest the run (`?100`, `?150`, NYY 4?2.5).
- Fittings and fixtures = block inserts on that layer (WC, gully, manhole, luminaire, socket). Unit `?d?d` or `d?st`.
- A cable schedule or AT sheet overrides the traced length when both exist. The 0.4 kV AT sheet already lists metres by cable type.

Vertical drops are not on the plan. Add the storey height once per riser that the schematic shows, or take the riser length from the schematic itself.

### 4.6 Roads, pavements, fence, grading

| Element | Geometry | Quantity |
|---|---|---|
| Asphalt and concrete roads | Closed outline on the master plan. The bill already states 383.7 m?, 216 m? and 1,021 m? | Area from the polygon. Each course is area ? thickness from the general note (asphalt 40 or 50 or 70 mm, crushed stone 150 mm, gravel 100 or 250 mm, concrete B15 at 150 mm) |
| Pavements | Same, bill area 1,437.8 m? | Area ? 40 mm asphalt ? 100 mm gravel |
| Fence and retaining wall | Long polylines on the fence drawing `istinad divari ve hasar dk.dwg` | Length split at the lettered points the bill uses: B�C, F�G, G�A. Wall volume = length ? section area. The temporary site fence, 249.1 m, is a preliminaries item and lives on the POS drawing, not on this wall |
| Vertical grading | Contours and spot levels in `Vertikalka.dwg` | There is no stored TIN. Build one from points that carry an elevation (Z coordinate, or a level text such as 694.70). Formation surface minus existing surface = cut and fill in m?. This is bill section 18 |
| Landscaping | Closed regions on the master plan outside buildings, roads and pavements | Area in m?. The note states 3,482.30 m? as the design figure to check against |

Spot levels around **694.4�694.7 m** on the depot and tank sheets are absolute heights. Excavation depth is the difference between the site level and the underside of blinding. Do not use the 408.80 m figure from the architecture chapter; that passage names Z?ngilan and belongs to another project.

### 4.7 Counted objects

Doors, windows, pumps, boards, fans, columns-as-blocks: count inserts of each block name. The fan table in the general note is already this count (K 200 L, OV 2E 200, CT 315-4, with duties). Match the block name to the bill description. A symbol with no block, only loose lines, is counted by the vision reader from the legend, then checked against the schedule.

---

## 5. Layer dictionary found in the depot architecture PDF

The plot multiplied layers by pen number. `�����_���. ����__21` and `�����_���. ����__1` are one layer. Strip the suffix, then classify the stem.

| Stem (after cleanup) | Treat as | Use |
|---|---|---|
| `Xarici divarlar`, `Exterior walls`, `�����`, `�����`, `DIVAR2`, `����������� - �����������` | External wall | Length and area |
| `�����������`, `Arakesmelerin x?tti`, `����?��?`, `��������- �����������` | Partition | Separate from external wall |
| `�������`, `Kalonlar` | Column | Count and section size |
| `�����`, `����� ArchiCAD` | Door | Opening width, count |
| `����` | Window | Opening width, count |
| `Demir-beton tava`, `DOSEME` | Slab | Area |
| `�������� - �����`, `Metal kiremit`, `Dam m?h?cc?ri` | Roof and railing | Area, length |
| `Pilleken`, `�������� - ��������` | Stair | Count and going; concrete from the section |
| `������� ������ - ����` | Room zone | Room area, already a polygon |
| `-S0`, `-K1`, `-K3`, `S1` | Water and sewer | Pipe length by system |
| `sq torlari` | Mesh | Do not measure; use the steel schedule |
| `���`, `OXLAR`, `Koordinasiya oxlar?`, `��� ����` | Grid | Ignore for quantities. Use only to name fence stretches |
| `������`, `Olculer daxili`, `Olculer xarici`, `Xar. ?l??l?r`, `Dimensioning`, `0_ANNOT_Dimensions` | Dimensions | Read the **text**. Ignore the dimension lines |
| `Fills`, `shtrix`, `������` | Hatch | Drop |
| `������`, `�������� - ������` | Furniture | Drop |
| `���������` | Hidden | Drop |
| `Yaz?`, `Text blocks`, `K?nc ?tamp?` | Notes and title block | Drop, except room names and level text |

The same cleanup applies to every DWG once it is DXF. Layer names will differ by discipline. DK files will add footing, bar and formwork layers. SK files will add pipe layers. The classifier is a dictionary plus a fallback: a closed polyline wider than 150 mm on an unknown layer is reviewed, not auto-counted.

---

## 6. Units

| Written on the sheet | Meaning | Example on these files |
|---|---|---|
| 45200, 6000, 400, 5000 | Millimetres | Building 45.2 m, bay 6 m, wall 0.4 m, tank 5 m |
| 1395.80, 65.20, 9.6 | Square metres when the label is an area | First floor, tower footprint, metal tile |
| 694.70 | Metres above datum | Absolute level of �0.000 on the structural sheets |
| 25� | Slope | Guard-room roof |
| m? in a `material s?rfi` cell | Already a volume | Concrete and timber tables |

Inside a DWG the same rule is checked against the coordinate range, not assumed. A file inserted as metres into a millimetre file is a known failure; the 45.2 m side is the test that catches it.

Haul weight in tonnes is not geometry. The bill converts excavation m? to tonnes with a density. That factor comes from the norm line (soil group), not from the drawing. Geology gives the soil (gravel with loam, then hard loam) so the norm line can be chosen. It does not give the trench volume.

---

## 7. Acceptance checks on this project

A geometry run is accepted only if these, which are already printed, come back within the tolerance.

| Check | Expected | Tolerance |
|---|---|---|
| Depot plan, long side | 45.200 m | 50 mm |
| Depot plan, short side | 34.600 m | 50 mm |
| Bay module | 6.000 m | 20 mm |
| Basement storey height | 2.70 m | 20 mm |
| Upper storey height | 3.30 m | 20 mm |
| First-floor area text | 1,395.80 m? | the polygon sum within 3% |
| Tower footprint / total area / volume | 65.20 m? / 127.14 m? / 790.80 m? | 3% if remeasured, exact if read from the title block |
| Guard room plan | 2.00 ? 2.00 m grid | 20 mm |
| Guard roof timber and tile | 0.23 m? and 9.6 m? | exact, from the schedule |
| Fire tank plan | 5.00 m | 20 mm |
| Toilet footing | 500 ? 400 mm | exact, from the note on the sheet |
| Roads and pavements | 383.7, 216, 1,021, 1,437.8 m? | 3% against the bill areas |
| Greenery | 3,482.30 m? | 5%, the outline is less sharp than a building |
| Two 81 m? tanks | equal quantities | they must match each other |
| Two 27 m? tanks | equal quantities | they must match each other |

The first test to build is the depot plan side, because the dimension text, the note and the bill all name 45.2 ? 34.6 m. If that fails, scaling or units are wrong and nothing else should be trusted.

---

## 8. What geometry extraction will not produce

- **A 3D model.** The files are plans, sections and elevations. Volume is always area times a thickness or a height taken from another view.
- **Reinforcement tonnage from bar lines.** Use the schedule.
- **Cut and fill from a button in Civil 3D.** `Vertikalka.dwg` has no surface object. The surface is rebuilt from contours and spot levels.
- **Order 9526 quantities from vectors.** Those 78 drawing pages are photographs of sheets. Until someone supplies the DWG, only vision-on-raster is possible, and only for text and tables.
- **Demolition, section 1 of the bill.** 7,625.4 m? and 2,501 t are in the bill. No existing-building drawing is in the drop.
- **Depot fire alarm, CCTV, data and the technology layout**, where a separate drawn set was not found. Leave the bill lines open rather than invent a route.
- **The LIRA file** `Xocavend transformator.lir`. That is an analysis model (LIRA-SAPR 2013), not the construction drawing.
- **Prices, overheads, and the 700,000 AZN gap** between the bill header and the sum of the lines.

---

## 9. Order of work

1. Convert the depot structural DWG and `9335 MH`�s native file (the PDF is the plot; the DK file is `9335 Xocavend yangin deposu dk son.dwg`) to DXF. Prove the 45.200 ? 34.600 m check.
2. Add the layer dictionary in section 5 and measure external wall, partition, column and slab for the depot only. Compare concrete m? and wall m? with bill section 2.
3. Read every `material s?rfi`, door, window and AT schedule into a table. That covers reinforcement, openings and most of the electrical counts without tracing.
4. Repeat per building DWG: tower, guard room, heating point, pump station, tanks, toilet, wash, gazebo, fence. Tanks and the fence are next because they are simple shapes and large bill sections.
5. Site: roads and pavements from the master plan, then a TIN from `Vertikalka.dwg`.
6. Pipes and cables by system layer, overridden by schedules where the schedule exists.
7. Only then run the vector-PDF path, as an audit that the DXF takeoff and the plotted sheet agree.
8. Vision is reserved for the scanned 9526 set and for any SHX note the DXF text does not return as Unicode.

Each stored quantity keeps its source. A reviewer can open the layer and see the polyline that produced the number. That link is the product. A single project total with no source is not.
