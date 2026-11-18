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
AXE = Path("/home/claude/tooling/node_modules/axe-core/axe.min.js")
BANNED = [r"Office of the Chief Data Officer", r"\bOCDO\b", r"Data Management Team", r"Data Quality (?:&amp;|&) Management team", r"dam-return-and-desk",
          r"beisgov\.sharepoint\.com"]
CONTACT = "https://github.com/cyberdudeuk/dam-capability-playbooks/issues/new?template=contact.yml"

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
    """D-01: the contact form link is the one verified to exist (dam-capability-playbooks contact.yml)."""
    bad = []
    for f in pages(out):
        for h in re.findall(r'(?:href|data-contact)="([^"]*issues/new[^"]*)"', f.read_text()):
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

STATIC = [s10_class_collision, s1_banned, s2_emails, s3_csp, s4_links, s5_external, s6_structure, s7_traceability, s8_contact, s9_wording]

# ---------------- browser checks ----------------
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(out):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(out)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"

WIDTHS = [320, 768, 1280]
THEMES = ["light", "dark", "contrast"]

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
                    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
                    pg.add_script_tag(content=axe)
                    res = pg.evaluate("axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']},resultTypes:['violations']}).then(r=>r.violations.map(v=>v.id+' x'+v.nodes.length+' '+(v.nodes[0]&&v.nodes[0].target.join(' '))))")
                    if res: fails.append(f"B4 {f.name} {theme} {w}px: {res[:3]}")
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
            ({"official": "unsure", "purpose": ["1"], "shared": "dsa", "accountable": "own", "source": "source"}, "check"),
            ({"official": "yes", "purpose": ["unsure"], "shared": "unsure", "accountable": "own", "source": "source"}, "check"),
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
        # F11: works with JavaScript turned off (content readable)
        ctx = b.new_context(java_script_enabled=False); p2 = ctx.new_page()
        for f in ("index.html", "questions.html", "people.html"):
            p2.goto(base + f)
            if len(p2.inner_text("main")) < 400: fails.append(f"F11 {f} has little content without JavaScript")
        ctx.close(); b.close()
    srv.shutdown()
    return fails

# ---------------- negative tests: each check must fail on a broken copy ----------------
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
        (s5_external, lambda o: edit(o, "index.html", 'target="_blank" rel="noopener noreferrer"', '')),
        (s6_structure, lambda o: edit(o, "index.html", "</main>", "<h1>Second</h1></main>")),
        (s6_structure, lambda o: edit(o, "index.html", 'alt=""', '')),
        (s7_traceability, lambda o: (o / "explorer-data.json").write_text((o / "explorer-data.json").read_text().replace('"qa": "dqap"', '"qa": "nope"', 1))),
        (s8_contact, lambda o: edit(o, "index.html", "dam-capability-playbooks/issues/new", "elsewhere/issues/new")),
        (s9_wording, lambda o: edit(o, "policy.html", "<h1>", "<h1>The three tests ")),
        (s10_class_collision, lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + "\n.bar { height: 1rem; }")),
    ]
    bad = []
    for check, breaker in cases:
        o = mutate(breaker)
        if not check(o): bad.append(f"NEGATIVE {check.__name__} did not fail on its broken copy")
        shutil.rmtree(o.parent)
    # browser negatives: overflow (B1), contrast (B4), script error (B3)
    for label, breaker, needle in [
        ("B1", lambda o: edit(o, "index.html", "</main>", '<pre class="wide-test">' + "x" * 400 + "</pre></main>") or (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".wide-test{white-space:pre;overflow:visible}"), "B1"),
        ("B4", lambda o: (o / "assets" / "explorer.css").write_text((o / "assets" / "explorer.css").read_text() + ".lead{color:#bbbbbb !important}"), "B4"),
        ("B3", lambda o: (o / "assets" / "explorer.js").write_text((o / "assets" / "explorer.js").read_text() + "\nundefinedFunctionCall();"), "B3"),
    ]:
        o = mutate(breaker); f, _ = browser_checks(o, quick=True)
        if not any(x.startswith(needle) for x in f): bad.append(f"NEGATIVE {label} did not fail on its broken copy")
        shutil.rmtree(o.parent)
    return bad, len(cases) + 3

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
