// Second reader. One DWG per process: LibreDWG leaks state between files and
// crashed reading a second file in the same process on this package.
// Writes per-layer, per-type counts of top-level entities as JSON.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { LibreDwg, Dwg_File_Type } from "@mlightcad/libredwg-web";

const here = dirname(fileURLToPath(import.meta.url));
const wasmDir = join(here, "node_modules", "@mlightcad", "libredwg-web", "wasm").replaceAll("\\", "/");
const [src, out] = process.argv.slice(2);
const row = { source: src };
try {
  const lib = await LibreDwg.create(wasmDir);
  const b = readFileSync(src);
  const ptr = lib.dwg_read_data(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), Dwg_File_Type.DWG);
  if (!ptr) {
    row.status = "read_failed";
  } else {
    const { database, stats } = lib.convertEx(ptr);
    const counts = {};
    let total = 0;
    for (const e of database.entities || []) {
      const key = `${e.layer ?? ""}\u0000${e.type}`;
      counts[key] = (counts[key] || 0) + 1;
      total += 1;
    }
    row.status = total === 0 ? "empty" : "ok";
    row.total = total;
    row.unknown = stats?.unknownEntityCount ?? null;
    row.counts = counts;
    lib.dwg_free(ptr);
  }
} catch (err) {
  row.status = "crash";
  row.error = String(err?.message || err).slice(0, 300);
}
writeFileSync(out, JSON.stringify(row), "utf8");
