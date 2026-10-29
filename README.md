# AZ-BOQ: Hadrut drawing-to-bill check

Checks the client's bill of quantities for the Hadrut fire station (order 9335) against its own drawings, and shows every number with the sheet it came from.

- `backend/`: Python pipeline and FastAPI (`python -m azboq ...`), rules in `backend/demo_rules/`, tests in `backend/tests/`
- `frontend/`: React + Vite app (built copy in `frontend/dist/`)
- `cache/`: everything the pipeline derived (sheet dumps, tiles, number index, SQLite stage store, exports)
- `DEMO-SCRIPT.md`: the 10-minute walkthrough; `HARDCODED.md`: values entered by hand and known gaps

## Run the demo from the cache

```powershell
pip install -r backend/requirements.txt
.\run-demo.ps1            # http://127.0.0.1:8780
```

## Not in this repository

- `data/`: the raw client package (DWG, PDF, BOQ-Hadrut.xlsx). Put it back under `data/` to re-run the pipeline or the exports.
- Five DXF files over 100 MB in `cache/dxf/`. Regenerate with `python -m azboq convert` (needs ODA).
- ODA File Converter: install it and copy it into `tools/oda/`. Its licence does not allow redistribution.
- `node_modules/`: run `npm install` in `frontend/` and `tools/libredwg/`.

Full rebuild once `data/` and ODA are present: `.\run-demo.ps1 -Rebuild`.
