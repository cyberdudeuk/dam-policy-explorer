"""Refresh the pinned snapshot of the DAM capability playbooks used by the explorer's search.

The build never fetches anything: it reads data/playbooks-snapshot.json, which this script writes.
Run it by hand when the playbooks publish a new version, then commit the snapshot:

    python3 -I tools/playbooks_snapshot.py

It reads the playbooks' published machine-readable content (data/playbooks.json) and their main
pages, keeps only titles, a one-line summary and a link (never the body, so nothing is copied that has
its master in the playbooks), and drops any item whose anchor is not on the live page.
"""
import hashlib, html, json, re, sys, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "playbooks-snapshot.json"
BASE = "https://cyberdudeuk.github.io/dam-capability-playbooks/"
# Main pages a coordinator would go to; capabilities are already in the explorer's own search.
PAGES = ["governance.html", "cataloguing.html", "quality.html", "change.html", "tooling.html", "sectors.html",
         "personas.html", "learning.html", "library.html", "community.html", "capability-model.html", "bodies.html"]
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")   # allowlist for anchors taken from the source


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:   # fixed host; only paths from this file
        return r.read()


def plain(s, n=240):
    s = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s)))).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def main():
    raw = get("data/playbooks.json")
    pb = json.loads(raw)
    pages, ids = {}, {}   # page HTML and the ids on each page
    for p in PAGES:
        t = get(p).decode("utf-8", "replace")
        pages[p] = t
        ids[p] = set(re.findall(r'\sid="([^"]+)"', t))
    items = []
    for p in PAGES:
        t = pages[p]
        title = plain(re.search(r"<title>(.*?)</title>", t, re.S).group(1)).split(" - ")[0]
        m = re.search(r'<meta name="description" content="([^"]*)"', t)
        x = plain(m.group(1) if m else "")
        cap = {"governance.html": "gov", "cataloguing.html": "cat", "quality.html": "dq"}.get(p)
        if cap and re.search(r"(\.\.\.|…)$", x):   # the page description is cut short; use the capability's own one-line summary
            x = plain(next(c for c in pb["capabilities"] if c["id"] == cap)["in_brief"][0])
        items.append({"t": title, "x": x, "u": BASE + p, "k": "Playbook"})
    for s in pb["supplements"]:
        if SAFE.match(s["id"]) and s["id"] in ids["sectors.html"]:
            items.append({"t": "Sector supplement: " + plain(s["title"], 120), "x": plain(s.get("summary", "")), "u": BASE + "sectors.html#" + s["id"], "k": "Playbook"})
    for m in pb["modules"]:
        if SAFE.match(m["id"]) and m["id"] in ids["learning.html"]:
            items.append({"t": "Learning module: " + plain(m["title"], 120), "x": plain((m.get("outcomes") or [""])[0].rstrip(".") + "." if m.get("outcomes") else ""), "u": BASE + "learning.html#" + m["id"], "k": "Playbook"})
    meta = pb["meta"]
    snap = {"source": BASE + "data/playbooks.json", "playbooks_version": meta.get("version"), "playbooks_as_of": meta.get("as_of"),
            "retrieved": date.today().isoformat(), "sha256": hashlib.sha256(raw).hexdigest(), "count": len(items), "items": items}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n")
    print(f"playbooks {snap['playbooks_version']} ({snap['playbooks_as_of']}): {len(items)} items -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
