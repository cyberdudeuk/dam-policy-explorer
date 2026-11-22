#!/usr/bin/env python3
"""Verification for the DAM Policy Explorer. Run: python3 -I tests/check.py [out-dir] [--negative]

Static checks (S*) read the built files. Browser checks (B*) load every page at three widths and in three colour
themes and run axe-core for WCAG 2.2 AA. Functional checks (F*) drive the tools. --negative breaks a copy of the
build once per check and proves that each check fails when it should (a check that cannot fail is not trusted).
Each check names the defect that created it (see docs/defect-register.md).
"""
import html, json, re, shutil, sys, tempfile, threading, functools, http.server
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AXE = next(p for p in [ROOT / "node_modules/axe-core/axe.min.js", Path("/home/claude/tooling/node_modules/axe-core/axe.min.js")] if p.exists())
BANNED = [r"Office of the Chief Data Officer", r"\bOCDO\b", r"Data Management Team", r"Data Quality (?:&amp;|&) Management team", r"dam-return-and-desk",
          r"beisgov\.sharepoint\.com"]
CONTACT = "https://forms.cloud.microsoft/e/SLBvuPX7jK"

def pages(out): return sorted(out.glob("*.html"))

# ---------------- static checks ----------------
def s1_banned(out):
    """D-01 / standing rule: retired names, the dead repo and internal-only SharePoint links must never appear."""
    bad = []
    for f in list(out.rglob("*.html")) + list(out.rglob("*.js")) + list(out.rglob("*.json")):
        t = f.read_text(errors="ignore")
        bad += [f"{f.name}: {p}" for p in BANNED if re.search(p, t)]
    return bad

def s2_emails(out):
    """Contact is by form only: no email address anywhere, except reserved example.invalid test data."""
    bad = []
    for f in list(out.rglob("*.html")) + list(out.rglob("*.js")):
        for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", f.read_text(errors="ignore")):
            if not m.endswith("example.invalid"): bad.append(f"{f.name}: {m}")
    return bad

def s3_csp(out):
    """D-03: the Content Security Policy forbids inline scripts and style attributes, so none may exist."""
    bad = []
    for f in pages(out):
        t = f.read_text()
        if re.search(r'\sstyle="', t): bad.append(f"{f.name}: style attribute")
        if re.search(r"<script(?![^>]*\bsrc=)[^>]*>", t): bad.append(f"{f.name}: inline script")
        if re.search(r'\son[a-z]+="', t): bad.append(f"{f.name}: inline event handler")
        if "Content-Security-Policy" not in t: bad.append(f"{f.name}: no CSP")
    return bad

def s4_links(out):
    """D-04: every link inside the app resolves to a file and, where given, to an id on that page."""
    ids = {f.name: set(re.findall(r'\sid="([^"]+)"', f.read_text())) for f in pages(out)}
    bad = []
    for f in pages(out):
        for href in re.findall(r'href="([^"]+)"', f.read_text()):
            href = html.unescape(href)
            if re.match(r"(https?:|mailto:|#$)", href): continue
            href = re.sub(r"\?[^#]*", "", href)   # query strings are for the page's script
            path, _, frag = href.partition("#")
            target = path or f.name
            if not (out / target).exists(): bad.append(f"{f.name} -> {href} (no file)"); continue
            if frag and target.endswith(".html") and frag not in ids.get(target, set()) and frag != "main":
                bad.append(f"{f.name} -> {href} (no id)")
    return bad

def s5_external(out):
    """External links open in a new tab (the app runs inside Teams), safely, and say so to screen readers."""
    bad = []
    for f in pages(out):
        for m in re.finditer(r'(<a [^>]*href="https?://[^"]*"[^>]*>)(.*?)</a>', f.read_text(), re.S):
            tag, inner = m.groups()
            if 'target="_blank"' not in tag or "noopener" not in tag: bad.append(f"{f.name}: {tag[:80]}")
            elif "new tab" not in inner: bad.append(f"{f.name}: no new-tab warning: {tag[:60]}")
    return bad

def s6_structure(out):
    """Each page: one h1, a language, a title, a skip link, a main landmark; every image has alt."""
    bad = []
    for f in pages(out):
        t = f.read_text()
        if len(re.findall(r"<h1[\s>]", t)) != 1: bad.append(f"{f.name}: h1 count {len(re.findall(r'<h1[\s>]', t))}")
        for need in ('<html lang="en-GB">', "<title>", 'class="skip"', '<main id="main"'):
            if need not in t: bad.append(f"{f.name}: missing {need}")
        bad += [f"{f.name}: img without alt" for i in re.findall(r"<img(?![^>]*\salt=)[^>]*>", t)]
        dup = [k for k in set(re.findall(r'\sid="([^"]+)"', t)) if len(re.findall(r'\sid="' + re.escape(k) + '"', t)) > 1]
        bad += [f"{f.name}: duplicate id {d}" for d in dup]
    return bad

def s19_no_tracked_build_outputs(out, files=None):
    """D-32: compiled Python (tests/__pycache__) was committed in 1.1.0, before .gitignore excluded it; ignoring a path
    does not untrack it. Nothing generated (bytecode, out/, dist/, inputs/) may be tracked."""
    import subprocess
    if files is None:
        r = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True)
        if r.returncode: return ["git ls-files failed, so the check proves nothing"]
        files = r.stdout.splitlines()
    return [f"tracked build output: {f}" for f in files
            if f.endswith((".pyc", ".pyo")) or "__pycache__/" in f or f.split("/")[0] in ("out", "dist", "inputs", "node_modules")]

def s18_section_citations(out):
    """D-31: citations of GOV.UK guidance link to the section the answer rests on, not the whole document (owner rule,
    19 Nov 2026), and scope answers do not cite data quality guidance (three did, through a one-letter alias)."""
    sys.path.insert(0, str(ROOT / "tools")); import content as C
    docs = {u: k for k, (t, u) in C.GOVUK.items() if k in C.SECTIONS}
    d = json.loads((out / "explorer-data.json").read_text()); bad, seen = [], 0
    for q in d["qa"]:
        for t, u in q["src"]:
            if not u: continue
            base, _, frag = u.partition("#")
            if base in docs:
                seen += 1
                if frag not in C.SECTIONS[docs[base]]: bad.append(f"answer {q['id']}: '{t}' links to the whole document, or to an unknown section '{frag}'")
            if q["topic"] == C.S and "implement-a-data-quality-action-plan" in u: bad.append(f"scope answer {q['id']} cites data quality guidance: {t}")
    if not seen: bad.append("no GOV.UK guidance citation found: the check proves nothing")
    return bad

def s20_playbook_results(out):
    """1.5.0 guard: search includes a pinned snapshot of the capability playbooks. Every playbook result must link to the
    playbooks site (so a tampered snapshot cannot inject another site or a script URL), and the count must match the snapshot."""
    d = json.loads((out / "explorer-data.json").read_text()); snap = json.loads((ROOT / "data" / "playbooks-snapshot.json").read_text())
    base = "https://cyberdudeuk.github.io/dam-capability-playbooks/"; bad = []
    items = [i for i in d["index"] if i["k"] == "Playbook"]
    if len(items) != snap["count"] or not items: bad.append(f"{len(items)} playbook results, snapshot says {snap['count']}")
    for i in items:
        if not i["u"].startswith(base) or re.search(r"[\s\"'<>]", i["u"]): bad.append(f"playbook result leaves the playbooks site: {i['u']}")
        if i["p"]: bad.append(f"playbook result labelled '{i['p']}': the app's provenance labels describe its own content, and the playbooks are not written for it")
    for k in ("sha256", "playbooks_version", "retrieved"):
        if not snap.get(k): bad.append(f"snapshot has no {k}")
    return bad

def s21_choices_and_open(out):
    """1.5.0 guard (owner request, 22 Nov 2026): the policy page says what is fixed and what is up to each organisation,
    each item with a section-level GOV.UK source, and lists every answer still labelled Open."""
    sys.path.insert(0, str(ROOT / "tools")); import content as C
    t = (out / "policy.html").read_text(); bad = []
    for c in C.CHOICES:
        m = re.search(r'<li class="req[^"]*" id="choice-' + re.escape(c["id"]) + r'">(.*?)</li>\s*(?=<li class="req|</ul>)', t, re.S)
        if not m: bad.append(f"choice {c['id']} is not on the policy page"); continue
        if not re.search(r'href="https://www\.gov\.uk/[^"#]+#[^"]+"', m.group(1)): bad.append(f"choice {c['id']} has no section-level GOV.UK source")
    opens = [q["id"] for q in C.QA if q["prov"] == "open"]
    listed = re.findall(r'<li><a href="questions\.html#q-([^"]+)">', t.split('id="open"')[1].split("<h2")[0]) if 'id="open"' in t else []
    if sorted(listed) != sorted(opens): bad.append(f"Open list shows {len(listed)} answers, there are {len(opens)}")
    return bad

def s24_dqap(out):
    """1.7.0 guard (owner request, 22 Nov 2026): the DQAP tool cites the exact GOV.UK section for every check, links the
    GOV.UK template, and publishes the dimensions the same way in Turtle and JSON-LD (one graph, two formats)."""
    import rdflib
    from rdflib.compare import isomorphic
    bad = []
    try:
        d = json.loads((out / "dqap-data.json").read_text())
    except Exception as e:  # noqa: BLE001
        return [f"dqap-data.json missing or unreadable: {e}"]
    for c in d["checks"]:
        if c["test"] != "examples" and not c["src"]: bad.append(f"check {c['id']} cites no source")
        for x in c["src"]:
            if not re.fullmatch(r"https://www\.gov\.uk/government/publications/implement-a-data-quality-action-plan/[a-z-]+#[a-z0-9-]+|https://www\.gov\.uk/government/publications/data-asset-management-policy-in-government/[a-z-]+#[a-z0-9-]+", x["u"]):
                bad.append(f"check {c['id']} source is not a GOV.UK section: {x['u']}")
    if len(d["equiv"]) != 7 or [e["step"] for e in d["equiv"]] != list(range(1, 8)): bad.append("the self-assessment does not cover steps 1 to 7")
    # D-35: link text repeated the full document title on every line, which made the results hard to scan on a phone
    for c in d["checks"]:
        for x in c["src"]:
            if not re.match(r"(The policy|DQAP guide|Issues framework), .{3,70} \(GOV\.UK\)$", x["t"]): bad.append(f"check {c['id']} link text is not short: {x['t'][:80]}")
    t = (out / "dqap.html").read_text()
    # D-35: a heading inside a hidden result panel became a drawer link to nothing
    for m in re.finditer(r'<section[^>]* hidden>(.*?)</section>', t.split('<main', 1)[-1], re.S):   # the drawer collects headings in main only
        if "<h2" in m.group(1): bad.append("a section heading (h2) sits inside a hidden panel, so the contents drawer links to it")
    # D-35: vocabulary terms such as dcat:Dataset broke mid-word in the mapping table
    if not re.search(r"\.dqv-map code \{[^}]*word-break: normal;[^}]*overflow-wrap: normal", (out / "assets" / "explorer.css").read_text().replace("white-space: normal; ", "")): bad.append("DQV terms in the mapping table can break mid-word")
    if "assets.publishing.service.gov.uk/media/690b8da814b040dfe829237f/DQAP_Supporting_Materials_Template.xlsx" not in t: bad.append("dqap.html does not link the GOV.UK template")
    try:
        a = rdflib.Graph().parse(str(out / "vocab" / "dq.ttl"), format="turtle"); b = rdflib.Graph().parse(str(out / "vocab" / "dq.jsonld"), format="json-ld")
        if not isomorphic(a, b): bad.append("vocab/dq.ttl and vocab/dq.jsonld describe different graphs")
        n = len(list(a.subjects(rdflib.RDF.type, rdflib.URIRef("http://www.w3.org/ns/dqv#Dimension"))))
        if n != len(d["dims"]): bad.append(f"the vocabulary has {n} dimensions, the tool {len(d['dims'])}")
    except Exception as e:  # noqa: BLE001
        bad.append(f"the dimensions vocabulary does not parse: {e}")
    return bad

def s23_three_choices(out):
    """DAM-02 (SSRO backlog, 22 Nov 2026): role-based journeys. From the home page, each role and every task on its journey
    must be reachable in three choices or fewer, counted as link clicks over the built site (in-page links count too)."""
    import collections
    sys.path.insert(0, str(ROOT / "tools")); import content as C
    links = {}
    for f in pages(out):
        links[f.name] = {(f.name + h if h.startswith("#") else h).replace("&amp;", "&") for h in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', f.read_text())}
    depth, q = {"index.html": 0}, collections.deque(["index.html"])
    while q:
        p = q.popleft()
        for h in links.get(p, ()):
            pg = h.split("#")[0]
            if pg in links and pg not in depth: depth[pg] = depth[p] + 1; q.append(pg)
    def clicks(t):
        if "#" not in t and t in depth: return depth[t]
        c = [depth[p] + 1 for p, hs in links.items() if p in depth and t in hs]
        return min(c) if c else None
    bad = []
    for x in C.PERSONAS:
        for t in [f"people.html#p-{x['id']}"] + [h for items in x["journey"].values() for _, h in items]:
            n = clicks(t)
            if n is None or n > 3: bad.append(f"{x['name']}: {t} takes {n if n is not None else 'no route of'} choices from the home page")
    return bad

def s22_portal_pages(out):
    """1.5.0 guard: the Government Data portal pages are rebuilt from the published site, so their bodies must be safe to
    put in a SharePoint text web part (only headings, paragraphs, lists, links and emphasis; https or portal links; no
    addresses) and must state the versions they were made from."""
    sys.path.insert(0, str(ROOT / "tools")); import content as C
    snap = json.loads((ROOT / "data" / "playbooks-snapshot.json").read_text()); bad = []
    for name, stamp in (("explorer.html", f"version {C.VERSION}"), ("playbooks.html", f"playbooks version {snap['playbooks_version']}")):
        f = out / "portal" / name
        if not f.exists(): bad.append(f"portal/{name} was not built"); continue
        t = f.read_text()
        tags = set(re.findall(r"</?([a-zA-Z0-9]+)", t)) - {"h2", "p", "ul", "li", "a", "em"}
        if tags: bad.append(f"portal/{name}: tags a text web part should not carry: {sorted(tags)}")
        for h in re.findall(r'href="([^"]+)"', t):
            if not (h.startswith("https://") or re.fullmatch(r"[A-Za-z0-9-]+\.aspx", h)): bad.append(f"portal/{name}: link {h}")
        if "@" in t: bad.append(f"portal/{name}: an address")
        if stamp not in t: bad.append(f"portal/{name}: does not say it was made from {stamp}")
        if re.search(r"\bon\w+\s*=", t): bad.append(f"portal/{name}: an event handler")
    return bad

def s7_traceability(out):
    """Every forum need maps to an answer; every answer has a source unless it is labelled suggested practice."""
    d = json.loads((out / "explorer-data.json").read_text()); bad = []
    qa = {q["id"]: q for q in d["qa"]}
    for n in d["needs"]:
        if n["qa"] not in qa: bad.append(f"need {n['id']} -> missing answer {n['qa']}")
    for q in d["qa"]:
        if not q["src"] and q["prov"] not in ("practice", "open"): bad.append(f"answer {q['id']} ({q['prov']}) has no source")
    return bad

def s8_contact(out):
    """D-01: the contact form link is the one verified to exist (the Microsoft Form created 18 Nov 2026), and no other form is linked."""
    bad = []
    for f in pages(out):
        for h in re.findall(r'(?:href|data-contact)="([^"]*(?:issues/new|forms\.(?:cloud\.microsoft|office\.com))[^"]*)"', f.read_text()):
            if html.unescape(h) != CONTACT: bad.append(f"{f.name}: {h}")
    return bad

def s9_wording(out):
    """D-05: the retired 'three tests' framing must not come back; scope uses OFFICIAL plus the four principles."""
    return [f.name for f in pages(out) if re.search(r"three tests|all three tests", f.read_text(), re.I)] + \
           [f.name for f in (out / "assets").glob("*.js") if re.search(r"All three tests", f.read_text())]

def s10_class_collision(out):
    """D-10: the header row class (.bar) must not also be given a fixed height elsewhere in the stylesheets."""
    css = "".join(f.read_text() for f in (out / "assets").glob("*.css"))
    return [m for m in re.findall(r"(?m)^\s*\.bar\s*\{[^}]*height:[^}]*\}", css)]

def s11_no_unagreed_promises(out):
    """D-14: no service level (reply times) is stated until one is agreed."""
    return [f.name for f in pages(out) if re.search(r"within \d+ working days", f.read_text())]

def s12_agent_open_sources(out):
    """D-16: the Copilot agent must use only sources everyone can open (no SharePoint knowledge, no internal addresses)."""
    t = "".join(f.read_text() for f in (ROOT / "teams").glob("*.json"))
    return [p for p in ("OneDriveAndSharePoint", "sharepoint.com", "{{FAQ_URL}}") if p in t]

def s13_topics_grouped(out):
    """questions.html: each topic heading appears once, in the agreed topic order, and the build groups answers whatever their order in the content file (D-18)."""
    import importlib, random
    sys.path.insert(0, str(ROOT / "tools"))
    C = importlib.import_module("content")
    bad = []
    t = (out / "questions.html").read_text()
    found = re.findall(r'<h3 class="topic-h" id="topic-[^"]+">([^<]+)</h3>', t)
    found = [html.unescape(x) for x in found]
    if len(found) != len(set(found)): bad.append(f"questions.html: repeated topic headings {found}")
    if found != [x for x in C.TOPICS if x in found]: bad.append(f"questions.html: topics out of order {found}")
    B = importlib.import_module("build")
    orig = list(C.QA)
    try:
        random.Random(18).shuffle(C.QA)
        heads = re.findall(r'class="topic-h"', B.questions())
        if len(heads) != len({q["topic"] for q in C.QA}): bad.append("build does not group shuffled answers by topic")
    except Exception as e:
        bad.append(f"could not render questions with shuffled answers: {e}")
    finally:
        C.QA[:] = orig
    return bad


def s14_css_vars_defined(out):
    """D-19: every CSS custom property used (var(--x)) is defined, so a misspelt colour cannot silently do nothing."""
    css = "".join(f.read_text() for f in (out / "assets").glob("*.css"))
    html = "".join(f.read_text() for f in pages(out))
    defined = set(re.findall(r"(--[A-Za-z0-9-]+)\s*:", css + html))
    used = set(re.findall(r"var\((--[A-Za-z0-9-]+)\s*[,)]", css))
    return sorted(used - defined)

# Class names both stylesheets define, each reviewed by eye on 18 Nov 2026 (D-19, D-22 to D-25 came from unreviewed ones).
SHARED_CLASSES_REVIEWED = {
    "colophon": "footer barcode and QR row, restyled on purpose", "count": "count badge, restyled on purpose", "crumbs": "breadcrumbs, restyled on purpose",
    "hero": "explorer only styles the tour control inside the base dark band", "hint": "form hint text, same meaning", "ic": "icons, same meaning",
    "kicker": "small heading over a title, same meaning", "knob": "switch knob; each rule is scoped to its own switch", "lane": "base rule is scoped to svg.pm",
    "lead": "lead paragraph, same meaning", "legend": "explorer legend overrides layout; checked on Questions", "linkish": "button styled as a link, same meaning",
    "next": "explorer only uses .pill.next", "phase": "prototype banner, restyled on purpose", "pill": "status pill, restyled on purpose",
    "primary": "base rule is scoped to buttons; explorer to .xnav", "q": "base rule is scoped to .tree; explorer to .asset-test", "small": "small text, same meaning",
    "source": "source line, same rule", "stage": "base .stage is on Your return; explorer only styles .lane .stage", "step": "explorer only adds the mark-done button to base steps",
    "term": "glossary word, restyled on purpose", "tooltip": "the explorer tooltip has its own arrow rules (D-24)", "verdict": "asset-test result; checked by eye", "vh": "visually hidden text, same rule",
}

def s17_source_hosts(out):
    """D-29: a source labelled GOV.UK is on www.gov.uk. Every linked source was labelled GOV.UK, so the first source on
    another site (the Digital Economy Act register on data.gov.uk) was mislabelled."""
    bad, seen = [], 0
    for f in pages(out):
        for href, text in re.findall(r'<a href="([^"]+)"[^>]*>([^<]*\(GOV\.UK\))(?:<span[^>]*>[^<]*</span>)?</a>', f.read_text()):
            seen += 1
            if not html.unescape(href).startswith("https://www.gov.uk/"): bad.append(f"{f.name}: {text} -> {href}")
    if not seen: bad.append("no source labelled GOV.UK was found: the pattern no longer matches the page, so the check proves nothing")
    return bad

def s15_class_collisions(out):
    """D-19, D-22 to D-25: a class name defined in both the base and the explorer stylesheet must be reviewed, because base rules leak into explorer components."""
    def classes(css):
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S); found = set()
        for sel in re.findall(r"([^{}]+)\{", css):
            if not sel.strip().startswith("@"): found |= set(re.findall(r"\.([A-Za-z][\w-]*)", sel))
        return found
    a = (out / "assets" / "style.css").read_text(); b = (out / "assets" / "explorer.css").read_text()
    return sorted(c for c in classes(a) & classes(b) if c not in SHARED_CLASSES_REVIEWED)

def s16_repo_licences(out):
    """D-25: the repository had no licence, so nobody had the right to reuse it; MIT code and OGL content must be stated and linked, with no unagreed reply times in the repository's own files (D-14)."""
    bad = []
    lic = ROOT / "LICENSE"
    if not lic.exists() or "MIT License" not in lic.read_text(): bad.append("LICENSE missing or not MIT")
    cl = ROOT / "docs" / "CONTENT-LICENCE.md"
    if not cl.exists() or "Open Government Licence v3.0" not in cl.read_text(): bad.append("docs/CONTENT-LICENCE.md missing or not OGL v3.0")
    readme = (ROOT / "README.md").read_text()
    for target in ("(LICENSE)", "(docs/CONTENT-LICENCE.md)"):
        if target not in readme: bad.append(f"README does not link {target}")
    for name in ("README.md", "CONTRIBUTING.md", "SUPPORT.md", "SECURITY.md"):
        f = ROOT / name
        if f.exists() and re.search(r"within \d+ working days", f.read_text()): bad.append(f"{name} states a reply time")
    return bad

STATIC = [s24_dqap, s23_three_choices, s22_portal_pages, s21_choices_and_open, s20_playbook_results, s19_no_tracked_build_outputs, s18_section_citations, s16_repo_licences, s12_agent_open_sources, s11_no_unagreed_promises, s10_class_collision, s1_banned, s2_emails, s3_csp, s4_links, s5_external, s6_structure, s7_traceability, s8_contact, s9_wording, s13_topics_grouped, s14_css_vars_defined, s15_class_collisions, s17_source_hosts]

# ---------------- browser checks ----------------
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(out):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(out)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"

WIDTHS = [320, 768, 1280]
THEMES = ["light", "dark", "contrast"]


def _lum(c):
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c[:3]; return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)

B5_JS = """() => [...document.querySelectorAll('h1, main .lead, main .kicker, .tour-start, .hero a, .hero button, .home-hero a, .home-hero .lead')]
  .filter(e => { const r = e.getBoundingClientRect(); return r.width > 4 && r.height > 4 && getComputedStyle(e).visibility !== 'hidden'; })
  .slice(0, 10).map(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); const fs = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
    return { sel: e.tagName.toLowerCase() + (e.className && e.className.baseVal === undefined ? '.' + String(e.className).split(' ')[0] : ''), x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
             fg: cs.color.match(/[0-9.]+/g).slice(0, 3).map(Number), large: fs >= 24 || (bold && fs >= 18.66) }; })"""

def b5_pixel_contrast(pg, label):
    """B5 (D-19, D-20): text contrast measured against the pixels actually behind it, which axe cannot judge on gradients."""
    from PIL import Image
    import io
    out = []
    for el in pg.evaluate(B5_JS):
        try:
            png = pg.screenshot(clip={"x": el["x"], "y": el["y"], "width": max(1, el["w"]), "height": max(1, el["h"])}, full_page=True)
        except Exception:
            continue
        im = Image.open(io.BytesIO(png)).convert("RGB")
        fg = tuple(el["fg"])
        allpx = list(im.getdata())
        far = [c for c in allpx if _ratio(c, fg) > 1.15]
        # Background: when most of the box is clearly unlike the text, take its commonest colour (coarse bins, so a gradient is one colour);
        # when almost none is, the text is nearly invisible on its background (D-19), so compare with the whole box.
        # (Taking the commonest colour of the whole box picked the text itself on gradients; filtering alone hid D-19.)
        src = far if len(far) >= 0.3 * len(allpx) else allpx
        q = {}
        for c in src: k = (c[0] // 16, c[1] // 16, c[2] // 16); q[k] = q.get(k, 0) + 1
        k = max(q, key=q.get); bg = tuple(v * 16 + 8 for v in k)
        need = 3.0 if el["large"] else 4.5
        r = _ratio(fg, bg)
        if r < need: out.append(f"B5 {label}: {el['sel']} contrast {r:.2f} < {need} (text {fg} on {bg})")
    return out

def browser_checks(out, quick=False):
    from playwright.sync_api import sync_playwright
    srv, base = serve(out); fails = []; axe = AXE.read_text(); runs = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for theme in (THEMES[:1] if quick else THEMES):
            for w in (WIDTHS[:1] if quick else WIDTHS):
                ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme="dark" if theme == "dark" else "light", bypass_csp=True)
                ctx.add_init_script("try{localStorage.setItem('dpe.prefs',JSON.stringify({theme:'%s'}))}catch(e){}" % theme)
                pg = ctx.new_page(); errs = []
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errs.append(str(e)))
                for f in pages(out):
                    errs.clear(); pg.goto(base + f.name); pg.wait_for_timeout(150)
                    # B1: no sideways scrolling (WCAG 1.4.10 reflow at 320 px)
                    sw = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    if sw > 1: fails.append(f"B1 {f.name} {theme} {w}px: overflows by {sw}px")
                    # B2: main navigation never wider than the screen
                    nw = pg.evaluate("(()=>{const n=document.querySelector('#site-nav');return n?n.scrollWidth-window.innerWidth:0})()")
                    if nw > 1: fails.append(f"B2 {f.name} {theme} {w}px: nav overflows by {nw}px")
                    # B3: no script errors or CSP violations
                    if errs: fails.append(f"B3 {f.name} {theme} {w}px: {errs[:2]}")
                    # B4: axe-core, WCAG 2.2 A and AA, with every collapsed section opened so hidden content is tested too
                    pg.evaluate("document.querySelectorAll('main details').forEach(d=>d.open=true)")   # content sections only; the menu dropdown is meant to overlay the page
                    pg.add_script_tag(content=axe)
                    res = pg.evaluate("axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']},resultTypes:['violations']}).then(r=>r.violations.map(v=>v.id+' x'+v.nodes.length+' '+(v.nodes[0]&&v.nodes[0].target.join(' '))))")
                    if res: fails.append(f"B4 {f.name} {theme} {w}px: {res[:3]}")
                    fails += b5_pixel_contrast(pg, f"{f.name} {theme} {w}px")
                    # B7 (D-26, D-27): roadmap text starts on its pill's line; glossary definitions keep a readable width
                    if f.name == "about.html":
                        off = pg.evaluate("Math.max(0,...[...document.querySelectorAll('.roadmap li')].map(li=>{const a=li.querySelector('.pill'),b=li.querySelector('.rm-t');return a&&b?Math.abs(a.getBoundingClientRect().top-b.getBoundingClientRect().top):999}))")
                        if off > 8: fails.append(f"B7 {f.name} {theme} {w}px: roadmap text is {off:.0f}px off its pill's line")
                    if f.name == "glossary.html":
                        gw = pg.evaluate("(()=>{const g=document.querySelector('.glossary');return g?g.getBoundingClientRect().width:0})()")
                        if gw > 48 * 16 + 2: fails.append(f"B7 {f.name} {theme} {w}px: glossary is {gw:.0f}px wide")
                    # B8 (D-22): no word in a Track stage title is broken across lines
                    if f.name == "track.html":
                        broken = pg.evaluate("[...document.querySelectorAll('.st-opt b')].filter(b=>{const r=document.createRange();r.selectNodeContents(b);const lines=new Set([...r.getClientRects()].map(x=>Math.round(x.top)));return b.textContent.trim().split(/\\s+/).length < lines.size}).map(b=>b.textContent)")
                        if broken: fails.append(f"B8 {f.name} {theme} {w}px: stage titles broken mid-word: {broken}")
                    # B9 (D-28): every answer's question starts on the same line as its triangle
                    if f.name == "questions.html":
                        off = pg.evaluate("Math.max(0,...[...document.querySelectorAll('.qa summary')].map(s=>{const q=s.querySelector('.qtext');return q?q.getBoundingClientRect().top-s.getBoundingClientRect().top:0}))")
                        if off > 24: fails.append(f"B9 {f.name} {theme} {w}px: a question starts {off:.0f}px below its triangle")
                    # B6 (D-21): one contents control per page, never two
                    nd = pg.evaluate("document.querySelectorAll('.drawer-toggle, .drawer-switch').length")
                    if nd > 1: fails.append(f"B6 {f.name} {theme} {w}px: {nd} contents controls")
                    runs += 1
                ctx.close()
        b.close()
    srv.shutdown()
    return fails, runs

def functional_checks(out):
    from playwright.sync_api import sync_playwright
    srv, base = serve(out); fails = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(base + "asset-test.html")
        # F1: the scope decision, one case per rule
        cases = [
            ({"official": "yes", "purpose": ["1"], "shared": "dsa", "accountable": "own", "source": "source"}, "in"),
            ({"official": "no", "purpose": ["1"], "shared": "dsa", "accountable": "own", "source": "source"}, "out"),
            ({"official": "yes", "purpose": [], "shared": "dsa", "accountable": "own", "source": "source"}, "out"),
            ({"official": "yes", "purpose": ["3"], "shared": "no", "accountable": "own", "source": "source"}, "out"),
            ({"official": "yes", "purpose": ["5"], "shared": "open", "accountable": "asis", "source": "source"}, "out"),
            ({"official": "yes", "purpose": ["1"], "shared": "dsa", "accountable": "own", "source": "derived"}, "out"),
            ({"official": "yes", "purpose": ["1"], "shared": "dsa", "accountable": "enriched", "source": "product"}, "in"),
            ({"official": "yes", "purpose": ["2"], "shared": "potential", "accountable": "own", "source": "source"}, "in-later"),
            ({"official": "unsure", "purpose": ["1"], "shared": "dsa", "accountable": "own", "source": "source"}, "flag"),
            ({"official": "yes", "purpose": ["unsure"], "shared": "unsure", "accountable": "own", "source": "source"}, "flag"),
            ({"official": "no", "purpose": ["unsure"], "shared": "unsure", "accountable": "own", "source": "source"}, "out"),
        ]
        for a, want in cases:
            got = pg.evaluate("a => window.DPE.decideAsset(a).verdict", a)
            if got != want: fails.append(f"F1 decideAsset {a} -> {got}, expected {want}")
        # F2: the form works end to end and the result is announced
        pg.check('input[name=official][value=yes]'); pg.check('input[name=purpose][value="1"]'); pg.check('input[name=shared][value=dsa]')
        pg.check('input[name=accountable][value=own]'); pg.check('input[name=source][value=derived]'); pg.fill("#asset-name", "=HYPERLINK(\"x\")")
        pg.click("form.asset-test button[type=submit]")
        if "Leave it out" not in pg.inner_text("[data-result]"): fails.append("F2 asset test result not shown")
        with pg.expect_download() as dl: pg.click("[data-download]")
        csv = Path(dl.value.path()).read_text()
        if "'=HYPERLINK" not in csv: fails.append("F3 CSV does not neutralise a spreadsheet formula")
        if not csv.startswith("Unique identifier,Data asset name,OFFICIAL,Critical purpose,Shared,Accountable,Source asset,Reason"): fails.append("F3 CSV headings do not match the template")
        tmpl = (out / "templates" / "left-out-template.csv").read_text().strip()
        if csv.splitlines()[0] != tmpl: fails.append("F3 CSV headings differ from templates/left-out-template.csv")
        # F4: question search and topic filter
        pg.goto(base + "questions.html"); pg.fill("#qa-search", "legal gateway")
        if not re.match(r"^[1-9]\d* question", pg.inner_text("#qa-count")): fails.append("F4 search found nothing for 'legal gateway'")
        pg.fill("#qa-search", "zzzz-no-match")
        if not pg.inner_text("#qa-count").startswith("0 questions"): fails.append("F4 search did not report no matches")
        # F5: capability filter by role
        pg.goto(base + "capabilities.html"); pg.check('input[name=who][value=coo]')
        n = pg.evaluate("document.querySelectorAll('.caps .cap:not([hidden])').length")
        if n != 6: fails.append(f"F5 coordinator capability filter shows {n}, expected 6")
        # F6: progress is saved and shown on the home page
        pg.goto(base + "return.html"); pg.locator("#step-1 summary").click(); pg.locator("#step-1 .mark").click()
        pg.goto(base + "index.html")
        if "1 of 12 steps done" not in pg.inner_text("[data-progress-home]"): fails.append("F6 progress not shown on home page")
        # F7: display settings apply and persist; Teams theme parameter is honoured
        pg.click(".settings-btn"); pg.check("input[name=theme][value=contrast]"); pg.reload()
        if pg.evaluate("document.documentElement.getAttribute('data-theme')") != "contrast": fails.append("F7 theme setting not kept")
        pg.evaluate("localStorage.clear()"); pg.goto(base + "index.html?theme=dark")
        if pg.evaluate("document.documentElement.getAttribute('data-theme')") != "dark": fails.append("F7 Teams theme=dark not applied")
        # F8: self-check passes on every page
        pg.goto(base + "about.html")
        txt = pg.inner_text("[data-selfcheck]")
        if "Failed" in pg.inner_html("[data-selfcheck]"): fails.append("F8 self-check reports a failure: " + txt[:200])
        for f in pages(out):
            pg.goto(base + f.name); r = pg.evaluate("window.DPE.selfCheck().filter(x=>!x.ok && !/last checked|save/.test(x.name)).map(x=>x.name+': '+x.detail)")
            if r: fails.append(f"F8 {f.name}: {r}")
        # F9: glossary tooltip shows on focus and hides on Escape (WCAG 1.4.13)
        pg.goto(base + "policy.html"); pg.focus("a.term")
        if pg.is_hidden("#term-tip"): fails.append("F9 tooltip not shown on focus")
        pg.keyboard.press("Escape")
        if not pg.is_hidden("#term-tip"): fails.append("F9 tooltip not dismissed by Escape")
        # F10: menu folds on a narrow screen and opens with the button
        pg.set_viewport_size({"width": 360, "height": 800}); pg.goto(base + "index.html")
        if not pg.is_visible(".menu-btn"): fails.append("F10 menu button not shown on narrow screen")
        pg.click(".menu-btn")
        if not pg.is_visible("#site-nav .primary"): fails.append("F10 menu does not open")
        # F12 (D-12): on a narrow screen the page contents start closed, so the main content comes first
        pg.evaluate("localStorage.removeItem('dpe.drawer')"); pg.set_viewport_size({"width": 360, "height": 800}); pg.goto(base + "policy.html")
        if pg.is_visible(".contents"): fails.append("F12 page contents open by default on a narrow screen")
        pg.set_viewport_size({"width": 1280, "height": 900}); pg.goto(base + "policy.html")
        if not pg.is_visible(".contents"): fails.append("F12 page contents closed by default on a wide screen")
        # F13 (D-13): the countdown counts calendar days (18 Nov to 18 Dec 2026 is 30)
        p3 = b.new_page(); p3.clock.set_fixed_time("2026-11-18T12:00:00"); p3.goto(base + "index.html")
        if "30 days" not in p3.inner_text("[data-countdown]"): fails.append("F13 countdown wrong: " + p3.inner_text("[data-countdown]"))
        p3.clock.set_fixed_time("2026-12-18T09:00:00"); p3.goto(base + "index.html")
        if "Today" not in p3.inner_text("[data-countdown]"): fails.append("F13 countdown on the day: " + p3.inner_text("[data-countdown]"))
        p3.close()
        # F14: tracker keeps its stage; the return analysis reads an (invented) return correctly
        pg.goto(base + "track.html"); pg.check("input[name=stage][value=received]"); pg.fill("#tr-ref", "REF-1"); pg.locator("#tr-ref").dispatch_event("change"); pg.reload()
        if not pg.is_checked("input[name=stage][value=received]") or "REF-1" not in pg.inner_text("[data-tr-saved]"): fails.append("F14 tracker did not keep its stage and reference")
        pg.set_input_files("#tr-file", str(ROOT / "tests" / "fixtures" / "invented-return.csv")); pg.wait_for_timeout(300)
        txt = pg.inner_text("[data-tr-analytics]")
        for want in ("3 assets", "67%", "33%"):
            if want not in txt: fails.append(f"F14 analysis missing '{want}'")
        if pg.evaluate("[...document.querySelectorAll('[data-tr-analytics] .fill')].some(f=>!f.style.width)"): fails.append("F14 chart bars have no width")
        # F15: tours are offered once, open as a modal dialog, keep keyboard focus inside, and close with Escape
        pg.set_viewport_size({"width": 1280, "height": 900}); pg.evaluate("localStorage.clear()"); pg.goto(base + "index.html")
        if not pg.is_visible(".tour-offer"): fails.append("F15 first-visit tour offer not shown")
        pg.click(".tour-offer [data-o=go]")
        if not pg.is_visible(".tour[role=dialog][aria-modal=true]"): fails.append("F15 tour dialog not shown")
        for _ in range(12): pg.keyboard.press("Tab")
        if not pg.evaluate("!!document.activeElement.closest('.tour')"): fails.append("F15 focus escaped the tour dialog")
        pg.keyboard.press("Escape")
        if pg.is_visible(".tour"): fails.append("F15 Escape did not close the tour")
        pg.reload()
        if pg.is_visible(".tour-offer"): fails.append("F15 tour offered again after it was taken")
        for name, pagef in (("asset", "asset-test.html"), ("check", "return.html"), ("track", "track.html"), ("answers", "questions.html")):
            pg.goto(base + pagef + "#tour-" + name); pg.wait_for_timeout(600)
            if not pg.is_visible(".tour"): fails.append(f"F15 tutorial {name} did not start on {pagef}")
            n = pg.evaluate("parseInt((document.querySelector('.tour-n')||{}).textContent.split(' of ')[1]||'0')")
            if n < 2: fails.append(f"F15 tutorial {name} has {n} steps on screen")
            pg.keyboard.press("Escape")
        # F16: tooltips everywhere: menu items, buttons and labels have one, and it shows on focus
        pg.goto(base + "questions.html")
        missing = pg.evaluate("[...document.querySelectorAll('.xnav a, .settings-btn, .hs-btn, .prov, .copy')].filter(e=>!e.getAttribute('data-tip')).length")
        if missing: fails.append(f"F16 {missing} controls have no tooltip")
        if pg.evaluate("document.querySelectorAll('[title]:not(svg *)').length"): fails.append("F16 native title attributes left (they would show twice)")
        pg.focus(".prov")
        if pg.is_hidden("#term-tip") or not pg.inner_text("#term-tip").strip(): fails.append("F16 badge tooltip not shown on focus")
        # F11: works with JavaScript turned off (content readable)
        ctx = b.new_context(java_script_enabled=False); p2 = ctx.new_page()
        for f in ("index.html", "questions.html", "people.html"):
            p2.goto(base + f)
            if len(p2.inner_text("main")) < 400: fails.append(f"F11 {f} has little content without JavaScript")
        ctx.close()
        # FD1 to FD6: the data quality action plan tool (1.7.0, owner request 22 Nov 2026)
        sys.path.insert(0, str(ROOT / "tests")); from check_dqap import dqap_functional
        fails += dqap_functional(b, base)
        b.close()
    srv.shutdown()
    return fails

# ---------------- negative tests: each check must fail on a broken copy ----------------
def _poison_playbook(o):
    d = json.loads((o / "explorer-data.json").read_text())
    next(i for i in d["index"] if i["k"] == "Playbook")["u"] = "javascript:alert(1)"
    (o / "explorer-data.json").write_text(json.dumps(d))

def _label_playbook(o):
    d = json.loads((o / "explorer-data.json").read_text())
    next(i for i in d["index"] if i["k"] == "Playbook")["p"] = "practice"
    (o / "explorer-data.json").write_text(json.dumps(d))

def f_dqap(out):
    """FD1 to FD6 on their own, so the negative tests can run them against a broken copy."""
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(ROOT / "tests")); from check_dqap import dqap_functional
    srv, base = serve(out)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(); f = dqap_functional(b, base); b.close()
    finally:
        srv.shutdown()
    return f

def negatives(out):
    def mutate(fn):
        tmp = Path(tempfile.mkdtemp()); shutil.copytree(out, tmp / "o"); fn(tmp / "o"); return tmp / "o"
    def edit(o, name, a, b):
        p = o / name; t = p.read_text(); assert a in t, (name, a); p.write_text(t.replace(a, b, 1))
    cases = [
        (s1_banned, lambda o: edit(o, "index.html", "<h1>", "<h1>Office of the Chief Data Officer ")),
        (s1_banned, lambda o: edit(o, "about.html", "<h1>", '<h1><a href="https://beisgov.sharepoint.com/x">x</a>')),
        (s2_emails, lambda o: edit(o, "index.html", "<h1>", "<h1>someone@example.gov.uk ")),
        (s3_csp, lambda o: edit(o, "index.html", "<h1>", '<h1 style="color:red">')),
        (s3_csp, lambda o: edit(o, "index.html", "</body>", "<script>alert(1)</script></body>")),
        (s4_links, lambda o: edit(o, "index.html", 'href="policy.html"', 'href="policy.html#nowhere"')),
        (s4_links, lambda o: edit(o, "index.html", 'href="policy.html"', 'href="missing.html"')),
        (s18_section_citations, lambda o: (o / "explorer-data.json").write_text((o / "explorer-data.json").read_text().replace("data-asset-management-policy-in-government#data-quality-action-plans", "data-asset-management-policy-in-government", 1))),
        (s18_section_citations, lambda o: (o / "explorer-data.json").write_text((o / "explorer-data.json").read_text().replace("identify-and-record-critical-data-assets/identifying-and-recording-critical-data-assets#what-critical-data-assets-are", "implement-a-data-quality-action-plan/data-quality-issues-framework#what-data-quality-rules-and-issues-are", 1))),
        (s20_playbook_results, lambda o: _poison_playbook(o)),
        (s24_dqap, lambda o: (o / "vocab" / "dq.jsonld").write_text((o / "vocab" / "dq.jsonld").read_text().replace('"skos:closeMatch"', '"skos:exactMatch"', 1))),
        (s24_dqap, lambda o: (o / "dqap-data.json").write_text((o / "dqap-data.json").read_text().replace("#step-2-identify-data-quality-rules", "", 1))),
        (s24_dqap, lambda o: edit(o, "dqap.html", '<h3 id="dq-result-h">Your plan</h3>', '<h2 id="dq-result-h">Your plan</h2>')),
        (s24_dqap, lambda o: edit(o, "assets/explorer.css", ".dqv-map code { white-space: normal; word-break: normal;", ".dqv-map code { white-space: normal; word-break: break-all;")),
        (s24_dqap, lambda o: (o / "dqap-data.json").write_text((o / "dqap-data.json").read_text().replace('"DQAP guide, Step 2: Identify data quality rules (GOV.UK)"', '"Data quality action plan: implementation guide: Step 2: Identify data quality rules"', 1))),
        (s23_three_choices, lambda o: [f.write_text(re.sub(r'href="people\.html[^"]*"', 'href="index.html"', f.read_text())) for f in o.glob("*.html") if f.name != "people.html"]),
        (s22_portal_pages, lambda o: (o / "portal" / "playbooks.html").write_text((o / "portal" / "playbooks.html").read_text() + '<script>alert(1)</script>')),
        (s22_portal_pages, lambda o: (o / "portal" / "explorer.html").write_text((o / "portal" / "explorer.html").read_text().replace('href="https://', 'href="javascript:', 1))),
        (s20_playbook_results, lambda o: _label_playbook(o)),
        (s21_choices_and_open, lambda o: edit(o, "policy.html", 'id="choice-catalogue"', 'id="choice-gone"')),
        (s21_choices_and_open, lambda o: edit(o, "policy.html", '<h3 id="open">Still being decided</h3>', '<h3 id="open">Still being decided</h3><ul><li><a href="questions.html#q-extra">x</a></li></ul>')),
        (s17_source_hosts, lambda o: edit(o, "questions.html", "(digital-economy-act-register.data.gov.uk)<span", "(GOV.UK)<span")),
        (s5_external, lambda o: edit(o, "index.html", 'target="_blank" rel="noopener noreferrer"', '')),
        (s6_structure, lambda o: edit(o, "index.html", "</main>", "<h1>Second</h1></main>")),
        (s6_structure, lambda o: edit(o, "index.html", 'alt=""', '')),
        (s7_traceability, lambda o: (o / "explorer-data.json").write_text((o / "explorer-data.json").read_text().replace('"qa": "dqap"', '"qa": "nope"', 1))),
        (s8_contact, lambda o: edit(o, "index.html", 'href="https://forms.cloud.microsoft/e/SLBvuPX7jK"', 'href="https://forms.cloud.microsoft/e/WRONG1"')),
        (s9_wording, lambda o: edit(o, "policy.html", "<h1>", "<h1>The three tests ")),
        (s12_agent_open_sources, lambda o: None),
        (s11_no_unagreed_promises, lambda o: edit(o, "index.html", "<h1>", "<h1>We reply within 5 working days. ")),
        (s13_topics_grouped, lambda o: edit(o, "questions.html", '<h3 class="topic-h" id="topic-implementation">', '<h3 class="topic-h" id="topic-roles2">Roles and governance</h3><h3 class="topic-h" id="topic-implementation">')),
        (s14_css_vars_defined, lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".x{color:var(--ink)}")),
        (s15_class_collisions, lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + "\n.stages li { margin: 0; }")),
        (s10_class_collision, lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + "\n.bar { height: 1rem; }")),
    ]
    bad = []
    tpl = ROOT / "teams" / "declarativeAgent.template.json"; orig = tpl.read_text()
    try:
        tpl.write_text(orig.replace('"name": "WebSearch"', '"name": "OneDriveAndSharePoint"'))
        if not s12_agent_open_sources(out): bad.append("NEGATIVE s12_agent_open_sources did not fail on its broken copy")
    finally:
        tpl.write_text(orig)
    lic = ROOT / "LICENSE"; lic_orig = lic.read_text()
    try:
        lic.write_text("All rights reserved.\n")
        if not s16_repo_licences(out): bad.append("NEGATIVE s16_repo_licences did not fail on its broken copy")
        if not s19_no_tracked_build_outputs(out, ["README.md", "tests/__pycache__/check.cpython-313.pyc"]): bad.append("NEGATIVE s19_no_tracked_build_outputs did not fail on its broken copy")
        if not s19_no_tracked_build_outputs(out, ["README.md", "inputs/notes.txt"]): bad.append("NEGATIVE s19_no_tracked_build_outputs did not fail on inputs/")
    finally:
        lic.write_text(lic_orig)
    # FD: the DQAP tool must fail when its parts are broken (examples not detected, DQV link dropped, protected files not recognised)
    for name, x, y in (("examples left in", "p.examples++; return;", "return;"),
                       ("DQV measurement link", "ds['dqv:hasQualityMeasurement'].push(ref(mm['@id']));", ""),
                       ("protected file", "if (u8[0] === 0xD0 && u8[1] === 0xCF) throw new Error('protected');", ""),
                       ("template fractions shown as percentages", "return n == null ? norm(v) : String(Math.round(n * 1e4) / 100);", "return norm(v);")):
        o = mutate(lambda o: edit(o, "assets/dqap.js", x, y))
        if not f_dqap(o): bad.append(f"NEGATIVE f_dqap did not fail when the tool was broken: {name}")
    cases = [c for c in cases if c[0] is not s12_agent_open_sources]
    for check, breaker in cases:
        o = mutate(breaker)
        if not check(o): bad.append(f"NEGATIVE {check.__name__} did not fail on its broken copy")
        shutil.rmtree(o.parent)
    # browser negatives: overflow (B1), contrast (B4), script error (B3)
    for label, breaker, needle in [
        ("B1", lambda o: edit(o, "index.html", "</main>", '<pre class="wide-test">' + "x" * 400 + "</pre></main>") or (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".wide-test{white-space:pre;overflow:visible}"), "B1"),
        ("B4", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".lead{color:#bbbbbb !important}"), "B4"),
        ("B5", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".home-hero h1{color:#fff}"), "B5"),
        ("B6", lambda o: edit(o, "index.html", "</main>", '<button class="drawer-toggle" type="button">On this page</button></main>'), "B6"),
        ("B7", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".roadmap li{display:flex!important;flex-wrap:wrap}.rm-t{flex-basis:100%}"), "B7"),
        ("B8", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".st-opt b{grid-column:auto;overflow-wrap:anywhere;width:3.5rem}"), "B8"),
        ("B9", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".qa summary{display:flex!important;flex-wrap:wrap!important}.qa summary .qwrap{flex-basis:100%}"), "B9"),
        ("B3", lambda o: (o / "assets" / "explorer.js").write_text((o / "assets" / "explorer.js").read_text() + "\nundefinedFunctionCall();"), "B3"),
    ]:
        o = mutate(breaker); f, _ = browser_checks(o, quick=True)
        if not any(x.startswith(needle) for x in f): bad.append(f"NEGATIVE {label} did not fail on its broken copy")
        shutil.rmtree(o.parent)
    return bad, len(cases) + 9

def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else ROOT / "out"
    total_fail = []
    for c in STATIC:
        r = c(out); print(f"{'PASS' if not r else 'FAIL'} {c.__name__}: {c.__doc__.splitlines()[0]}" + ("" if not r else f"\n   {r[:6]}")); total_fail += r
    f = functional_checks(out); print(f"{'PASS' if not f else 'FAIL'} functional: {len(f)} failures" + ("" if not f else f"\n   " + "\n   ".join(f[:12]))); total_fail += f
    b, runs = browser_checks(out); print(f"{'PASS' if not b else 'FAIL'} browser: {runs} page loads ({len(pages(out))} pages x 3 widths x 3 themes), axe WCAG 2.2 AA, reflow, nav width, script errors" + ("" if not b else "\n   " + "\n   ".join(b[:20]))); total_fail += b
    if "--negative" in sys.argv:
        n, k = negatives(out); print(f"{'PASS' if not n else 'FAIL'} negative tests: {k} breakages, each caught" + ("" if not n else "\n   " + "\n   ".join(n))); total_fail += n
    print("ALL PASS" if not total_fail else f"{len(total_fail)} FAILURES")
    sys.exit(1 if total_fail else 0)

if __name__ == "__main__":
    main()
