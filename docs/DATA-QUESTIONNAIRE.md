# Requirements questions for the Hadrut check

Answer in plain words. If a document does not exist, write **None**. The check will not invent a quantity, a rate, or a missing file.

There are 20 questions. Each one is a decision. The note under it is the rule the software uses today, so you can correct it.

## What is already in the platform

The check compares the Hadrut drawings with the client bill for order 9335.

The bill file is `BOQ-Hadrut.xlsx`. It has 2,175 priced work lines. Each line has a code, a description, a unit, a quantity, a unit rate in manat, and an amount. The rate is stored. It is used only to turn a quantity difference into money. The rate is not compared with a price book.

The sheet header is rebuilt from the work lines as follows: sum of the line amounts, then 1.8 percent for temporary buildings, then 2 percent contingency on that new sum, then minus 0.02, then 18 percent VAT. That chain reproduces the header of 3,811,193.36 manat. Progress columns on this copy are zero.

Tables printed on the drawings already give some quantities. They include door and window marks, room areas, floor layers, and concrete and steel totals marked as material consumption (`material sərfi`). Those tables name a material and a quantity or a weight. They do not print a rate in manat.

A scan with no text is shown and is not measured. Two readers of the same DWG must agree before a value from that file is treated as settled. When two documents disagree, both numbers are kept. Nothing is averaged.

Materials received, monthly site measurements, and invoices have no rows. Those screens are empty on purpose.

Order 9526 has its own official estimate, `SMETA.pdf`, in thousand manat, on the price base of 1 September 2022. It is a different job and a different price layout from the Excel bill. The two are not merged.

The screens are Overview, Drawings, Takeoff, Bill, Report, Inputs ledger, Area book, Conflicts, Coverage, Translations, Run log, and the registers Drawing register, Contract bill, Materials, Measurements, Invoices, and Codes.

## A. Materials and rates

### 1. Is there a schedule that lists the materials of a work line, each with its own quantity and rate?

This is not the bill, and it is not the `material sərfi` table on a drawing. The bill has one rate for the whole work. The drawing table has quantities and no manat. The schedule we still need would sit under a work line and name each material, its quantity, its unit, and its rate.

If it exists, give the file name and the format (Excel, PDF with real text, or a scan). If it does not exist, write None.

Answer:

### 2. Copy one real row, and say how it finds the bill line

Write every column heading and the value in that row. Include material name, specification or class, unit, quantity, rate, and amount if those columns exist. Say whether the quantity is for one unit of the work, or for the whole bill line.

Then say how the row names its bill line. Use one of these only: the bill code, such as 2.2.4, the full work description, a drawing mark such as Md-1 or B25, or no link. If there is no code, the check will not guess which bill line the material belongs to.

Answer:

### 3. Does the bill line amount equal the sum of the material rows?

The bill rate is manat for one unit of the work. The line amount is that rate times the bill quantity. A material row has its own quantity, its own rate, and its own amount. Say which is true.

* The bill line amount must equal the sum of the material row amounts under it.
* The bill rate is a commercial price for the whole work, and it need not equal that sum.
* There is no material schedule, so only the bill rate and the bill amount exist.

Answer:

### 4. Where do the rates come from?

Name the book or the agreement: the rates already in `BOQ-Hadrut.xlsx`, a norm book, a dated price base, or a supplier quote. Say whether order 9335 has an official estimate in thousand manat. The 9526 estimate is already in the package and must stay a separate document.

Answer:

### 5. Labour, machines, and waste

Some bill lines name an excavator, a soil group, or a haul distance. The drawing shows the trench. It does not show which machine was chosen. Say if labour hours and machine hours are their own rows with rates, or if they stay inside the single bill rate.

Then say how waste is written: a percent, a separate row, or absent. Say which quantity the bill line must match: the drawing quantity before waste, or the schedule quantity after waste.

Answer:

## B. How a quantity is allowed to match

### 6. Confirm the area rule

The rule is to measure a floor, a wall, a road, or a pavement once. Where the bill already repeats that same quantity on the next lines, including a line that only adds an extra 5 mm or 1 mm, the check treats those lines as one measurement. It does not measure each layer again. A sloped roof sheet is not one of those repeats: the flat layers share one area, and the sheet is a separate area, stated at 1,660 m² and at 1,992 m². Confirm this, or name the lines that must be measured on their own. Other stated areas are internal asphalt 383.7 m², external asphalt 216 m², reinforced-concrete roads 1,021 m², pavements 1,437.8 m², and greenery 3,482.30 m².

Answer:

### 7. Confirm the match tolerances

A quantity copied from a schedule cell must match the bill at the number of decimals printed on that line. A quantity calculated from the drawing geometry must be within 1 percent of the measured figure. Rates, machine names, haul distance, and soil group are not scored. Say if the contract uses different tolerances. If you do not change them, these remain the rules.

Answer:

### 8. Steel, and the sets with no drawing

Drawing tables name a bar mark and a weight in kilograms. The bill prices class A-I and class A-III in tonnes, and the same sentence is used on many buildings. The check does not turn those kilograms into a bill quantity, because it does not have a count of each mark on the plan. If a schedule has that count, name the file and the columns. If it does not, steel weights stay off the bill quantity.

These sections also have no drawing of their own. For each, write a file name or None.

* Technology set TX, including furniture and loose equipment.
* Communications set RI.
* Fire alarm set YS, if it is not already inside a combined drawing.
* Demolition of the existing buildings, about 7,625.4 m³ of masonry and 2,501 t of rubble.

Answer:

### 9. Which drawing figure is compared when the package disagrees?

The bill quantity stays as printed. Both numbers are kept until you pick the drawing figure to compare. Do not average them.

* Seismic zone. Structural notes say 8 points. One architecture passage says 9 points and names Zəngilan.
* Level 0.000. Structural notes say 694.70 m. A tower sheet says 694.40 m. The same architecture passage says 408.80 m. Excavation depth uses 694.70 m until you say otherwise.
* Substation. The 2024 note says 10/0.4 kV. Order 9526 says 1×250 kVA at 35/0.4 kV. The 2026 set is the later document.
* Floor areas. The general note prints the basement as 1,360.20 m². The room schedule prints 1,360.80 m², and the rooms add to 1,371.8 m². The first floor prints 1,395.80 m², and the rooms add to 1,392.9 m². The second floor adds up exactly, at 779.00 m². The garage is 658.30 m² on the floor schedule, 665.3 m² on the finish schedule, and a hatch on the plan measures 659.39 m². A later brief page states a total area of 3,672.10 m².

Answer:

### 10. Confirm the money chain on the bill

The header of 3,811,193.36 manat is the work lines, then 1.8 percent temporary buildings, then 2 percent contingency, then minus 0.02, then 18 percent VAT. Write yes if that is the contract rule. If a percent is wrong, write the correct percent and what it is for.

Answer:

## C. Deliveries, measurements, and who may change a figure

### 11. Delivery notes

A delivery note is not the material schedule. It records what arrived on site. If you have notes, list the columns: date, supplier, material, quantity, unit, note number, and bill code. Say whether a delivered quantity above the bill line should be a warning or should block payment. Say whether the same note number written twice should be flagged. If you have no notes, write None.

Answer:

### 12. The contract, the monthly certificate, site measurements, and invoices

This copy of the bill has progress columns, and they are zero, so it is the contract and not a filled payment certificate. Write contract only, or say that a filled monthly certificate will be sent and which columns are that month's measured work.

A site measurement records how much of a bill line was done in a month. An invoice asks to be paid. If either exists, say what it points at: a bill code, a material row, or a month. Say whether an invoice higher than the measured work should be a warning or should block payment. If neither exists, write None. Those screens stay empty until the rows exist.

Answer:

### 13. Who may change a figure

Two different boxes exist. Do not treat them as the same action.

On the bill, a person may type a quantity only when the line is different, needs a person, or not on the drawings. A line that matches, is printed on a drawing, or is derived does not offer that box. The screen requires a name and a reason. The measured figure stays visible and can be restored. Accepting a review note records that the note was seen. It does not change the quantity.

On the area book, choosing a side means typing a number already printed on the card. A number that is not printed there is rejected. Conflicts keep both sides until that choice.

Say who may type a bill quantity. Say whether a rate may be changed the same way, or must stay as printed. Name the person who will check a sample of areas against the drawings. If the area book must accept a figure no document prints, say so. That is not allowed today.

Answer:

## D. One line that proves the screens

### 14. Give one complete example

Fill every field. Leave a field blank only if that document does not exist.

* Bill code and the work description.
* Unit, bill quantity, bill rate, bill amount.
* Each material under that line: name, unit, quantity, rate, amount.
* The drawing file and the sheet the quantity was read from, and the exact text on that sheet.
* The delivery quantity and the invoice quantity, if those documents exist.

Answer:

### 15. What must agree before you trust that line?

Say which of these must agree, and which may differ without failing the check: the drawing quantity, the bill quantity, the material schedule quantity, the bill rate, the material rates, the delivered quantity, and the invoiced quantity.

Answer:

## E. The other screens

### 16. Overview and drawings

Overview shows how many lines contradict the drawings, the share of bill money a drawing confirms, four steps from the drawings to the export files, and the lines that need a person. Who is this page for: the person checking quantities, a manager who only reads the counts, or both?

Drawings lists every file, how it was read, and the sheets inside it. Opening a sheet shows the picture and the text the check read. A person can mark that text on the sheet. The check does not let a person draw a new area. Say whether a new issue replaces the old file, or both stay and the later one is the source. Backup files, plot logs, and the zip of the same folder are dropped. Confirm that, or name a file of that kind that must be kept.

Answer:

### 17. Takeoff and the bill

Takeoff lists the quantities taken from the drawings, with the formula, the inputs, and the sheet for each input. A person does not type over a measured item. A change is made on the bill, and the measured figure stays. Confirm this. If the measured item itself must be editable, say who, and say that the original figure must remain visible.

The bill shows 2,175 lines. A line is one of: matches, printed on a drawing, derived from another line, different, needs a person, blocked because an input is missing, or not on the drawings. Which of these results must be in the file you hand to someone else? Name any result you do not want shown outside the check.

Answer:

### 18. Report, coverage, translations, and the run log

Eight files can be downloaded: the bill by floor, the client bill with the check added, a bill built from the measured items, and the discrepancy report, each as Excel and as PDF. The client bill's own quantities are not rewritten. Steel is listed by family and is not added into a bill quantity. Which of these eight is the file you hand over? Name any file you need that is not in that list.

Coverage shows how much bill money has a drawing, a PDF only, a scan only, or nothing, by building and trade. A cell marked nothing means this package has no drawing for that building and trade. Is this page part of the handover, or only for the person running the check? Name any nothing cell that is a file you still have, and any that is correctly empty.

English is for reading. Azerbaijani is the text the check uses. Say who may correct English. The Azerbaijani source does not change. The run log lists every warning. Say whether those warnings stay on the check screen only, or must also be in the handover file.

Answer:

### 19. Registers and codes

The drawing register and the contract bill are the same package and the same bill, listed so a later check can start from them. Codes are the section codes, units, buildings, and trades already on the bill. A unit the bill uses that the check does not recognise is marked on that line. Subsection codes that Excel stored as numbers, so that 2.10 became 2.1, are repaired from their position. Name any unit, building, or trade that is missing. If the lists are complete, write None.

Answer:

### 20. Departments that are not built

Question 18 is about the check's own downloads. This question is not. The platform does not include a programme of works, quality forms, safety records, a project handover dossier, or an organisation chart. Those stay out until you ask for one. Name any you need next, and the file that would fill it. If none are needed for this job, write None.

Answer:

## Send with the answers

* The material and rate schedule from question 1, if it exists.
* The official estimate for order 9335, if it exists. Do not send the 9526 estimate again.
* The steel mark count from question 8, if it exists.
* Any drawing named in question 8.
* One delivery note, one month of measurements, and one invoice, if they exist. Cover any price you do not want stored. The check needs the quantity, the unit, the rate, the date, and the bill code.

Azerbaijani is the source of the check. English on screen is for reading only. A scan can be displayed. A quantity or a rate is taken only from Excel or from a PDF that contains real text.
