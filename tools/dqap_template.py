#!/usr/bin/env python3
"""Pin what the DQAP checker needs to know about the official GOV.UK DQAP template.

Run: python3 -I tools/dqap_template.py [path-to-downloaded-template.xlsx]

Reads the template GDS publishes with "Implement a data quality action plan" and writes data/dqap-template.json:
the sheet names, the header row of each table, the guidance row under it, and the example rows, with the file's
sha256 and the date it was read. The checker uses these to find the tables in a filled-in copy and to spot
example rows left in. Nothing from the template is shown to users except the sheet and column names.
Rerun when GOV.UK publishes a new version of the template (the checker says which version it knows).
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
URL = "https://assets.publishing.service.gov.uk/media/690b8da814b040dfe829237f/DQAP_Supporting_Materials_Template.xlsx"
PAGE = "https://www.gov.uk/government/publications/implement-a-data-quality-action-plan"
# The tables, the first header cell that marks each one, and the step of the DQAP implementation guide it serves.
TABLES = {
    "Data Criticality Matrix": ("Reference", 1),
    "Data Issues Log": ("Data issue reference", 1),
    "Rules": ("ID", 2),
    "Results": ("ID", 3),
    "Causes": ("Data quality issue", 5),
    "Actions": ("Data quality issue", 5),
}


def text(v):
    if v is None: return ""
    if isinstance(v, datetime.datetime): return v.date().isoformat()
    return " ".join(str(v).split())


def main(path):
    raw = Path(path).read_bytes()
    if raw[:2] != b"PK": sys.exit("not an .xlsx file (expected a zip)")
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {"source": URL, "page": PAGE, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
           "retrieved": datetime.date.today().isoformat(), "sheets": [ws.title for ws in wb.worksheets], "tables": {}, "details": [], "cover": []}
    for name, (first, step) in TABLES.items():
        ws = wb[name]; rows = [[text(c) for c in r] for r in ws.iter_rows(values_only=True)]
        h = next(i for i, r in enumerate(rows) if r and r[0] == first)
        header = [c for c in rows[h] if c]
        if name == "Results": header = header[:4]   # later columns are measurement dates, one per re-measurement
        guide, examples, seen = [], [], False
        for r in rows[h + 1:]:
            cells = [c for c in r if c]
            if not cells: continue
            if cells[0] == "Examples below": seen = True; continue   # the template's own marker: rows after it are examples
            (examples if seen else guide).append(cells[0][:60] + (" | " + cells[1][:60] if seen and len(cells) > 1 else ""))
        out["tables"][name] = {"step": step, "first": first, "header": header, "guide": guide, "examples": examples}
    ws = wb["Details"]
    out["details"] = [text(r[0]) for r in ws.iter_rows(values_only=True) if r and text(r[0]).endswith(":")]
    ws = wb["Cover page"]
    out["cover"] = [[text(r[0]), text(r[1])[:80]] for r in ws.iter_rows(values_only=True) if r and text(r[0]).isdigit()]
    (ROOT / "data" / "dqap-template.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"data/dqap-template.json: {len(out['tables'])} tables, {sum(len(t['examples']) for t in out['tables'].values())} example rows, "
          f"{len(out['details'])} detail fields, {len(out['cover'])} cover steps, sha256 {out['sha256'][:12]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dqapx/t.xlsx")
