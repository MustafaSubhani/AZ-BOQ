# Hadrut / Xocav?nd client data � what each file is, and how an automatic BOQ can be built from it

The language is **Azerbaijani** (`Az?rbaycan dili`), not an unknown script. The design institute writes in Latin Azerbaijani. Older Word files and some CAD fonts are in Cyrillic Azerbaijani or Russian. Norm titles (SNiP, GOST, AzDTN) are left in Russian. The commercial bill of quantities is bilingual English / Azerbaijani.

This is one real project that can be used as the first training and test case for an automatic bill-of-quantities platform. It already contains both the design and a priced bill.

---

## 1. What the project is

| | |
|---|---|
| Client | Ministry of Emergency Situations of Azerbaijan (`F?vq?lad? Hallar Nazirliyi`, FHN), Capital Construction Department |
| Designer | `Az?rd?vl?ts?nayelayih?` State Design Institute, under the State Agency for Supervision of Safety in Construction |
| Main order | **Sifari? No. 9335**, Baku, 2024. Chief engineer G.A. Feyzullayev |
| Later order | **Sifari? No. 9526**, Baku, 2026. External power supply only |
| Object | State Fire Protection Unit (`D?vl?t Yan??ndan M?hafiz? Hiss?si`) in **Hadrut** settlement, **Xocav?nd** district. A **4-bay fire station** (`4 ??x??l? yan??ns?nd?rm? deposu`) plus yard buildings |
| Site | **0.842 ha = 8,242.50 m?**. Buildable area stated as 1,881.70 m?. Greenery 3,482.30 m? (42%) |
| Main building | 2 storeys plus basement, plan **45.2 m ? 34.6 m**, capacity **8 fire vehicles**. Basement floor area stated as 1,360.20 m?, first floor 1,395.80 m? |
| Structure | Monolithic reinforced-concrete frame (columns, beams, slabs, strip footings). External walls of sawn limestone, mark M50, about 400 mm, on cement-sand mortar. Concrete B25. Reinforcement A240 and A500C. Seismic **8 points**, soil class II (`AzDTN 2.3-1`) |
| Climate used for design | Zone IV B. Winter design temperature about ?8 to ?10 �C. Snow 120 kg/m? (region II). Wind 60 kg/m? (region V) |
| Ground | Modern deluvial-proluvial deposits. Upper layer: fine gravel with up to 20% hard loam, 1.20�3.80 m thick, then hard loam. No groundwater struck in the boreholes. Sulphates in the soil are aggressive to concrete; vertical faces in contact with soil get 2 coats of hot bitumen |
| Power | Calculated demand in the 2024 note: **142 kW**. Adopted package substation **KTY / KTM 250 kVA**. See the conflict in section 7: the 2024 note says 10/0.4 kV, the 2026 drawings say **35/0.4 kV** |
| Contract BOQ header | **3,811,193.36 AZN** |
| Sum of priced work lines in that same file | **about 3,110,506 AZN** across 2,176 work items in 132 subsections. These two figures do not match. Keep both, and reconcile them; do not treat either one as �the� project value until the gap (about 700,000 AZN) is explained |

Buildings and yard elements named in the general note and in the bill (position numbers are the master-plan marks, `m?vqe`):

| Mark | Element | Where it appears in the bill |
|---|---|---|
| 1 | Fire station, 4 bays, basement + 2 floors | Section 2. The largest part of the bill, about 1.84 million AZN of line value |
| 2 | Special-purpose garage (mentioned with the main building) | Inside section 2 |
| 3, 3a | Two fire-water tanks, **81 m?** each | Sections 10 and 11 |
| 4 | Water pump station | Section 14 |
| 5, 5a | Two drinking-water tanks, **27 m?** each (one sheet also calls them drinking and fire-protection tanks) | Sections 12 and 13 |
| 6 | Drill / hose tower (`q?ll?`, `t?lim q?ll?si`) | Section 4. Drawing states site 65.20 m?, total area 127.14 m?, volume 790.80 m? |
| 7 | Guard room (`n?zar?t?i ota??`) | Section 3 |
| 8 | Transformer substation, 1 ? 250 kVA | Separate order **9526**, not fully inside the 3.81 million bill |
| 9 | Vehicle wash (`avtoyuma`) | Section 15 |
| 10 | Barrier (`?laqbaum`) | Named on the master plan. No section of its own in the bill |
| 11 | Running track (`qa??? zola??`) | Named on the master plan. No section of its own |
| 12 | Sand training pit | Section 24 |
| 13 | Shelter / gazebo (`s?hb?tgah`) | Section 26 |
| 14 | Rest area | Named on the master plan |
| 15 | Sports area | Named on the master plan |
| 16 | Diesel generator, about 50 kVA / 40 kW, weight about 1,180 kg | Section 6 |
| 17 | Heating point (`istilik m?nt?q?si`) and heating network. One sheet sizes it at 6.00 ? 4.00 m, one storey | Section 9 |
| 18 | Waste point, and also the fence (`hasar`) � the note uses 18 twice | Fence and retaining wall are section 25, the second-largest block of the bill, about 0.46 million AZN of line value |
| � | Two-seat toilet (`2 yerlik ayaqyolu`) | Section 16 |
| � | Roads, pavements, vertical grading, landscaping, external lighting, site water and sewer, 0.4 kV network, site fire-alarm cable, site CCTV | Sections 5, 7, 8, 17�23, 27 |

The official composition of the design, copied from the general note, is the checklist the platform should expect on every future job:

1. Explanatory note
2. Working drawings: master plan and architecture; structures; power supply; water and sewerage; heating, ventilation and air conditioning; technology; heating point, heat mechanics, internal gas and automation; fire alarm, communications and CCTV; construction organisation; ecology
3. Estimate documents: local estimates, object estimate, summary estimate

This drop has almost all of the drawings and notes for order 9335. It does **not** include the official norm-based estimates (`smeta`) for 9335. Those are replaced here by the commercial bill `BOQ-Hadrut`. The only official smeta in the drop is order 9526 (external power).

---

## 2. Two different �quantity and price� documents

These must not be merged into one template.

### `data/BOQ-Hadrut.xlsx` and `data/BOQ-Hadrut.pdf`

Same document. One Excel sheet named `BOQ`, 2,342 rows, and a 63-page PDF print of it.

It is a **contract bill of quantities and interim payment certificate** (the sheet says PPC / `AKT`), bilingual, in manat. It is the target shape of the platform�s output for this client.

Columns:

- BOQ number
- Description (`??in ad?`)
- Unit (`?l?? vahidi`)
- Quantity (`H?cmi`)
- Unit rate in AZN
- Line total in AZN
- Progress to date, previous period, and this month (quantity and amount). All progress cells in this file are zero, so this copy is the tender / contract bill, not a filled monthly certificate

How the codes are built: `2.3` means building 2 (the fire station), trade 3 (reinforced-concrete frame). Item numbers restart at 1 inside each subsection.

Trades repeat for almost every building, in this order where they apply:

earthworks, foundations, reinforced concrete, walls and partitions, roof, doors and windows, floors, internal finishes, external finishes, then building services (water, sewer, heating, ventilation, cooling, power, lighting, fire alarm, CCTV, communications, technology).

Units actually used, and how often:

| Unit | Meaning | Item count |
|---|---|---|
| `?d?d` | number / each | 728 |
| `m` | metre | 399 |
| `m?` (stored as `m3` or `m(3)`) | cubic metre | 370 |
| `m?` (stored as `m2` or `m(2)`) | square metre | 357 |
| `ton` | tonne | 241 |
| `d?st` | set | 56 |
| `km` | kilometre | 10 |
| `kg` | kilogram | 8 |
| `pagon metr`, `p/m` | linear metre, same thing as `m`, written three ways | 5 |

Line value by bill section (sum of line totals, not the 3.81 million header):

| Code | Content | AZN |
|---|---|---|
| 1 | Demolition of existing buildings (`s?k?nt?`) | 68,439 |
| 2 | 4-bay fire station, all trades | 1,840,646 |
| 3 | Guard room | 7,897 |
| 4 | Tower | 140,808 |
| 5 | 0.4 kV site network | 22,734 |
| 6 | Diesel generator | 21,850 |
| 7 | Site fire-alarm cable | 3,785 |
| 8 | Site CCTV | 14,923 |
| 9 | Heating point, boiler, gas, heating pipes | 81,116 |
| 10�11 | Two 81 m? fire tanks | 19,875 each |
| 12�13 | Two 27 m? drinking tanks | about 10,430 each |
| 14 | Pump station | 37,007 |
| 15 | Vehicle wash | 13,063 |
| 16 | Two-seat toilet | 10,582 |
| 17 | Site-wide water and domestic sewer materials | 30,052 |
| 18 | Vertical grading (`?aquli planla?d?rma`) | 88,623 |
| 19 | Internal asphalt roads, stated area 383.7 m? | 17,223 |
| 20 | External asphalt roads, stated area 216 m? | 7,799 |
| 21 | Reinforced-concrete roads, stated area 1,021 m? | 77,544 |
| 22 | Pavements and yards, stated area 1,437.8 m? | 29,032 |
| 23 | Landscaping | 51,890 |
| 24 | Sand pit | 3,049 |
| 25 | Retaining walls and stone fence | 463,713 |
| 26 | Gazebo | 11,399 |
| 27 | External lighting | 6,717 |

The wording of the work items is the wording of Azerbaijani construction norms: excavator bucket size, soil group, haul distance, footing width, reinforcement class, wall thickness. Example from the fire-station foundations: gravel base 544 m?, blinding concrete 67.66 m?, strip footings up to 1,000 mm wide 279.74 m?, class A-I reinforcement 4.783 t, class A-III 14.262 t. A platform that only outputs �concrete� and �steel� is not enough. It has to output the **same norm sentence and the same unit**.

Excel damaged some codes. `2.10`, `2.20`, `2.30`, `3.10`, `4.10`, `9.10` and `14.10` were stored as numbers, so `2.10` became `2.1` and now collides with the real section 2.1. Store BOQ codes as text.

### `Hadrut Xocavend transform 9526/SMETA.pdf`

This is the other pricing system: the **official Azerbaijani estimate** (`smeta s?n?dl?ri`).

- 39 pages, scanned, no text layer
- Order **9526**, year 2026
- Scope is only **external power supply** of the same Hadrut fire station: 1?250 kVA, 35/0.4 kV transformer substation, the 35 kV cable, and landscaping of that work
- Price base: current estimate norms in force on **1 September 2022**
- Summary estimate: **436.712 thousand manat** (436,712 AZN), of which 0.4 thousand is unforeseen
- Chapter 4 (energy) is the only filled chapter on the summary sheet that was read: substation 267.168 thousand, 35 kV cable 67.721 thousand, landscaping 4.785 thousand. Columns split cost into construction works, installation works, equipment, and other costs

The platform needs both outputs later: a norm smeta in thousand manat for state approval, and a unit-rate bill in manat for the contractor. Drawings feed both. The rate library is different.

---

## 3. Drawing marks used on the title blocks

These abbreviations are consistent on the sheets that were read. Future uploads should be classified by the stamp, not by the folder name. Folder names are messy. Stamps are not.

| Mark | Meaning | What a quantity system reads from it |
|---|---|---|
| BP | `Ba? plan`, master plan | Building positions, road and pavement areas, fence lines, greenery |
| MH | `Memarl?q h?lli`, architecture | Plans, sections, elevations, room heights, floor build-ups, door and window schedules, finish schedules |
| DK | `D?mir-beton konstruksiyalar`, reinforced concrete | Footings, columns, slabs, tanks, bar bending schedules, concrete and steel quantities already totalled as `material s?rfi` |
| SK | `Su-kanalizasiya sisteml?ri`, water and sewerage | Pipe runs, diameters, fixtures, manholes. System codes in the bill: S0 cold/general water, ?S3/?S4 hot and circulation, K1 domestic sewer, K1T pumped domestic sewer, K3 process sewer, K3T pumped process sewer |
| ?V | `?stilik-ventilyasiya`, heating and ventilation | Radiators, pipework, fans, ducts. The note�s fan schedule is a ready takeoff (see below) |
| E, EE, E?A | Electrical. E?A is the mark printed on the lighting and small-power sheets. EE is the external 0.4 kV and lighting set | Cable schedules, luminaire counts, board schedules. Several sheets are already titled `Avadanl?qlar?n t?snifat?` and list mark, name, quantity, unit |
| RI | `Rabit? v? i?ar?verm?`, communications and signalling | Named on the depot sheet index. No separate folder in this drop |
| TX | `Texnologiya`, process equipment of the fire station | Named on the sheet index and present as bill sections 2.30 and 2.31. No separate drawing folder found |
| YS | `Yan??n siqnalizasiyas?`, fire alarm | Named on the sheet index and present in the bill |
| EYS, ET, YS | Cover title of the 9526 electrical volume: �power supply and low-current systems� | Do not split this filename into three guessed expansions. The cover itself says the volume is power supply and low-current systems for the 35/0.4 kV substation |
| MT | Seen on the guard-room roof sheet (`9335-08-MT`) | Roof plan, rafter plan, timber schedule. Treat MT as the architectural/structural roof sheet of that small building |
| POS / TTL | Construction organisation. POS is the Russian abbreviation, TTL is the Azerbaijani name (`Tikintinin T??kili Layih?si`) | Methods, duration, plant, temporary fence length. Weak source of permanent quantities, strong source of preliminaries |
| KTM / KTY | Package transformer substation, 250 kVA | One object, two spellings |

Sheet numbering is `order�building�mark`, for example `9335-01-MH` (architecture of the depot) and `9335-6-MH` (architecture of the tower). `9335-00-BP` is the master plan.

---

## 4. File by file

Ignore these. They are not design content:

- `data/Hadrut DEPO.zip` � the same folder packed again, about 182 MB
- every `.bak` � AutoCAD backup of the `.dwg` beside it
- `~$Titul.doc` � Word lock file, not a document
- every `plot.log` and `hardcopy.log` � AutoCAD plot logs

Drawings were saved from AutoCAD, including Architectural Desktop 2007. Master-plan, vertical-grading and construction-site drawings contain Civil 3D objects (surfaces, alignments, section labels). The transformer calculation file is **LIRA-SAPR 2013**.

### `data/` (next to the zip)

| File | What it is |
|---|---|
| `BOQ-Hadrut.xlsx` | The priced bill described in section 2. This is the answer key for the platform |
| `BOQ-Hadrut.pdf` | 63-page print of the same bill. Text extracts cleanly |

### `Hadrut DEPO/9335/` � plotted working drawings of the small buildings and the depot architecture

These PDFs have a real text layer, except the tower file. Text is Azerbaijani, sometimes with broken CAD-font encoding, so a vision read of the sheet is safer than raw PDF text.

| File | Pages | What it contains |
|---|---|---|
| `9335 MH.pdf` | 24 | Architectural volume of the **4-bay depot**, order 9335, Baku 2024. Cover plus sheet index. The index lists general data, basement plan, first-floor plan, second-floor plan, sections 1-1 and 2-2, elevations, attic plan, roof plan, roof-element schedule, roof hatch, roof railing, roof windows, floor specification, door and window schedule, partition schedule, and insulation fixings on the elevations. This is the main architectural quantity source for section 2 of the bill |
| `9335 n?zar?t?i ota??.pdf` | 11 | Guard room. General data, plan, elevations, section, floor and finish schedule, door and window schedule. Roof sheet `9335-08-MT` has a **ready timber takeoff**: rafter sizes, piece counts, volume per member, metal tile area 9.6 m?, timber total 0.23 m?, PVC gutter 12.8 m, two downpipes of 3.3 m |
| `9335 Q?ll?.pdf` | 12 | Tower architecture. First pages did not yield text (treated as drawn sheets). The general-data sheet that was read gives climate, masonry, roof, and the area/volume box quoted above, plus the project-wide sheet-mark list |
| `9335 su nasos stansiyas?.pdf` | 11 | Pump-station architecture: plans, section, elevations. General notes on climate, masonry category II, R = 120 kPa |
| `9335 ?ST?L?K M?NT?Q?S?.pdf` | 9 | Heating-point architecture: general data, plan, section 1-1, elevations, details 1�3 |
| `9335 2 yerlik ayaqyolu.pdf` | 9 | Two-seat toilet. General data, plan, section, elevations, foundation plan, section, strip footing Mlb-1 and detail D-1 with reinforcement. Notes say the drawings are for seismic 8, strip footing 500 ? 400 mm |
| `Xocavend Yangin su anbari.pdf` | 7 | Fire-water tank, structural set DK. Layout, sections, base-slab reinforcement and material total, roof-slab reinforcement and material total, wall Md-1 reinforcement and material total, vent pipe H-1, chamber K-1 |
| `Xocavend yangi ve icmeli su anbari .pdf` | 7 | Drinking and fire-protection tank, same kind of DK set: layout, sections, reinforcement and material totals |
| `KTY-250kVA- Xocav?nd.pdf` | 7 | Package substation KTM-250 kVA, mark `9335-7-E?A`. Same plot also sits in the Elektrik folder |

### `Hadrut DEPO/9335-SK Xocav?nd r Hadrud q YD/` � water and sewerage DWGs

SK on the stamp means water and sewerage, and the text recovered from these files matches that (sanitaryware, polyethylene pressure pipe, domestic sewer K1, welded steel water pipe). Native AutoCAD. PDF text extraction from DWG is the wrong tool; these need a DWG reader.

| File | What it is |
|---|---|
| `9335-0-XSK  Xocav?nd  Ba? plan.dwg` | Site plan of the utilities. Civil 3D / Architectural Desktop objects |
| `9335-1-SK Xocav?nd depo 2-ci variant.dwg` | Depot water and sewerage, second variant. Largest file in the set, about 23 MB. Contains sanitary fixtures and pressure pipe |
| `9335-2-SK ?stilik m?nt?q?si.dwg` | Heating-point pipework. Welded steel pipe |
| `9335-3,3a-SK-81m?  Yan??n su anbar?..dwg` | Pipework of the two 81 m? fire tanks |
| `9335-4-SK SU NASOS STANS?YASI.dwg` | Pump-station water/sewer, including the drinking and fire systems |
| `9335-5,5a -SK ??m?li v? yan??n ?leyhin? su anbar? V= 27m?.dwg` | Pipework of the 27 m? tanks |
| `9335-6-SK Xocav?nd  Q?LL?.dwg` | Tower water/sewer. The bill only has a short process-sewer subsection here |
| `9335-9- SK - Xocav?nd  AVTOYUMA.dwg` | Vehicle-wash water and process sewer |
| `9335-13 -SK-2 yerlik ayaqyolu.dwg` | Toilet water supply and domestic sewer K1 |

There is no SK file in this folder for the guard room. Its plumbing is either inside another drawing or was not sent.

### `Hadrut DEPO/Xocavend dk/` � reinforced-concrete DWGs, one file per structure

DK = reinforced concrete. These are the native files behind the tank PDFs and the structural part of the bill (concrete m?, reinforcement tonnes, formwork).

| File | Structure |
|---|---|
| `9335 Xocavend yangin deposu dk son.dwg` | Main fire station, final (`son`). About 10 MB |
| `9335 Xocevend-telim qullesi dk.dwg` | Drill tower |
| `9335 Xocavend istilik menteqesi.dwg` | Heating point. About 21 MB |
| `9335 Xocavend su nasos stansiyasi dk.dwg` | Pump station |
| `9335 Xocevend yangin su anbari dk.dwg` | Fire-water tank |
| `9335 Xocavend icmeli su anbari dk.dwg` | Drinking-water tank |
| `9335 Xocavend nezaretci otagi dk.dwg` | Guard room |
| `9335 Xocav?nd ayaqyolu dk.dwg` | Toilet |
| `9335 Xocavend avtoyuma dk.dwg` | Vehicle wash |
| `9335 Xocavend sohbetgah dk.dwg` | Gazebo |
| `9335 Xocavend generator altliq dk.dwg` | Generator plinth |
| `9335 Xocavend transformator altliq dk.dwg` | Transformer plinth |
| `9335 Xocavend istinad divari ve hasar dk.dwg` | Retaining wall and fence. About 20 MB. This is the drawing behind the second-largest bill section |

### `Hadrut DEPO/Depo  Hadrut BP/` � master plan and vertical grading

| File | What it is |
|---|---|
| `9335 Xocav?nd  rayon   DYNX.dwg` | Site layout drawing, Civil 3D (parcels, alignments, section labels). The letters DYNX are not spelled out on a sheet that could be read. It sits in the master-plan folder next to the vertical-grading model, and a second copy is in the external-works folder |
| `9335 Xocav?nd  rayon  Vertikalka.dwg` | Vertical planning (`?aquli planla?d?rma`): proposed levels, cut and fill. This is the source of bill section 18. Because it is Civil 3D, volumes should be read from the surface, not traced off a PDF |

### `Hadrut DEPO/YRS - VM - Xocav?nd/` � external works and networks

The folder name is not expanded in the files. Contents are external civil and mechanical networks. `(SON)` means final.

| File | What it is |
|---|---|
| `YRS - VN -9335 hadrut xocevend (SON).dwg` | Final combined external-works drawing, about 26 MB. Largest DWG in the drop |
| `YRS - VM - XOCAVEND-N?ZAR?T.dwg` | A supervision / record copy (`n?zar?t`) of the same kind of drawing |
| `9335-0- Xocav?nd  rayon   DYNX.dwg` | Another copy of the Civil 3D site layout |
| `Xocav?nd AQ.dwg` | Site drawing that labels the existing fence and designed work. AQ is not spelled out in extractable text. Landscaping and fence geometry are the likely content, and both exist as bill sections |
| `AK-  Xocav?nd Qazanxana v??stilik ??b?k?si.dwg` | Boiler house and heating network. Direct source for bill sections 9.16�9.19 (gas, boiler automation, heating-network pipes) |
| `TVM -0 - 9335 Xocav?nd  rayon  POS (TAPRQ).dwg` | Construction-site plan (POS), Civil 3D. Crane positions, temporary roads, storage. A near-copy is `9335 Xocav?nd  rayon   POS.dwg` in the notes folder |

### `Hadrut DEPO/Elektrik/` � electrical plots and one combined DWG

| File | What it is |
|---|---|
| `9335 hadrut xocevend elektrik.dwg` | Combined electrical model, about 2.5 MB |
| `0.4kV kabel x?tti v? XI/9335 EE.pdf` | External electrical, mark EE. General notes and the external-lighting plan. XI is external lighting (`xarici i??qlanma`), which the sheet title states in words |
| `0.4kV kabel x?tti v? XI/AT.pdf` | Equipment schedule of that set: already quantified. Examples read from the sheet: NYY 1 kV cable 3?95+1?50 mm?, PVC pipe ?100, smaller lighting cables 5?4, 4?4 and 3?4 mm?, with lengths in metres and counts in `?d?d` |
| `KTM/9335 KTM.pdf` | Same 7-page KTM-250 kVA set as `KTY-250kVA- Xocav?nd.pdf` |
| `Generator/1.pdf` | Generator plinth and specification. One diesel set EPR-50 kVA, 40 kW, 380 V, plus automatic panel, steel strip 40?4 and steel pipe ?100. CAD fonts on this page are Cyrillic and extract badly; read it visually |
| `Nasosxana/su nasos stansiyasi 9335.pdf` and `-AT.pdf` | Pump-station electrical, mark `9335-4-E?A`, plus its equipment schedule |
| `NBM/NBM 9335.pdf` and `AT.pdf` | Guard-room electrical, mark `9335-8-E?A`. The folder name NBM is the guard-room set, not a separate discipline |
| `q?lle/QULLE 9335.pdf` and `AT.pdf` | Tower lighting. The schedule already lists luminaire counts, cable lengths and switches. Stated installed power 1.0 kW |

Internal power, lighting, fire alarm, CCTV and data of the **main depot** are in the bill (sections 2.22�2.29) and are named on the architectural sheet index (E, RI, YS). They were not found as their own PDF volume in this drop. They are either inside the combined electrical DWG or were not sent.

### `Hadrut DEPO/9335 Xocav?nd  Hadrut Depo ?V/` � heating and ventilation calculations, plus one drawing

| File | What it is |
|---|---|
| `9335 -01- IV. Xocav?nd.dwg` | HVAC working drawing of the depot, mark ?V. About 2.4 MB. Pipe and duct geometry live here |
| `Xocav?nd depo son istilik itkil?ri.pdf` | Final heat-loss calculation. Areas of walls, windows, doors, floor and ceiling by orientation, with transmission losses. Useful as a cross-check of envelope areas, not as the bill itself |
| `Xocav?nd izolyasiya.pdf` | Insulation check. Required thermal resistance by element (wall, roof, attic, window) and layer thickness. Source for insulation thickness and area |
| `Enerji effektivliyi hesabat?.pdf` | Energy-performance calculation: design outdoor temperature, heating-season length, degree-days, indoor temperature |
| `Enerji sinfi.pdf` | One-page scale of energy classes A�E. A classification result, not a quantity |

A page of the general note already schedules the fans, which is the kind of table the platform should lift rather than redraw:

| System | Room | Unit | Duty |
|---|---|---|---|
| S1 | Sanitary rooms | K 200 L | 400 L/s |
| S2, S3 | Dining | OV 2E 200 | 300 L/s |
| S4 | Drying room | OV 2E 200 | 400 L/s |
| S5 | Showers | K 200 L | 375 L/s |
| S6 | Sanitary rooms | K 200 L | 350 L/s |
| S7, S8 | Garage | CT 315-4 | 3,000 L/s |

### `Hadrut DEPO/Xocav?nd DEPO DQT  Izahat Tikintinin t??kili/` � written volumes

DQT is not spelled out in the documents. The folder holds the narratives and the construction-organisation drawing.

| File | What it is |
|---|---|
| `9335 Depo Xocav?nd ?mumi ?zahat/?mumi ?ZAHAT.pdf` | **General explanatory note**, 56 pages, scanned (no text layer). Cover, contents, authors, then chapters that were read: initial data and the building list; master plan and grading, including road and pavement build-ups; architecture; structures; geology and foundation conditions; electrical load; ventilation schedule; a room-by-room design brief. This is the best single document for �what exists on the site� and for build-ups (layer thicknesses) |
| `9335 Depo Xocav?nd ?mumi ?zahat/T?TUL   t?TUL9335.doc` | Title-page file for that note. Same bytes as `T?TUL A4 � �����.doc` (a copy; the filename is Russian for �copy�) |
| `POS 9335.docx` | Construction organisation project, called TTL in the text, order 9335, Baku 2024. Site area, greenery, soil strength, seismic 8, structural description, duration **16.5 months** after coefficients, labour about 173,364 man-hours, about 58 workers, temporary buildings, plant list (excavators ��-2621 and ��-3322, bulldozer, cranes KB-3575A and MKQ-16, mixers), temporary fence **249.1 m** long and 2.0 m high. Preliminaries, not permanent work quantities |
| `EKALOG?YA -1. S?if 9335 Depo 4 ??x??l?.docx` | Ecology volume, order 9335. Legal basis, site, climate, geology, construction duration, impacts on soil, air (paint, welding, machinery), water, noise, solid and hazardous waste, landscaping, mitigation. Emissions accounting. Not a quantity source for the bill, except waste volumes if a preliminaries bill is added later |
| `9335 Xocav?nd  rayon   POS.dwg` | Drawing of the construction site plan. Backup `.bak` beside it |
| `Xocav?nd DQT.dwg` | Small drawing in this notes folder. Title text could not be recovered from the DWG. Keep it with the written set until it is opened in CAD |
| `Geologiya Xocav?nd/Titul.doc` | Cover and contents of the engineering-geology report. Client: FHN Capital Construction. Boreholes, climate, lithology, hydrogeology, laboratory tables (compression, shear, gravel analysis), geological sections I�I to IV�IV |
| `Geologiya Xocav?nd/iqlim.doc` | Climate tables for the report: air temperature, humidity, rainfall, snow, icing. Mostly Cyrillic Azerbaijani |
| `Geologiya Xocav?nd/hesabat.doc` | The geology report itself. Boreholes 22.3�37.0 m apart. Topographic survey at 1:1000. Layer descriptions match the general note. Soil parameters quoted in the construction-organisation note: ? = 35�, c = 10 kg/cm?, E = 450 kg/cm?, ? = 1.92 g/cm?, R0 = 4.00 kg/cm?. Annual rainfall stated as 560 mm. These parameters choose the norm (soil group, foundation depth). They are not themselves bill quantities |

Road and pavement build-ups drawn in the general note, which turn an area into layer volumes:

- Pavement: asphalt 40 mm, gravel 100 mm, compacted subgrade
- Asphalt road: coarse asphalt 50 mm, fine asphalt 70 mm, crushed stone 150 mm, gravel 250 mm, compacted subgrade
- Reinforced-concrete road: asphalt 50 mm, asphalt 70 mm, concrete B15 with mesh, 150 mm, then crushed stone

The bill already states the areas (383.7, 216, 1,021 and 1,437.8 m?). Layer thickness ? area is the quantity of each course.

### `Hadrut DEPO/Hadrut Xocavend transform 9526/` � external power, a separate 2026 commission

All six PDFs are scans. They are the external electrical supply of the same fire station, not a second campus.

| File | Pages | What it is |
|---|---|---|
| `Izahat.pdf` | 18 | Explanatory note, order 9526, Baku 2026 |
| `BP.pdf` | 6 | Master plan of the transformer substation, 1?250 kVA, 35/0.4 kV |
| `MH.pdf` | 14 | Architecture of that substation |
| `DK.pdf` | 21 | Reinforced concrete of that substation |
| `EYS,ET,YS.pdf` | 37 | Power supply and low-current systems |
| `SMETA.pdf` | 39 | Official estimate, summary total 436.712 thousand manat. Described in section 2 |
| `Xocavend transformator.lir` | � | **LIRA-SAPR 2013** structural analysis model of the transformer structure. A calculation model, not a drawing and not a bill. Useful only to cross-check member sizes after the DK drawings are read |

---

## 5. Where each kind of measurement actually sits

An automatic bill should not �look at the project� in one pass. Each quantity has a best source. In this package the designer has already done a large part of the takeoff, inside schedules on the sheets.

| Quantity the bill needs | Best source in this drop | How it is measured |
|---|---|---|
| Door, window, luminaire, fan, pump, board, sanitaryware counts | Schedules already on MH, E?A, AT, ?V sheets (`t?snifat`, `avadanl?qlar?n t?snifat?`) | Read the table. Unit is `?d?d` or `d?st`. Do not count symbols on the plan unless the schedule is missing |
| Cable, pipe and gutter lengths | The same schedules, then the SK / EE / ?V drawings for anything not scheduled | Length in metres along the route, by diameter and system code (K1, S0, NYY 4?2.5, and so on) |
| Concrete volume and reinforcement tonnage | DK sheets, the `material s?rfi` tables next to each bar schedule | Sum by member mark (footing, column, slab, wall Md-1), then split reinforcement into A-I / A240 and A-III / A500C, because the bill prices them separately |
| Masonry area | MH plans and elevations, wall thickness from the note (400 mm limestone, 200 and 500 mm concrete walls) | Length ? height minus openings. The bill�s unit for the limestone basement wall is m?, not m? |
| Floor and finish areas | Floor specification (`d???m?l?rin eksplikasiyas?`) on the MH sheets | Area by floor type. The bill splits types (laminate, ceramic, concrete, screed) |
| Roof | Roof plan plus the timber / tile schedule, as on the guard-room sheet | Plan area, slope factor, and the piece schedule for timber |
| Excavation | DK sections (depth and width of footings and tanks) and the Civil 3D vertical-grading surface | Footing trench volume is separate from site cut-and-fill. The bill also splits machine excavation, hand excavation, haul in tonnes, backfill and compaction |
| Roads and pavements | Master plan for areas, general note for layer thicknesses | Area is given in the bill already. Each course is area ? thickness |
| Retaining wall and fence | `istinad divari ve hasar dk.dwg` | Length by segment. The bill is split into stretches B�C, F�G and G�A, so the drawing�s lettered grid has to be kept |
| Earthworks soil group, haul, winter and seismic coefficients | Geology report and the norm, not the drawing | Drawing gives m?. The norm sentence (�soil group 1�, �haul 5 km�) comes from the report and the client�s rate library |
| Demolition, section 1 | Not found as a measured drawing | 7,625.4 m? of masonry demolition and 2,501 t of rubble are in the bill, and the construction note says existing buildings on the south-west and north of the site are to be removed. This quantity needs a survey or an existing-buildings drawing that is not in the drop |
| Technology equipment, CCTV, telephone, public address | Bill sections exist. A matching drawn volume was not found as its own file | Do not invent counts. Flag the section as �rate list present, drawing not in the package� |
| Prices | Nowhere in the geometry | Unit rates are commercial. The 9526 smeta uses the September 2022 norm price base and splits construction / installation / equipment. The platform measures; a rate library prices |

---

## 6. How the platform should work on this material

### Step 1. Classify every file before reading it

Use the title block, not the folder.

- Order number: 9335 or 9526
- Building mark: 01 depot, 6 tower, 7 or 8 guard room, and the master-plan `m?vqe` number
- Discipline mark: BP, MH, DK, SK, ?V, E / EE / E?A, RI, TX, YS, POS
- Document class: drawing, schedule sheet, calculation, narrative, smeta, contract bill, analysis model, junk (bak, log, zip, lock file)

Azerbaijani and Russian abbreviations should be a fixed dictionary inside the product. The list in section 3 is the start of that dictionary.

### Step 2. Read drawings with the right tool

Three different situations are in this drop:

1. **DWG with real geometry**, including Civil 3D surfaces on the site model. This is the source for lengths, areas and cut/fill. Open the DWG (ODA / RealDWG / a Civil 3D export to LandXML for the surfaces). Do not measure the PDF plot of the same drawing.
2. **PDF plots with a text layer** (most of folder `9335` and `Elektrik`). Schedules can be parsed. Many dimension texts use SHX fonts and come out as the wrong alphabet. When the extracted string is nonsense, read the sheet as an image.
3. **Scanned PDFs with no text** � the 56-page general note, the whole 9526 set, and parts of the tower set. These need a vision model that can read Azerbaijani Latin and Cyrillic, including stamps and rotated title blocks.

Dimension text and geometry must be checked against each other. On these sheets a length is often a written dimension, not a polyline drawn to scale, and details are drawn out of scale next to a scaled plan.

### Step 3. Prefer the schedule over the geometry

For this institute the sheet is already a mini bill of quantities. The guard-room roof table and the electrical AT sheets are the pattern: mark, name, size, count, unit, total. The first model should be a schedule extractor. Geometry measurement is the fallback for walls, slabs, trenches, roads and fences, where the schedule does not exist.

### Step 4. Compute quantities with the norm�s unit, not with a generic unit

The existing bill shows the rules the model has to learn:

- Concrete in m? and reinforcement in tonnes, on separate lines, by class
- Limestone wall in m? at a stated thickness, not in m?
- Excavation split into machine, hand, haul (tonnes, distance stated), disposal, backfill, compaction
- Pipes split by system code and by �supply and lay� versus material
- Repeated buildings (two identical 81 m? tanks, two 27 m? tanks) are copied as separate sections with the same quantities. The model should detect the copy, not measure twice and then average

### Step 5. Map the result onto the client�s bill structure

The 132 subsections of `BOQ-Hadrut.xlsx` are the work-breakdown structure. A new project of this client should come out as:

`building ? trade ? norm line ? unit ? quantity ? rate ? amount`

and, for state submission, the same quantities regrouped into a smeta by object chapter (site preparation, main buildings, services, external networks, landscaping), with construction / installation / equipment split, in thousand manat.

The rate is a lookup. This file is the first rate library: about 2,000 priced sentences. Matching must be on the norm meaning (excavator 0.5 m?, soil group 1, haul 5 km), not on fuzzy equality of the whole sentence, because the same sentence is reused for every building.

### Step 6. Keep a human check on the lines that move money

On this project the fire-station fabric and the retaining wall are about three quarters of the line value. Those two, plus vertical grading and the tower, are where a wrong m? matters. Door counts and luminaire counts are worth automating fully because the schedule is explicit and the money per line is small.

Anything the model cannot tie to a sheet should stay as an open item: demolition, the barrier, the running track, and the depot low-current systems whose drawings were not in the drop.

---

## 7. Conflicts the platform must surface, not silently pick

These were found by reading the note against the drawings. They are normal in a multi-year design package, and they will break a naive extractor.

- **Seismic intensity.** Structures chapter, geology and the construction note: 8 points. Architecture chapter: 9 points, and that chapter names **Z?ngilan**, which is a different district. That architecture passage was copied from another fire-station job.
- **Datum of level 0.000.** Structures chapter: absolute level **694.70 m**. Tower sheet: **694.40**. Architecture chapter: **408.80**, in the same copied passage. Do not mix them when computing excavation depth.
- **Substation voltage and size.** 2024 general note: demand 142 kW, adopted KTY-250 kVA, **10/0.4 kV**, and a heading that still says KTY-160. 2026 order 9526: **1?250 kVA, 35/0.4 kV**, with its own smeta of 436.712 thousand manat. The 2026 set is the one that matches a built substation. The 2024 sentence is stale.
- **Floor areas.** Page 6 of the note: basement 1,360.20 m?, first floor 1,395.80 m?. A later brief page: total area 3,672.10 m?, construction area 1,612.70 m?, volume 18,570.40 m?, and it uses the acronym DYMX. Treat the later page as a design brief until it is checked against the MH floor plans.
- **Bill header versus line sum.** 3,811,193.36 AZN on the cover, about 3,110,506 AZN if the work lines are added. Both numbers are in the file. The difference has to be explained (overheads, a missing summary, or cells that did not land in the amount column) before either is called the contract sum.
- **Broken section numbers** in Excel, described in section 2. `2.10` stored as `2.1`.
- **Duplicate files.** The zip repeats the folder. KTM PDF is stored twice. DYNX and the POS drawing each appear in two folders. Title-page DOC is stored twice. A classifier should hash files and keep one.
- **Two price systems** for one site: the manat unit-rate bill for 9335, and the thousand-manat norm smeta for 9526 only. There is no 9335 smeta in the drop.

---

## 8. What is realistic to automate first

From this package, in order:

1. **Ingest and file register.** Every future upload gets the classification in section 6, in Azerbaijani and English. This drop is the test: the register should reproduce section 4 without a person renaming files.
2. **Schedule reader.** AT sheets, door/window schedules, fan tables, reinforcement `material s?rfi`, roof timber tables. These already are quantities. Accuracy on this project can be scored against `BOQ-Hadrut.xlsx`.
3. **Geometry takeoff from DWG** for the things schedules do not give: wall lengths, slab areas, trench volumes, fence lengths, road areas. Check them against the areas already written in the bill (roads 383.7 / 216 / 1,021 m?, pavements 1,437.8 m?, tower 65.20 / 127.14 m?).
4. **Civil 3D surface** for cut and fill, checked against bill section 18.
5. **Norm matcher** that turns those quantities into lines written like the existing bill, then applies the rates already in the bill.
6. **Smeta exporter** only after the quantities are trusted, using 9526 as the format example. Do not train the smeta layout on the Excel bill; the columns are different.

One project is enough to build the pipeline and to measure accuracy. It is not enough to trust unattended output. The comparison set is this bill: 2,176 lines, known quantities, known rates. The useful score is not �a number was produced�. It is �the same norm line, the same unit, quantity within a stated tolerance, and every line that has no drawing left open�.
