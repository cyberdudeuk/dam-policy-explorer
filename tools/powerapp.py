#!/usr/bin/env python3
"""Generate the Power Apps (canvas, phone layout) edition of the DAM Policy Explorer.

One source of content: the same content.py / examples.py and built pages (out/) that the web explorer uses.
Outputs to pa/:
  formulas.fx          -> App.Formulas (named formulas holding all content as tables)
  screens/NN-Name.yaml -> one screen each, pasted into Power Apps Studio (tree view > Paste)
  report.txt           -> counts, used to reconcile the app against the web build

Run after tools/build.py. Checks at the end fail the run (exit 1) on any breach.
"""
import re, sys, pathlib, os, json, hashlib
from bs4 import BeautifulSoup, NavigableString, Comment

HERE = pathlib.Path(__file__).resolve().parent.parent
ROOT = pathlib.Path(os.environ.get("DPE_ROOT", HERE))   # DPE_ROOT points at an older checkout when building a baseline
sys.path.insert(0, str(ROOT / "tools"))
import content as C   # noqa: E402
if (ROOT / "tools" / "examples.py").exists():
    import examples as X   # noqa: E402
else:                      # releases before 1.2.0 had no worked examples (D-PA8: do not fall back to today's file when building an old baseline)
    class X: EXAMPLES, TOPICS = [], []

OUT, PA = ROOT / "out", pathlib.Path(os.environ.get("DPE_PA_OUT", HERE / "pa"))   # DPE_PA_OUT: write somewhere else (used by the negative tests)
BASELINE = PA / "baseline.json"   # what the previous release contained: {"version": "...", "items": {key: hash}}
SITE = "https://cyberdudeuk.github.io/dam-policy-explorer/"
NATIVE = {"index.html", "asset-test.html", "questions.html", "examples.html", "glossary.html"}   # rebuilt as native screens
READER = [  # (file, short title, group, one-line summary)
    ("policy.html", "The policy", "Understand", "What the policy asks, who it applies to and who does what"),
    ("return.html", "Your return", "Do", "The twelve steps of the Baseline Return"),
    ("track.html", "Track your return", "Do", "What happens after you send it, and what it shows"),
    ("people.html", "Roles and journeys", "Understand", "Who does what, by role"),
    ("capabilities.html", "Capabilities", "Understand", "The capabilities behind the policy"),
    ("embed.html", "Embed it", "Do", "Make the policy part of how you work"),
    ("resources.html", "Resources", "Find", "Templates, guidance and playbooks"),
    ("guide.html", "User guide", "Help", "How to use the explorer, and how to get it in your organisation"),
    ("ask.html", "Ask a question", "Help", "How to ask, and what happens next"),
    ("team.html", "For the GDS team", "Help", "Process returns and answer questions"),
    ("about.html", "About this app", "Help", "Sources, method, versions and roadmap"),
    ("accessibility.html", "Accessibility", "Help", "Accessibility and inclusion statement"),
]
DROP = {"svg", "nav", "aside", "form", "fieldset", "button", "input", "select", "textarea", "option", "label", "noscript", "script", "style", "img", "legend"}
KEEP = {"p", "ul", "ol", "li", "b", "strong", "em", "i", "a", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td", "caption", "br", "code", "pre"}
REPO = "https://github.com/cyberdudeuk/dam-policy-explorer"   # the repository that hosts the web explorer: its issue forms take bugs and ideas
BANNED = re.compile(r"OCDO|Office of the Chief Data Officer|Data Management Team|sharepoint\.com|@dsit\.gov|@[a-z0-9-]+\.gov\.uk", re.I)


def fx(s):
    """A Power Fx string literal."""
    return '"' + re.sub(r"\s+", " ", str(s)).strip().replace('"', '""') + '"'


def absurl(href):
    if not href or href.startswith("#"):
        return None
    if re.match(r"^(https?:|mailto:)", href):
        return href if href.startswith("http") else None
    return SITE + href


def clean(node):
    """Reduce a parsed fragment to the small HTML subset the HtmlViewer control renders. Output is built, never passed through."""
    out = []
    for ch in node.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            out.append(str(ch).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
        t = ch.name
        cls = ch.get("class") or []
        if t in DROP or ch.has_attr("hidden") or "vh" in cls or "permalink" in cls:
            continue
        inner = clean(ch)
        if not inner.strip() and t not in ("br", "td", "th"):
            continue
        if t == "a":
            u = absurl(ch.get("href"))
            out.append(f'<a href="{u}">{inner}</a>' if u else inner)
        elif t in ("th",):
            out.append(f'<th style="text-align:left;border-bottom:2px solid #8a9095;padding:6px">{inner}</th>')
        elif t in ("td",):
            out.append(f'<td style="vertical-align:top;border-bottom:1px solid #8a9095;padding:6px">{inner}</td>')
        elif t == "table":
            out.append(stack_table(ch))
        elif t == "caption":
            out.append(f'<caption style="text-align:left;font-weight:bold;padding:6px 0">{inner}</caption>')
        elif t in KEEP:
            out.append(f"<{t}>{inner}</{t}>" if t != "br" else "<br>")
        elif t in ("summary", "dt", "figcaption", "h5", "h6"):
            out.append(f"<p><b>{inner}</b></p>")
        elif t == "dd":
            out.append(f"<p>{inner}</p>")
        elif t == "span" and ({"prov", "badge", "verdict-pill", "pill", "asked"} & set(cls) or any(c.startswith("prov-") for c in cls)):
            out.append(f" <b>[{inner.strip()}]</b> ")
        elif t in ("div", "section", "article", "details", "dl", "figure", "header", "footer", "main", "blockquote"):
            out.append(inner if re.search(r"<(p|ul|ol|table|h3|h4)\b", inner) else f"<p>{inner}</p>")
        else:
            out.append(inner)
    return "".join(out)


def stack_table(tbl):
    """A table rewritten as one short block per row ("Heading: value"), so it fits a phone without scrolling sideways and reads in order."""
    cap = tbl.find("caption")
    heads = [text_of(str(th)) for th in (tbl.find("thead").find_all("th") if tbl.find("thead") else [])]
    out = [f"<p><b>{clean(cap)}</b></p>"] if cap else []
    body = tbl.find("tbody") or tbl
    for tr in body.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells or (not tbl.find("thead") and tr.find_parent("thead")):
            continue
        first = clean(cells[0]).strip()
        items = "".join(f"<li><b>{heads[i]}:</b> {clean(c)}</li>" if i < len(heads) and heads[i] else f"<li>{clean(c)}</li>" for i, c in enumerate(cells[1:], 1) if clean(c).strip())
        out.append(f"<p><b>{first}</b></p>" + (f"<ul>{items}</ul>" if items else ""))
    return "".join(out)


def text_of(html):
    return re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ")).strip()


def page_sections(fn):
    soup = BeautifulSoup((OUT / fn).read_text(encoding="utf-8"), "html.parser")
    main = soup.find("main")
    h1 = main.find("h1")
    title = text_of(str(h1))
    for el in main.find_all(["aside", "nav"]):
        el.decompose()
    # walk top-level flow after h1, splitting on h2 at any depth: flatten wrappers that contain an h2
    def flow(node):
        for ch in list(node.children):
            if getattr(ch, "name", None) and ch.name != "h2" and ch.find("h2"):
                yield from flow(ch)
            else:
                yield ch
    secs, cur_h, cur = [], "Overview", BeautifulSoup("<div></div>", "html.parser").div
    for ch in flow(main):
        if getattr(ch, "name", None) == "h1":
            continue
        if getattr(ch, "name", None) == "h2":
            secs.append((cur_h, cur))
            cur_h, cur = text_of(str(ch)), BeautifulSoup("<div></div>", "html.parser").div
            continue
        cur.append(ch.__copy__() if hasattr(ch, "__copy__") else ch)
    secs.append((cur_h, cur))
    res = []
    for h, node in secs:
        html = clean(node)
        if len(text_of(html)) < 25:
            continue
        res.append((re.sub(r"\s*\d+$", "", h).strip() or "Overview", html))
    return title, res


def build_tables():
    rep = []
    pages, sections = [], []
    for fn, short, group, summ in READER:
        if not (OUT / fn).exists():
            continue
        title, secs = page_sections(fn)
        pid = fn[:-5]
        pages.append((pid, short, title, PAGE_SEC[pid], summ, len(secs)))
        for i, (h, html) in enumerate(secs, 1):
            sections.append((pid, i, h, html))
        rep.append(f"page {pid}: {len(secs)} sections, {sum(len(x[1]) for x in secs)} chars")
    # questions: text and answers from the content source; sources appended
    qas = []
    for q in sorted(C.QA, key=lambda q: C.TOPICS.index(q["topic"])):
        body = clean(BeautifulSoup(q["a"], "html.parser"))
        src = "".join(f'<li><a href="{u}">{t}</a></li>' if u else f"<li>{t}</li>" for t, u in q["src"])
        if src:
            body += f"<p><b>Sources</b></p><ul>{src}</ul>"
        prov = C.PROV[q["prov"]]
        body = f"<p><b>[{prov[0]}]</b> {prov[1]}</p>" + body
        qas.append((q["id"], q["topic"], prov[0], q["q"], body, text_of(body)[:600]))
    rep.append(f"questions: {len(qas)}")
    KIND = {"in": "In scope", "out": "Out of scope", "depends": "It depends", "fill": "Filling in the return", "role": "Roles", "process": "Process", "": "Scenario"}
    exs = []
    for (eid, title, topics, sector, scen, outcome, kind, status, links) in X.EXAMPLES:
        lk = "".join(f'<li><a href="{SITE}{l}">{l.split(".")[0].replace("-", " ").capitalize()}: related guidance</a></li>' for l in links)
        st = "Agreed" if status == "agreed" else "Being agreed"
        body = f"<p><b>[{KIND[kind]}]</b> <b>[{st}]</b> {sector}</p><p>{scen}</p>" + (f"<p><b>Outcome.</b> {outcome}</p>" if outcome else "<p><b>Outcome.</b> Not yet agreed. Treat this as a scenario to discuss, not a ruling.</p>") + (f"<ul>{lk}</ul>" if lk else "")
        exs.append((eid, title, "; ".join(topics), sector, KIND[kind], st, body, scen[:300]))
    rep.append(f"examples: {len(exs)} ({sum(1 for e in exs if e[5]=='Agreed')} agreed)")
    glo = [(t, d) for _, t, d in sorted(C.GLOSSARY, key=lambda g: g[1].lower())]
    rep.append(f"glossary: {len(glo)}")
    return pages, sections, qas, exs, glo, rep


class Raw(str):
    """A Power Fx expression written into a table as-is (an icon or a colour), not as a string."""


def manifest(sections, qas, exs, glo):
    """One hash per item a reader can open. Comparing two manifests says what is new and what has changed."""
    h = lambda t: hashlib.sha1(re.sub(r"\s+", " ", text_of(t) if "<" in t else t).strip().encode()).hexdigest()[:12]
    m = {f"sec:{s[0]}:{s[2]}": h(s[3]) for s in sections}
    m.update({f"qa:{q[0]}": h(q[3] + " " + q[4]) for q in qas})
    m.update({f"ex:{e[0]}": h(e[1] + " " + e[6]) for e in exs})
    m.update({f"glo:{g[0]}": h(g[1]) for g in glo})
    return m


def flagger(now):
    """Returns (function key -> "New" | "Updated" | ""), baseline version). No baseline means nothing to compare, so no flags."""
    if not BASELINE.exists():
        return (lambda k: ""), ""
    base = json.loads(BASELINE.read_text())
    old = base["items"]
    return (lambda k: "New" if k not in old else ("Updated" if old[k] != now[k] else "")), base["version"]


def table(name, cols, rows):
    recs = ",\n".join("  {" + ", ".join(f"{c}: {(str(v) if isinstance(v, (int, Raw)) else fx(v))}" for c, v in zip(cols, r)) + "}" for r in rows)
    return f"{name} = Table(\n{recs}\n);\n"


def _steps():
    soup = BeautifulSoup((OUT / "return.html").read_text(encoding="utf-8"), "html.parser")
    out = []
    for i in range(1, 13):
        el = soup.find(id=f"step-{i}")
        h = el.find(["h3", "h2", "summary"]) or el
        out.append(re.sub(r"^\d+\.\s*", "", text_of(str(h))))
    return out


STEPS = _steps()
# (title, one line, colour, tint, pale RGB for the background artwork)
SECTIONS = [("Understand the policy", "What it asks, who it applies to and who does what", "RGBA(11,85,163,1)", "RGBA(230,238,247,1)", (120, 170, 235)),
            ("Decide what is in scope", "Test an asset, compare examples, look for a match", "RGBA(0,105,92,1)", "RGBA(224,240,238,1)", (90, 200, 185)),
            ("Make your return", "The twelve steps, sending it, tracking it and keeping it current", "RGBA(11,107,58,1)", "RGBA(231,243,236,1)", (130, 205, 150)),
            ("Find an answer", "Questions, search, glossary and resources", "RGBA(90,47,138,1)", "RGBA(238,232,245,1)", (175, 145, 230)),
            ("Get help", "How to use this app, how to ask, and what it is built on", "RGBA(138,74,0,1)", "RGBA(247,237,224,1)", (240, 185, 110)),
            ("Your area and more", "Your progress and saved items, the team page and the web explorer", "RGBA(156,31,92,1)", "RGBA(247,230,239,1)", (235, 140, 185))]
# Tutorials: (id, title, one line, minutes, where "Try it now" goes: kind, ref, icon, steps)
TUTORIALS = [
    ("around", "Find your way around", "The six sections, the main navigation and how pages work", 2, "home", "", "Waypoint", [
        ("Home is in six numbered sections", "They follow the order you will need them: 1 understand the policy, 2 decide what is in scope, 3 make and send your return, 4 find an answer, 5 get help, 6 your area. Each section has its own colour and lists its own links."),
        ("The main navigation is always there", "On a phone it is the bar at the bottom of the screen. On a laptop or large tablet it moves to the top right. It has Home, Asset test, Questions, Examples and My area."),
        ("Long pages are split into sections", "A page shows one section at a time. Use Next and Previous at the bottom, or Contents to jump. The bar under the title shows how far through you are."),
        ("Search from Home", "The search box on Home looks across pages, answers, examples and the glossary. Type two or more letters."),
        ("Save what you need", "Choose Save on any page section, answer, example or word. You will find them again in My area, under Saved."),
        ("Know where an answer comes from", "Every answer carries a label: Policy, GDS position, Suggested practice, Programme plan or Open. If anything here disagrees with GOV.UK, GOV.UK is right.")]),
    ("scope", "Decide whether an asset is in scope", "Use the asset test and the worked examples", 3, "test", "", "CheckBadge", [
        ("Open the Asset test", "Choose Asset test in the main navigation, or in section 2 on Home."),
        ("Name the asset if you want to", "The name only labels your result. It stays on this device."),
        ("Answer five questions, one at a time", "Choose an answer, then Next. For the purposes question you can choose several. If you do not know, choose Not sure: the test will tell you what to confirm."),
        ("Read the result", "There are four possible results: include it, include it if you have time, include it provisionally and flag it, or leave it out. The result gives the reason and the next step."),
        ("Compare with worked examples", "Open Examples and filter by In scope, Out of scope or It depends to find a case like yours."),
        ("Find your tested assets later", "They are listed in My area, under Tested.")]),
    ("match", "Look for a match in the National Data Library", "Check whether the data set is already listed on data.gov.uk", 2, "match", "", "Link", [
        ("Open Matchmaker", "It is in section 2 on Home, and at the end of an asset test result."),
        ("Describe the data asset", "One or two sentences about what the data is. Leave out anything sensitive: your search words are sent to data.gov.uk when you search."),
        ("Narrow it down if you can", "Publisher, topic and format are optional. They are added to the search words."),
        ("Search", "Matchmaker picks the key words from your description and opens the results on data.gov.uk in your browser. You can also search with your exact words."),
        ("Use what you find", "If the same data set is listed, use its title and publisher so your return describes it the same way. If nothing matches, note that too.")]),
    ("return", "Work through your return", "The twelve steps, and how to keep track", 3, "page", "return", "DetailList", [
        ("Open Your return", "It is in section 3 on Home. The page takes you through the twelve steps of the Baseline Return."),
        ("Read one section at a time", "Use Next and Previous. Use Contents to jump to a step."),
        ("Mark steps as done", "Open My area and choose Progress. Select a step to mark it done, and again to undo it. The bar shows how many of the twelve you have finished."),
        ("See what happens after you send it", "Track your return, also in section 3, explains what happens next and what the return shows.")]),
    ("answers", "Find, read and save an answer", "Questions and answers, search and the glossary", 2, "questions", "", "QuestionMark", [
        ("Open Questions", "Choose Questions in the main navigation."),
        ("Filter or search", "Choose a topic to filter the list, or type a word in the search box. The count shows how many answers match."),
        ("Read the answer and its source", "Open an answer to read it. The label at the top says where it comes from, and the sources are listed at the end."),
        ("Save it", "Choose Save. Saved answers are kept in My area, under Saved."),
        ("Check a word", "The Glossary, in section 4 on Home, explains the terms the policy uses.")]),
    ("access", "Use it your way", "Keyboard, screen reader, phone, tablet or laptop", 2, "page", "accessibility", "View", [
        ("Keyboard", "Use Tab and Shift+Tab to move between controls, and Enter or Space to choose. The control you are on has a thick yellow outline."),
        ("Screen reader", "Each screen has one main heading and section headings you can jump between. Counts and results are announced when they change. Icons that only decorate are hidden from screen readers."),
        ("Any screen size", "Everything fits the width of your screen: one column on a phone, two or three on larger screens, and nothing scrolls sideways. Turn a phone or tablet on its side to give wide content more room."),
        ("Long sections", "A long section scrolls with the page. With a keyboard, move to Save at the top of the section, then use the arrow keys or Page Down. Previous, Contents and Next are at the end of each section."),
        ("Motion", "The background moves slowly. It stops if your device is set to reduce motion.")]),
]
GO = {"test": "ScrTest", "match": "ScrMatch", "questions": "ScrQuestions", "examples": "ScrExamples", "me": "ScrMe", "learn": "ScrLearn", "support": "ScrSupport", "search": "ScrSearch", "glossary": "ScrGlossary"}
SCREEN_TUT = {"Pg": "around", "Rd": "answers", "Qs": "answers", "Ex": "scope", "Gl": "answers", "Sr": "answers", "Ts": "scope", "Me": "return", "Mt": "match"}
PAGE_SEC = {"policy": 1, "people": 1, "capabilities": 1, "return": 3, "track": 3, "embed": 3, "resources": 4, "guide": 5, "ask": 5, "about": 5, "accessibility": 5, "team": 6}


def bg_svg(rgb):
    """Pale 'liquid glass' backdrop for one section: soft drifting pools of the section's colour on white.
    Generated artwork (no stock or third-party imagery). Motion is slow, and stops when the device asks for reduced motion."""
    r, g, b = rgb
    c = f"rgb({r},{g},{b})"
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 1200' preserveAspectRatio='xMidYMid slice'>"
            "<style>@keyframes f{to{transform:translate(46px,-34px) scale(1.08)}}@keyframes g{to{transform:translate(-40px,30px) scale(.94)}}.a{animation:f 24s ease-in-out infinite alternate}.b{animation:g 30s ease-in-out infinite alternate}@media (prefers-reduced-motion:reduce){.a,.b{animation:none}}</style>"
            f"<defs><filter id='s' x='-30%' y='-30%' width='160%' height='160%'><feGaussianBlur stdDeviation='60'/></filter><linearGradient id='l' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#fff'/><stop offset='1' stop-color='{c}' stop-opacity='.16'/></linearGradient></defs>"
            "<rect width='800' height='1200' fill='#fff'/><rect width='800' height='1200' fill='url(#l)'/>"
            f"<g filter='url(#s)'><circle class='a' cx='640' cy='210' r='230' fill='{c}' opacity='.30'/><circle class='b' cx='120' cy='620' r='260' fill='{c}' opacity='.22'/><circle class='a' cx='610' cy='1040' r='250' fill='{c}' opacity='.26'/></g>"
            "<path d='M-20 330 C 200 250, 420 420, 820 300' fill='none' stroke='#fff' stroke-width='3' opacity='.7'/><path d='M-20 900 C 260 820, 520 980, 820 880' fill='none' stroke='#fff' stroke-width='2' opacity='.6'/></svg>")


# Splash artwork: generated for this app. Liquid ribbons and glass drops, each drop holding a data motif (a data store,
# a document, a table), joined by fine lines: data assets being found, described and matched.
SPLASH_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 1200' preserveAspectRatio='xMidYMid slice'>"
              "<style>@keyframes u{to{transform:translateY(-22px)}}@keyframes v{to{transform:translate(18px,16px)}}@keyframes w{to{stroke-dashoffset:-48}}.u{animation:u 9s ease-in-out infinite alternate}.v{animation:v 12s ease-in-out infinite alternate}.w{animation:w 6s linear infinite}@media (prefers-reduced-motion:reduce){.u,.v,.w{animation:none}}</style>"
              "<defs><linearGradient id='b' x1='0' y1='0' x2='.6' y2='1'><stop offset='0' stop-color='#0b55a3'/><stop offset='.55' stop-color='#083e78'/><stop offset='1' stop-color='#052a55'/></linearGradient>"
              "<radialGradient id='o' cx='.35' cy='.3' r='.8'><stop offset='0' stop-color='#fff' stop-opacity='.55'/><stop offset='.5' stop-color='#9fd8ff' stop-opacity='.20'/><stop offset='1' stop-color='#fff' stop-opacity='.08'/></radialGradient>"
              "<linearGradient id='r' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#00c2a8' stop-opacity='.0'/><stop offset='.5' stop-color='#3fd0ff' stop-opacity='.55'/><stop offset='1' stop-color='#b48cff' stop-opacity='.0'/></linearGradient>"
              "<filter id='s'><feGaussianBlur stdDeviation='26'/></filter></defs>"
              "<rect width='800' height='1200' fill='url(#b)'/>"
              "<g filter='url(#s)'><path class='v' d='M-60 250 C 160 120, 360 380, 560 230 S 860 180, 900 300' fill='none' stroke='url(#r)' stroke-width='90'/><path class='u' d='M-60 520 C 200 420, 380 640, 620 500 S 880 470, 900 560' fill='none' stroke='url(#r)' stroke-width='70'/></g>"
              "<g fill='none' stroke='#bfe6ff' stroke-width='2' stroke-dasharray='6 10' opacity='.75'><path class='w' d='M190 235 L400 150'/><path class='w' d='M400 150 L620 265'/><path class='w' d='M190 235 L330 420'/><path class='w' d='M620 265 L500 430'/></g>"
              "<g class='u'><circle cx='190' cy='235' r='62' fill='url(#o)' stroke='#fff' stroke-opacity='.6' stroke-width='2'/><g fill='none' stroke='#fff' stroke-width='5' stroke-linecap='round'><ellipse cx='190' cy='215' rx='24' ry='9'/><path d='M166 215v36c0 5 11 9 24 9s24-4 24-9v-36'/><path d='M166 233c0 5 11 9 24 9s24-4 24-9'/></g></g>"
              "<g class='v'><circle cx='400' cy='150' r='48' fill='url(#o)' stroke='#fff' stroke-opacity='.6' stroke-width='2'/><g fill='none' stroke='#fff' stroke-width='4.5' stroke-linecap='round' stroke-linejoin='round'><path d='M384 126h22l12 12v36h-34z'/><path d='M391 150h18M391 160h18'/></g></g>"
              "<g class='u'><circle cx='620' cy='265' r='56' fill='url(#o)' stroke='#fff' stroke-opacity='.6' stroke-width='2'/><g fill='none' stroke='#fff' stroke-width='4.5' stroke-linecap='round'><rect x='594' y='243' width='52' height='44' rx='5'/><path d='M594 258h52M594 272h52M612 243v44'/></g></g>"
              "<g class='v'><circle cx='330' cy='420' r='34' fill='url(#o)' stroke='#fff' stroke-opacity='.5' stroke-width='2'/><path d='M318 420l9 9 16-18' fill='none' stroke='#7ff0d8' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/></g>"
              "<g class='u'><circle cx='500' cy='430' r='28' fill='url(#o)' stroke='#fff' stroke-opacity='.5' stroke-width='2'/><g fill='none' stroke='#fff' stroke-width='4' stroke-linecap='round'><circle cx='497' cy='427' r='9'/><path d='M504 434l8 8'/></g></g>"
              "<rect y='560' width='800' height='640' fill='#052a55' opacity='.35'/></svg>")

LOGO_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='#0b55a3'/><ellipse cx='27' cy='20' rx='13' ry='5' fill='none' stroke='#fff' stroke-width='3.2'/>"
            "<path d='M14 20v20c0 2.8 5.8 5 13 5' fill='none' stroke='#fff' stroke-width='3.2' stroke-linecap='round'/><path d='M14 30c0 2.8 5.8 5 13 5' fill='none' stroke='#fff' stroke-width='3.2' stroke-linecap='round'/>"
            "<path d='M40 20v6' stroke='#fff' stroke-width='3.2' stroke-linecap='round'/><circle cx='43' cy='42' r='9.5' fill='#00a88f' stroke='#fff' stroke-width='3.2'/><path d='M43 36.5l2.2 4.5-4.4 1.1z' fill='#fff'/><path d='M43 47.5l-2.2-4.5 4.4-1.1z' fill='#fff' opacity='.75'/></svg>")
PURPOSES = ["Delivering public services", "A legislative, legal or contractual requirement", "Defence, national security and resilience", "Developing and evaluating policy", "Official statistics", "The public interest", "Fraud and error"]
TEST_Q = [
    ("official", "Is it classified OFFICIAL?", "OFFICIAL with markings such as sensitive counts. SECRET and TOP SECRET do not.", [("yes", "Yes"), ("no", "No, it is SECRET or TOP SECRET"), ("unsure", "Not sure")]),
    ("purpose", "Which critical purposes does it serve?", "Principle 1, a critical criterion. Choose all that apply, or none.", [(str(i), f"{i}. {p}") for i, p in enumerate(PURPOSES, 1)] + [("unsure", "Not sure")]),
    ("shared", "How is it shared?", "Principle 2, shared. Choose the best fit.", [("dsa", "Shared with a public sector organisation under a data sharing agreement"), ("open", "Published as open data"), ("potential", "Not shared yet, but could create value if it were"), ("no", "Only used inside our organisation"), ("unsure", "Not sure")]),
    ("accountable", "Who is accountable for it?", "Principle 3, accountable.", [("own", "We manage or control it"), ("enriched", "It came from another organisation, and we have materially changed or enriched it"), ("asis", "It came from another organisation and we use it as it is"), ("unsure", "Not sure")]),
    ("source", "Is it the source data?", "Principle 4, prioritise the source.", [("source", "Yes, it is the source data set"), ("product", "No, it is an extract, report, API or product, but it is managed and owned in its own right"), ("derived", "No, it is an extract, report, API or product drawn from source data"), ("unsure", "Not sure")]),
]


def formulas(pages, sections, qas, exs, glo):
    now = manifest(sections, qas, exs, glo)
    fl, base_ver = flagger(now)
    sec_f = {(s[0], s[1]): fl(f"sec:{s[0]}:{s[2]}") for s in sections}
    agg = lambda fs: "New" if fs and all(x == "New" for x in fs) else ("Updated" if any(fs) else "")
    page_f = {p[0]: agg([v for (pid, _), v in sec_f.items() if pid == p[0]]) for p in pages}
    some = lambda fs: "New" if "New" in fs else ("Updated" if "Updated" in fs else "")
    kind_f = {"questions": some([fl(f"qa:{q[0]}") for q in qas]), "examples": some([fl(f"ex:{e[0]}") for e in exs]), "glossary": some([fl(f"glo:{g[0]}") for g in glo])}
    f = "// DAM Policy Explorer content. Generated by tools/powerapp.py from the web explorer's source. Do not edit by hand.\n"
    f += LAYOUT_FX
    f += f'nfVersion = "{C.VERSION}";\nnfChecked = "{C.CONTENT_CHECKED}";\nnfSite = "{SITE}";\n'
    f += f'nfBaseVer = "{base_ver}";\nnfNotes = {fx(C.CHANGES[0][2])};\n'
    f += table("nfPages", ["id", "short", "title", "sec", "summ", "n", "flag"], [(*p, page_f[p[0]]) for p in pages])
    f += table("nfSections", ["pid", "n", "h", "x", "flag"], [(*s, sec_f[(s[0], s[1])]) for s in sections])
    PC = {"Policy": ("RGBA(11,85,163,1)", "RGBA(230,238,247,1)"), "GDS position": ("RGBA(0,105,92,1)", "RGBA(224,240,238,1)"), "Suggested practice": ("RGBA(90,47,138,1)", "RGBA(238,232,245,1)"), "Programme plan": ("RGBA(138,74,0,1)", "RGBA(247,237,224,1)"), "Open": ("RGBA(163,38,26,1)", "RGBA(251,233,231,1)")}
    f += table("nfQA", ["id", "topic", "prov", "q", "x", "t", "col", "tint", "flag"], [(*q, Raw(PC[q[2]][0]), Raw(PC[q[2]][1]), fl(f"qa:{q[0]}")) for q in qas])
    KC = {"In scope": ("CheckBadge", "RGBA(11,107,58,1)", "RGBA(231,243,236,1)"), "Out of scope": ("CancelBadge", "RGBA(163,38,26,1)", "RGBA(251,233,231,1)"), "It depends": ("Warning", "RGBA(138,74,0,1)", "RGBA(253,241,225,1)"),
          "Filling in the return": ("DetailList", "RGBA(11,85,163,1)", "RGBA(230,238,247,1)"), "Roles": ("People", "RGBA(90,47,138,1)", "RGBA(238,232,245,1)"), "Process": ("Sync", "RGBA(0,105,92,1)", "RGBA(224,240,238,1)"), "Scenario": ("LevelsLayersItems", "RGBA(74,79,84,1)", "RGBA(242,243,244,1)")}
    f += table("nfEx", ["id", "title", "topics", "sector", "kind", "stat", "x", "t", "ic", "col", "tint", "flag"], [(*e, Raw("Icon." + KC[e[4]][0]), Raw(KC[e[4]][1]), Raw(KC[e[4]][2]), fl(f"ex:{e[0]}")) for e in exs])
    f += table("nfGlo", ["term", "def", "flag"], [(*g, fl(f"glo:{g[0]}")) for g in glo])
    f += table("nfTopics", ["topic"], [("All",)] + [(t,) for t in C.TOPICS if any(q[1] == t for q in qas)])
    f += table("nfExKinds", ["kind"], [("All",)] + [(k,) for k in ["In scope", "Out of scope", "It depends", "Filling in the return", "Roles", "Process", "Scenario"] if any(e[4] == k for e in exs)])
    f += table("nfTestQ", ["n", "key", "q", "hint", "multi"], [(i, k, q, h, 1 if k == "purpose" else 0) for i, (k, q, h, _) in enumerate(TEST_Q, 1)])
    f += table("nfTestOpt", ["key", "v", "label"], [(k, v, lab) for k, _, _, opts in TEST_Q for v, lab in opts])
    # Six sections, in the order a coordinator, owner or steward meets them: understand, decide scope, do the return, find answers, get help, own area.
    home = [(1, "The policy in plain English", "What the policy asks, who it applies to and who does what", "page", "policy", "Journal"),
            (1, "Roles and journeys", "Who does what, by role", "page", "people", "People"),
            (1, "Capabilities", "The capabilities behind the policy", "page", "capabilities", "Waypoint"),
            (2, "Asset test", "Five questions: is this a critical data asset?", "test", "", "CheckBadge"),
            (2, "Worked examples", f"{len(exs)} examples of what is in scope and what is not", "examples", "", "LevelsLayersItems"),
            (2, "Matchmaker", "Is the same or a related data set already in the National Data Library?", "match", "", "Link"),
            (3, "Your return", "The twelve steps of the Baseline Return", "page", "return", "DetailList"),
            (3, "Track your return", "What happens after you send it", "page", "track", "RadarActivityMonitor"),
            (3, "Embed it", "Make the policy part of how you work", "page", "embed", "Tools"),
            (4, "Questions and answers", f"{len(qas)} answers, each showing its source", "questions", "", "QuestionMark"),
            (4, "Search everything", "Pages, answers, examples and glossary", "search", "", "Search"),
            (4, "Glossary", f"{len(glo)} words explained", "glossary", "", "Tag"),
            (4, "Resources", "Templates, guidance and playbooks", "page", "resources", "Folder"),
            (5, "User guide", "How to use this app", "page", "guide", "Journal"),
            (5, "Tutorials and tours", "Short walk-throughs of the main tasks", "learn", "", "Lightbulb"),
            (5, "Support and contact", "Get help or ask a question", "support", "", "Message"),
            (5, "Report a bug or suggest an idea", "Opens the public forms on GitHub", "feedback", "", "Bug"),
            (5, "About this app", "Sources, method, versions and roadmap", "page", "about", "Information"),
            (5, "Accessibility", "Accessibility and inclusion statement", "page", "accessibility", "View"),
            (6, "My area", "Your progress, saved items and tested assets", "me", "", "Person"),
            (6, "For the GDS team", "Process returns and answer questions", "page", "team", "OfficeBuilding"),
            (6, "Open the full web explorer", "Opens in your browser", "web", "", "OpenInNewWindow")]
    f += table("nfHome", ["sec", "title", "summ", "kind", "ref", "ic", "col", "tint", "flag"], [(*h[:5], Raw("Icon." + h[5]), Raw(SECTIONS[h[0] - 1][2]), Raw(SECTIONS[h[0] - 1][3]), page_f.get(h[4], "") if h[3] == "page" else kind_f.get(h[3], "")) for h in home])
    f += table("nfSect", ["n", "title", "blurb", "col", "tint"], [(n, t, bl, Raw(c), Raw(ti)) for n, (t, bl, c, ti, _) in enumerate(SECTIONS, 1)])
    for n, sec in enumerate(SECTIONS, 1):
        f += f'nfBg{n} = "data:image/svg+xml;utf8," & EncodeUrl("{bg_svg(sec[4])}");\n'
    f += 'nfSplashArt = "data:image/svg+xml;utf8," & EncodeUrl("' + SPLASH_SVG + '");\n'
    f += table("nfNdlTopics", ["v"], [(t,) for t in ["Any", "Environment", "Crime and justice", "Government", "Mapping", "Society", "Towns and cities", "Education", "Health", "Transport"]])
    f += table("nfNdlFormats", ["v"], [(t,) for t in ["Any", "CSV", "JSON", "XML", "GEOJSON", "XLS", "WMS", "WFS", "KML", "PDF"]])
    f += table("nfStop", ["w"], [(w,) for w in "data dataset datasets asset assets about with from that this which their there have been will each used uses using also into over such they were what when your information records record held holds hold contains containing including includes across between other every where than then them these those some more most only very being would could should".split()])
    f += table("nfTut", ["id", "title", "summ", "mins", "kind", "ref", "ic"], [(t[0], t[1], t[2], t[3], t[4], t[5], Raw("Icon." + t[6])) for t in TUTORIALS])
    f += table("nfTutSteps", ["tid", "n", "h", "t"], [(t[0], i, h, x) for t in TUTORIALS for i, (h, x) in enumerate(t[7], 1)])
    f += f'nfContact = "{C.CONTACT}";\nnfStale = {C.STALE_AFTER_DAYS};\n'
    f += table("nfSupTabs", ["tab"], [("Get help",), ("Contact us",), ("Feedback",)])
    f += f'nfRepo = "{REPO}";\n'
    f += table("nfReqTypes", ["v"], [(t,) for t in ["A question about the policy", "A problem with this app", "An accessibility problem", "A suggestion", "Something else"]])
    f += table("nfSupport", ["title", "summ", "kind", "ref", "ic"], [(t, su, k, r, Raw("Icon." + ic)) for t, su, k, r, ic in [
        ("Tutorials and tours", "Short walk-throughs of the main tasks", "learn", "", "Lightbulb"),
        ("User guide", "How to use this app", "page", "guide", "Journal"),
        ("Questions and answers", "Check whether your question is already answered", "questions", "", "QuestionMark"),
        ("How to ask a policy question", "Who to ask, and what happens next", "page", "ask", "Message"),
        ("Accessibility", "What works, what does not yet, and how to tell us", "page", "accessibility", "View"),
        ("About this app", "Version, sources, method and what is planned", "page", "about", "Information"),
        ("Report a problem or suggest something", "Write a message and open the contact form", "contact", "", "Send")]])
    f += table("nfSteps", ["n", "title"], [(i, t) for i, t in enumerate(STEPS, 1)])
    f += table("nfRoles", ["role", "tip"], [("Lead coordinator", "Start with Your return, then Track your return."), ("Chief data officer", "Start with The policy in plain English, then Roles and journeys."), ("Data owner", "Start with the Asset test, then Worked examples."),
                                            ("Data steward", "Start with Your return, step 7: fill in the 24 details."), ("Exploring", "Start with The policy in plain English, or take the tour.")])
    f += table("nfMeTabs", ["tab"], [("Progress",), ("Saved",), ("Tested",), ("Settings",)])
    f += f'nfStats = "{len(qas)} answers · {len(exs)} worked examples · {len(glo)} words explained";\n'
    f += 'nfFirst = With({n: User().FullName}, If("," in n, Trim(First(Split(Last(Split(n, ",")).Value, "(")).Value), First(Split(n, " ")).Value));\n'
    f += 'nfLogo = "data:image/svg+xml;utf8," & EncodeUrl("' + LOGO_SVG + '");\n'
    f += table("nfNav", ["n", "label", "ic"], [(i, l, Raw("Icon." + ic)) for i, (l, ic) in enumerate([("Home", "Home"), ("Asset test", "CheckBadge"), ("Questions", "QuestionMark"), ("Examples", "LevelsLayersItems"), ("Search", "Search")])])
    tour = [("Welcome", "This app answers questions about the Data Asset Management Policy. Every answer shows where it comes from."),
            ("Six sections, in order", "Home has six numbered sections in the order you will need them: understand, decide what is in scope, make your return, find an answer, get help, and your own area."),
            ("Test an asset", "The asset test asks five questions and tells you whether an asset goes in your return, and why."),
            ("Find a match", "Matchmaker checks whether the same or a related data set is already listed in the National Data Library on data.gov.uk."),
            ("Read a page", "Long pages are split into sections. Use Contents, Previous and Next to move around."),
            ("If it disagrees with GOV.UK", "This is a prototype. If anything here disagrees with GOV.UK, GOV.UK is right.")]
    f += table("nfTour", ["n", "h", "t"], [(i, h, t) for i, (h, t) in enumerate(tour, 1)])
    idx = [("Page", p[1] + ": " + s[2], "page", p[0], s[1], text_of(s[3])[:500], sec_f[(s[0], s[1])]) for p in pages for s in sections if s[0] == p[0]]
    idx += [("Answer", q[3], "qa", q[0], 0, q[5], fl(f"qa:{q[0]}")) for q in qas]
    idx += [("Example", e[0] + " " + e[1], "ex", e[0], 0, e[7], fl(f"ex:{e[0]}")) for e in exs]
    idx += [("Glossary", g[0], "glo", g[0], 0, g[1], fl(f"glo:{g[0]}")) for g in glo]
    f += f"nfNewCount = {sum(1 for r in idx if r[6])};\n"
    IC = {"Page": ("Journal", "RGBA(11,85,163,1)", "RGBA(230,238,247,1)"), "Answer": ("QuestionMark", "RGBA(0,105,92,1)", "RGBA(224,240,238,1)"), "Example": ("LevelsLayersItems", "RGBA(138,74,0,1)", "RGBA(247,237,224,1)"), "Glossary": ("Tag", "RGBA(90,47,138,1)", "RGBA(238,232,245,1)")}
    f += table("nfIndex", ["type", "title", "kind", "ref", "n", "t", "flag", "ic", "col", "tint"], [(*r, Raw("Icon." + IC[r[0]][0]), Raw(IC[r[0]][1]), Raw(IC[r[0]][2])) for r in idx])
    return f.replace("{N}", str(len(idx))), len(idx)


# ---------- screens ----------
# Design basis (recorded in docs/power-apps-edition.md):
#  - Government Design Principles and GOV.UK Design System patterns (one thing per page, plain language, phase banner,
#    tags, yellow focus state). The app is not on service.gov.uk, so it must not use the crown, the GOV.UK logotype or
#    GDS Transport (Service Manual, "Making your service look like GOV.UK"); it keeps the web explorer's own identity.
#  - App conventions: search-led home, bottom tab bar on phones that becomes top navigation on wide screens,
#    cards with icon tiles, colour used with text and icons, never alone.
#  - Responsive: "App layout: Responsive", so sizes are real pixels and every position comes from the live window size.
BRAND, INK, MUTED, SOFT, LINE, WHITE, FOCUS = "RGBA(11,85,163,1)", "RGBA(27,27,27,1)", "RGBA(74,79,84,1)", "RGBA(242,243,244,1)", "RGBA(138,144,149,1)", "RGBA(255,255,255,1)", "RGBA(255,221,0,1)"
BRAND_D, CLEAR = "RGBA(8,62,120,1)", "RGBA(0,0,0,0)"
OK_BG, WARN_BG, BAD_BG = "RGBA(231,243,236,1)", "RGBA(253,241,225,1)", "RGBA(251,233,231,1)"
OK_C, WARN_C, BAD_C = "RGBA(11,107,58,1)", "RGBA(138,74,0,1)", "RGBA(163,38,26,1)"
LAYOUT_FX = """nfCW = Min(App.Width - 64, 2360);
nfCX = (App.Width - nfCW) / 2;
nfRW = Min(App.Width - 64, 1520);
nfRX = (App.Width - nfRW) / 2;
nfWide = App.Width >= 1800;
nfNavH = If(nfWide, 0, 120);
nfPad = Max(0, nfCX - 32);
nfCols = If(App.Width >= 2200, 3, App.Width >= 1280, 2, 1);
nfCols2 = If(App.Width >= 1800, 2, 1);
nfCompact = App.Width < 1280;
nfDesign = App.Width = 640 && App.Height = 1136;
nfShort = App.Height < 1100;
nfTiny = App.Width < 720;
nfTiles = nfCompact || (nfShort && !nfWide);
"""
BAR, BTNH, S_BODY, S_SMALL, S_H2, S_LEAD, NAVW = 64, 48, 13, 11, 18, 15, 108
SEC_ROWS = 6; SEC_H = 92 + SEC_ROWS * 48 + 18; TILE_H = 92
PH = "(Parent.Height - nfNavH)"
SB = "(nfShort && !nfWide)"   # short and not wide: a phone held sideways
SHEET_Y = "If(nfShort, 8, 84)"   # top of the Home section sheet (84 = bar + 20)
SCROLL = {"ScrSupport": "Su", "ScrMatch": "Mt", "ScrTest": "Ts", "ScrMe": "Me", "ScrLearn": "Ln", "ScrPage": "Pg", "ScrRead": "Rd"}   # screens whose content scrolls as one page (D-PA15)
FADE = "ScreenTransition.Fade"


UNSCALED = []
GUARDED, UNGUARDED = [], []
K = 2   # phone-layout canvas apps use doubled units: a 375-point phone reports App.Width = 750
LENGTH_PROPS = {"X", "Y", "Width", "Height", "Size", "PaddingLeft", "PaddingRight", "PaddingTop", "PaddingBottom", "RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight",
                "BorderThickness", "FocusedBorderThickness", "TemplateSize", "TemplatePadding"}
_NUM = re.compile(r"(?<![A-Za-z_\d.])(\d+(?:\.\d+)?)(?![A-Za-z_\d.])")


def scale(v):
    """Multiply the lengths in a formula by K. A number that is a factor or divisor (next to * or /) is a ratio, not a length, and is left alone."""
    v = re.sub(r"\bpt\((\d+(?:\.\d+)?)\)", lambda m: f"raw({int(float(m.group(1)) * K)})", v)   # pt(n): a length written out in full; doubled here, once (D-PA19)
    v = re.sub(r"\braw\((\d+)\)", lambda m: "\x00" + "".join(chr(97 + int(d)) for d in m.group(1)) + "\x00", v)   # raw(n): a count, not a length; never doubled
    def f(m):
        before, after = v[:m.start()].rstrip(), v[m.end():].lstrip()
        if before.endswith(("*", "/")) or after.startswith(("*", "/")):
            return m.group(1)
        n = float(m.group(1)) * K
        return str(int(n)) if n == int(n) else str(n)
    v = _NUM.sub(f, v)
    return re.sub("\x00([a-j]+)\x00", lambda m: "".join(str(ord(c) - 97) for c in m.group(1)), v)


ROW_DESIGN_H = 1600   # design height of the scrolling row, in pixels. At run time the row is as tall as its content; this is only the limit Studio checks positions against (D-PA23)


def scroll_wrap(pfx, children):
    """D-PA15: put a screen's content inside a one-row gallery, which scrolls by touch, wheel and keyboard focus.
    The backdrop, header, navigation, anything pinned to the bottom of the window and the pop-up sheets stay outside."""
    fixed = {pfx + x for x in ("Bg", "Bar", "Rib", "Back", "Logo", "Title", "Help")}
    names = {c[0] for c in children}
    def chrome(c):
        n = c[0]
        return (n in fixed or "Nav" in n or "Shade" in n or "Sheet" in n or (n.endswith("Opts") and n[:-4] + "Shade" in names)
                or ("Toc" in n and n != pfx + "Toc"))      # the contents list is an overlay: it must not scroll away with the page
    def pinned(c): return not chrome(c) and "Parent.Height" in str(c[2].get("Y", ""))      # buttons and bars that stay at the bottom of the window
    body = [c for c in children if not chrome(c) and not pinned(c)]
    if not body: return children
    terms, panels = [], []
    for c in body:
        fills = "Parent.Height" in str(c[2].get("Height", ""))      # sized to the window: a list, a block of page text or a background panel
        if fills and c[1] == GAL:                                   # a list keeps a usable height on a short window
            c[2]["Height"] = f"Max(pt(200), {c[2]['Height']})"; terms.append(f"If({c[0]}.Visible, {c[0]}.Y + pt(200), 0)")
        elif fills and c[1] == HTM and not c[0].endswith("Panel"):
            # D-PA24: long page text grows to its full length inside the scrolling row, so the page scrolls by touch, wheel and keyboard
            # (arrow keys and Page Down, from any button on the page). Tested in Studio: AutoHeight needs a positive height to start from.
            c[2]["AutoHeight"] = "true"; c[2]["Height"] = "pt(100)"; terms.append(f"If({c[0]}.Visible, {c[0]}.Y + {c[0]}.Height, 0)")
        elif fills and c[0].endswith("Panel"): panels.append(c)
        elif not fills: terms.append(f"If({c[0]}.Visible, {c[0]}.Y + {c[0]}.Height, 0)")
    for c in panels:                                                # the card behind the content reaches at least to the end of the content
        c[2]["Height"] = f"Max({c[2]['Height']}, {pfx}End.Y - ({c[2]['Y']}) + pt(12))"
    # D-PA20: a fixed-height row does not learn the height of its own auto-height text (TemplateSize is not re-evaluated when a label inside grows),
    # so the last lines of a long tab sat behind the navigation with nothing to scroll. A flexible-height row follows its content; the clear spacer
    # at the end (first in the list, so beneath everything and never in the way of a tap) keeps the last control above the navigation and above
    # whatever is pinned to the bottom of the window in the current state.
    for c in children:                                              # a new section, step or question starts at the top of the page
        if pinned(c) and c[1] == BTN and "OnSelect" in c[2]: c[2]["OnSelect"] = f"{c[2]['OnSelect']}; Reset({pfx}Scroll)"
    stack = "".join(f", If({c[0]}.Visible, (Parent.Height - nfNavH) - {c[0]}.Y, 0)" for c in children if pinned(c))
    end = (pfx + "End", RECT, {"Fill": "RGBA(0,0,0,0)", "BorderThickness": 0, "TabIndex": -1, "AccessibleLabel": '""', "X": 0, "Y": f"Max({', '.join(terms)})", "Width": 2,
                               "Height": f"nfNavH + pt(16) + Max(0{stack})" if stack else "nfNavH + pt(16)"})
    wrap = (pfx + "Scroll", GAL, {"Items": "[1]", "X": 0, "Y": 0, "Width": "Parent.Width", "Height": "Parent.Height", "TemplatePadding": 0, "ShowScrollbar": "true", "TabIndex": -1,
                                  "TemplateSize": f"pt({ROW_DESIGN_H})", "AccessibleLabel": '"Page content"', "Transition": "Transition.None"}, [end] + body, "VariableHeight")
    out, placed = [], False
    for c in children:
        if c in body: continue
        out.append(c)
        if not placed and c[0] == pfx + "Bg": out.append(wrap); placed = True
    assert placed, pfx
    return out


ROW_HIDE = {"ScrPage": "!gToc"}
TABBABLE = ("Classic/Button", "Classic/TextInput", "Classic/Toggle")


def modal_guard(children):
    """D-PA26: while a sheet is open over a screen, nothing behind it may take keyboard focus (WCAG 2.2, 2.4.3 and 2.4.11).
    A sheet is every top-level control that shares its Visible formula with a control named ...Shade. Everything else that
    has a tab stop, at any depth, gives it up while any sheet on the screen is open."""
    opens = []
    for c in children:
        if c[0].endswith("Shade") and c[2].get("Visible") and c[2]["Visible"] not in opens: opens.append(c[2]["Visible"])
    if not opens: return children
    m = " || ".join(f"({o})" for o in opens) if len(opens) > 1 else opens[0]
    def guard(c):
        pr = c[2]
        if str(pr.get("TabIndex", 0 if c[1].startswith(TABBABLE) else -1)).strip() == "0": pr["TabIndex"] = f"If({m}, -1, 0)"
        for k in (c[3] if len(c) > 3 and c[3] else []): guard(k)
    for c in children:
        if c[2].get("Visible") not in opens: guard(c)
    return children


class Y:
    """Tiny YAML writer for Power Apps 'paste code'. Every formula is a block scalar, so no quoting rules to get wrong."""
    def __init__(self): self.l = []
    def w(self, ind, s): self.l.append(" " * ind + s)
    def props(self, ind, props):
        self.w(ind, "Properties:")
        for k in sorted(props):
            v = str(props[k])
            if k in LENGTH_PROPS:
                for m in re.finditer(r"[*/]\s*(\d+(?:\.\d+)?)(?![\d.])|(?<![\d.])(\d+(?:\.\d+)?)\s*[*/]", re.sub(r"(?:pt|raw)\(\d+\)", "", v)):
                    n = float(m.group(1) or m.group(2))
                    if n > 12: UNSCALED.append(f"{k}: {v[:80]}")   # D-PA10: looks like a length used as a factor; write pt(n)
                v = scale(v)
            v = re.sub(r"\braw\((\d+)\)", r"\1", v)
            self.w(ind + 2, f"{k}: |-")
            for i, line in enumerate(v.split("\n")):
                self.w(ind + 4, ("=" if i == 0 else "") + line)
    def ctl(self, ind, name, control, props, children=None, variant=None, guard=False):
        self.w(ind, f"- {name}:")
        self.w(ind + 4, f"Control: {control}")
        if variant: self.w(ind + 4, f"Variant: {variant}")
        if ind == 6 or guard:
            props = dict(props)
            # inside the scrolling row the limit is the row's design height (TemplateSize), not the window: content below the fold is still inside it,
            # so nothing is squeezed on a 320 x 568 phone or on the Studio canvas (D-PA23)
            for pos, size, par in (("X", "Width", "Parent.Width"), ("Y", "Height", "Parent.TemplateHeight" if guard else "Parent.Height")):
                own = (f"Self.{pos}", f"{name}.{pos}")
                if pos in props and size in props:      # a size written in terms of its own position is rewritten in terms of the position formula (Studio evaluated it with the position at 0)
                    for o in own: props[size] = str(props[size]).replace(o, f"({props[pos]})")
                if pos in props and not any(o in str(props.get(size, "")) for o in own):
                    props[pos] = f"If(nfDesign, Max(0, Min({props[pos]}, {par} - Self.{size})), {props[pos]})"; GUARDED.append(name)
                elif pos in props: UNGUARDED.append(f"{name}.{pos}")
        self.props(ind + 4, props)
        if children:
            self.w(ind + 4, "Children:")
            for c in children: self.ctl(ind + 6, *(list(c) + [None] * (5 - len(c))), guard=name.endswith("Scroll") and ind == 6)
    def screen(self, name, props, children):
        props = {"Width": "App.Width", "Height": "App.Height", **props}
        children = modal_guard(list(children))
        if name in SCROLL:
            children = scroll_wrap(SCROLL[name], list(children))
            if name in ROW_HIDE:    # D-PA26: an opaque panel covers the row, so the row and every link in it leave the tab order with it
                next(c for c in children if c[0] == SCROLL[name] + "Scroll")[2]["Visible"] = ROW_HIDE[name]
        self.w(0, "Screens:"); self.w(2, f"{name}:"); self.props(4, props); self.w(4, "Children:")
        for c in children: self.ctl(6, *c)
        return "\n".join(self.l) + "\n"


IMG = "Image@2.2.3"
LBL, BTN, ICON, RECT, TXT, GAL, HTM, TOG = "Label@2.5.1", "Classic/Button@2.2.0", "Classic/Icon@2.5.0", "Rectangle@2.3.0", "Classic/TextInput@2.3.2", "Gallery@2.15.0", "HtmlViewer@2.1.0", "Classic/Toggle@2.1.0"
FONT = "Font.'Open Sans'"


GLASS = ("border-radius:{r}px;background:linear-gradient(135deg,rgba(255,255,255,{a}),rgba(255,255,255,{b}));border:1px solid rgba(255,255,255,.95);"
         "box-shadow:0 8px 24px rgba(16,42,84,.10),inset 0 1px 0 rgba(255,255,255,.9);-webkit-backdrop-filter:blur(14px) saturate(1.4);backdrop-filter:blur(14px) saturate(1.4);box-sizing:border-box;overflow:hidden")


def glass(name, x, y, w, h, r=16, a=.94, b=.78, **p):
    """A translucent 'liquid glass' plate. Purely visual: an HTML text control holding one empty styled box, so it is
    not focusable and has nothing for a screen reader to announce. Text always sits on a plate, never on the artwork."""
    style = GLASS.format(r=r * K, a=a, b=b)
    d = {"HtmlText": f'"<div style=\'height:" & Max(0, Self.Height - 1) & "px;{style}\'></div>"', "X": x, "Y": y, "Width": w, "Height": h, "PaddingTop": 0, "PaddingBottom": 0, "PaddingLeft": 0, "PaddingRight": 0, "Font": FONT, "Size": 1}
    d.update(p); return (name, HTM, d)


def backdrop(name, expr):
    return (name, IMG, {"Image": expr, "X": 0, "Y": 0, "Width": "Parent.Width", "Height": "Parent.Height", "ImagePosition": "ImagePosition.Fill", "TabIndex": -1, "AccessibleLabel": '""'})


def divider(name, num, text, y, col=BRAND, x="nfRX", w="nfRW", **p):
    """Section divider: number badge, heading, rule. Marks where one part ends and the next begins."""
    return [label(f"{name}N", num, X=x, Y=y, Width=28, Height=28, AutoHeight="false", Size=12, FontWeight="FontWeight.Bold", Color=WHITE, Fill=col, Align="Align.Center", VerticalAlign="VerticalAlign.Middle", **p),
            label(f"{name}H", text, X=f"{x} + 38", Y=y, Width=f"{w} - 38", Height=28, AutoHeight="false", Size=S_LEAD, FontWeight="FontWeight.Semibold", Role="TextRole.Heading2", VerticalAlign="VerticalAlign.Middle", Wrap="false", **p),
            rect(f"{name}R", col, X=x, Y=f"{y} + 34", Width=w, Height=2, **p)]


def rect(name, fill, **p):
    d = {"Fill": fill, "BorderThickness": 0, "TabIndex": -1}
    d.update(p); return (name, RECT, d)


def label(name, text, **p):
    d = {"Text": text, "Font": FONT, "Size": S_BODY, "Color": INK, "Width": "nfRW", "X": "nfRX", "PaddingLeft": 0, "PaddingRight": 0, "PaddingTop": 2, "PaddingBottom": 2, "AutoHeight": "true", "TabIndex": -1, "LineHeight": 1.35, "FocusedBorderThickness": 2, "FocusedBorderColor": FOCUS}
    d.update(p); return (name, LBL, d)


def button(name, text, onselect, **p):
    d = {"Text": text, "OnSelect": onselect, "Font": FONT, "Size": S_BODY, "Fill": BRAND, "Color": WHITE, "HoverFill": BRAND_D, "HoverColor": WHITE, "PressedFill": BRAND_D, "PressedColor": WHITE,
         "DisabledFill": SOFT, "DisabledColor": MUTED, "DisabledBorderColor": LINE,
         "BorderThickness": 0, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "RadiusTopLeft": 8, "RadiusTopRight": 8, "RadiusBottomLeft": 8, "RadiusBottomRight": 8, "Height": BTNH, "TabIndex": 0, "FontWeight": "FontWeight.Semibold"}
    d.update(p); return (name, BTN, d)


def secondary(name, text, onselect, **p):
    return button(name, text, onselect, **{**dict(Fill=WHITE, Color=BRAND, HoverFill=SOFT, HoverColor=BRAND, PressedFill=SOFT, PressedColor=BRAND, BorderThickness=2, BorderColor=BRAND), **p})


def deco(name, ic, x, y, size, color, **p):
    """A decorative icon: no tab stop, no accessible name; a click passes to the control it decorates."""
    d = {"Icon": ic, "Color": color, "X": x, "Y": y, "Width": size, "Height": size, "TabIndex": -1, "AccessibleLabel": '""', "FocusedBorderThickness": 2, "FocusedBorderColor": FOCUS}
    d.update(p); return (name, ICON, d)


def bar_icon(name, ic, x, onselect, lab, **p):
    d = {"Icon": ic, "Color": WHITE, "Height": BAR, "Width": 56, "X": x, "PaddingLeft": 16, "PaddingRight": 16, "PaddingTop": 20, "PaddingBottom": 20, "OnSelect": onselect, "AccessibleLabel": fx(lab), "TabIndex": 0, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4}
    d.update(p); return (name, ICON, d)


NAV = [("ScrHome", "Icon.Home", "Home"), ("ScrTest", "Icon.CheckBadge", "Asset test"), ("ScrQuestions", "Icon.QuestionMark", "Questions"), ("ScrExamples", "Icon.LevelsLayersItems", "Examples"), ("ScrMe", "Icon.Person", "My area")]
TIMER = "Timer@2.1.0"
SAVE = {c: f'IfError(SaveData({c}, "dpe{c[3:]}"), Blank())' for c in ("colSaved", "colDone", "colTested", "colPrefs", "colTut")}


def image(name, x, y, size, **p):
    d = {"Image": "nfLogo", "X": x, "Y": y, "Width": size, "Height": size, "ImagePosition": "ImagePosition.Fit", "TabIndex": -1, "AccessibleLabel": '""'}
    d.update(p); return (name, IMG, d)


def read(kind, title, html, k, ref, tr=None):
    """Open one answer, example or word in the reader, remembering what it is so it can be saved."""
    return f'Set(gReadKind, {kind}); Set(gReadTitle, {title}); Set(gReadHtml, {html}); Set(gReadK, "{k}"); Set(gReadRef, {ref}); Navigate(ScrRead, {tr or FADE})'


def open_ref():
    """Open a record that has kind / ref / n (search results and saved items)."""
    return f"""Switch(ThisItem.kind,
    "page", Set(gPid, ThisItem.ref); Set(gSec, ThisItem.n); Navigate(ScrPage, {FADE}),
    "qa", {read('"Answer"', 'LookUp(nfQA, id = ThisItem.ref).q', 'LookUp(nfQA, id = ThisItem.ref).x', 'qa', 'ThisItem.ref')},
    "ex", {read('"Example " & ThisItem.ref', 'LookUp(nfEx, id = ThisItem.ref).title', 'LookUp(nfEx, id = ThisItem.ref).x', 'ex', 'ThisItem.ref')},
    "glo", {read('"Glossary"', 'ThisItem.ref', '"<p>" & LookUp(nfGlo, term = ThisItem.ref).def & "</p>"', 'glo', 'ThisItem.ref')})"""


def save_toggle(name, key, rec, y, x="nfRX + nfRW - 104"):
    on = f"{key} in colSaved.key"
    return secondary(name, f'If({on}, "✓ Saved", "Save")', f'If({on}, RemoveIf(colSaved, key = {key}), Collect(colSaved, {rec})); {SAVE["colSaved"]}', X=x, Y=y, Width=104, Height=40, Size=S_SMALL)


def nav(pfx, active):
    """Main navigation: a bottom tab bar on phones and small tablets, the same five items in the top bar on wide screens."""
    c = [glass(f"{pfx}NavBg", 0, "Parent.Height - 60", "Parent.Width", 60, r=0, a=.97, b=.92, Visible="!nfWide"),
         rect(f"{pfx}NavLine", LINE, Y="Parent.Height - 60", Height=1, Width="Parent.Width", Visible="!nfWide")]
    for i, (scr, ic, lab) in enumerate(NAV):
        on = scr == active
        b = f"{pfx}Nav{i}"
        col = f"If(nfWide, {WHITE}, {BRAND if on else MUTED})"
        c.append(deco(f"{b}Ic", ic, f"{b}.X + ({b}.Width - 22) / 2", f"{b}.Y + If(nfWide, 12, 8)", 22, col))
        if on:
            c.append(rect(f"{b}On", f"If(nfWide, {WHITE}, {BRAND})", X=f"{b}.X + 14", Width=f"{b}.Width - 28", Height=3, Y=f"If(nfWide, {BAR - 3}, Parent.Height - 60)"))
        c.append(button(b, fx(lab), f"Navigate({scr}, ScreenTransition.None)", X=f"If(nfWide, Parent.Width - nfPad - {(len(NAV) - i) * NAVW}, {i} * Parent.Width / {len(NAV)})", Y="If(nfWide, 0, Parent.Height - 60)",
                        Width=f"If(nfWide, {NAVW}, Parent.Width / {len(NAV)})", Height=f"If(nfWide, {BAR}, 60)", Fill=CLEAR, Color=col, HoverColor=col, PressedColor=col,
                        HoverFill=f"If(nfWide, RGBA(255,255,255,0.16), {SOFT})", PressedFill=f"If(nfWide, RGBA(255,255,255,0.24), {SOFT})", Size=9, VerticalAlign="VerticalAlign.Bottom", PaddingBottom=7, PaddingLeft=0, PaddingRight=0,
                        FontWeight="FontWeight.Semibold" if on else "FontWeight.Normal", RadiusTopLeft=0, RadiusTopRight=0, RadiusBottomLeft=0, RadiusBottomRight=0))
    return c


def header(pfx, title, back=True, active=None, right=16, bg="nfBg1", ribbon=BRAND):
    """Backdrop, then the top bar: back, title (the screen's only Heading1), a ribbon in the section's colour, then the main navigation."""
    c = [backdrop(f"{pfx}Bg", bg), rect(f"{pfx}Bar", BRAND, Height=BAR, Width="Parent.Width"), rect(f"{pfx}Rib", ribbon, Y=BAR, Height=4, Width="Parent.Width")]
    if back:
        c.append(bar_icon(f"{pfx}Back", "Icon.ChevronLeft", "nfPad", "Back()", "Back"))
    else:
        c.append(image(f"{pfx}Logo", "nfPad + 14", 14, 36))
    tut = SCREEN_TUT.get(pfx)
    if tut: right = 64
    c.append(label(f"{pfx}Title", title, Color=WHITE, Size="If(nfTiny, 13, 16)", LineHeight=1.15, FontWeight="FontWeight.Semibold", Height=BAR, AutoHeight="false", X=f"nfPad + {56 if back else 72}",
                   Width=f"If(nfWide, Parent.Width - Self.X - nfPad - {len(NAV) * NAVW + 64}, Parent.Width - Self.X - {right})", VerticalAlign="VerticalAlign.Middle", Role="TextRole.Heading1", Wrap="nfTiny"))
    if tut:
        c.append(bar_icon(f"{pfx}Help", "Icon.Lightbulb", f"If(nfWide, Parent.Width - nfPad - {len(NAV) * NAVW + 56}, Parent.Width - 56)", f'Set(gTut, "{tut}"); Set(gTutStep, 1); Navigate(ScrLearn, {FADE})', "Tutorial for this screen"))
    return c + nav(pfx, active)


def open_item(tr=FADE):
    return f"""Switch(ThisItem.kind,
    "page", Set(gPid, ThisItem.ref); Set(gSec, 1); Navigate(ScrPage, {tr}),
    "test", Navigate(ScrTest, {tr}),
    "examples", Navigate(ScrExamples, {tr}),
    "questions", Navigate(ScrQuestions, {tr}),
    "search", Navigate(ScrSearch, {tr}),
    "glossary", Navigate(ScrGlossary, {tr}),
    "me", Navigate(ScrMe, {tr}),
    "match", Navigate(ScrMatch, {tr}),
    "learn", Set(gTut, Blank()); Navigate(ScrLearn, {tr}),
    "support", Navigate(ScrSupport, {tr}),
    "feedback", Set(gSupTab, "Feedback"); Navigate(ScrSupport, {tr}),
    "contact", Set(gSupTab, "Contact us"),
    "web", Launch(nfSite))"""


TITLE_2L = 50    # units a two-line card title needs at body size (points, not pixels)
CARD_MIN = 10 + TITLE_2L + 24 + 12   # top, title, second line, bottom
CARD_SUB = 36     # the second line sits this far above the bottom of the card
CARD_GEOM = []
CHAR_W = 11       # width allowed per character of a card title at body size, in pixels: Open Sans Semibold averages about 9.7, plus room for word wrap (estimate, checked by eye at 320 px)
LINE_H = 21       # one more line of card title, in pixels


def cards(name, items, onselect, title, sub, y, tmpl=88, extra=None, cols="1", wide=True, ic=None, col=BRAND, tint="RGBA(230,238,247,1)", alabel=None, flag=None):
    """A grid of cards. Each card is one rounded button (its text is the accessible name); the icon tile, title and
    second line sit on top. Columns follow the window width. Colour always comes with an icon and words.
    The card height follows the longest title in the list at the current width (one to five lines), D-PA17."""
    tw, th = "Parent.TemplateWidth", "Parent.TemplateHeight"
    tx = 74 if ic else 20
    cx, cw = ("nfCX", "nfCW") if wide else ("nfRX", "nfRW")
    longest = f"Max({items}, Len({title.replace('ThisItem.', '')}))"
    txf = f"If(nfCompact, 20, {tx})" if ic else str(tx)
    lines = f"Min(raw(5), Max(raw(1), RoundUp({longest} * pt({CHAR_W}) / (({cw} + 10) / {cols} - ({txf} + 54)), 0)))"
    size = f"{CARD_MIN} + ({lines} - raw(2)) * pt({LINE_H}) + If(nfCompact, pt(14), 0)"
    CARD_GEOM.append((name, 10 + TITLE_2L, CARD_MIN - CARD_SUB, TITLE_2L))
    ch = [glass(f"{name}Pl", 5, 5, f"{tw} - 10", f"{th} - 10", r=14), rect(f"{name}Acc", col, X=5, Y=19, Width=4, Height=f"{th} - 38")]
    if ic:
        ch.append(deco(f"{name}Ic", ic, 20, f"{th} / 2 - 21", 42, col, Fill=tint, PaddingLeft=10, PaddingRight=10, PaddingTop=10, PaddingBottom=10, Visible="!nfCompact"))
    if flag:   # NEW / UPDATED tag: words on a high-contrast tag, never colour alone
        ch.append(label(f"{name}Flag", f"Upper({flag})", X=f"{tw} - 116", Y=f"{th} - 36", Width=72, Height=20, AutoHeight="false", Size=8, FontWeight="FontWeight.Bold", Fill=FOCUS, Color=INK, Align="Align.Center", VerticalAlign="VerticalAlign.Middle", Visible=f"!IsBlank({flag})"))
        asub = f'{sub} & If(IsBlank({flag}), "", ". " & {flag} & " in this version")'
    sw_ = f" - If(IsBlank({flag}), 0, 80)" if flag else ""
    ch += [label(f"{name}T", title, FontWeight="FontWeight.Semibold", Color=INK, Size=S_BODY, X=txf, Y=10, Width=f"{tw} - ({txf} + 44)", AutoHeight="false", Height=f"{th} - {CARD_MIN - TITLE_2L} - If(nfCompact, 14, 0)", Wrap="true", VerticalAlign="VerticalAlign.Top", LineHeight=1.2),
           label(f"{name}S", sub, Color=MUTED, Size=S_SMALL, X=txf, Y=f"{th} - {CARD_SUB} - If(nfCompact, 14, 0)", Width=f"{tw} - ({txf} + 44){sw_}", AutoHeight="false", Height="If(nfCompact, 38, 24)", Wrap="nfCompact", VerticalAlign="VerticalAlign.Top", LineHeight=1.2),
           deco(f"{name}Chev", "Icon.ChevronRight", f"{tw} - 36", f"{th} / 2 - 10", 20, MUTED),
           (f"{name}Card", BTN, {"Text": f"{title} & \". \" & {asub if flag else sub}", "Color": CLEAR, "HoverColor": CLEAR, "PressedColor": CLEAR, "OnSelect": "Select(Parent)", "Fill": CLEAR, "HoverFill": "RGBA(11,85,163,0.06)", "PressedFill": "RGBA(11,85,163,0.14)",
                                 "BorderColor": "RGBA(138,144,149,0.55)", "BorderThickness": 1, "HoverBorderColor": col, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "X": 5, "Y": 5, "Width": f"{tw} - 10", "Height": f"{th} - 10", "TabIndex": 0,
                                 "RadiusTopLeft": 14, "RadiusTopRight": 14, "RadiusBottomLeft": 14, "RadiusBottomRight": 14, "Font": FONT, "Size": 8})]
    p = {"Items": items, "OnSelect": onselect, "Y": y, "X": f"{cx} - 5", "Width": f"{cw} + 10", "Height": f"{PH} - Self.Y", "TemplateSize": size, "TemplatePadding": 0, "ShowScrollbar": "true", "TabIndex": -1, "WrapCount": cols, "AccessibleLabel": fx(alabel or name)}
    if extra: p.update(extra)
    return (name, GAL, p, ch, "Vertical")


def chips(name, items, field, var, y, text=None, size=176):
    on = f"{var} = ThisItem.{field}"
    text = text or f"ThisItem.{field}"
    return (name, GAL, {"Items": items, "Y": y, "X": "nfCX - 4", "Width": "nfCW + 8", "Height": 52, "TemplateSize": size, "TemplatePadding": 4, "ShowScrollbar": "false", "ShowNavigation": "true", "TabIndex": -1, "OnSelect": f"Set({var}, ThisItem.{field})", "AccessibleLabel": '"Filters"'},
            [button(f"{name}B", f'If({on}, "✓ ", "") & {text}', "Select(Parent)", Height=44, Size=S_SMALL, Width="Parent.TemplateWidth", Fill=f"If({on}, {BRAND}, {WHITE})", Color=f"If({on}, {WHITE}, {BRAND})", HoverColor=f"If({on}, {WHITE}, {BRAND})", HoverFill=f"If({on}, {BRAND}, {SOFT})",
                    BorderThickness=2, BorderColor=BRAND, RadiusTopLeft=22, RadiusTopRight=22, RadiusBottomLeft=22, RadiusBottomRight=22)],
            "Horizontal")


def picker(name, items, field, var, y, lab, x="nfCX", w="Min(nfCW, 380)", vis=None, then=""):
    """A filter that never scrolls sideways: one button showing the current choice, opening a short list on a glass sheet.
    Returns (controls in the page, controls for the sheet). The sheet goes last on the screen so it sits above everything."""
    on = f"{var} = ThisItem.{field}"
    op = f'gPick = "{name}"'
    b = secondary(f"{name}Btn", f'"{lab}: " & {var} & "  ▾"', f'Set(gPick, "{name}"); SetFocus({name}Shade)', X=x, Y=y, Width=w, Height=44, Size=S_SMALL, Align="Align.Left", PaddingLeft=16)
    if vis: b[2]["Visible"] = vis
    sw = "Min(Parent.Width - 32, 420)"
    sheet = [button(f"{name}Shade", '"Close the list"', "Set(gPick, Blank())", X=0, Y=0, Width="Parent.Width", Height="Parent.Height", Fill="RGBA(0,0,0,0.55)", HoverFill="RGBA(0,0,0,0.55)", PressedFill="RGBA(0,0,0,0.55)", Color=CLEAR, HoverColor=CLEAR, PressedColor=CLEAR,
                    RadiusTopLeft=0, RadiusTopRight=0, RadiusBottomLeft=0, RadiusBottomRight=0, Visible=op),
             glass(f"{name}Sheet", f"(Parent.Width - {sw}) / 2", BAR + 20, sw, f"Min(Parent.Height - {BAR + 40}, 72 + CountRows({items}) * pt(52))", r=20, a=.99, b=.97, Visible=op),
             label(f"{name}SheetH", fx(lab), X=f"(Parent.Width - {sw}) / 2 + 20", Y=BAR + 36, Width=f"{sw} - 40", Visible=op, Size=S_LEAD, FontWeight="FontWeight.Semibold", Role="TextRole.Heading2"),
             (f"{name}Opts", GAL, {"Items": items, "X": f"(Parent.Width - {sw}) / 2 + 12", "Y": BAR + 76, "Width": f"{sw} - 24", "Height": f"Min(Parent.Height - {BAR + 108}, CountRows({items}) * pt(52))", "TemplateSize": 52, "TemplatePadding": 0, "ShowScrollbar": "true", "TabIndex": -1,
                                   "Visible": op, "AccessibleLabel": fx(lab), "OnSelect": f"Set({var}, ThisItem.{field}); {then}Set(gPick, Blank())"},
              [button(f"{name}Opt", f'If({on}, "✓  ", "") & ThisItem.{field}', "Select(Parent)", X=0, Y=3, Width="Parent.TemplateWidth - 10", Height=46, Align="Align.Left", PaddingLeft=16, FontWeight="FontWeight.Normal",
                      Fill=f"If({on}, {BRAND}, {WHITE})", Color=f"If({on}, {WHITE}, {INK})", HoverFill=f"If({on}, {BRAND}, {SOFT})", HoverColor=f"If({on}, {WHITE}, {INK})", BorderThickness=1, BorderColor=LINE)], "Vertical")]
    return [b], sheet


def segmented(name, items, field, var, y):
    """Tabs that share the width equally. On a narrow phone, more than two tabs take two rows (D-PA16)."""
    on = f"{var} = ThisItem.{field}"
    rows = f"If((nfTiny && CountRows({items}) > raw(2)) || (nfCompact && CountRows({items}) > raw(3)), raw(2), raw(1))"
    return (name, GAL, {"Items": items, "Y": y, "X": "nfCX - 4", "Width": "nfCW + 8", "Height": f"{rows} * pt(52)", "TemplateSize": 52, "TemplatePadding": 0, "WrapCount": f"RoundUp(CountRows({items}) / {rows}, 0)", "ShowScrollbar": "false", "TabIndex": -1,
                        "OnSelect": f"Set({var}, ThisItem.{field})", "AccessibleLabel": '"Tabs"'},
            [button(f"{name}B", f'If({on}, "✓ ", "") & ThisItem.{field}', "Select(Parent)", X=4, Y=4, Height=44, Size=S_SMALL, Width="Parent.TemplateWidth - 8", Fill=f"If({on}, {BRAND}, {WHITE})", Color=f"If({on}, {WHITE}, {BRAND})", HoverColor=f"If({on}, {WHITE}, {BRAND})", HoverFill=f"If({on}, {BRAND}, {SOFT})",
                    BorderThickness=2, BorderColor=BRAND, RadiusTopLeft=22, RadiusTopRight=22, RadiusBottomLeft=22, RadiusBottomRight=22)],
            "Vertical")


SHORT_HINT = {"QsSearch": "Search questions", "ExSearch": "Search examples", "SrSearch": "Search everything", "TsName": "For example, Vehicle records"}   # hints that would be cut on a phone (D-PA18)


def text_box(name, hint, y, **p):
    d = {"HintText": fx(hint), "AccessibleLabel": fx(hint), "Default": '""', "DelayOutput": "true", "Font": FONT, "Size": S_BODY, "Height": BTNH, "Y": y, "X": "nfCX", "Width": "Min(nfCW, 760)", "BorderColor": INK, "BorderThickness": 2, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "Color": INK, "Fill": WHITE, "HoverFill": WHITE, "HoverBorderColor": BRAND, "Clear": "true", "TabIndex": 0, "RadiusTopLeft": 8, "RadiusTopRight": 8, "RadiusBottomLeft": 8, "RadiusBottomRight": 8, "PaddingLeft": 44}
    d.update(p)
    if name in SHORT_HINT: d["HintText"] = f"If(nfCompact, {fx(SHORT_HINT[name])}, {d['HintText']})"   # the full wording stays in the accessible label
    return (name, TXT, d)


def search_field(name, hint, y):
    return [deco(f"{name}Ic", "Icon.Search", f"{name}.X + 12", f"{name}.Y + 13", 22, BRAND), text_box(name, hint, y, Fill=CLEAR, HoverFill=CLEAR)]


def html_view(name, expr, y, h, **p):
    d = {"HtmlText": expr, "Y": y, "X": "nfRX", "Width": "nfRW", "Height": h, "Font": FONT, "Size": S_BODY, "Color": INK, "PaddingTop": 4, "PaddingBottom": 16, "PaddingLeft": 0, "PaddingRight": 8}
    d.update(p); return (name, HTM, d)


def empty(name, gallery, text, vis_extra="true"):
    return [deco(f"{name}Ic", "Icon.Search", "(Parent.Width - 40) / 2", f"{gallery}.Y + 28", 40, LINE, Visible=f"{gallery}.AllItemsCount = 0 && {vis_extra}"),
            label(name, fx(text), Y=f"{gallery}.Y + 76", Align="Align.Center", Color=MUTED, Visible=f"{gallery}.AllItemsCount = 0 && {vis_extra}", Live="Live.Polite")]


def progress(pfx, y, frac, vis="true"):
    return [rect(f"{pfx}Trk", SOFT, X="nfRX", Y=y, Width="nfRW", Height=6, Visible=vis), rect(f"{pfx}Bar2", BRAND, X="nfRX", Y=y, Width=f"nfRW * {frac}", Height=6, Visible=vis)]


def screens():
    S = {}
    scr = {"Fill": WHITE, "LoadingSpinnerColor": BRAND}
    h2 = dict(Size=S_H2, FontWeight="FontWeight.Semibold", Role="TextRole.Heading2", LineHeight=1.2)
    small = dict(Size=S_SMALL, Color=MUTED)
    foot_y = f"{PH} - {BTNH + 10}"
    def footer(pfx, vis=None):
        r = rect(f"{pfx}Foot", SOFT, Y=f"{PH} - {BTNH + 20}", Height=BTNH + 20, Width="Parent.Width")
        if vis: r[2]["Visible"] = vis
        return r
    # --- Home ---
    tv = "gTour > 0"
    tw, tx = "Min(App.Width - 32, 520)", "(App.Width - Min(App.Width - 32, 520)) / 2"
    lead_v = "!nfCompact && !nfShort"
    jv = "nfWide || Parent.Height >= 820"
    hero_b = "If(nfNewCount > 0 && !nfWide && !(nfShort && !nfWide), HmNew.Y + HmNew.Height, HmSearch.Y + HmSearch.Height) + 12"
    S["01-ScrHome"] = Y().screen("ScrHome", {**scr, "OnVisible": 'If(IsBlank(gTour), Set(gTour, 0)); Set(gHomeSec, Blank()); If(gTour > 0, SetFocus(HmTourNext))'}, [
        *header("Hm", '"DAM Policy Explorer"', back=False, active="ScrHome", right=72),
        rect("HmHero", "RGBA(8,62,120,0.94)", Y=BAR, Height=f"{hero_b} - {BAR}", Width="Parent.Width"),
        bar_icon("HmTourIc", "Icon.Lightbulb", "Parent.Width - 56", "Set(gTour, 1); SetFocus(HmTourNext)", "Take the 1-minute tour", Visible="!nfWide"),
        label("HmLead", '"Everything you need for the Data Asset Management Policy, in one place."', Y=BAR + 14, Size=f"If(nfWide, 20, {S_LEAD})", FontWeight="FontWeight.Semibold", Color=WHITE, X="nfCX", Width="nfCW", Visible=lead_v, LineHeight=1.2),
        label("HmTag", '"PROTOTYPE"', Y=f"If(HmLead.Visible, HmLead.Y + HmLead.Height + 8, {BAR + 12})", X="nfCX", Width=92, Height=22, AutoHeight="false", Size=9, FontWeight="FontWeight.Bold", Fill=WHITE, Color=BRAND_D, Align="Align.Center", VerticalAlign="VerticalAlign.Middle"),
        label("HmProto", 'If(nfCompact || nfShort, "If this disagrees with GOV.UK, GOV.UK is right.", "If anything here disagrees with GOV.UK, GOV.UK is right. Content checked " & Text(DateValue(nfChecked), "d mmmm yyyy") & ". Version " & nfVersion & ".") & If(DateDiff(DateValue(nfChecked), Today()) > nfStale, " This is more than " & nfStale & " days ago: check GOV.UK for anything newer.", "")', Y="HmTag.Y", X="nfCX + 102", Width="nfCW - 102", Size=S_SMALL, Color=WHITE),
        rect("HmSearchBg", WHITE, X="HmSearch.X", Y="HmSearch.Y", Width="HmSearch.Width", Height="HmSearch.Height"),
        deco("HmSearchIc", "Icon.Search", "HmSearch.X + 12", "HmSearch.Y + 13", 22, BRAND),
        button("HmSearch", f'If(nfCompact || {SB}, "Search everything", "Search the policy, answers and examples")', f"Navigate(ScrSearch, {FADE})", X="nfCX", Y="Max(HmTag.Y + HmTag.Height, HmProto.Y + HmProto.Height) + 12", Width=f"If(nfWide, Min(nfCW - 484, 640), {SB}, nfCW - 272, nfCW)", Fill=CLEAR, Color=MUTED, HoverFill="RGBA(11,85,163,0.06)", HoverColor=INK, PressedFill="RGBA(11,85,163,0.14)", PressedColor=INK, Align="Align.Left", PaddingLeft=44, FontWeight="FontWeight.Normal", RadiusTopLeft=0, RadiusTopRight=0, RadiusBottomLeft=0, RadiusBottomRight=0),
        button("HmTourBtn", '"Take the 1-minute tour"', "Set(gTour, 1); SetFocus(HmTourNext)", Y="HmSearch.Y", X="HmSearch.X + HmSearch.Width + 12", Width=200, Fill=CLEAR, BorderColor=WHITE, BorderThickness=2, HoverFill="RGBA(255,255,255,0.16)", PressedFill="RGBA(255,255,255,0.24)", Visible="nfWide"),
        button("HmNew", f'If({SB}, "What is new (" & nfNewCount & ")", "What is new in version " & nfVersion & " (" & nfNewCount & ")")', f"Navigate(ScrNew, {FADE})", X=f"If(nfWide, HmTourBtn.X + HmTourBtn.Width + 12, {SB}, HmSearch.X + HmSearch.Width + 12, nfCX)", Y=f"If(nfWide || {SB}, HmSearch.Y, HmSearch.Y + HmSearch.Height + 8)", Width=f"If(nfWide || {SB}, 260, nfCW)", Height=f"If(nfWide || {SB}, 48, 36)", Size=S_SMALL,
               Fill=FOCUS, Color=INK, HoverFill="RGBA(255,235,90,1)", HoverColor=INK, PressedFill="RGBA(255,235,90,1)", PressedColor=INK, Visible="nfNewCount > 0"),
        label("HmSecsH", 'If(nfTiles, "Six sections, in order", "Start here: six sections, in the order you will need them")', Y=f"{hero_b} + 8", X="nfCX", Width="nfCW", **{**h2, "Size": S_BODY}),
        ("HmSecs", GAL, {"Items": "nfSect", "Y": "HmSecsH.Y + HmSecsH.Height + 4", "X": "nfCX - 6", "Width": "nfCW + 12", "Height": f"{PH} - Self.Y", "TemplateSize": SEC_H, "TemplatePadding": 0, "WrapCount": "nfCols", "ShowScrollbar": "true", "TabIndex": -1,
                         "AccessibleLabel": '"Sections"', "DisplayMode": f"If({tv}, DisplayMode.Disabled, DisplayMode.Edit)", "Visible": "!nfTiles"},
         [glass("HmSecPl", 6, 6, "Parent.TemplateWidth - 12", SEC_H - 12, r=18),
          rect("HmSecTop", "ThisItem.col", X=22, Y=6, Width="Parent.TemplateWidth - 44", Height=4),
          label("HmSecN", "ThisItem.n", X=22, Y=24, Width=36, Height=36, AutoHeight="false", Size=15, FontWeight="FontWeight.Bold", Color=WHITE, Fill="ThisItem.col", Align="Align.Center", VerticalAlign="VerticalAlign.Middle"),
          label("HmSecT", "ThisItem.title", X=70, Y=20, Width="Parent.TemplateWidth - 92", Height=26, AutoHeight="false", Wrap="false", Size=S_LEAD, FontWeight="FontWeight.Semibold", Role="TextRole.Heading2", Color="ThisItem.col"),
          label("HmSecB", "ThisItem.blurb", X=70, Y=44, Width="Parent.TemplateWidth - 92", Height=36, AutoHeight="false", Wrap="true", LineHeight=1.2, VerticalAlign="VerticalAlign.Top", **small),
          rect("HmSecRule", "ThisItem.tint", X=22, Y=86, Width="Parent.TemplateWidth - 44", Height=2),
          ("HmSecItems", GAL, {"Items": "Filter(nfHome, sec = ThisItem.n)", "X": 14, "Y": 92, "Width": "Parent.TemplateWidth - 28", "Height": SEC_ROWS * 48, "TemplateSize": 48, "TemplatePadding": 0, "ShowScrollbar": "false", "TabIndex": -1, "AccessibleLabel": '"Links in this section"', "OnSelect": open_item()},
           [deco("HmItIc", "ThisItem.ic", 10, 9, 30, "ThisItem.col", Fill="ThisItem.tint", PaddingLeft=6, PaddingRight=6, PaddingTop=6, PaddingBottom=6),
            label("HmItT", "ThisItem.title", X=52, Y=0, Width="Parent.TemplateWidth - 88 - If(IsBlank(ThisItem.flag), 0, 80)", Height=48, AutoHeight="false", Wrap="true", LineHeight=1.15, VerticalAlign="VerticalAlign.Middle", FontWeight="FontWeight.Semibold"),
            label("HmItFlag", "Upper(ThisItem.flag)", X="Parent.TemplateWidth - 108", Y=14, Width=72, Height=20, AutoHeight="false", Size=8, FontWeight="FontWeight.Bold", Fill=FOCUS, Color=INK, Align="Align.Center", VerticalAlign="VerticalAlign.Middle", Visible="!IsBlank(ThisItem.flag)"),
            deco("HmItChev", "Icon.ChevronRight", "Parent.TemplateWidth - 30", 15, 18, MUTED),
            ("HmItBtn", BTN, {"Text": 'ThisItem.title & ". " & ThisItem.summ & If(IsBlank(ThisItem.flag), "", ". " & ThisItem.flag & " in this version")', "Color": CLEAR, "HoverColor": CLEAR, "PressedColor": CLEAR, "OnSelect": "Select(Parent)", "Fill": CLEAR, "HoverFill": "RGBA(11,85,163,0.07)", "PressedFill": "RGBA(11,85,163,0.15)", "BorderThickness": 0,
                              "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "X": 2, "Y": 2, "Width": "Parent.TemplateWidth - 4", "Height": 44, "TabIndex": 0, "RadiusTopLeft": 10, "RadiusTopRight": 10, "RadiusBottomLeft": 10, "RadiusBottomRight": 10, "Font": FONT, "Size": 8})], "Vertical")], "Vertical"),
        ("HmTiles", GAL, {"Items": "nfSect", "Y": "HmSecsH.Y + HmSecsH.Height + 4", "X": "nfCX - 5", "Width": "nfCW + 10", "Height": f"Max(96, {PH} - Self.Y)", "TemplateSize": TILE_H, "TemplatePadding": 0, "WrapCount": "If(nfTiny, 1, nfCompact, 2, 3)", "ShowScrollbar": "true", "TabIndex": -1,
                          "AccessibleLabel": '"Sections"', "Visible": "nfTiles", "DisplayMode": f"If({tv}, DisplayMode.Disabled, DisplayMode.Edit)", "OnSelect": "Set(gHomeSec, ThisItem.n); SetFocus(HmShShade)"},
         [glass("HmTilePl", 5, 5, "Parent.TemplateWidth - 10", TILE_H - 10, r=16),
          rect("HmTileTop", "ThisItem.col", X=19, Y=5, Width="Parent.TemplateWidth - 38", Height=4),
          label("HmTileN", "ThisItem.n", X=14, Y=20, Width=30, Height=30, AutoHeight="false", Size=13, FontWeight="FontWeight.Bold", Color=WHITE, Fill="ThisItem.col", Align="Align.Center", VerticalAlign="VerticalAlign.Middle"),
          label("HmTileT", "ThisItem.title", X=52, Y=14, Width="Parent.TemplateWidth - 64", Height=44, AutoHeight="false", Wrap="true", Size=S_BODY, FontWeight="FontWeight.Semibold", Color="ThisItem.col", LineHeight=1.15, VerticalAlign="VerticalAlign.Middle"),
          label("HmTileC", 'CountRows(Filter(nfHome, sec = ThisItem.n)) & " links" & If(CountRows(Filter(nfHome, sec = ThisItem.n && !IsBlank(flag))) > 0, " · new", "")', X=52, Y=58, Width="Parent.TemplateWidth - 64", Height=20, AutoHeight="false", Wrap="false", **small),
          ("HmTileBtn", BTN, {"Text": '"Section " & ThisItem.n & ": " & ThisItem.title & ". " & ThisItem.blurb', "Color": CLEAR, "HoverColor": CLEAR, "PressedColor": CLEAR, "OnSelect": "Select(Parent)", "Fill": CLEAR, "HoverFill": "RGBA(11,85,163,0.07)", "PressedFill": "RGBA(11,85,163,0.15)", "BorderThickness": 0,
                              "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "X": 5, "Y": 5, "Width": "Parent.TemplateWidth - 10", "Height": TILE_H - 10, "TabIndex": 0, "RadiusTopLeft": 16, "RadiusTopRight": 16, "RadiusBottomLeft": 16, "RadiusBottomRight": 16, "Font": FONT, "Size": 8})], "Vertical"),
        button("HmShShade", '"Close the section"', "Set(gHomeSec, Blank())", X=0, Y=0, Width="Parent.Width", Height="Parent.Height", Fill="RGBA(0,0,0,0.55)", HoverFill="RGBA(0,0,0,0.55)", PressedFill="RGBA(0,0,0,0.55)", Color=CLEAR, HoverColor=CLEAR, PressedColor=CLEAR, RadiusTopLeft=0, RadiusTopRight=0, RadiusBottomLeft=0, RadiusBottomRight=0, Visible="!IsBlank(gHomeSec)"),
        glass("HmSheet", "(Parent.Width - Min(Parent.Width - 32, 440)) / 2", SHEET_Y, "Min(Parent.Width - 32, 440)", f"HmShItems.Y + HmShItems.Height + 64 - ({SHEET_Y})", r=20, a=.99, b=.97, Visible="!IsBlank(gHomeSec)"),
        rect("HmShTop", "LookUp(nfSect, n = gHomeSec).col", X="(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 20", Y=SHEET_Y, Width="Min(Parent.Width - 32, 440) - 40", Height=4, Visible="!IsBlank(gHomeSec)"),
        label("HmShN", "gHomeSec", X="(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 20", Y=f"{SHEET_Y} + 20", Width=32, Height=32, AutoHeight="false", Size=14, FontWeight="FontWeight.Bold", Color=WHITE, Fill="LookUp(nfSect, n = gHomeSec).col", Align="Align.Center", VerticalAlign="VerticalAlign.Middle", Visible="!IsBlank(gHomeSec)"),
        label("HmShT", "LookUp(nfSect, n = gHomeSec).title", X="(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 62", Y=f"{SHEET_Y} + 16", Width="Min(Parent.Width - 32, 440) - 82", Size=S_LEAD, FontWeight="FontWeight.Semibold", Role="TextRole.Heading2", Color="LookUp(nfSect, n = gHomeSec).col", Visible="!IsBlank(gHomeSec)", Live="Live.Polite"),
        label("HmShB", "LookUp(nfSect, n = gHomeSec).blurb", X="(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 62", Y="HmShT.Y + HmShT.Height", Width="Min(Parent.Width - 32, 440) - 82", Visible="!IsBlank(gHomeSec)", **small),
        ("HmShItems", GAL, {"Items": "Filter(nfHome, sec = gHomeSec)", "X": "(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 10", "Y": "HmShB.Y + HmShB.Height + 10", "Width": "Min(Parent.Width - 32, 440) - 20", "Height": "Min(CountRows(Filter(nfHome, sec = gHomeSec)) * pt(48), Parent.Height - Self.Y - 72)", "TemplateSize": 48, "TemplatePadding": 0, "ShowScrollbar": "true", "TabIndex": -1, "AccessibleLabel": '"Links in this section"', "Visible": "!IsBlank(gHomeSec)", "OnSelect": "Set(gHomeSec, Blank()); " + open_item()},
           [deco("HmShIIc", "ThisItem.ic", 10, 9, 30, "ThisItem.col", Fill="ThisItem.tint", PaddingLeft=6, PaddingRight=6, PaddingTop=6, PaddingBottom=6, Visible="!nfTiny"),
            # D-PA25: under 360 px the icon gives way to the title, which was cut to three clipped lines beside an UPDATED tag
            label("HmShIT", "ThisItem.title", X="If(nfTiny, 10, 52)", Y=0, Width="Parent.TemplateWidth - If(nfTiny, 46, 88) - If(IsBlank(ThisItem.flag), 0, 80)", Height=48, AutoHeight="false", Wrap="true", LineHeight=1.15, VerticalAlign="VerticalAlign.Middle", FontWeight="FontWeight.Semibold"),
            label("HmShIFlag", "Upper(ThisItem.flag)", X="Parent.TemplateWidth - 108", Y=14, Width=72, Height=20, AutoHeight="false", Size=8, FontWeight="FontWeight.Bold", Fill=FOCUS, Color=INK, Align="Align.Center", VerticalAlign="VerticalAlign.Middle", Visible="!IsBlank(ThisItem.flag)"),
            deco("HmShIChev", "Icon.ChevronRight", "Parent.TemplateWidth - 30", 15, 18, MUTED),
            ("HmShIBtn", BTN, {"Text": 'ThisItem.title & ". " & ThisItem.summ & If(IsBlank(ThisItem.flag), "", ". " & ThisItem.flag & " in this version")', "Color": CLEAR, "HoverColor": CLEAR, "PressedColor": CLEAR, "OnSelect": "Select(Parent)", "Fill": CLEAR, "HoverFill": "RGBA(11,85,163,0.07)", "PressedFill": "RGBA(11,85,163,0.15)", "BorderThickness": 0,
                              "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "X": 2, "Y": 2, "Width": "Parent.TemplateWidth - 4", "Height": 44, "TabIndex": 0, "RadiusTopLeft": 10, "RadiusTopRight": 10, "RadiusBottomLeft": 10, "RadiusBottomRight": 10, "Font": FONT, "Size": 8})], "Vertical"),
        secondary("HmShClose", '"Close"', "Set(gHomeSec, Blank())", X="(Parent.Width - Min(Parent.Width - 32, 440)) / 2 + 20", Y="HmShItems.Y + HmShItems.Height + 8", Width="Min(Parent.Width - 32, 440) - 40", Height=40, Size=S_SMALL, Visible="!IsBlank(gHomeSec)"),
        rect("HmTourShade", "RGBA(0,0,0,0.6)", Width="Parent.Width", Height="Parent.Height", Visible=tv),
        glass("HmTourCard", tx, 96, tw, "HmTourNext.Y + HmTourNext.Height + 24 - Self.Y", r=20, a=.99, b=.96, Visible=tv),
        deco("HmTourIcon", "Icon.Lightbulb", f"{tx} + 24", 120, 36, BRAND, Fill="RGBA(230,238,247,1)", PaddingLeft=8, PaddingRight=8, PaddingTop=8, PaddingBottom=8, Visible=tv),
        label("HmTourStep", '"Step " & gTour & " of " & CountRows(nfTour)', X=f"{tx} + 72", Y=128, Width=f"{tw} - 96", Visible=tv, Live="Live.Polite", **small),
        *[rect(f"HmTourDot{i}", f"If(gTour >= {i}, {BRAND}, {LINE})", X=f"{tx} + 24 + {(i - 1)} * (({tw} - 48 - 40) / 6 + 8)", Y=170, Width=f"({tw} - 48 - 40) / 6", Height=4, Visible=tv) for i in range(1, 7)],
        label("HmTourH", "LookUp(nfTour, n = gTour).h", X=f"{tx} + 24", Y=188, Width=f"{tw} - 48", Visible=tv, Live="Live.Polite", **h2),
        label("HmTourT", "LookUp(nfTour, n = gTour).t", X=f"{tx} + 24", Y="HmTourH.Y + HmTourH.Height + 8", Width=f"{tw} - 48", Visible=tv, Live="Live.Polite"),
        secondary("HmTourSkip", 'If(gTour > 1, "Previous", "Skip the tour")', "If(gTour > 1, Set(gTour, gTour - 1), Set(gTour, 0))", X=f"{tx} + 24", Y="HmTourT.Y + HmTourT.Height + 24", Width=f"({tw} - 60) / 2", Visible=tv),
        button("HmTourNext", 'If(gTour < CountRows(nfTour), "Next", "Finish")', "If(gTour < CountRows(nfTour), Set(gTour, gTour + 1), Set(gTour, 0))", X="HmTourSkip.X + HmTourSkip.Width + 12", Y="HmTourSkip.Y", Width="HmTourSkip.Width", Visible=tv),
    ])
    # --- Page reader ---
    cur = "LookUp(nfSections, pid = gPid && n = gSec)"
    npg = "LookUp(nfPages, id = gPid).n"
    b3 = "(nfRW - 24) / 3"
    S["02-ScrPage"] = Y().screen("ScrPage", {**scr, "OnVisible": "Set(gToc, false); Reset(PgScroll)"}, [
        *header("Pg", "LookUp(nfPages, id = gPid).short", bg="Switch(LookUp(nfPages, id = gPid).sec, 1, nfBg1, 3, nfBg3, 4, nfBg4, 5, nfBg5, 6, nfBg6, nfBg1)", ribbon="LookUp(nfSect, n = LookUp(nfPages, id = gPid).sec).col"),
        glass("PgPanel", "nfRX - 12", BAR + 8, "nfRW + 24", f"{PH} - {BAR} - 8 - {BTNH + 24}", r=18),
        label("PgPos", f'"Section " & gSec & " of " & {npg}', Y=BAR + 10, Width="nfRW - 116", Live="Live.Polite", **small),
        save_toggle("PgSave", '("page:" & gPid & ":" & gSec)', f'{{key: "page:" & gPid & ":" & gSec, kind: "page", ref: gPid, n: gSec, title: LookUp(nfPages, id = gPid).short & ": " & {cur}.h}}', BAR + 2),
        *progress("Pg", BAR + 46, f"If(IsBlank({npg}) || {npg} = 0, 0, gSec / {npg})"),
        label("PgH", f"{cur}.h", Y=BAR + 62, Live="Live.Polite", **h2),
        html_view("PgBody", f"{cur}.x", "PgH.Y + PgH.Height + 4", f"{PH} - Self.Y - {BTNH + 24}"),
        # D-PA24: Previous, Contents and Next sit at the end of the section, inside the scrolling page. A keyboard user reads down with the
        # arrow keys from Save, reaches them by Tab, and after Next the focus is still inside the page, so the arrow keys keep working.
        secondary("PgPrev", '"Previous"', "Set(gSec, gSec - 1); Reset(PgScroll)", X="nfRX", Y="PgBody.Y + PgBody.Height + 16", Width=b3, DisplayMode="If(gSec > 1, DisplayMode.Edit, DisplayMode.Disabled)"),
        secondary("PgToc", '"Contents"', "Set(gToc, true); SetFocus(PgTocClose)", X="PgPrev.X + PgPrev.Width + 12", Y="PgPrev.Y", Width=b3),
        button("PgNext", '"Next"', "Set(gSec, gSec + 1); Reset(PgScroll)", X="PgToc.X + PgToc.Width + 12", Y="PgPrev.Y", Width=b3, DisplayMode=f"If(gSec < {npg}, DisplayMode.Edit, DisplayMode.Disabled)"),
        rect("PgTocBg", WHITE, Y=BAR, Width="Parent.Width", Height=f"{PH} - {BAR}", Visible="gToc"),
        label("PgTocH", '"On this page"', Y=BAR + 20, Visible="gToc", Width="nfRW - 120", **h2),
        secondary("PgTocClose", '"Close"', "Set(gToc, false)", X="nfRX + nfRW - 104", Y=BAR + 12, Width=104, Height=44, Visible="gToc"),
        cards("PgTocList", "Filter(nfSections, pid = gPid)", "Set(gSec, ThisItem.n); Set(gToc, false); Reset(PgScroll)", "ThisItem.h", '"Section " & ThisItem.n & If(ThisItem.n = gSec, " · you are here", "")', BAR + 68, tmpl=76, extra={"Visible": "gToc", "Height": f"{PH} - Self.Y - {BTNH + 20}"}, wide=False, alabel="Sections on this page", flag="ThisItem.flag"),
        secondary("PgTocWeb", '"Open the full page in the web explorer"', 'Launch(nfSite & gPid & ".html")', X="nfRX", Y=foot_y, Width="nfRW", Visible="gToc"),
    ])
    # --- Reader for one answer / example / word ---
    S["03-ScrRead"] = Y().screen("ScrRead", {**scr, "OnVisible": "Reset(RdScroll)"}, [
        *header("Rd", "gReadKind", bg='If(gReadK = "ex", nfBg2, nfBg4)', ribbon='If(gReadK = "ex", RGBA(0,105,92,1), RGBA(90,47,138,1))'),
        glass("RdPanel", "nfRX - 12", BAR + 8, "nfRW + 24", f"{PH} - {BAR} - 16", r=18),
        save_toggle("RdSave", '(gReadK & ":" & gReadRef)', '{key: gReadK & ":" & gReadRef, kind: gReadK, ref: gReadRef, n: 0, title: gReadTitle}', BAR + 10),
        label("RdH", "gReadTitle", Y=BAR + 58, **h2),
        html_view("RdBody", "gReadHtml", "RdH.Y + RdH.Height + 4", f"{PH} - Self.Y - 8"),
    ])
    # --- Questions ---
    qitems = 'Filter(nfQA, (gTopic = "All" || topic = gTopic) && (IsBlank(QsSearch.Text) || QsSearch.Text in q || QsSearch.Text in t))'
    qp = picker("QsTopic", "nfTopics", "topic", "gTopic", BAR + 68, "Topic")
    S["04-ScrQuestions"] = Y().screen("ScrQuestions", {**scr, "OnVisible": 'If(IsBlank(gTopic), Set(gTopic, "All"))'}, [
        *header("Qs", '"Questions and answers"', active="ScrQuestions", bg="nfBg4", ribbon="RGBA(90,47,138,1)"),
        *search_field("QsSearch", "Search questions and answers", BAR + 12),
        *qp[0],
        label("QsCount", f'CountRows({qitems}) & " of " & CountRows(nfQA) & " answers"', Y=BAR + 118, X="nfCX", Width="nfCW", Live="Live.Polite", **small),
        cards("QsList", qitems, read('"Answer"', "ThisItem.q", "ThisItem.x", "qa", "ThisItem.id"), "ThisItem.q", 'ThisItem.prov & " · " & ThisItem.topic', BAR + 144, tmpl=120, cols="nfCols2", ic="Icon.QuestionMark", col="ThisItem.col", tint="ThisItem.tint", flag="ThisItem.flag"),
        *empty("QsNone", "QsList", "No answers match. Try a different word, or choose All."),
        *qp[1],
    ])
    # --- Examples ---
    eitems = 'Filter(nfEx, (gExKind = "All" || kind = gExKind) && (!ExAgreed.Value || stat = "Agreed") && (IsBlank(ExSearch.Text) || ExSearch.Text in title || ExSearch.Text in t || ExSearch.Text in topics || ExSearch.Text in sector))'
    ep = picker("ExKind", "nfExKinds", "kind", "gExKind", BAR + 68, "Show", w="Min((nfCW - 12) / 2, 300)")
    S["05-ScrExamples"] = Y().screen("ScrExamples", {**scr, "OnVisible": 'If(IsBlank(gExKind), Set(gExKind, "All"))'}, [
        *header("Ex", '"Worked examples"', active="ScrExamples", bg="nfBg2", ribbon="RGBA(0,105,92,1)"),
        *search_field("ExSearch", "Search examples, sectors and topics", BAR + 12),
        *ep[0],
        ("ExAgreed", TOG, {"Default": "false", "TrueText": '"Agreed only"', "FalseText": '"Agreed only"', "AccessibleLabel": '"Show agreed examples only"', "X": "ExKindBtn.X + ExKindBtn.Width + 12", "Y": BAR + 68, "Width": "nfCW - ExKindBtn.Width - 12", "Height": 44, "Size": S_SMALL, "Font": FONT, "Color": INK, "TabIndex": 0, "TrueFill": BRAND, "FalseFill": MUTED, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4}),
        label("ExCount", f'CountRows({eitems}) & " of " & CountRows(nfEx) & " examples"', Y=BAR + 118, X="nfCX", Width="nfCW", Live="Live.Polite", **small),
        cards("ExList", eitems, read('"Example " & ThisItem.id', "ThisItem.title", "ThisItem.x", "ex", "ThisItem.id"), 'ThisItem.id & ": " & ThisItem.title', 'ThisItem.kind & " · " & ThisItem.stat & " · " & ThisItem.sector', BAR + 144, tmpl=120, cols="nfCols2", ic="ThisItem.ic", col="ThisItem.col", tint="ThisItem.tint", flag="ThisItem.flag"),
        *empty("ExNone", "ExList", "No examples match. Try a different word, or choose All."),
        *ep[1],
    ])
    # --- Glossary ---
    gitems = "Filter(nfGlo, IsBlank(GlSearch.Text) || GlSearch.Text in term || GlSearch.Text in def)"
    S["06-ScrGlossary"] = Y().screen("ScrGlossary", scr, [
        *header("Gl", '"Glossary"', bg="nfBg4", ribbon="RGBA(90,47,138,1)"),
        *search_field("GlSearch", "Search the glossary", BAR + 12),
        cards("GlList", gitems, read('"Glossary"', "ThisItem.term", '"<p>" & ThisItem.def & "</p>"', "glo", "ThisItem.term"), "ThisItem.term", "ThisItem.def", BAR + 72, tmpl=84, cols="nfCols", ic="Icon.Tag", col="RGBA(90,47,138,1)", tint="RGBA(238,232,245,1)", flag="ThisItem.flag"),
        *empty("GlNone", "GlList", "No words match. Try a different word."),
    ])
    # --- Search ---
    sitems = "If(Len(Trim(SrSearch.Text)) < 2, Blank(), Filter(nfIndex, SrSearch.Text in title || SrSearch.Text in t))"
    S["07-ScrSearch"] = Y().screen("ScrSearch", scr, [
        *header("Sr", '"Search"', bg="nfBg4", ribbon="RGBA(90,47,138,1)"),
        *search_field("SrSearch", "Search pages, answers, examples and glossary", BAR + 12),
        label("SrCount", f'If(Len(Trim(SrSearch.Text)) < 2, "Type two or more letters to search {{N}} pages, answers, examples and words.", CountRows({sitems}) & " results")', Y=BAR + 68, X="nfCX", Width="nfCW", Live="Live.Polite", **small),
        cards("SrList", sitems, open_ref(), "ThisItem.title", 'ThisItem.type & " · " & ThisItem.t', "SrCount.Y + SrCount.Height + 8", tmpl=112, cols="nfCols2", ic="ThisItem.ic", col="ThisItem.col", tint="ThisItem.tint", flag="ThisItem.flag"),
        *empty("SrNone", "SrList", "No results. Try a different word.", "Len(Trim(SrSearch.Text)) >= 2"),
    ])
    # --- Asset test: one question per step, then the result. Same rules as decideAsset() in the web explorer. ---
    a = lambda k: f'LookUp(colAns, key = "{k}").v'
    purp = 'Filter(colPurp, v <> "unsure")'
    fails = [(f'{a("official")} = "no"', "It is SECRET or TOP SECRET. Only OFFICIAL data is in scope."),
             ('CountRows(colPurp) = 0', "It serves none of the seven critical purposes."),
             (f'{a("shared")} = "no"', "It is only used inside your organisation, so it has no value across government through sharing."),
             (f'{a("accountable")} = "asis"', "You use another organisation's data as it is. The organisation accountable for it reports it."),
             (f'{a("source")} = "derived"', "It is drawn from source data. Report the source data set instead, even if the source itself is never shared.")]
    any_fail = " || ".join(c for c, _ in fails)
    uns = [(f'IsBlank({a("official")}) || {a("official")} = "unsure"', "whether it is OFFICIAL"), (f'CountRows(colPurp) > 0 && CountRows({purp}) = 0', "which critical purposes it serves"),
           (f'IsBlank({a("shared")}) || {a("shared")} = "unsure"', "how it is shared"), (f'IsBlank({a("accountable")}) || {a("accountable")} = "unsure"', "who is accountable for it"), (f'IsBlank({a("source")}) || {a("source")} = "unsure"', "whether it is the source data")]
    any_uns = " || ".join(f"({c})" for c, _ in uns)
    uns_list = "Concat(Filter(Table(" + ", ".join(f"{{c: {c}, s: {fx(s)}}}" for c, s in uns) + '), c), s, ", ")'
    verdict = f'If({any_fail}, "out", {any_uns}, "flag", {a("shared")} = "potential", "in-later", "in")'
    head = 'Switch(gVerdict, "in", "Include it in your return", "in-later", "In scope: include it if you have time", "out", "Leave it out", "Include it provisionally, flagged")'
    reasons = ('Switch(gVerdict,\n    "out", ' + " & ".join(f'If({c}, "<li>{s}</li>", "")' for c, s in fails)
               + f',\n    "flag", "<li>Include it for now and flag it. Before you send the return, confirm " & {uns_list} & " with the people who know the data, or ask your lead coordinator.</li>"'
               + ',\n    "in-later", "<li>It is in scope, but it is not shared yet. For the Baseline Return, start with assets already shared or published, and add this one if you have time.</li>"'
               + f',\n    "<li>It is OFFICIAL, serves purpose " & Concat(Sort({purp}, Value(v)), v, ", ") & ", is " & If({a("shared")} = "open", "published as open data", "shared under a data sharing agreement") & ", you are accountable for it, and it is " & If({a("source")} = "product", "a product managed and owned in its own right", "the source data") & ".</li>")')
    nxt = ('Switch(gVerdict, "in", "Next: give it an owner and a steward (step 6 of Your return) and fill in its details (step 7).", "in-later", "Next: note it for the October 2027 return, or add it now if you have time.", '
           '"out", "Next: add it to your list of assets left out, with the reason.", "Next: add it to your list with a note in its description saying what still needs confirming, then test it again once you know.")')
    q = "LookUp(nfTestQ, n = gStep)"
    s0, isq, isres = "gStep = 0", "gStep >= 1 && gStep <= 5", "gStep = 6"
    sel = 'If(' + q + '.multi = 1, ThisItem.v in colPurp.v, LookUp(colAns, key = ' + q + '.key).v = ThisItem.v)'
    pick = ('If(' + q + '.multi = 1,\n    If(ThisItem.v in colPurp.v, RemoveIf(colPurp, v = ThisItem.v), Collect(colPurp, {v: ThisItem.v})),\n'
            '    RemoveIf(colAns, key = ' + q + '.key); Collect(colAns, {key: ' + q + '.key, v: ThisItem.v}))')
    tested = 'Concat(colTested, "• " & name & ": " & head, Char(10))'
    has_t = "gStep = 0 && CountRows(colTested) > 0"
    b2 = "(nfRW - 12) / 2"
    vcol = f'Switch(gVerdict, "in", {OK_C}, "out", {BAD_C}, {WARN_C})'
    S["08-ScrTest"] = Y().screen("ScrTest", {**scr, "OnVisible": "If(IsBlank(gStep), Set(gStep, 0))"}, [
        *header("Ts", '"Asset test"', active="ScrTest", bg="nfBg2", ribbon="RGBA(0,105,92,1)"),
        glass("TsPanel", "nfRX - 12", BAR + 8, "nfRW + 24", f"{PH} - {BAR} - 16", r=18),
        deco("TsIntroIc", "Icon.CheckBadge", "nfRX", BAR + 20, 48, BRAND, Fill="RGBA(230,238,247,1)", PaddingLeft=11, PaddingRight=11, PaddingTop=11, PaddingBottom=11, Visible=s0),
        label("TsIntroH", '"Is this a critical data asset?"', Y=BAR + 80, Visible=s0, **h2),
        label("TsIntro", '"Answer five short questions about one possible asset. You will find out whether it goes in your return, and why. Based on the OFFICIAL scope rule in the policy and the four DAM Policy scope principles. What you enter stays on this device."', Y="TsIntroH.Y + TsIntroH.Height + 8", Visible=s0),
        label("TsNameL", '"Name of the possible asset (optional)"', Y="TsIntro.Y + TsIntro.Height + 16", FontWeight="FontWeight.Semibold", Visible=s0),
        text_box("TsName", "Name of the possible asset (optional)", "TsNameL.Y + TsNameL.Height + 4", Visible=s0, MaxLength=120, Clear="false", X="nfRX", Width="nfRW", DelayOutput="false", PaddingLeft=12, HintText='"For example, Vehicle keeper records"'),
        button("TsStart", '"Start the test"', "Clear(colAns); Clear(colPurp); Set(gStep, 1)", X="nfRX", Y="TsName.Y + TsName.Height + 16", Width="Min(nfRW, 260)", Visible=s0),
        label("TsTestedH", '"Assets you have tested on this device"', Y="TsStart.Y + TsStart.Height + 24", Visible=has_t, **{**h2, "Size": S_LEAD}),
        label("TsTested", tested, Y="TsTestedH.Y + TsTestedH.Height + 4", Visible=has_t),      # D-PA21: plain text that grows; the HTML box was squeezed to nothing on a phone
        label("TsQn", '"Question " & gStep & " of 5"', Y=BAR + 10, Visible=isq, Live="Live.Polite", **small),
        *progress("Ts", BAR + 36, "gStep / 5", isq),
        label("TsQ", f"{q}.q", Y=BAR + 52, Visible=isq, Live="Live.Polite", **h2),
        label("TsHint", f"{q}.hint", Y="TsQ.Y + TsQ.Height + 4", Visible=isq, **small),
        # D-PA22: answer rows are as tall as the longest answer needs (three-line answers touched the edge of a fixed row)
        ("TsOpts", GAL, {"Items": f"Filter(nfTestOpt, key = {q}.key)", "Y": "TsHint.Y + TsHint.Height + 8", "X": "nfRX", "Width": "nfRW", "Height": f"{PH} - Self.Y - {BTNH + 24}", "TemplateSize": f"pt(38) + Min(raw(4), Max(raw(1), RoundUp((Max(Filter(nfTestOpt, key = {q}.key), Len(label)) + raw(3)) * pt(10) / (nfRW - 44), 0))) * pt(22)", "TemplatePadding": 0, "Visible": isq, "ShowScrollbar": "true", "TabIndex": -1, "OnSelect": pick, "AccessibleLabel": '"Answers"'},
         [button("TsOpt", f'If({sel}, "✓  ", "") & ThisItem.label', "Select(Parent)", X=0, Y=4, Width="Parent.TemplateWidth - 12", Height="Parent.TemplateHeight - 8", Align="Align.Left", PaddingLeft=16,
                 Fill=f"If({sel}, {BRAND}, {WHITE})", Color=f"If({sel}, {WHITE}, {INK})", HoverFill=f"If({sel}, {BRAND}, {SOFT})", HoverColor=f"If({sel}, {WHITE}, {INK})", PressedFill=BRAND, BorderThickness=2, BorderColor=f"If({sel}, {BRAND}, {INK})", FontWeight="FontWeight.Normal")], "Vertical"),
        footer("Ts", isq),
        secondary("TsPrev", '"Previous"', "Set(gStep, gStep - 1)", X="nfRX", Y=foot_y, Width=b2, Visible=isq),
        button("TsNext", 'If(gStep = 5, "See the result", "Next")', f'If(gStep = 5, Set(gVerdict, {verdict}); Collect(colTested, {{name: If(IsBlank(Trim(TsName.Text)), "Unnamed asset", Trim(TsName.Text)), head: {head}}}); {SAVE["colTested"]}); Set(gStep, gStep + 1)', X="TsPrev.X + TsPrev.Width + 12", Y=foot_y, Width=b2, Visible=isq),
        label("TsResKicker", '"Your result"', Y=BAR + 12, Visible=isres, **small),
        rect("TsResBg", f'Switch(gVerdict, "in", {OK_BG}, "out", {BAD_BG}, {WARN_BG})', X="nfRX - 8", Y=BAR + 36, Width="nfRW + 16", Height="Max(TsResH.Height, 40) + 24", Visible=isres),
        rect("TsResAcc", vcol, X="nfRX - 8", Y=BAR + 36, Width=5, Height="TsResBg.Height", Visible=isres),
        deco("TsResIc", 'Switch(gVerdict, "in", Icon.CheckBadge, "out", Icon.CancelBadge, Icon.Warning)', "nfRX + 8", BAR + 48, 40, vcol, Visible=isres),
        label("TsResH", f'If(IsBlank(Trim(TsName.Text)), "", Trim(TsName.Text) & ": ") & {head}', Y=BAR + 48, X="nfRX + 60", Width="nfRW - 60", Visible=isres, Live="Live.Assertive", **h2),
        label("TsRes", f'Substitute(Substitute({reasons}, "<li>", "• "), "</li>", Char(10) & Char(10)) & {nxt}', Y="TsResBg.Y + TsResBg.Height + 12", Visible=isres),
        secondary("TsMatch", '"Look for a match in the National Data Library"', f"Navigate(ScrMatch, {FADE})", X="nfRX", Y=f"{PH} - {2 * BTNH + 30}", Width="nfRW", Visible=isres),
        footer("TsR", isres),
        button("TsAgain", '"Test another asset"', "Reset(TsName); Clear(colAns); Clear(colPurp); Set(gStep, 0)", X="nfRX", Y=foot_y, Width=b2, Visible=isres),
        secondary("TsToReturn", '"Go to Your return"', f'Set(gPid, "return"); Set(gSec, 1); Navigate(ScrPage, {FADE})', X="TsAgain.X + TsAgain.Width + 12", Y=foot_y, Width=b2, Visible=isres),
    ])
    # --- Splash: who you are signed in as, what the app is, one clear way in. Moves on by itself after 4 seconds. ---
    load = "; ".join(f'IfError(LoadData({c}, "dpe{c[3:]}", true), Blank())' for c in SAVE)
    cxm = "Parent.Width / 2"
    go_nav = "Switch(gGo, " + ", ".join(f'"{k}", Navigate({v}, {FADE})' for k, v in GO.items()) + f", Navigate(ScrHome, {FADE}))"
    S["00-ScrSplash"] = Y().screen("ScrSplash", {"Fill": BRAND_D, "LoadingSpinnerColor": WHITE, "OnVisible": f'If(IsBlank(gLoaded), Set(gLoaded, true); {load}; Set(gRole, First(colPrefs).role)); Set(gTour, 0); Set(gGo, Lower(Coalesce(Param("go"), "")))'}, [
        backdrop("SpArt", "nfSplashArt"),
        glass("SpDisc", f"{cxm} - 60", "SpLogo.Y - 12", 120, 120, r=60, a=.30, b=.12),
        image("SpLogo", f"{cxm} - 48", "If(Parent.Height < 1300, 14, Max(24, (Parent.Height - 440) * 0.5))", 96, AccessibleLabel='"DAM Policy Explorer logo: a data store with a compass"'),
        label("SpTitle", '"DAM Policy Explorer"', X="nfRX", Width="nfRW", Y="SpLogo.Y + 132", Align="Align.Center", Color=WHITE, Size="If(nfWide, 30, 24)", FontWeight="FontWeight.Bold", Role="TextRole.Heading1", LineHeight=1.2),
        label("SpStrap", '"Everything you need for the Data Asset Management Policy, in one place."', X="nfRX", Width="nfRW", Y="SpTitle.Y + SpTitle.Height + 8", Align="Align.Center", Color=WHITE, Size=S_LEAD, Visible="!nfShort"),
        label("SpHello", '"Hello, " & nfFirst & "."', X="nfRX", Width="nfRW", Y="SpStrap.Y + SpStrap.Height + 16", Align="Align.Center", Color=WHITE, Size=S_H2, FontWeight="FontWeight.Semibold", Visible="!nfShort"),
        label("SpStats", "nfStats", X="nfRX", Width="nfRW", Y="SpHello.Y + SpHello.Height + 6", Align="Align.Center", Color=WHITE, Size=S_SMALL, Visible="Parent.Height >= 1300"),
        button("SpGo", '"Open the explorer"', go_nav, X=f"{cxm} - 130", Width=260, Y="Min(If(SpStats.Visible, SpStats.Y + SpStats.Height, If(SpHello.Visible, SpHello.Y + SpHello.Height, SpTitle.Y + SpTitle.Height)) + 20, Parent.Height - 124)", Fill=WHITE, Color=BRAND_D, HoverFill=SOFT, HoverColor=BRAND_D, PressedFill=SOFT, PressedColor=BRAND_D),
        label("SpProto", '"Prototype. GOV.UK is right if anything differs. Version " & nfVersion & "."', X="nfRX", Width="nfRW", Y="SpGo.Y + SpGo.Height + 12", Align="Align.Center", Color=WHITE, Size=S_SMALL),
        ("SpTimer", TIMER, {"Duration": 4000, "AutoStart": "true", "Repeat": "false", "Visible": "false", "OnTimerEnd": go_nav}),
    ])
    # --- My area: progress, saved items, tested assets, settings. Identity comes from the organisation's sign-in; data stays on the device. ---
    tab = lambda t: f'gMeTab = "{t}"'
    done = "ThisItem.n in colDone.n"
    rp = picker("MeRole", "nfRoles", "role", "gRole", "MeRoleH.Y + MeRoleH.Height + 4", "I am a", vis=tab("Settings"), then=f'ClearCollect(colPrefs, {{role: ThisItem.role}}); {SAVE["colPrefs"]}; ')
    S["09-ScrMe"] = Y().screen("ScrMe", {**scr, "OnVisible": 'If(IsBlank(gMeTab), Set(gMeTab, "Progress"))'}, [
        *header("Me", '"My area"', active="ScrMe", bg="nfBg6", ribbon="RGBA(156,31,92,1)"),
        label("MeHello", '"Hello, " & nfFirst', Y=BAR + 14, X="nfCX", Width="nfCW", **h2),
        label("MeWho", '"Signed in as " & User().FullName & ". What you save here stays on this device and is not sent anywhere."', Y="MeHello.Y + MeHello.Height + 2", X="nfCX", Width="nfCW", **small),
        segmented("MeChips", "nfMeTabs", "tab", "gMeTab", "MeWho.Y + MeWho.Height + 8"),
        # progress
        label("MeProg", 'CountRows(colDone) & " of 12 steps of your return done"', Y="MeChips.Y + MeChips.Height + 8", X="nfCX", Width="nfCW", FontWeight="FontWeight.Semibold", Visible=tab("Progress"), Live="Live.Polite"),
        rect("MeTrk", SOFT, X="nfCX", Y="MeProg.Y + MeProg.Height + 4", Width="nfCW", Height=8, Visible=tab("Progress")),
        rect("MeProgBar", OK_C, X="nfCX", Y="MeTrk.Y", Width="nfCW * CountRows(colDone) / 12", Height=8, Visible=tab("Progress")),
        cards("MeSteps", "nfSteps", f'If({done}, RemoveIf(colDone, n = ThisItem.n), Collect(colDone, {{n: ThisItem.n}})); {SAVE["colDone"]}', 'ThisItem.n & ". " & ThisItem.title', f'If({done}, "Done. Select to mark as not done.", "Not done yet. Select to mark as done.")', "MeTrk.Y + 18", tmpl=84, cols="nfCols2",
              ic=f"If({done}, Icon.CheckBadge, Icon.Clock)", col=f"If({done}, {OK_C}, {MUTED})", tint=f"If({done}, {OK_BG}, {SOFT})", extra={"Visible": tab("Progress")}),
        # saved
        cards("MeSaved", "colSaved", open_ref(), "ThisItem.title", 'Switch(ThisItem.kind, "page", "Page section", "qa", "Answer", "ex", "Example", "Glossary")', "MeChips.Y + MeChips.Height + 8", tmpl=84, cols="nfCols2", ic="Icon.Bookmark", extra={"Visible": tab("Saved")}),
        label("MeSavedNone", '"Nothing saved yet. Choose Save on any page section, answer, example or word."', Y="MeChips.Y + MeChips.Height + 24", X="nfCX", Width="nfCW", Color=MUTED, Visible=f'{tab("Saved")} && CountRows(colSaved) = 0'),
        # tested
        cards("MeTested", "colTested", "false", "ThisItem.name", "ThisItem.head", "MeChips.Y + MeChips.Height + 8", tmpl=84, cols="nfCols2", ic="Icon.CheckBadge", extra={"Visible": tab("Tested"), "Height": f"{PH} - Self.Y - {BTNH + 24}"}),
        label("MeTestedNone", '"No assets tested yet."', Y="MeChips.Y + MeChips.Height + 24", X="nfCX", Width="nfCW", Color=MUTED, Visible=f'{tab("Tested")} && CountRows(colTested) = 0'),
        button("MeTestGo", '"Test an asset"', f"Navigate(ScrTest, {FADE})", X="nfCX", Y=foot_y, Width="Min(nfCW, 260)", Visible=tab("Tested")),
        # settings
        label("MeRoleH", '"What best describes you?"', Y="MeChips.Y + MeChips.Height + 8", X="nfCX", Width="nfCW", FontWeight="FontWeight.Semibold", Visible=tab("Settings")),
        *rp[0],
        label("MeTip", 'If(IsBlank(gRole), "Choose one to get a suggested place to start.", "Suggested: " & LookUp(nfRoles, role = gRole).tip)', Y="MeRoleBtn.Y + 52", X="nfCX", Width="nfCW", Visible=tab("Settings"), Live="Live.Polite"),
        secondary("MeTour", '"Tutorials and tours"', f"Set(gTut, Blank()); Navigate(ScrLearn, {FADE})", X="nfCX", Y="MeTip.Y + MeTip.Height + 20", Width="Min(nfCW, 300)", Visible=tab("Settings")),
        secondary("MeClear", '"Clear my data on this device"', f'Clear(colSaved); Clear(colDone); Clear(colTested); Clear(colPrefs); Clear(colTut); Set(gRole, Blank()); {"; ".join(SAVE.values())}; Notify("Your saved items, progress and tested assets have been cleared from this device.", NotificationType.Success)', X="nfCX", Y="MeTour.Y + MeTour.Height + 12", Width="Min(nfCW, 300)", Visible=tab("Settings"), Color=BAD_C, BorderColor=BAD_C, HoverColor=BAD_C, PressedColor=BAD_C),
        label("MeIam", '"Sign-in is handled by your organisation account. This app does not ask for a password and keeps no account of its own. Display size: " & App.Width / 2 & " × " & App.Height / 2 & " points."', Y="MeClear.Y + MeClear.Height + 16", X="nfCX", Width="nfCW", Visible=tab("Settings"), **small),
        *rp[1],
    ])
    # --- Matchmaker: is the same or a related data set already in the National Data Library (data.gov.uk)? Three short steps. ---
    kw = 'Concat(FirstN(Distinct(Filter(MatchAll(Lower(MtDesc.Text), "[a-z][a-z\\-]{3,}"), !(FullMatch in nfStop.w)), FullMatch), 6), Value, " ")'
    terms = f'Trim({kw} & " " & Trim(MtPub.Text) & " " & If(gMtTopic = "Any" || IsBlank(gMtTopic), "", gMtTopic) & " " & If(gMtFmt = "Any" || IsBlank(gMtFmt), "", gMtFmt))'
    ndl = '"https://www.data.gov.uk/search?q=" & EncodeUrl('
    m = lambda n: f"gMt = {n}"
    tealc = "RGBA(0,105,92,1)"
    mt = picker("MtTopic", "nfNdlTopics", "v", "gMtTopic", BAR + 196, "Topic", x="nfRX", w="nfRW", vis=m(2))
    mf = picker("MtFormat", "nfNdlFormats", "v", "gMtFmt", BAR + 252, "Format", x="nfRX", w="nfRW", vis=m(2))
    S["10-ScrMatch"] = Y().screen("ScrMatch", {**scr, "OnVisible": 'If(IsBlank(gMt), Set(gMt, 1); Set(gMtTopic, "Any"); Set(gMtFmt, "Any"))'}, [
        *header("Mt", '"Matchmaker"', bg="nfBg2", ribbon=tealc),
        glass("MtPanel", "nfRX - 12", BAR + 8, "nfRW + 24", f"{PH} - {BAR} - 16", r=18),
        label("MtPos", '"Step " & gMt & " of 3"', Y=BAR + 16, Live="Live.Polite", **small),
        *progress("Mt", BAR + 42, "gMt / 3"),
        # 1 describe
        *divider("MtD1", '"1"', '"Describe the data asset"', BAR + 60, col=tealc, Visible=m(1)),
        label("MtIntro", '"Find out whether the same or a related data set is already listed in the National Data Library on data.gov.uk. Say what the data is about, in a sentence or two."', Y=BAR + 106, Visible=m(1)),
        text_box("MtDesc", "Describe the data asset", "MtIntro.Y + MtIntro.Height + 10", X="nfRX", Width="nfRW", Height=120, Mode="TextMode.MultiLine", Clear="false", PaddingLeft=12, DelayOutput="false", MaxLength=500, HintText='"For example, live and historical river levels and flood warnings for England"', Visible=m(1)),
        label("MtSafe", '"Leave out anything sensitive. Your search words go to data.gov.uk when you search."', Y="MtDesc.Y + MtDesc.Height + 8", Visible=m(1), **small),
        # 2 narrow
        *divider("MtD2", '"2"', '"Narrow it down (optional)"', BAR + 60, col=tealc, Visible=m(2)),
        label("MtPubL", '"Publisher"', Y=BAR + 106, FontWeight="FontWeight.Semibold", Visible=m(2)),
        text_box("MtPub", "Publisher (optional)", BAR + 132, X="nfRX", Width="nfRW", Clear="true", PaddingLeft=12, HintText='"For example, Environment Agency"', Visible=m(2)),
        *mt[0], *mf[0],
        # 3 search
        *divider("MtD3", '"3"', '"Search data.gov.uk"', BAR + 60, col=tealc, Visible=m(3)),
        label("MtTermsL", '"We will search for"', Y=BAR + 106, Visible=m(3), **small),
        label("MtTerms", f'If(IsBlank({terms}), "Go back and describe the data asset first.", {terms})', Y=BAR + 128, Size=S_LEAD, FontWeight="FontWeight.Semibold", Visible=m(3), Live="Live.Polite"),
        button("MtGo", '"Find matches on data.gov.uk"', f'Launch({ndl}{terms}))', X="nfRX", Y="MtTerms.Y + MtTerms.Height + 16", Width="nfRW", Fill=tealc, HoverFill="RGBA(0,80,70,1)", PressedFill="RGBA(0,80,70,1)", DisplayMode=f"If(IsBlank({terms}), DisplayMode.Disabled, DisplayMode.Edit)", Visible=m(3)),
        secondary("MtExact", '"Search with my exact words instead"', f'Launch({ndl}Left(Trim(MtDesc.Text), 150)))', X="nfRX", Y="MtGo.Y + MtGo.Height + 10", Width="nfRW", DisplayMode="If(IsBlank(Trim(MtDesc.Text)), DisplayMode.Disabled, DisplayMode.Edit)", Visible=m(3)),
        label("MtNote", '"Results open on data.gov.uk in your browser. Publisher, topic and format are added as search words; use the filters on the results page to narrow further. If you find the same data set, use its title and publisher so your return describes it the same way. If nothing matches, that is a useful finding too."', Y="MtExact.Y + MtExact.Height + 14", Visible=m(3), **small),
        footer("Mt"),
        secondary("MtPrev", '"Previous"', "Set(gMt, gMt - 1)", X="nfRX", Y=foot_y, Width=b2, DisplayMode="If(gMt > 1, DisplayMode.Edit, DisplayMode.Disabled)"),
        button("MtNext", 'If(gMt = 3, "Start again", "Next")', "If(gMt = 3, Reset(MtDesc); Reset(MtPub); Set(gMtTopic, \"Any\"); Set(gMtFmt, \"Any\"); Set(gMt, 1), Set(gMt, gMt + 1))", X="MtPrev.X + MtPrev.Width + 12", Y=foot_y, Width=b2, Fill=tealc, HoverFill="RGBA(0,80,70,1)", PressedFill="RGBA(0,80,70,1)"),
        *mt[1], *mf[1],
    ])
    # --- Tutorials and tours: a list of short task walk-throughs; each one is stepped, with a "Try it now" that goes to the real screen. ---
    amber = "RGBA(138,74,0,1)"
    lst, stp = "IsBlank(gTut)", "!IsBlank(gTut)"
    T = "LookUp(nfTut, id = gTut)"
    nst = "CountRows(Filter(nfTutSteps, tid = gTut))"
    stepr = "LookUp(nfTutSteps, tid = gTut && n = gTutStep)"
    tdone = "ThisItem.id in colTut.id"
    try_it = f"""Switch({T}.kind,
    "home", Set(gTour, 1); Navigate(ScrHome, {FADE}),
    "test", Navigate(ScrTest, {FADE}),
    "match", Navigate(ScrMatch, {FADE}),
    "questions", Navigate(ScrQuestions, {FADE}),
    "page", Set(gPid, {T}.ref); Set(gSec, 1); Navigate(ScrPage, {FADE}))"""
    S["11-ScrLearn"] = Y().screen("ScrLearn", {**scr, "OnVisible": "If(IsBlank(gTutStep), Set(gTutStep, 1))"}, [
        *header("Ln", '"Tutorials and tours"', bg="nfBg5", ribbon=amber),
        label("LnIntro", '"Short walk-throughs of the main tasks. Each takes two or three minutes, and you can try each step in the app as you go."', Y=BAR + 16, X="nfCX", Width="nfCW", Visible=lst),
        label("LnCount", 'CountRows(colTut) & " of " & CountRows(nfTut) & " completed"', Y="LnIntro.Y + LnIntro.Height + 4", X="nfCX", Width="nfCW", Visible=lst, Live="Live.Polite", **small),
        cards("LnList", "nfTut", "Set(gTut, ThisItem.id); Set(gTutStep, 1)", "ThisItem.title", f'ThisItem.mins & " minutes · " & ThisItem.summ & If({tdone}, " · Completed", "")', "LnCount.Y + LnCount.Height + 8", tmpl=88, cols="nfCols2",
              ic=f"If({tdone}, Icon.CheckBadge, ThisItem.ic)", col=f"If({tdone}, {OK_C}, {amber})", tint=f"If({tdone}, {OK_BG}, RGBA(247,237,224,1))", extra={"Visible": lst}, alabel="Tutorials"),
        glass("LnPanel", "nfRX - 12", BAR + 8, "nfRW + 24", f"{PH} - {BAR} - 8 - {BTNH + 24}", r=18, Visible=stp),
        label("LnKicker", f'{T}.title', Y=BAR + 18, Height=20, AutoHeight="false", Wrap="false", Visible=stp, **small),
        label("LnPos", f'"Step " & gTutStep & " of " & {nst}', Y=BAR + 40, Visible=stp, Live="Live.Polite", **small),
        *progress("Ln", BAR + 66, f"If({nst} = 0, 0, gTutStep / {nst})", stp),
        deco("LnIc", f"{T}.ic", "nfRX", BAR + 88, 44, amber, Fill="RGBA(247,237,224,1)", PaddingLeft=10, PaddingRight=10, PaddingTop=10, PaddingBottom=10, Visible=stp),
        label("LnH", f"{stepr}.h", Y=BAR + 144, Visible=stp, Live="Live.Polite", **h2),
        label("LnT", f"{stepr}.t", Y="LnH.Y + LnH.Height + 8", Size=S_LEAD, Visible=stp, Live="Live.Polite"),
        secondary("LnTry", '"Try it now"', try_it, X="nfRX", Y="LnT.Y + LnT.Height + 20", Width="Min(nfRW, 260)", Visible=stp, Color=amber, BorderColor=amber, HoverColor=amber, PressedColor=amber),
        footer("Ln", stp),
        secondary("LnPrev", 'If(gTutStep > 1, "Previous", "All tutorials")', "If(gTutStep > 1, Set(gTutStep, gTutStep - 1), Set(gTut, Blank()))", X="nfRX", Y=foot_y, Width=b2, Visible=stp),
        button("LnNext", f'If(gTutStep < {nst}, "Next", "Finish")', f'If(gTutStep < {nst}, Set(gTutStep, gTutStep + 1), If(!(gTut in colTut.id), Collect(colTut, {{id: gTut}})); {SAVE["colTut"]}; Set(gTut, Blank()))', X="LnPrev.X + LnPrev.Width + 12", Y=foot_y, Width=b2, Visible=stp),
    ])
    # --- Support: help yourself first, then contact. The message is written here and copied; the contact form itself opens in the browser. ---
    amber2 = "RGBA(138,74,0,1)"
    hp, ct, fb = 'gSupTab = "Get help"', 'gSupTab = "Contact us"', 'gSupTab = "Feedback"'
    fbmsg = 'Trim(SuFbMsg.Text) & Char(10) & Char(10) & "DAM Policy Explorer (Power Apps), version " & nfVersion & ", screen " & App.Width / 2 & " x " & App.Height / 2 & " points."'
    issue = lambda t: f'If(!IsBlank(Trim(SuFbMsg.Text)), Copy({fbmsg}); Notify("Copied. Paste it into the form on GitHub.", NotificationType.Success)); Launch(nfRepo & "/issues/new?template={t}.yml&version=" & EncodeUrl(nfVersion) & "&where=" & EncodeUrl("Power Apps app"))'
    tp = picker("SuType", "nfReqTypes", "v", "gReqType", "SuD1N.Y + 44", "It is about", x="nfRX", w="nfRW", vis=ct)
    msg = '"[" & gReqType & "] " & Trim(SuMsg.Text) & If(SuDetails.Value, Char(10) & Char(10) & "Sent from: DAM Policy Explorer (Power Apps), version " & nfVersion & ", content checked " & nfChecked & ", screen " & App.Width / 2 & " x " & App.Height / 2 & " points.", "")'
    S["12-ScrSupport"] = Y().screen("ScrSupport", {**scr, "OnVisible": 'If(IsBlank(gSupTab), Set(gSupTab, "Get help")); If(IsBlank(gReqType), Set(gReqType, "A question about the policy"))'}, [
        *header("Su", '"Support and contact"', bg="nfBg5", ribbon=amber2),
        segmented("SuTabs", "nfSupTabs", "tab", "gSupTab", BAR + 12),
        cards("SuList", "nfSupport", open_item(), "ThisItem.title", "ThisItem.summ", "SuTabs.Y + SuTabs.Height + 8", tmpl=84, cols="nfCols2", ic="ThisItem.ic", col=amber2, tint="RGBA(247,237,224,1)", extra={"Visible": hp}, alabel="Ways to get help"),
        glass("SuPanel", "nfRX - 12", "SuTabs.Y + SuTabs.Height + 4", "nfRW + 24", f"If({ct}, SuNote.Y + SuNote.Height, SuFbNote.Y + SuFbNote.Height) + 16 - (SuTabs.Y + SuTabs.Height + 4)", r=18, Visible=f"!({hp})"),
        *divider("SuD1", '"1"', '"What is it about?"', "SuTabs.Y + SuTabs.Height + 20", col=amber2, Visible=ct),
        *tp[0],
        *divider("SuD2", '"2"', '"Your message"', "SuTypeBtn.Y + 56", col=amber2, Visible=ct),
        text_box("SuMsg", "Your message", "SuD2N.Y + 44", X="nfRX", Width="nfRW", Height="If(Parent.Height < 680, 72, 110)", Mode="TextMode.MultiLine", Clear="false", PaddingLeft=12, DelayOutput="false", MaxLength=1500, HintText='"Say what happened, or what you need. Leave out personal or sensitive details."', Visible=ct),
        ("SuDetails", TOG, {"Default": "true", "TrueText": '"Add app version and screen size"', "FalseText": '"Add app version and screen size: off"', "AccessibleLabel": '"Add app version and screen size to the message"', "X": "nfRX", "Y": "SuMsg.Y + SuMsg.Height + 8", "Width": "nfRW", "Height": 40, "Size": S_SMALL, "Font": FONT, "Color": INK, "TabIndex": 0, "TrueFill": BRAND, "FalseFill": MUTED, "FocusedBorderColor": FOCUS, "FocusedBorderThickness": 4, "Visible": ct}),
        *divider("SuD3", '"3"', '"Send it"', "SuDetails.Y + 48", col=amber2, Visible=ct),
        button("SuSend", 'If(nfCompact, "Copy and open the form", "Copy my message and open the contact form")', f'Copy({msg}); Notify("Message copied. Paste it into the contact form.", NotificationType.Success); Launch(nfContact)', X="nfRX", Y="SuD3N.Y + 44", Width="nfRW", DisplayMode="If(IsBlank(Trim(SuMsg.Text)), DisplayMode.Disabled, DisplayMode.Edit)", Visible=ct),
        secondary("SuOpen", 'If(nfCompact, "Open the form only", "Open the contact form without a message")', "Launch(nfContact)", X="nfRX", Y=f"SuD3N.Y + {44 + BTNH + 10}", Width="nfRW", Visible=ct),
        label("SuNote", '"Nothing is sent from this app. The form opens in your browser; paste your copied message into it."', Y=f"SuD3N.Y + {44 + 2 * (BTNH + 10)}", Visible=ct, **small),
        label("SuFbIntro", '"Bugs and ideas are tracked in the open on GitHub, next to the explorer\'s code. You need a free GitHub account. What you write there is public: leave out anything personal or sensitive."', Y="SuTabs.Y + SuTabs.Height + 20", Visible=fb),
        text_box("SuFbMsg", "Describe the bug or idea (optional)", "SuFbIntro.Y + SuFbIntro.Height + 12", X="nfRX", Width="nfRW", Height=96, Mode="TextMode.MultiLine", Clear="false", PaddingLeft=12, DelayOutput="false", MaxLength=1500, HintText='"Describe the bug or idea (optional). It is copied so you can paste it into the form."', Visible=fb),
        button("SuBug", '"Report a bug"', issue("bug"), X="nfRX", Y="SuFbMsg.Y + SuFbMsg.Height + 16", Width="nfRW", Visible=fb),
        button("SuIdea", 'If(nfCompact, "Suggest an idea or feature", "Suggest an idea, a new feature or an improvement")', issue("idea"), X="nfRX", Y=f"SuFbMsg.Y + SuFbMsg.Height + {16 + BTNH + 10}", Width="nfRW", Visible=fb),
        secondary("SuSeen", '"See what has been reported"', 'Launch(nfRepo & "/issues")', X="nfRX", Y=f"SuFbMsg.Y + SuFbMsg.Height + {16 + 2 * (BTNH + 10)}", Width="nfRW", Visible=fb),
        label("SuFbNote", '"No GitHub account? Choose Contact us instead."', Y=f"SuFbMsg.Y + SuFbMsg.Height + {16 + 3 * (BTNH + 10)}", Visible=fb, **small),
        *tp[1],
    ])
    # --- What's new: everything flagged New or Updated against the previous release, with the release note. ---
    S["13-ScrNew"] = Y().screen("ScrNew", scr, [
        *header("Nw", '"What is new"', bg="nfBg5", ribbon="RGBA(138,74,0,1)"),
        label("NwH", '"Version " & nfVersion & If(IsBlank(nfBaseVer), "", ", compared with version " & nfBaseVer)', Y=BAR + 16, X="nfCX", Width="nfCW", **h2),
        label("NwNotes", "nfNotes", Y="NwH.Y + NwH.Height + 6", X="nfCX", Width="nfCW", AutoHeight="false", Height=f"If(gNwMore, Max(120, Min(400, {PH} - Self.Y - 120)), If(nfCompact, 73, 97))", Overflow="If(gNwMore, Overflow.Scroll, Overflow.Hidden)", VerticalAlign="VerticalAlign.Top"),
        secondary("NwMore", 'If(gNwMore, "Show less of the release note", "Read the full release note")', "Set(gNwMore, !gNwMore)", X="nfCX", Y="NwNotes.Y + NwNotes.Height + 6", Width="Min(nfCW, 300)", Height=36, Size=S_SMALL),
        label("NwCount", 'nfNewCount & " items are new or updated. Each is tagged where it appears in the app."', Y="NwMore.Y + NwMore.Height + 8", X="nfCX", Width="nfCW", **small),
        cards("NwList", 'Filter(nfIndex, !IsBlank(flag))', open_ref(), "ThisItem.title", "ThisItem.type", "NwCount.Y + NwCount.Height + 8", tmpl=92, cols="nfCols2", ic="ThisItem.ic", col="ThisItem.col", tint="ThisItem.tint", flag="ThisItem.flag", alabel="New and updated items"),
        *empty("NwNone", "NwList", "Nothing has changed since the previous version."),
    ])
    return S


def main():
    pages, sections, qas, exs, glo, rep = build_tables()
    if "--write-baseline" in sys.argv:   # run against a checkout of the release being replaced (DPE_ROOT), when work on the next version starts
        out = pathlib.Path(sys.argv[sys.argv.index("--write-baseline") + 1])
        if pathlib.Path(ROOT).resolve() == pathlib.Path(HERE).resolve():
            # D-PA27: a release recorded as its own baseline has nothing new in it, so every New and Updated flag disappears
            sys.exit("FAIL: a baseline is written from the release being replaced, not from this one (D-PA27). "
                     "Check the published release out in another folder and run with DPE_ROOT set to it.")
        out.write_text(json.dumps({"version": C.VERSION, "items": manifest(sections, qas, exs, glo)}, indent=0, sort_keys=True))
        print(f"baseline for {C.VERSION}: {out}"); return
    f, nidx = formulas(pages, sections, qas, exs, glo)
    m = re.search(r"nfNewCount = (\d+)", f); rep.append(f"release flags: {m.group(1)} items new or updated since " + (re.search(r'nfBaseVer = "([^"]*)"', f).group(1) or "(no baseline)"))
    PA.mkdir(exist_ok=True); (PA / "screens").mkdir(exist_ok=True)
    (PA / "formulas.fx").write_text(f, encoding="utf-8")
    S = {k: v.replace("{N}", str(nidx)) for k, v in screens().items()}
    for k, v in S.items():
        (PA / "screens" / f"{k}.yaml").write_text(v, encoding="utf-8")
    (PA / "all-screens.yaml").write_text("Screens:\n" + "".join(v.split("\n", 1)[1] for _, v in sorted(S.items())), encoding="utf-8")
    rep += [f"search index: {nidx}", f"formulas: {len(f)} chars", "screens: " + ", ".join(f"{k} {len(v)}" for k, v in S.items())]
    # ---- checks ----
    bad = []
    allout = f + "".join(S.values())
    for m in BANNED.finditer(allout):
        ctx = allout[max(0, m.start() - 40): m.end() + 20]
        if "For the GDS team" in ctx: continue
        bad.append(f"banned term {m.group(0)!r}: …{ctx!r}")
    if len(qas) != len(C.QA): bad.append("question count differs from source")
    if len(exs) != len(X.EXAMPLES): bad.append("example count differs from source")
    content_only = "\n".join(l for l in f.split("\n") if not re.match(r"nf(Logo|Bg\d|SplashArt) = ", l))   # artwork is inline SVG drawn by Image controls, never passed to the HTML viewer
    if re.search(r"<(script|iframe|style|img|svg)\b", content_only, re.I): bad.append("disallowed tag in generated HTML")
    if re.search(r'href=""(?!https://)', f): bad.append("non-https link in generated HTML")
    for where, text in [("formulas", f)] + [(k, v) for k, v in S.items()]:      # every address the app can open, not only links inside page text
        for u in set(re.findall(r"http://[^\s\"'<>)]+", text)):
            if not u.startswith("http://www.w3.org/"): bad.append(f"address that is not https in {where}: {u[:60]}")
    for p in pages:
        if p[5] < 1: bad.append(f"page {p[0]} has no sections")
    # D-PA2: control names must be unique across the whole app, or Studio rejects the paste (MeBar was used twice)
    names = re.findall(r"^ +- ([A-Za-z0-9_]+):$", "".join(S.values()), re.M)
    for n in sorted({n for n in names if names.count(n) > 1}): bad.append(f"control name used more than once: {n}")
    for n, bottom, sy, th_ in CARD_GEOM:
        if sy < bottom or th_ < TITLE_2L: bad.append(f"card {n}: second line at {sy} overlaps a title ending {bottom}, or the title box {th_} is under two lines (D-PA12)")
    for u in sorted(set(UNGUARDED)): bad.append(f"top-level position not kept inside the design screen, Studio will replace it with a constant on paste (D-PA14): {u}")
    for u in sorted(set(UNSCALED)): bad.append(f"length next to * or / is not scaled, write pt(n): {u}")
    import yaml
    def walk(name, node, k):
        pr = node.get("Properties", {}); ctl = node.get("Control", "Screen")
        if ctl.split("@")[0] in ("Label", "Classic/Icon", "Rectangle", "Image") and "OnSelect" in pr:
            # D-PA3: anything with OnSelect is interactive, so it needs a name and a tab stop
            if pr.get("AccessibleLabel", '=""').strip() in ('=""', "=") or not re.fullmatch(r"=(0|If\(.+, -1, 0\))", str(pr.get("TabIndex", "=-1")).strip()):
                bad.append(f"{k}/{name}: has OnSelect but no accessible name or tab stop")
        if name.endswith("Scroll") and ctl.startswith("Gallery"):
            kids = [cn for c in node.get("Children", []) or [] for cn in c]
            if node.get("Variant") != "VariableHeight" or name[:-6] + "End" not in kids:
                bad.append(f"{k}/{name}: page content must be a flexible-height row with an end spacer, or long text hides behind the navigation (D-PA20)")
        if name.endswith("Scroll") and ctl.startswith("Gallery"):
            for c in node.get("Children", []) or []:
                for cn, cv in c.items():
                    cp = cv.get("Properties", {})
                    if "Parent.Height - Self.Height" in cp.get("Y", ""):
                        bad.append(f"{k}/{cn}: held inside the window height, so a long page is squeezed on a 320 x 568 phone and on the Studio canvas; the limit is the row (D-PA23)")
                    if cv.get("Control", "").startswith("HtmlViewer") and not cn.endswith("Panel") and ("Parent.Height" in cp.get("Height", "") or (cn.endswith("Body") and cp.get("AutoHeight", "").strip() != "=true")):
                        bad.append(f"{k}/{cn}: an HTML box sized to the window is squeezed to nothing on a phone; inside a scrolling page it must grow with its content (D-PA21)")
        if ctl == "Screen":
            for c in node.get("Children", []) or []:
                for cn, cv in c.items():
                    if cv.get("Control", "").startswith("HtmlViewer") and "Parent.Height" in cv.get("Properties", {}).get("Height", "") and not cn.endswith(("Panel", "Sheet")):
                        bad.append(f"{k}/{cn}: long text outside a scrolling page cannot be scrolled with the keyboard (D-PA24)")
        if ctl == "Screen":
            # D-PA26: with a sheet open, nothing behind it keeps a tab stop, and the sheet itself has one
            top = [(cn, cv) for c in node.get("Children", []) or [] for cn, cv in c.items()]
            opens = {cv.get("Properties", {}).get("Visible") for cn, cv in top if cn.endswith("Shade")} - {None}
            def stops(cn, cv):
                cp = cv.get("Properties", {}); t = str(cp.get("TabIndex", "=0" if cv.get("Control", "").startswith(TABBABLE) else "=-1")).strip()
                return ([cn] if t == "=0" else []) + [x for c in cv.get("Children", []) or [] for a, b in c.items() for x in stops(a, b)]
            for cn, cv in top:
                if opens and cv.get("Properties", {}).get("Visible") not in opens:
                    for x in stops(cn, cv): bad.append(f"{k}/{x}: keeps its tab stop while a sheet covers it, so keyboard focus goes where it cannot be seen (D-PA26)")
            for o in opens:
                if not any(stops(cn, cv) for cn, cv in top if cv.get("Properties", {}).get("Visible") == o):
                    bad.append(f"{k}: the sheet shown when {o} has nothing that takes keyboard focus (D-PA26)")
            covers = [cv.get("Properties", {}).get("Visible", "").strip().lstrip("=") for cn, cv in top if cn.endswith("TocBg")]
            for cn, cv in top:
                if covers and cn.endswith("Scroll") and cv.get("Properties", {}).get("Visible", "").strip() != "=!" + covers[0]:
                    bad.append(f"{k}/{cn}: the page stays in the tab order behind the contents list (D-PA26)")
        if name == "TsOpts" and "Len(label)" not in pr.get("TemplateSize", ""):
            bad.append(f"{k}/{name}: answer rows have a fixed height, so a three-line answer touches the edge of its row on a phone (D-PA22)")
        if node.get("Variant") == "Horizontal" and "CountRows" not in pr.get("TemplateSize", ""):
            bad.append(f"{k}/{name}: horizontal list can scroll sideways (D-PA7: content must fit the screen width)")
        if ctl.startswith("Classic/Button") and pr.get("Text", "").strip() in ('=""', "=") and "Disabled" not in pr.get("DisplayMode", ""):
            bad.append(f"{k}/{name}: button with no text has no accessible name")
        for c in node.get("Children", []) or []:
            for cn, cv in c.items(): walk(cn, cv, k)
    for k, v in S.items():
        try:
            d = yaml.safe_load(v)
            for sn, sv in d["Screens"].items(): walk(sn, sv, k)
        except Exception as e: bad.append(f"{k}: YAML does not parse: {e}")
    (PA / "report.txt").write_text("\n".join(rep + (["FAIL: " + b for b in bad] or ["ALL CHECKS PASS"])) + "\n")
    print("\n".join(rep)); print("\n".join("FAIL: " + b for b in bad) or "ALL CHECKS PASS")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
