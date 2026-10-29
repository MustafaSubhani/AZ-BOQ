# Hadrut demo, 10 minutes

Start: `.\run-demo.ps1` (opens http://127.0.0.1:8780). Everything runs from `cache/`, with no network.
Before the meeting: run `.\run-demo.ps1 -Rebuild` once if anything in `data/` or `backend/demo_rules/` changed, and check `HARDCODED.md` (for you, not for the audience).

## 1. Home (1 min)
- "This is the client's bill for the Hadrut fire station, checked against its own drawings."
- Contract card: the header 3,811,193.36 is reproduced to the cent from 2,175 lines (3,110,505.89, then 1.8%, 2%, −0.02, VAT 18%).
- The strip: 2 lines the drawings contradict, 136 backed by a drawing, 629 that need a person, 1,408 with no drawing evidence.

## 2. A real discrepancy (2 min)
- Click **Different from drawings**, then line **4.12.5**.
- Bill says 6 manual call points for the tower; the equipment schedule on sheet 9335-6-YS lists 5.
- Point at the source card: the drawing text was stored in a legacy Cyrillic-slot font ("Ял иля хябярверичи") and is shown decoded ("Əl ilə xəbərverici").
- The viewer opens the real sheet, rendered from the DWG through ODA, with the row circled.

## 3. How a number is earned (2 min)
- **Takeoff**, "Depot long side": 45.2004 m from 63 dimensions on the (SON).dwg plan, confirmed by the 45200 text in 9335 MH.pdf. The depot gate (45.2 × 34.6) passes, so the file is trusted.
- "Basement storey height" 2.7 m: floor marks −2.700 on the plan, confirmed by a section dimension. Scroll to **Looked at and rejected**: −2.45 and −2.75 were seen and refused because no section confirms them.
- "Basement limestone wall area" is **Blocked**: wall length has no measurement yet, so there is no number, and bill line 2.4.1 says Blocked instead of guessing.

## 4. Where documents disagree (1 min)
- **Conflicts**: seismic 8 vs 9 points (the 9 comes from a passage naming Zəngilan, copied from another project), datum 694.70 / 694.40 / 408.80, basement area 1360.80 vs 1360.20. Both sides are kept with their sources; a suggestion is shown, not applied.

## 5. What the package covers (1 min)
- **Coverage**: bill value by building and trade. 96% of the value has a drawing of its building and trade; the red cells have nothing in the package.
- **Drawings**: 34 DWGs, 23 vector PDFs, scans. 9 DWGs where the second reader (LibreDWG) disagrees with ODA; their values go to review.

## 6. Language (30 s)
- Toggle **EN / AZ / Both**. Hover any English text to see the Azerbaijani original. The Azerbaijani is what the check uses; English is for reading.
- Search the bill for "sokuntu": Azerbaijani letters fold, so it finds "Söküntü işləri".

## 7. Exports (1.5 min)
- **Report → Exports**: the client's own workbook with the check filled in (0 cell styles changed, 2 quantities changed, the header moves by 42.50), the discrepancy report in Excel and PDF, and a bill generated from our own lines in the client's layout.
- Open `BOQ-Hadrut-checked.xlsx`: it opens with no external-link prompts.

## 8. Next (30 s)
- **Operations**: the drawing register and the contract bill are seeded from this package. Materials, measurements and invoices are empty because the package has none; the fraud checks that need them say so.

## If asked
- "Is anything typed in by hand?" Yes, a few values a person read from a scanned note, each with its page; they show as "Project rule", never as measured.
- "Why are many lines 'Not on drawings'?" Most are trades with no drawing in the package, or quantities not printed anywhere; Coverage shows which.
- "Can it read the scans?" The vision reader is built and review-only; it needs an OpenAI key on this machine.
