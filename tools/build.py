#!/usr/bin/env python3
"""Build the DAM Policy Explorer into out/. Every page is plain HTML that works without JavaScript;
assets/explorer.js only adds to it (progressive enhancement, as the GDS Service Manual asks).

Usage: python3 -I tools/build.py [--home-url URL]
"""
import html, json, re, shutil, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import content as C  # noqa: E402

SRC, OUT = ROOT / "src", ROOT / "out"
E = html.escape
HOME_URL = sys.argv[sys.argv.index("--home-url") + 1] if "--home-url" in sys.argv else ""
PREVIEW = "--preview" in sys.argv   # claude.ai preview: cannot serve .ics or webmanifest files, and blocks downloads

NAV = [("index.html", "Home", "i-home"), ("policy.html", "The policy", "i-book"), ("return.html", "Your return", "i-list"),
       ("asset-test.html", "Asset test", "i-target"), ("track.html", "Track", "i-dashboard"), ("questions.html", "Questions", "i-help"), ("people.html", "Roles", "i-people"),
       ("capabilities.html", "Capabilities", "i-map")]
MORE = [("guide.html", "User guide and set-up", "i-book"), ("resources.html", "Resources", "i-folder"), ("ask.html", "Ask", "i-chat"), ("embed.html", "Embed it", "i-layers"), ("glossary.html", "Glossary", "i-tag"), ("team.html", "For the GDS team", "i-inbox"),
        ("about.html", "About this app", "i-info"), ("accessibility.html", "Accessibility", "i-shield")]

def sprite():
    s = (SRC / "index.html").read_text()
    m = re.search(r'<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">(.*?)</svg>', s, re.S)
    extra = ('<symbol id="i-home" viewBox="0 0 24 24"><path d="M3.5 11.5L12 4l8.5 7.5"/><path d="M6 10v10h12V10"/><path d="M10 20v-5h4v5"/></symbol>'
             '<symbol id="i-sliders" viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></symbol>'
             '<symbol id="i-sparkle" viewBox="0 0 24 24"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 1.8 1.8.7-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z"/></symbol>'
             '<symbol id="i-drawer" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/><path d="M5.5 8h1.5M5.5 11h1.5M5.5 14h1.5"/></symbol>'
             '<symbol id="i-cycle" viewBox="0 0 24 24"><path d="M20 12a8 8 0 0 1-14 5.3"/><path d="M4 12a8 8 0 0 1 14-5.3"/><path d="M18 3v4h-4M6 21v-4h4"/></symbol>')
    return '<svg xmlns="http://www.w3.org/2000/svg" class="sprite" aria-hidden="true" focusable="false"><defs>' + \
        re.sub(r'</?defs>', '', m.group(1)) + extra + '</defs></svg>'

SPRITE = None
def ic(name, cls="ic"):
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#{name}"/></svg>'

def badge(prov):
    label, tip = C.PROV[prov]
    return f'<span class="prov prov-{prov}" title="{E(tip)}">{E(label)}</span>'

def src_links(srcs):
    if not srcs: return ""
    return '<p class="source">Source: ' + "; ".join((f'<a href="{E(u)}">{E(t)} (GOV.UK)</a>' if u else f'{E(t)}') for t, u in srcs) + "</p>"

def long_date(iso):
    d = datetime.date.fromisoformat(iso); return f"{d.day} {d.strftime('%B %Y')}"

def page(fname, title, body, desc, scripts=("explorer.js",), crumbs=True, contents=True):
    nav_items = "".join(f'<li><a href="{h}"{" aria-current=\"page\"" if h == fname else ""}>{ic(i)}<span>{E(t)}</span></a></li>' for h, t, i in NAV)
    more_cur = any(h == fname for h, _, _ in MORE)
    more_items = "".join(f'<li><a href="{h}"{" aria-current=\"page\"" if h == fname else ""}>{ic(i)}<span>{E(t)}</span></a></li>' for h, t, i in MORE)
    heads = re.findall(r'<h2 id="([^"]+)"(?: data-count="(\d+)")?(?: data-new="1")?[^>]*>(.*?)</h2>', body, re.S)
    toc = ""
    if contents and len(heads) >= 2:
        toc = ('<nav class="contents" aria-labelledby="contents-h" data-drawer><h2 class="contents-h" id="contents-h">On this page</h2><ol>' +
               "".join(f'<li><a href="#{i}">{re.sub("<[^>]+>", "", t).strip()}' + (f' <span class="count" aria-label="{n} items">{n}</span>' if n else "") + '</a></li>'
                       for i, n, t in heads) + '</ol></nav>')
    crumb = "" if not crumbs or fname == "index.html" else f'<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="index.html">Home</a></li><li aria-current="page">{E(title)}</li></ol></nav>'
    js = "".join(f'<script src="assets/{s}" defer></script>' for s in scripts)
    return f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'">
<meta name="referrer" content="no-referrer">
<title>{E(title)} – DAM Policy Explorer</title>
<meta name="description" content="{E(desc)}">
<meta name="theme-color" content="#0b55a3">
<link rel="icon" href="assets/app-icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="assets/icon-192.png">
<link rel="manifest" href="manifest.webmanifest">
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="assets/explorer.css">
{js}
</head>
<body data-contact="{E(C.CONTACT)}" data-checked="{C.CONTENT_CHECKED}" data-stale-days="{C.STALE_AFTER_DAYS}" data-ready-by="{C.READY_BY}" data-version="{C.VERSION}">
{SPRITE}
<a class="skip" href="#main">Skip to main content</a>
<header class="xbanner">
  <div class="xwrap bar">
    <a class="brand" href="index.html"><img src="assets/app-icon.svg" alt="" width="36" height="36"><span><b>DAM Policy Explorer</b><small>Data Asset Management Policy, in one place</small></span></a>
    <form class="hsearch" action="ask.html" method="get" role="search"><label for="hq" class="vh">Ask a question about the DAM Policy</label><input id="hq" name="q" type="search" placeholder="Ask a question" autocomplete="off"><button type="submit" class="hs-btn">{ic("i-help")}<span class="vh">Ask</span></button></form>
    <button type="button" class="menu-btn" aria-expanded="false" aria-controls="site-nav" hidden>{ic("i-menu")}<span>Menu</span></button>
    <button type="button" class="settings-btn" aria-expanded="false" aria-controls="settings" hidden>{ic("i-sliders")}<span>Display</span></button>
  </div>
  <nav id="site-nav" class="xnav" aria-label="Main">
    <div class="xwrap"><ul class="primary">{nav_items}<li class="more"><details{" open" if False else ""}><summary{" class=\"cur\"" if more_cur else ""}>{ic("i-menu")}<span>More</span></summary><ul>{more_items}</ul></details></li></ul></div>
  </nav>
  <section id="settings" class="settings" aria-labelledby="settings-h" hidden>
    <div class="xwrap">
      <h2 id="settings-h" class="small-h">Display settings</h2>
      <p class="small">Saved on this device only.</p>
      <div class="set-grid">
        <fieldset><legend>Colours</legend>
          <label><input type="radio" name="theme" value="auto" checked> Match my device</label>
          <label><input type="radio" name="theme" value="light"> Light</label>
          <label><input type="radio" name="theme" value="dark"> Dark</label>
          <label><input type="radio" name="theme" value="contrast"> High contrast</label></fieldset>
        <fieldset><legend>Text size</legend>
          <label><input type="radio" name="text" value="normal" checked> Standard</label>
          <label><input type="radio" name="text" value="large"> Large</label>
          <label><input type="radio" name="text" value="xlarge"> Larger</label></fieldset>
        <fieldset><legend>Reading</legend>
          <label><input type="checkbox" name="spacing" value="wide"> Wider letter and line spacing</label>
          <label><input type="checkbox" name="motion" value="reduce"> Turn off animation</label>
          <label><input type="checkbox" name="underline" value="all"> Underline every link</label></fieldset>
      </div>
      <p><button type="button" class="btn secondary" data-reset>Reset to standard</button></p>
    </div>
  </section>
  <div class="xwrap phase"><span class="tag">Prototype</span> <span>This is a test version, not an official government service. If anything here disagrees with GOV.UK, GOV.UK is right. <a href="{E(C.CONTACT)}">Tell us what you think</a>.</span></div>
  <p class="stale" hidden></p>
</header>
<div class="xwrap layout">
{toc}
<main id="main" class="xmain" tabindex="-1">
{crumb}
{body}
{next_block(fname)}
</main>
</div>
{footer()}
<p id="announce" class="vh" aria-live="polite"></p>
</body>
</html>
'''

def footer():
    pol = "".join(f'<li><a href="{E(C.GOVUK[k][1])}">{E(C.GOVUK[k][0])}</a></li>' for k in ("policy", "cda", "metadata", "ownership", "dqap"))
    return f'''<footer class="xfoot">
  <div class="xwrap cols">
    <section aria-labelledby="f1"><h2 id="f1" class="small-h">About this app</h2><ul>
      <li><a href="about.html">About, roadmap and what changed</a></li>
      <li><a href="about.html#transparency">How it was made, and the use of AI</a></li>
      <li><a href="about.html#privacy">Privacy: what stays on your device</a></li>
      <li><a href="accessibility.html">Accessibility and inclusion</a></li>
      <li><a href="{E(C.CONTACT)}">Contact us (form)</a></li></ul></section>
    <section aria-labelledby="f2"><h2 id="f2" class="small-h">Published guidance</h2><ul>{pol}</ul></section>
    <section aria-labelledby="f3" class="colophon-col"><h2 id="f3" class="small-h">Version</h2>
      <div class="colophon">
        <img src="assets/qr.svg" width="104" height="104" alt="{"QR code that opens the home page of the DAM Policy Explorer" if HOME_URL else "QR code of the app name and version"}">
        <img src="assets/barcode.svg" width="200" height="72" alt="Barcode of the version number, DPE {C.VERSION}">
      </div>
      <p class="small">Version {C.VERSION}, built {long_date(C.BUILD_DATE)}.<br>Sources last checked {long_date(C.CONTENT_CHECKED)}.</p></section>
  </div>
  <div class="xwrap notes small">
    <p><b>Disclaimer.</b> This prototype explains the policy in plain English. It is not the policy. The published guidance on GOV.UK always takes priority.</p>
    <p><b>Disclosure.</b> Built with the help of an AI assistant (Claude, made by Anthropic). Every fact about the policy was checked against GOV.UK, and every answer shows where it comes from.</p>
    <p><b>Contact.</b> We use a Microsoft Form. You do not need to sign in, and only GDS sees what you send. Do not include sensitive information.</p>
    <p><b>Licence.</b> Text is available under the <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>, except where otherwise stated. © Crown copyright.</p>
  </div>
</footer>'''

# ---------- signposting ----------
JOURNEY = [("Understand", "policy.html", "i-book"), ("Test your assets", "asset-test.html", "i-target"), ("Prepare your list", "return.html#stage-3", "i-list"),
           ("Check it", "return.html#check", "i-check"), ("Send it", "return.html#step-10", "i-send"), ("Keep it current", "embed.html#cycle", "i-cycle")]
def journey(here=None):
    li = "".join(f'<li{" class=\"here\" aria-current=\"step\"" if here == i else ""}><a href="{h}">{ic(c)}<span class="jn">{i + 1}</span><span>{E(t)}</span></a></li>' for i, (t, h, c) in enumerate(JOURNEY))
    return f'<nav class="journey" aria-label="The DAM Policy journey"><ol>{li}</ol></nav>'

NEXT = {
    "index.html": (("Read the policy in plain English", "policy.html"), [("Test whether an asset is in scope", "asset-test.html"), ("Find an answer", "questions.html"), ("See all resources", "resources.html")]),
    "policy.html": (("Test whether an asset is in scope", "asset-test.html"), [("Start your return", "return.html"), ("Questions about scope", "questions.html#topic-scope"), ("Words explained", "glossary.html")]),
    "asset-test.html": (("Go to step 5: agree the list across your organisation", "return.html#step-5"), [("The four scope principles explained", "questions.html#q-principles"), ("Judging potential value", "questions.html#q-potential-value"), ("What to report: data sets or APIs", "questions.html#q-what-to-report")]),
    "return.html": (("Check your list before you send it", "return.html#check"), [("Asset test", "asset-test.html"), ("Questions about the return", "questions.html#topic-reporting"), ("Templates", "resources.html")]),
    "questions.html": (("Still stuck? Ask us through the contact form", None), [("The policy in plain English", "policy.html"), ("Your return, step by step", "return.html"), ("Glossary", "glossary.html")]),
    "embed.html": (("Plan your annual review now", "return.html#step-11"), [("Roles: who does what", "policy.html#roles"), ("Data quality action plan guide", "https://www.gov.uk/government/publications/implement-a-data-quality-action-plan/data-quality-action-plan-implementation-guide"), ("Questions about embedding", "questions.html#topic-embedding")]),
    "resources.html": (("Start your return", "return.html"), [("Find an answer", "questions.html"), ("Asset test", "asset-test.html"), ("Glossary", "glossary.html")]),
    "people.html": (("Start your return", "return.html"), [("Capabilities and playbooks", "capabilities.html"), ("Find an answer", "questions.html"), ("Full personas in the playbooks", C.PLAYBOOKS + "personas.html")]),
    "capabilities.html": (("Open the capability playbooks", C.PLAYBOOKS), [("Roles and journeys", "people.html"), ("Embed it in business as usual and change", "embed.html"), ("The policy", "policy.html")]),
    "guide.html": (("Start your return", "return.html"), [("Ask a question", "ask.html"), ("Accessibility", "accessibility.html"), ("About this app", "about.html")]),
    "track.html": (("Check your list before you send it", "return.html#check"), [("Sign off and send", "return.html#step-10"), ("Partial progress: how to report it", "questions.html#q-partial"), ("Embed it", "embed.html")]),
    "ask.html": (("Browse all questions and answers", "questions.html"), [("Glossary", "glossary.html"), ("Roles and journeys", "people.html")]),
    "glossary.html": (("Find an answer", "questions.html"), [("The policy in plain English", "policy.html"), ("Resources", "resources.html")]),
    "team.html": (("See what coordinators are asking", "questions.html#asked"), [("Check a return", "return.html#check"), ("About this app", "about.html")]),
    "about.html": (("Tell us what you think", None), [("Accessibility", "accessibility.html"), ("Roadmap", "about.html#roadmap")]),
    "accessibility.html": (("Change the display settings", "#settings"), [("About this app", "about.html")]),
}
def next_block(fname):
    if fname not in NEXT: return ""
    (pt, ph), rel = NEXT[fname]
    ph = ph or C.CONTACT
    rl = "".join(f'<li><a href="{E(h)}">{E(t)}</a></li>' for t, h in rel)
    return (f'<aside class="nextbest" aria-labelledby="nb-h"><h2 id="nb-h" class="nb-h">{ic("i-flag")} What to do next</h2>'
            f'<p><a class="btn" href="{E(ph)}">{E(pt)} <span aria-hidden="true">→</span></a></p>'
            f'<h3 class="rel-h">Related</h3><ul class="related">{rl}</ul></aside>')

def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-").split("-")[0] if t else ""

def cap_name(c):
    return next(x[2] for x in C.CAPS if x[0] == c)

def cap_chips(ids, names=True):
    return " ".join('<a class="cap-chip" href="' + E(C.cap_url(c)) + '">' + c + ((" " + E(cap_name(c))) if names else "") + '</a>' for c in ids)

def pathway(with_playbook=False):
    out = []
    for r, cs, pb in C.REQ_TO_CAP:
        li = '<li><span class="pw-req">' + E(r) + '</span><span class="pw-arrow" aria-hidden="true">→</span><span class="pw-caps">' + cap_chips(cs, not with_playbook) + '</span>'
        if with_playbook:
            li += '<span class="pw-arrow" aria-hidden="true">→</span><a class="pw-pb" href="' + E(C.PLAYBOOKS + pb) + '">' + E(pb.split(".")[0].capitalize()) + ' playbook</a>'
        out.append(li + '</li>')
    return '<ol class="pathway">' + "".join(out) + '</ol>'

# ---------- pages ----------

def home():
    roles = [("coordinator", "I coordinate my organisation's return", "i-flag", "return.html", "Twelve steps, your progress, and a check before you send.", True),
             ("cdo", "I am a chief data officer", "i-key", "people.html#p-cdo", "What you are responsible for, and what to ask your coordinator.", False),
             ("owner", "I own or look after data", "i-database", "people.html#p-own", "Test whether your data is in scope, then describe it and plan its quality.", False),
             ("alb", "I work in an arm's length body", "i-building", "questions.html#q-alb-returns", "How your return fits with your department's.", False),
             ("change", "I run a project or a service", "i-branch", "people.html#p-prg", "Build the policy in from the start of a change.", False),
             ("new", "I am new to this", "i-sparkle", "policy.html", "The policy in five minutes, in plain English.", False)]
    cards = "".join(f'<li class="card{" primary" if p else ""}"><a href="{h}">{ic(i, "ic big")}<span class="ct">{E(t)}</span><span class="cd">{E(d)}</span></a></li>'
                    for _, t, i, h, d, p in roles)
    answered = sum(1 for n in C.NEEDS if next(q for q in C.QA if q["id"] == n["qa"])["prov"] != "open")
    return page("index.html", "Home", f'''
<div class="hero">
  <div class="hero-text">
    <p class="kicker">{ic("i-sparkle")} For DAM Policy coordinators, and everyone who helps them</p>
    <h1>Everything you need for the Data Asset Management Policy, in one place</h1>
    <p class="lead">Find out what the policy asks, test which of your data is in scope, make your return step by step, and get answers to the questions other coordinators have asked.</p>
    <p class="cta"><a class="btn" href="return.html">{ic("i-list")} Start or continue your return</a> <a class="btn secondary" href="questions.html">{ic("i-help")} Find an answer</a></p>
  </div>
  <img class="hero-art" src="assets/hero.svg" alt="" width="420" height="320">
</div>

<h2 id="path">Your path through the policy</h2>
{journey()}

<section class="glance" aria-labelledby="glance-h">
  <h2 id="glance-h" class="vh">At a glance</h2>
  <ul class="stats">
    <li><span class="num" data-count-to="4">4</span><span class="lbl">scope principles decide if an asset is in</span></li>
    <li><span class="num" data-count-to="7">7</span><span class="lbl">critical purposes</span></li>
    <li><span class="num" data-count-to="24">24</span><span class="lbl">details to record for each asset</span></li>
    <li><span class="num" data-count-to="12">12</span><span class="lbl">steps from start to sent</span></li>
  </ul>
</section>

<div class="duo">
  <section class="panel" aria-labelledby="when-h">
    <h2 id="when-h">{ic("i-calendar")} When</h2>
    <p class="big-date"><span data-countdown>Aim to be ready by Friday 18 December 2026.</span></p>
    <p>GDS plans to collect the first return, the Baseline Return, in January 2027. {badge("plan")}</p>
    <p class="small">These dates are not yet in the published policy. The policy itself asks for a review every year. {badge("policy")}</p>
    {"" if PREVIEW else '<p><a href="assets/dam-key-dates.ics" download>' + ic("i-calendar") + ' Add the readiness date to Outlook</a></p>'}
  </section>
  <section class="panel" aria-labelledby="prog-h">
    <h2 id="prog-h">{ic("i-check")} Your progress</h2>
    <div class="progress-home" data-progress-home>
      <p>Mark steps as done on <a href="return.html">your return</a> and your progress shows here. It is saved on this device only.</p>
    </div>
  </section>
</div>

<h2 id="who">What brings you here?</h2>
<ul class="cards">{cards}</ul>

<p class="small">{ic("i-info")} <a href="guide.html">User guide, and how to get the explorer in Teams, Outlook, Copilot, on your intranet or on any device</a>.</p>

<h2 id="asked" data-count="{len(C.NEEDS)}">Built from your questions</h2>
<p>This app answers the questions coordinators have raised in the working group, on the Knowledge Hub, by email and in meetings. {answered} of the {len(C.NEEDS)} needs we heard now have an answer here. The rest are being decided, and each one says what to do meanwhile.</p>
<p><a href="questions.html#asked">See every need and where it is answered</a></p>

<h2 id="plain">The policy in five sentences</h2>
<ol class="plain">
  <li>Government departments and their arm's length bodies must find and record their important shared data, and report it to GDS.</li>
  <li>Only OFFICIAL data counts, and only if it serves one of seven critical purposes, has value across government through sharing, and your organisation is accountable for it.</li>
  <li>Every one of these data assets needs a named owner and a plan to keep its quality good enough.</li>
  <li>Your chief data officer is responsible, and the list must be reviewed every year.</li>
  <li>Listing data does not mean you have to share it.</li>
</ol>
<p class="small">Source: <a href="{E(C.GOVUK["policy"][1])}">Data Asset Management Policy in government (GOV.UK)</a> and <a href="{E(C.GOVUK["cda"][1])}">Identifying and recording critical data assets (GOV.UK)</a>.</p>

<h2 id="new">What's new</h2>
<ul class="changes">{"".join(f'<li><span class="when">{long_date(d)}</span> <b>Version {v}.</b> {E(t)}</li>' for d, v, t in C.CHANGES)}</ul>
''', "One place for everything about the Data Asset Management Policy: what it asks, the return step by step, and answers to coordinators' questions.")

def policy():
    must = [("Find and record your data assets", "Identify the data assets in scope, manage metadata about them in your data catalogue, and report them to GDS.", "Section 4"),
            ("Departments coordinate their arm's length bodies", "Send metadata on your own assets, and coordinate and assure the returns from your arm's length bodies.", "Section 4"),
            ("Name an owner for every asset", "Every identified data asset must have a named data owner, accountable for decisions about it.", "Section 5"),
            ("Plan for quality", "Every identified data asset must have a data quality action plan or equivalent.", "Section 6"),
            ("Keep it up to date", "Maintain what you send and review it every year.", "Section 4"),
            ("Your chief data officer is responsible", "The chief data officer of each organisation in scope is responsible for putting the policy into practice there.", "Section 8")]
    mustli = "".join(f'<li class="req">{ic("i-check")}<div><h3>{E(t)}</h3><p>{E(d)}</p><p class="small muted">{E(s)} of the policy {badge("policy")}</p></div></li>' for t, d, s in must)
    roles = "".join(f'<tr><th scope="row">{E(r["role"])}</th><td>{E(r["does"])}</td><td>{badge(r["prov"])}{(" <a href=\"" + E(r["src"][1]) + "\">source</a>") if r["src"] else ""}</td></tr>' for r in C.ROLES)
    scope = [("Government departments", "Must", "yes"), ("Arm's length bodies: executive agencies, non-departmental public bodies, non-ministerial departments", "Must", "yes"),
             ("Public corporations", "Optional", "maybe"), ("Local government", "Optional", "maybe"), ("Devolved governments", "Use their own data sharing governance", "no")]
    scoperows = "".join(f'<tr><th scope="row">{E(a)}</th><td><span class="pill {c}">{E(b)}</span></td></tr>' for a, b, c in scope)
    purposes = ["Delivering public services", "A legislative, legal or contractual requirement", "Defence, national security and resilience", "Developing and evaluating policy", "Official statistics", "The public interest", "Fraud and error"]
    return page("policy.html", "The policy", f'''
<h1>The policy in plain English</h1>
{journey(0)}
<p class="lead">The Data Asset Management Policy asks government organisations to find, describe and look after the data they share with each other. GDS published it on 27 May 2026.</p>
<div class="facts"><p>{ic("i-info")} This page explains the policy. It does not replace it. <a href="{E(C.GOVUK["policy"][1])}">Read the policy on GOV.UK</a>.</p></div>

<h2 id="why">Why it exists</h2>
<p>Government relies on data that passes between organisations. When nobody knows what that data is, who owns it or how good it is, services and decisions suffer. The policy sets a minimum standard for quality, discoverability, interoperability and clear ownership. {badge("policy")}</p>

<h2 id="who">Who it applies to</h2>
<table class="tbl"><caption class="vh">Who the policy applies to</caption><thead><tr><th scope="col">Organisation</th><th scope="col">Applies?</th></tr></thead><tbody>{scoperows}</tbody></table>
{src_links([C.GOVUK["policy"]])}

<h2 id="must" data-count="{len(must)}">What you must do</h2>
<ul class="reqs">{mustli}</ul>

<h2 id="scope">What counts as a critical data asset</h2>
<p>First, the data must be OFFICIAL. SECRET and TOP SECRET data is not in scope. {badge("policy")}</p>
<p>Then all four DAM Policy scope principles must apply. {badge("gds")}</p>
<ol class="tests principles">
  <li><b>It meets a critical criterion.</b> It supports at least one of seven critical purposes.</li>
  <li><b>It is shared.</b> It has value across government through reuse: shared under a data sharing agreement, published as open data, or could create value if shared.</li>
  <li><b>You are accountable for it.</b> You manage or control it, including others' data you have materially changed or enriched.</li>
  <li><b>It is the source.</b> Report the source data behind a critical extract, report or API.</li>
</ol>
<details><summary>The seven critical purposes</summary><div class="body"><ol>{"".join(f"<li>{E(p)}</li>" for p in purposes)}</ol></div></details>
<p><a class="btn" href="asset-test.html">{ic("i-target")} Test a possible asset</a></p>
{src_links([C.GOVUK["cda"], C.FAQ])}

<h2 id="not">What the policy does not do</h2>
<ul><li>It does not make you share data.</li><li>It does not remove any legal obligation you already have.</li><li>It does not promise that data will be available, or of a given quality, beyond what is already agreed.</li></ul>
{src_links([C.GOVUK["policy"]])}

<h2 id="myths" data-count="{len(C.MYTHS)}">Myths and facts</h2>
<ul class="myths">{"".join(f'<li><p class="myth"><span class="tagm">Myth</span> {E(m)}</p><p class="fact"><span class="tagf">Fact</span> {E(f)} {badge(pv)}</p></li>' for m, f, pv in C.MYTHS)}</ul>
{src_links([C.GOVUK["policy"], C.FAQ])}

<h2 id="capabilities">From requirement to capability</h2>
<p>Each requirement rests on a capability your organisation needs. The <a href="capabilities.html">capabilities page</a> shows all 32 and links to a playbook for each.</p>
{pathway()}

<h2 id="roles" data-count="{len(C.ROLES)}">Who does what</h2>
<div class="tbl-scroll" tabindex="0" role="region" aria-label="Who does what, scrollable table"><table class="tbl"><caption class="vh">Roles and responsibilities</caption><thead><tr><th scope="col">Role</th><th scope="col">What they do</th><th scope="col">Where this comes from</th></tr></thead><tbody>{roles}</tbody></table></div>

<h2 id="family">The guidance that goes with it</h2>
<ul class="guide-list">{"".join(f'<li><a href="{E(C.GOVUK[k][1])}">{E(C.GOVUK[k][0])}</a></li>' for k in ("cda", "metadata", "ownership", "dqap", "dqissues", "dqf"))}</ul>

<h2 id="support">What GDS offers</h2>
<ul><li>Published guidance and standards, including the data quality action plan guide and the data quality issues framework.</li><li>Support targeted at organisations' different levels of data maturity and resources, starting with assets that are proven to be reused.</li><li>A service, being developed, to make data asset metadata easy to find across government.</li></ul>
{src_links([C.GOVUK["policy"]])}
''', "The Data Asset Management Policy in plain English: who it applies to, what you must do, and who does what.")

def asset_test():
    purposes = ["Delivering public services", "A legislative, legal or contractual requirement", "Defence, national security and resilience", "Developing and evaluating policy", "Official statistics", "The public interest", "Fraud and error"]
    pur = "".join(f'<label class="opt"><input type="checkbox" name="purpose" value="{i}"> {i}. {E(p)}</label>' for i, p in enumerate(purposes, 1))
    def radios(name, num, q, hint, opts):
        o = "".join(f'<label class="opt"><input type="radio" name="{name}" value="{v}"> {E(t)}</label>' for v, t in opts)
        return f'<fieldset class="q" data-q="{name}"><legend><h2 id="q-{name}"><span class="qn">{num}</span> {q}</h2></legend><p class="hint">{hint}</p>{o}</fieldset>'
    unsure = ("unsure", "Not sure")
    return page("asset-test.html", "Asset test", f"""
<h1>Is this a critical data asset?</h1>
{journey(1)}
<p class="lead">Answer five short questions about one possible asset. You will find out whether it goes in your return, and why.</p>
<p class="small">Based on the OFFICIAL scope rule in the policy {badge("policy")} and the four DAM Policy scope principles {badge("gds")}. Nothing you type leaves your device.</p>
<form class="asset-test" action="#result" method="get" novalidate>
  <div class="field"><label for="asset-name"><b>Name of the possible asset</b> (optional)</label><span class="hint" id="asset-hint">For example, "Vehicle keeper records". It only labels your result.</span><input id="asset-name" name="asset" type="text" autocomplete="off" maxlength="120" aria-describedby="asset-hint"></div>
  {radios("official", "1", "Is it classified OFFICIAL?", "OFFICIAL with markings such as sensitive counts. SECRET and TOP SECRET do not.", [("yes", "Yes"), ("no", "No, it is SECRET or TOP SECRET"), unsure])}
  <fieldset class="q" data-q="purpose"><legend><h2 id="q-purpose"><span class="qn">2</span> Which critical purposes does it serve?</h2></legend><p class="hint">Principle 1, a critical criterion. Choose all that apply, or none.</p>{pur}<label class="opt"><input type="checkbox" name="purpose" value="unsure"> Not sure</label></fieldset>
  {radios("shared", "3", "How is it shared?", "Principle 2, shared. Choose the best fit.", [("dsa", "Shared with a public sector organisation under a data sharing agreement"), ("open", "Published as open data"), ("potential", "Not shared yet, but could create value if it were"), ("no", "Only used inside our organisation"), unsure])}
  {radios("accountable", "4", "Who is accountable for it?", "Principle 3, accountable.", [("own", "We manage or control it"), ("enriched", "It came from another organisation, and we have materially changed or enriched it"), ("asis", "It came from another organisation and we use it as it is"), unsure])}
  {radios("source", "5", "Is it the source data?", "Principle 4, prioritise the source.", [("source", "Yes, it is the source data set"), ("product", "No, it is an extract, report, API or product, but it is managed and owned in its own right"), ("derived", "No, it is an extract, report, API or product drawn from source data"), unsure])}
  <p><button type="submit" class="btn">See the result</button></p>
</form>
<section id="result" class="result" tabindex="-1" aria-labelledby="result-h"><h2 id="result-h">Your result</h2><noscript><p>With JavaScript turned off, read the questions above: the asset goes in your return if it is OFFICIAL, serves at least one purpose, is shared or could be, you are accountable for it, and it is the source.</p></noscript><div data-result aria-live="polite"><p>Answer the questions, then choose <b>See the result</b>.</p></div></section>
<section class="tested" aria-labelledby="tested-h" hidden><h2 id="tested-h">Assets you have tested</h2><div data-tested></div>
<p><button type="button" class="btn secondary" data-download>{ic("i-download")} Download the assets left out (CSV)</button> <button type="button" class="btn secondary" data-clear>Clear the list</button></p></section>
""", "Check a possible asset against the DAM Policy scope rules, one question at a time.")

def questions():
    topics = [t for t in C.TOPICS if any(q["topic"] == t for q in C.QA)]
    chips = '<label class="chip"><input type="radio" name="topic" value="" checked> All</label>' + "".join(f'<label class="chip"><input type="radio" name="topic" value="{E(t)}"> {E(t)}</label>' for t in topics)
    needs_by_q = {}
    for n in C.NEEDS: needs_by_q.setdefault(n["qa"], []).append(n)
    items = ""; last = None
    # D-18: group by topic order, so an answer added out of place cannot split a topic into two headings
    for q in sorted(C.QA, key=lambda q: C.TOPICS.index(q["topic"])):
        if q["topic"] != last:
            items += f'<h3 class="topic-h" id="topic-{slug(q["topic"])}">{E(q["topic"])}</h3>'; last = q["topic"]
        asked = needs_by_q.get(q["id"], [])
        n = sum(x["raised"] for x in asked)
        items += (f'<article class="qa" id="q-{q["id"]}" data-topic="{E(q["topic"])}"><details><summary><span class="qtext">{E(q["q"])}</span> {badge(q["prov"])}'
                  + (f' <span class="asked" title="Times raised in forums">asked {n}×</span>' if n else "") + f'</summary><div class="body">{q["a"]}{src_links(q["src"])}'
                  + (f'<p class="small muted">Answers needs {", ".join(x["id"] for x in asked)} below.</p>' if asked else "") + '</div></details></article>')
    themes = {}
    for nd in C.NEEDS: themes[nd["theme"]] = themes.get(nd["theme"], 0) + nd["raised"]
    mx = max(themes.values())
    bars = "".join(f'<li><span class="bl">{E(t)}</span><span class="chartbar" data-w="{round(v / mx * 100)}"><span class="fill w{round(v / mx * 10) * 10}"></span></span><span class="bv">{v}</span></li>' for t, v in sorted(themes.items(), key=lambda kv: -kv[1]))
    rows = ""
    for nd in C.NEEDS:
        q = next(x for x in C.QA if x["id"] == nd["qa"])
        rows += f'<tr><td>{nd["id"]}</td><td>{E(nd["need"])}</td><td>{E(nd["theme"])}</td><td>{nd["raised"]}</td><td>{badge(q["prov"])}</td><td><a href="#q-{q["id"]}">{E(q["q"])}</a></td></tr>'
    return page("questions.html", "Questions and answers", f'''
<h1>Questions and answers</h1>
<p class="lead">Answers to the questions coordinators have actually asked. Each answer says where it comes from, so you know how far you can rely on it.</p>
<p class="small">Includes every answer in the GDS DAM Policy FAQs (November 2026), rewritten in plain English, with the published GOV.UK guidance where it covers the same point.</p>
<nav class="topic-jump" aria-label="Topics"><ul>{"".join(f'<li><a href="#topic-{slug(t)}">{E(t)} <span class="count">{sum(1 for q in C.QA if q["topic"] == t)}</span></a></li>' for t in topics)}</ul></nav>
<div class="legend">{"".join(badge(k) + f'<span class="small">{E(v[1])}</span>' for k, v in C.PROV.items())}</div>

<h2 id="answers" data-count="{len(C.QA)}">Find an answer</h2>
<div class="filters" role="search">
  <label for="qa-search"><b>Search questions and answers</b></label>
  <input id="qa-search" type="search" autocomplete="off" aria-describedby="qa-count">
  <fieldset class="chips"><legend>Topic</legend>{chips}</fieldset>
  <p id="qa-count" class="small" aria-live="polite">{len(C.QA)} questions</p>
</div>
<div class="qa-list">{items}</div>

<h2 id="asked" data-count="{len(C.NEEDS)}">What coordinators asked us</h2>
<p>We collect every question raised in the DAM Policy Coordinators Working Group, on the Knowledge Hub, at the Data Catalogue and Analysis Platform Working Group, by email and in meetings. Each need below is written in our own words, with names and organisations removed. The table shows where each one is answered. {badge("gds")}</p>
<figure class="chart"><figcaption>Times each theme was raised</figcaption><ul class="bars">{bars}</ul></figure>
<div class="tbl-scroll" tabindex="0" role="region" aria-label="Needs and where they are answered, scrollable table"><table class="tbl small"><caption class="vh">Needs and where they are answered</caption>
<thead><tr><th scope="col">Need</th><th scope="col">What people asked</th><th scope="col">Theme</th><th scope="col">Times raised</th><th scope="col">Status</th><th scope="col">Answered in</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small muted">From the GDS question register, as it stood on {long_date(C.REGISTER_SNAPSHOT)}. Questions about other topics, such as AI, are handled elsewhere.</p>
<p>Not here? <a href="{E(C.CONTACT)}">Ask us through the contact form</a>. We add repeated questions to this page.</p>
''', "Answers to the questions DAM Policy coordinators have asked, each with its source.")

def embed():
    cycle = [("Identify", "Test possible assets against the scope principles.", "policy"), ("Record", "Describe each asset in your catalogue.", "policy"),
             ("Own", "Name an owner, and a steward to look after it.", "policy"), ("Assure quality", "Keep a quality plan, and act on the issues it finds.", "policy"),
             ("Report", "Send your return to GDS.", "policy"), ("Review", "Look at the whole list again at least once a year.", "policy")]
    cyc = "".join(f'<li><span class="cn">{i}</span><b>{E(t)}</b><span>{E(d)}</span></li>' for i, (t, d, _) in enumerate(cycle, 1))
    bau = [("Put it in role descriptions", "Write data owner and steward duties into the roles that hold them, so they survive people moving on."),
           ("Use your existing governance", "Take the asset list and quality plans to the board or committee that already oversees information risk."),
           ("Fix a yearly date", "Pick a month for the annual review and put it in the business plan, ahead of the return."),
           ("Keep the catalogue as the source", "Update the catalogue first and fill the return from it, so you never keep two lists."),
           ("Track gaps, not just answers", "Keep a short list of policy gaps, such as assets with no owner, and review progress quarterly.")]
    change = [("Discovery", "List the data the service will create, use or share with other organisations. Note which critical purposes it serves."),
              ("Alpha", "Run each likely asset through the asset test. Agree who will own it. Check the legal basis for any sharing."),
              ("Beta", "Describe each asset in your catalogue using the core metadata. Start its data quality action plan."),
              ("Live", "Make sure the assets are in your organisation's next return, and hand ownership to the business, not the project."),
              ("Retirement", "When the service closes, update or remove its assets from your list and your catalogue.")]
    return page("embed.html", "Embed it", f'''
<h1>Make the policy part of how you work</h1>
<p class="lead">The return is one moment in the year. The policy works when knowing, owning and looking after your shared data becomes normal, both in day-to-day business and whenever something changes.</p>

<h2 id="cycle">The yearly cycle</h2>
<p>Each stage comes from a requirement in the policy. {badge("policy")}</p>
<ol class="cycle">{cyc}</ol>
{src_links([C.GOVUK["policy"]])}

<h2 id="bau" data-count="{len(bau)}">In business as usual</h2>
<p>Ways organisations can keep the policy working after the first return. {badge("practice")}</p>
<ul class="tiles">{"".join(f'<li>{ic("i-cycle")}<div><h3>{E(t)}</h3><p>{E(d)}</p></div></li>' for t, d in bau)}</ul>

<h2 id="change" data-count="{len(change)}">In change: projects and new services</h2>
<p>Build it in from the start, so a new service's data joins your list without extra work. This follows the Service Standard's delivery phases and point 10 of the Technology Code of Practice, which asks teams to plan for data across its lifecycle. {badge("practice")}</p>
<ol class="phases">{"".join(f'<li><span class="ph">{E(p)}</span><p>{E(d)}</p></li>' for p, d in change)}</ol>
{src_links([C.GOVUK["tcop10"], C.GOVUK["standard"]])}

<h2 id="owners">Practical kit for data owners and stewards</h2>
<p>Coordinators asked for practical help, not more policy. Use these as they are, or adapt them to your organisation. {badge("practice")}</p>
<div class="kit">
<section class="kit-card" aria-labelledby="k-own"><h3 id="k-own">{ic("i-key")} Data owner: what to do first</h3><ol class="checklist">
<li>Accept the role in writing, and name a successor so the asset is never left without an owner.</li>
<li>Know each asset: what it is for, who relies on it, and what it must not be used for.</li>
<li>Agree quality targets with your steward, and approve the asset's quality plan.</li>
<li>Decide which risks you accept, and record them on the risk register you already use.</li>
<li>Before each return, check the asset's details in your catalogue are current.</li></ol></section>
<section class="kit-card" aria-labelledby="k-stw"><h3 id="k-stw">{ic("i-gear")} Data steward: what to do first</h3><ol class="checklist">
<li>Complete the catalogue record, and record each fact once, in one place.</li>
<li>Write the quality rules and targets with the owner, and measure where you start.</li>
<li>Fix problems where they start, not where they show up.</li>
<li>Log issues using the data quality issues framework, and tell the owner what needs a decision.</li>
<li>Keep a short handover note, so the next steward can carry on.</li></ol></section>
<section class="kit-card" aria-labelledby="k-q"><h3 id="k-q">{ic("i-help")} Questions for the owner to ask each quarter</h3><ul>
<li>Who relies on this data now, and for what?</li><li>Has anything changed: the system, a supplier, the law, the people?</li>
<li>Are the known quality issues getting better?</li><li>Who would I call if it failed tomorrow?</li><li>Is my named successor still right?</li></ul></section>
<section class="kit-card" aria-labelledby="k-c"><h3 id="k-c">{ic("i-chat")} Owner and steward conversation (30 minutes, each quarter)</h3><ol>
<li>What changed since last time.</li><li>Quality against targets, and the top issues.</li><li>Decisions the owner needs to make, including risks to accept.</li>
<li>Requests to share or reuse the data.</li><li>Anything for the next return.</li></ol></section>
</div>
<p><b>What works elsewhere:</b> one department found most stewards are not data specialists. It builds steward tasks into moments when they already deal with the data team, such as adding the data behind published analysis to the catalogue, rather than asking for separate work. {badge("practice")}</p>
{src_links([C.GOVUK["ownership"], C.GOVUK["dqap"], C.GOVUK["dqissues"]])}
<p>More: the <a href="{C.PLAYBOOKS}governance.html">data governance playbook</a> and the <a href="people.html#p-own">data owner</a> and <a href="people.html#p-stw">data steward</a> journeys. GDS is also developing training for data owners.</p>

<h2 id="brief">Briefing your arm's length bodies</h2>
<p>An outline for a 45-minute introduction, with a page here for each point that people can read afterwards. GDS is happy to support departments in these conversations: ask through the <a href="{E(C.CONTACT)}">contact form</a>. {badge("practice")}</p>
<ol class="phases">
<li><span class="ph">The ask (5 minutes)</span><p>Find, record and report your critical data assets, each with an owner and a quality plan. <a href="policy.html#must">What you must do</a></p></li>
<li><span class="ph">The scope (10 minutes)</span><p>OFFICIAL, and the four scope principles. <a href="asset-test.html">Asset test</a></p></li>
<li><span class="ph">Why it matters (5 minutes)</span><p>Government relies on data that passes between organisations. <a href="policy.html#why">Why it exists</a></p></li>
<li><span class="ph">How your return works (10 minutes)</span><p>Version 3 of the template, through your department, due in January 2027. <a href="questions.html#q-alb-returns">Arm's length bodies and the return</a></p></li>
<li><span class="ph">Support, and questions (15 minutes)</span><p>This explorer, the playbooks and GDS. <a href="questions.html">Questions and answers</a></p></li>
</ol>

<h2 id="capability">Build the capability behind it</h2>
<p>The return shows where your organisation's data management needs to grow: catalogues, ownership, metadata and quality. Start with the gaps the return reveals, and use the published guidance for each one.</p>
<ul class="guide-list"><li><a href="{E(C.GOVUK["ownership"][1])}">Ownership: the data ownership model</a></li><li><a href="{E(C.GOVUK["metadata"][1])}">Metadata: recording metadata for critical data assets</a></li><li><a href="{E(C.GOVUK["dqap"][1])}">Quality: the data quality action plan guide</a></li><li><a href="{E(C.GOVUK["dqf"][1])}">Quality culture: the Government Data Quality Framework</a></li></ul>
''', "Make the Data Asset Management Policy part of business as usual and of every change project.")

def resources():
    types = sorted({r["type"] for r in C.RESOURCES})
    fl = '<label class="chip"><input type="radio" name="rtype" value="" checked> All</label>' + "".join(f'<label class="chip"><input type="radio" name="rtype" value="{t}"> {t}</label>' for t in types)
    fa = '<label class="chip"><input type="radio" name="raud" value="" checked> Everyone</label>' + "".join(f'<label class="chip"><input type="radio" name="raud" value="{k}"> {E(v)}</label>' for k, v in C.AUDIENCES.items())
    icon = {"Guidance": "i-book", "Template": "i-download", "Tool": "i-gear"}
    items = "".join(f'<li class="res" data-type="{r["type"]}" data-aud="{" ".join(r["for"])}">{ic(icon[r["type"]], "ic big")}<div><h3><a href="{E(r["u"])}"{" download" if r["u"].endswith(".csv") else ""}>{E(r["t"])}</a></h3><p>{E(r["d"])}</p><p class="small muted">{r["type"]} · for {", ".join(C.AUDIENCES[a] for a in r["for"])} {badge(r["prov"])}</p></div></li>' for r in C.RESOURCES)
    return page("resources.html", "Resources", f'''
<h1>Resources</h1>
<p class="lead">All the published guidance, templates and tools for the policy, in one list.</p>
<h2 id="all" data-count="{len(C.RESOURCES)}">Guidance, templates and tools</h2>
<div class="filters"><fieldset class="chips"><legend>Type</legend>{fl}</fieldset><fieldset class="chips"><legend>Who it is for</legend>{fa}</fieldset><p id="res-count" class="small" aria-live="polite">{len(C.RESOURCES)} resources</p></div>
<ul class="res-list">{items}</ul>
<h2 id="meetings">Meetings and recordings</h2>
<p>The coordinators' FAQ and meeting recordings are kept with the DAM Policy Coordinators Working Group on the Knowledge Hub. If you cannot open something, <a href="{E(C.CONTACT)}">tell us through the contact form</a> and we will send it another way.</p>
''', "Published guidance, templates and tools for the Data Asset Management Policy.")

def people():
    order = ["Learn", "Prepare", "Do", "Report", "Improve"]
    needs = {n["id"]: n for n in C.NEEDS}
    cards = "".join(f'<li><a href="#p-{x["id"]}">{ic(x["icon"])}<span>{E(x["name"])}</span></a></li>' for x in C.PERSONAS)
    head = "".join(f'<th scope="col">{s}</th>' for s in order)
    rows = ""
    for x in C.PERSONAS:
        cells = "".join('<td><ul>' + "".join(f'<li><a href="{E(h)}">{E(t)}</a></li>' for t, h in x["journey"].get(s, [])) + '</ul></td>' for s in order)
        rows += f'<tr><th scope="row"><a href="#p-{x["id"]}">{E(x["name"])}</a></th>{cells}</tr>'
    sections = ""
    for x in C.PERSONAS:
        lanes = "".join(f'<li class="lane"><span class="stage">{i + 1}. {s}</span><ul>' + "".join(f'<li><a href="{E(h)}">{E(t)}</a></li>' for t, h in x["journey"].get(s, [])) + '</ul></li>' for i, s in enumerate(order))
        capl = cap_chips(x["caps"])
        asked = "".join(f'<li>{E(needs[n]["need"])} <a href="questions.html#q-{needs[n]["qa"]}">Answer</a></li>' for n in x["needs"])
        sections += f"""<section class="persona{' primary' if x.get('primary') else ''}" id="p-{x['id']}" aria-labelledby="ph-{x['id']}">
<h2 id="ph-{x['id']}">{ic(x['icon'], 'ic big')} {E(x['name'])}</h2>
<p class="lead-s">{E(x['role'])}</p>
<div class="p-grid">
<div><h3>Context</h3><p>{E(x['context'])}</p><h3>Goals</h3><ul>{"".join(f"<li>{E(g)}</li>" for g in x['goals'])}</ul></div>
<div><h3>User stories</h3><ul class="stories">{"".join(f"<li>As a {E(x['name'].lower())}, I need {E(st)}.</li>" for st in x['stories'])}</ul>
<h3>What gets in the way</h3><ul>{"".join(f"<li>{E(b)}</li>" for b in x['blockers'])}</ul></div>
</div>
<p class="success">{ic('i-target')} <b>Success looks like:</b> {E(x['success'])}</p>
<h3>Journey</h3><ol class="lanes">{lanes}</ol>
<h3>What people in this role asked us</h3><ul>{asked}</ul>
<h3>Capabilities to build</h3><p class="chips-row">{capl}</p>
<p><a href="{C.PLAYBOOKS}personas.html#p-{x['id']}">Full route and learning journey in the playbooks</a></p>
</section>"""
    return page("people.html", "Roles and journeys", f"""
<h1>Roles and journeys</h1>
<p class="lead">Who takes part in the DAM Policy, what each person needs, and the route through this app and the playbooks that fits their role.</p>
<p class="small">The roles and user stories come from the <a href="{C.PLAYBOOKS}personas.html">DAM capability playbooks</a>, and the questions from the GDS question register. They still need testing with real users. {badge("practice")}</p>
<nav class="persona-pick" aria-label="Choose a role"><ul>{cards}</ul></nav>
<h2 id="map">All journeys at a glance</h2>
<p>Each role moves through the same five stages. Choose a link to go to that step.</p>
<div class="tbl-scroll" tabindex="0" role="region" aria-label="Journey map for every role, scrollable table"><table class="tbl journey-map"><caption class="vh">Journey map: roles by stage</caption><thead><tr><th scope="col">Role</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>
{sections}
""", "Roles in the DAM Policy, their user stories and their journeys through the app and the capability playbooks.")

def capabilities():
    out = ""
    for gi, g in enumerate(C.CAP_GROUPS):
        tiles = ""
        for cid, grp, name, link in C.CAPS:
            if grp != gi: continue
            who = [x["name"] for x in C.PERSONAS if cid in x["caps"]]
            tiles += (f'<li class="cap" data-link="{link}" data-who="{" ".join(x["id"] for x in C.PERSONAS if cid in x["caps"])}"><span class="cap-id">{cid}</span>'
                      f'<h3><a href="{E(C.cap_url(cid))}">{E(name)}</a></h3><p class="small"><span class="lk lk-{link.lower()}" title="{E(C.CAP_LINK[link])}">{link}</span> '
                      + (f'· for {E(", ".join(who))}' if who else "") + f'</p><p class="small"><a href="{E(C.cap_model_url(cid))}">In the capability model</a></p></li>')
        out += f'<h2 id="g{gi}" data-count="{sum(1 for c in C.CAPS if c[1] == gi)}">{E(g)}</h2><ul class="caps">{tiles}</ul>'
    roles = '<label class="chip"><input type="radio" name="who" value="" checked> Everyone</label>' + "".join(f'<label class="chip"><input type="radio" name="who" value="{x["id"]}"> {E(x["name"])}</label>' for x in C.PERSONAS)
    links = '<label class="chip"><input type="radio" name="link" value="" checked> All</label>' + "".join(f'<label class="chip"><input type="radio" name="link" value="{k}"> {k}</label>' for k in C.CAP_LINK)
    expl = "".join(f'<dt><span class="lk lk-{k.lower()}">{k}</span></dt><dd>{E(v)}</dd>' for k, v in C.CAP_LINK.items())
    return page("capabilities.html", "Capabilities", f"""
<h1>The capabilities behind the policy</h1>
<p class="lead">The policy names a few things you must do. Doing them well rests on 32 capabilities, from leadership and strategy to tooling, risk and handover. Find the ones that matter to you, and go straight to the playbook for each.</p>
<p class="small">The capability model and playbooks are the <a href="{C.PLAYBOOKS}">DAM capability playbooks</a>, a prototype. They are not government guidance. Where they repeat GOV.UK, GOV.UK is the authority. {badge("practice")}</p>
<dl class="lk-legend">{expl}</dl>
<h2 id="find">Find capabilities</h2>
<div class="filters"><fieldset class="chips"><legend>For my role</legend>{roles}</fieldset><fieldset class="chips"><legend>How the policy relates to it</legend>{links}</fieldset><p id="cap-count" class="small" aria-live="polite">32 capabilities</p></div>
<h2 id="start">Where to start</h2>
<p>Start with the core capabilities the policy names. They are the ones your first return depends on.</p>
{pathway(True)}
{out}
""", "The 32 capabilities behind the DAM Policy, filtered by role, each linked to its playbook.")

def ask():
    starters = ["Do arm's length bodies send their own return?", "What goes in the legal gateway field?", "Do we report APIs or data sets?", "What counts as an equivalent quality plan?", "When is the next return due?", "Do data owners replace information asset owners?"]
    chips = "".join(f'<li><a href="ask.html?q={E(x)}">{E(x)}</a></li>' for x in starters)
    return page("ask.html", "Ask", f"""
<h1>Ask a question</h1>
<p class="lead">Type a question in your own words. The explorer finds the best answers from everything it holds: questions and answers, the glossary, roles and capabilities.</p>
<form class="askform" action="ask.html" method="get" role="search">
  <label for="ask-q"><b>Your question</b></label>
  <div class="ask-row"><input id="ask-q" name="q" type="search" autocomplete="off" aria-describedby="ask-hint"><button type="submit" class="btn">{ic("i-help")} Find answers</button></div>
  <span id="ask-hint" class="hint">For example: "Do arm's length bodies send their own return?" Nothing you type leaves your device.</span>
</form>
<section aria-labelledby="ask-res-h"><h2 id="ask-res-h">Answers</h2><div data-ask aria-live="polite"><noscript><p>Searching needs JavaScript. Browse all <a href="questions.html">questions and answers</a> instead.</p></noscript><p>Ask a question, or try one of these:</p><ul class="starters">{chips}</ul></div></section>
<h2 id="copilot">Ask the DAM Policy assistant in Copilot</h2>
<p>If your organisation uses Microsoft 365 Copilot, the <b>DAM Policy assistant</b> answers in conversation, in Teams and in Copilot Chat. It uses only GOV.UK, this explorer (which includes every answer in the GDS FAQs) and the capability playbooks, and it shows its sources. It is an AI tool: check important answers against the source it gives. {badge("practice")}</p>
<p class="small">How the search on this page works: it matches the words in your question, and common alternatives such as ALB for arm's length body, against the explorer's content and ranks the closest matches. It is not generative AI and does not make up answers.</p>
""", "Ask a question about the Data Asset Management Policy and get answers with their sources.", contents=False)

def track():
    stages = [("preparing", "Preparing", "You are building your list and checking it."), ("sent", "Sent", "Your chief data officer signed it off and your coordinator emailed it to GDS."),
              ("received", "Received", "GDS has acknowledged it and given you a reference."), ("checked", "Checked", "GDS has checked the workbook and each asset."),
              ("questions", "Questions", "GDS has asked you about anything unclear, once."), ("accepted", "Accepted", "Your return is accepted, with any policy gaps recorded."),
              ("register", "In the register", "Your assets are in the cross-government register and the analytics.")]
    st = "".join(f'<li data-stage="{k}"><label class="st-opt"><input type="radio" name="stage" value="{k}"> <span class="st-n">{i + 1}</span> <b>{E(n)}</b><span class="small">{E(d)}</span></label></li>' for i, (k, n, d) in enumerate(stages))
    measures = [("Returns received", "Returns received against the organisations expected to send one.", "Department and arm's length body"),
                ("Critical data assets reported", "Number of assets in returns.", "Sector, critical purpose"),
                ("Owner and steward assigned", "Share of assets with a data owner and a data steward assigned.", "Organisation group"),
                ("In a data catalogue", "Share of assets recorded in a catalogue, planned or not yet.", "Organisation group"),
                ("Quality plan in place", "Share of assets with a data quality action plan or documented equivalent, in development or not yet.", "Organisation group"),
                ("Discoverability of standards", "In place, partial or not in place.", "Organisation group"),
                ("Policy gaps", "The most common gaps, to target support.", "Theme")]
    mrows = "".join(f'<tr><th scope="row">{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td><td><span class="pill later">After the Baseline Return</span></td></tr>' for a, b, c in measures)
    return page("track.html", "Track and analyse", f"""
<h1>Track your return, and see what it shows</h1>
<p class="lead">For coordinators and chief data officers: where your return has got to, what you sent, and what the policy's measures will show across government.</p>
<div class="facts"><p>{ic("i-lock")} <b>Your information stays with you.</b> Everything on this page is saved or read in your own browser. Nothing is uploaded or sent to anyone.</p></div>

<h2 id="where">Where your return has got to</h2>
<p>Record each stage as it happens, so you and your chief data officer can see it at a glance. GDS tells you each step by email to your coordinator.</p>
<form class="tracker" action="#where" novalidate>
  <div class="tr-fields">
    <div class="field"><label for="tr-ref"><b>Your return reference</b> (optional)</label><span class="hint" id="tr-ref-h">GDS gives you this when it receives your return.</span><input id="tr-ref" type="text" maxlength="40" autocomplete="off" aria-describedby="tr-ref-h"></div>
    <div class="field"><label for="tr-date"><b>Date sent</b> (optional)</label><input id="tr-date" type="date"></div>
  </div>
  <fieldset><legend>Current stage</legend><ol class="stages">{st}</ol></fieldset>
  <p class="small" data-tr-saved aria-live="polite"></p>
</form>

<h2 id="sent">What you sent</h2>
<p>Open the CSV copy of the version 3 workbook you sent (in Excel, choose <b>Save as</b>, then <b>CSV</b>). The page shows what is in it and how ready each asset is, using the same checks GDS uses first.</p>
<div class="field"><label for="tr-file"><b>Your return as a CSV file</b></label><input id="tr-file" type="file" accept=".csv,text/csv"></div>
<div data-tr-analytics aria-live="polite"><noscript><p>This needs JavaScript.</p></noscript></div>

<h2 id="government">Across government</h2>
<p>When returns arrive, GDS will report these measures to the Chief Data Officer Council and to ministers. No returns have arrived yet: the Baseline Return is due in January 2027, so nothing is shown here until then. {badge("plan")}</p>
<div class="tbl-scroll" tabindex="0" role="region" aria-label="Planned measures, scrollable table"><table class="tbl"><caption class="vh">Planned cross-government measures</caption><thead><tr><th scope="col">Measure</th><th scope="col">What it shows</th><th scope="col">Broken down by</th><th scope="col">Available</th></tr></thead><tbody>{mrows}</tbody></table></div>
<p class="small">To protect organisations, no group of fewer than five organisations will be shown on its own.</p>

<h2 id="next">Coming next: your organisation's live view in Teams</h2>
<p>The next release will show each organisation its own return, status and measures, live, inside this app in Microsoft Teams. Return data will be kept in SharePoint, and Power BI will show each organisation only its own data, after you sign in with your work account. {badge("practice")}</p>
""", "Track your DAM Policy return, see what you sent, and the measures GDS will report.", scripts=("checker.js", "explorer.js"))

def guide():
    site = HOME_URL.rstrip("/") + "/" if HOME_URL.startswith("https://") and "claude.ai" not in HOME_URL else "https://cyberdudeuk.github.io/dam-policy-explorer/"
    pkg = "" if PREVIEW else '<p><a class="btn" href="downloads/dam-policy-explorer-teams.zip" download>' + ic("i-download") + ' Download the Microsoft 365 app package (.zip)</a></p>'
    steps = [("Read the policy in plain English", "policy.html", "Five minutes on what the policy asks and who does what."),
             ("Test your possible assets", "asset-test.html", "Five questions per asset. Anything you are not sure about is included and flagged."),
             ("Work through your return", "return.html", "Twelve steps. Mark each one done; your progress is kept on your device."),
             ("Check your list before you send it", "return.html#check", "Open the CSV of your workbook. It is read in your browser and never uploaded."),
             ("Track it, and see what it shows", "track.html", "Record each stage, and see how ready each asset is.")]
    qs = "".join(f'<li><a href="{h}"><b>{E(t)}</b></a><span>{E(d)}</span></li>' for t, h, d in steps)
    return page("guide.html", "User guide and set-up", f"""
<h1>User guide, and how to get the explorer in your organisation</h1>
<p class="lead">How to use the explorer, and every way to open it: in a browser on any device, installed like an app, in Microsoft Teams, Outlook and the Microsoft 365 app, in Copilot, or on your intranet.</p>

<h2 id="quick">Quick start for coordinators</h2>
<ol class="quick">{qs}</ol>
<p>Stuck? Type your question in <b>Ask a question</b> at the top of any page, or browse <a href="questions.html">questions and answers</a>.</p>

<h2 id="tutorials" data-count="5">Tours and tutorials</h2>
<p>Each tutorial opens the right page and walks you through it, one step at a time. You can stop at any point with <b>Close the tour</b> or the Escape key. Pages with a tour also have a <b>Take a short tour of this page</b> link under their title.</p>
<ul class="tutorials">
<li>{ic("i-home")}<div><h3>Find your way around</h3><p>The search box, menu, display settings, your path and your progress. One minute.</p><p><button type="button" class="btn secondary" data-tutorial="home" data-page="index.html">Start this tutorial</button></p></div></li>
<li>{ic("i-target")}<div><h3>Test whether an asset is in scope</h3><p>The five questions, what happens when you are not sure, and how to export your list of assets left out.</p><p><button type="button" class="btn secondary" data-tutorial="asset" data-page="asset-test.html">Start this tutorial</button></p></div></li>
<li>{ic("i-check")}<div><h3>Check your list before you send it</h3><p>Open your workbook as a CSV, read the result, and track the twelve steps.</p><p><button type="button" class="btn secondary" data-tutorial="check" data-page="return.html">Start this tutorial</button></p></div></li>
<li>{ic("i-dashboard")}<div><h3>Track your return and see what it shows</h3><p>Record the stage, open what you sent, and see the measures GDS will report.</p><p><button type="button" class="btn secondary" data-tutorial="track" data-page="track.html">Start this tutorial</button></p></div></li>
<li>{ic("i-help")}<div><h3>Find an answer and share it</h3><p>Search, filter by topic, read the labels, and copy a link to an answer for Teams or email.</p><p><button type="button" class="btn secondary" data-tutorial="answers" data-page="questions.html">Start this tutorial</button></p></div></li>
</ul>
<noscript><p>Tours need JavaScript. The quick start above works without it.</p></noscript>

<h2 id="tips">Finding your way around</h2>
<ul>
<li><b>The menu</b> at the top takes you between sections. On a narrow screen it folds behind the <b>Menu</b> button.</li>
<li><b>Page contents</b>, on the left, lists the sections of the page you are on. Hide or show it with its switch.</li>
<li><b>What to do next</b>, at the end of each page, suggests the next step and related pages.</li>
<li><b>Tooltips</b>: point at, or tab to, menu items, buttons, labels and words with a dotted underline to see what they mean or do. Press Escape to hide one. Every word is also in the <a href="glossary.html">glossary</a>.</li>
<li><b>Labels on answers</b> tell you how far to rely on them: Policy, GDS position, Suggested practice, Programme plan or Open.</li>
<li><b>Display</b>, at the top, changes colours (including high contrast), text size, spacing, animation and link underlining.</li>
</ul>

<h2 id="browser">On any device, in a web browser</h2>
<p>Open <b>{E(site)}</b> in Edge, Chrome, Safari or Firefox, on a computer, tablet or phone. You do not need an account or to sign in. Bookmark it, or install it:</p>
<div class="tbl-scroll" tabindex="0" role="region" aria-label="How to install, scrollable table"><table class="tbl"><caption class="vh">How to install the explorer like an app</caption><thead><tr><th scope="col">Device</th><th scope="col">How to install it</th></tr></thead><tbody>
<tr><th scope="row">Windows or Mac, Edge</th><td>Open the page, then <b>Settings and more</b> (…) › <b>Apps</b> › <b>Install this site as an app</b>.</td></tr>
<tr><th scope="row">Windows, Mac or Chromebook, Chrome</th><td>Open the page, then the install icon in the address bar, or <b>Menu</b> › <b>Cast, save and share</b> › <b>Install page as app</b>.</td></tr>
<tr><th scope="row">iPhone or iPad</th><td>Open the page in Safari, then <b>Share</b> › <b>Add to Home Screen</b>.</td></tr>
<tr><th scope="row">Android</th><td>Open the page in Chrome, then <b>Menu</b> › <b>Add to home screen</b> or <b>Install app</b>.</td></tr>
</tbody></table></div>
<p>Once installed, the pages you have opened also work without a connection.</p>

<h2 id="teams">In Microsoft Teams</h2>
<h3>As a tab in a channel, today, with no administrator</h3>
<ol><li>In the channel, select <b>+</b> (Add a tab).</li><li>Choose <b>Website</b>.</li><li>Name it "DAM Policy Explorer" and paste <b>{E(site)}</b>.</li><li>Select <b>Save</b>. Everyone in the channel can now open it.</li></ol>
<h3>As an app in the Teams sidebar, in Outlook and in the Microsoft 365 app</h3>
<p>The app adds Home, Your return, Track and Ask tabs, follows your Teams theme (including high contrast) and works on Teams desktop, web and mobile. Your Teams administrator adds it once for your organisation (see <a href="#admins">for IT administrators</a>). Then:</p>
<ol><li>In Teams, select <b>Apps</b>, then <b>Built for your org</b>.</li><li>Choose <b>DAM Policy Explorer</b>, then <b>Add</b>.</li><li>Right-click its icon in the sidebar and choose <b>Pin</b>. It also appears in Outlook and the Microsoft 365 app under <b>Apps</b>.</li></ol>

<h2 id="copilot">In Microsoft 365 Copilot</h2>
<p>Where your organisation has Microsoft 365 Copilot and allows agents, the <b>DAM Policy assistant</b> comes with the app. Open Copilot Chat in Teams or at m365.cloud.microsoft, choose the assistant from the list of agents, and ask your question. It answers only from GOV.UK, this explorer and the capability playbooks, and shows where each answer comes from. It is an AI tool: check important answers against the source it gives.</p>

<h2 id="intranet">On your intranet or SharePoint</h2>
<ul>
<li><b>Link to it</b> from a news post, a Quick links web part or your data pages: <b>{E(site)}</b>.</li>
<li><b>Embed a page</b> using SharePoint's <b>Embed</b> web part. A SharePoint administrator may first need to allow <b>cyberdudeuk.github.io</b> under the site's <b>HTML Field Security</b> settings.</li>
<li><b>Link to one answer</b>: open it on the questions page and choose <b>Copy a link to this answer</b>.</li>
</ul>

<h2 id="admins">For IT administrators: add it for your organisation</h2>
<h3>Microsoft Teams, Outlook and the Microsoft 365 app</h3>
{pkg}
<ol>
<li>Download the app package from this page.</li>
<li>In the <b>Teams admin centre</b>, go to <b>Teams apps</b> › <b>Manage apps</b> › <b>Actions</b> › <b>Upload new app</b>, and upload the package.</li>
<li>Check it is allowed in your app permission policies. To pin it for a group of people, add it to a <b>setup policy</b>.</li>
<li>For the Copilot assistant, allow the app under <b>Integrated apps</b> in the Microsoft 365 admin centre. People need Microsoft 365 Copilot licences to use it.</li>
</ol>
<h3>What the app does and does not do</h3>
<ul>
<li>It is a set of web pages at <b>cyberdudeuk.github.io</b>. Allow that address through your web filter.</li>
<li>No sign-in, no cookies, no tracking and no server storing anything about users. Settings, progress and tested assets stay in each person's browser.</li>
<li>Files people check, such as a return workbook, are read in their browser and never uploaded.</li>
<li>The pages use a strict content security policy: no inline scripts, and nothing loaded from other sites.</li>
<li>The app asks Teams for no permissions to read user data. It only follows the Teams theme.</li>
<li>Every release passes automated accessibility, security and content checks before it is published.</li>
</ul>
<p>The source code, checks and change history are public. <a href="about.html#transparency">How it was made</a>.</p>

<h2 id="help">Getting help</h2>
<p>Use the <a href="{E(C.CONTACT)}">contact form</a> for questions, problems or suggestions. For questions about your own return, speak to your organisation's lead DAM Policy coordinator.</p>
""", "How to use the DAM Policy Explorer, and how to get it on your device, in Microsoft Teams, Outlook, Copilot or your intranet.")

def glossary():
    items = "".join(f'<div class="term-row" id="t-{k}"><dt>{E(t)}</dt><dd>{E(d)}</dd></div>' for k, t, d in sorted(C.GLOSSARY, key=lambda x: x[1].lower()))
    letters = sorted({t[0].upper() for _, t, _ in C.GLOSSARY})
    return page("glossary.html", "Glossary", f'''
<h1>Glossary</h1>
<p class="lead">What the words used in the policy and in this app mean. Words with a dotted underline elsewhere in the app link here, and show their meaning when you point at them or tab to them.</p>
<h2 id="terms" data-count="{len(C.GLOSSARY)}">Terms</h2>
<p class="small">Jump to: {" ".join(f"<span>{l}</span>" for l in letters)}</p>
<dl class="glossary">{items}</dl>
''', "What the words used in the Data Asset Management Policy mean.", contents=False)

def about():
    road = "".join(f'<li><span class="pill {w.lower()}">{w}</span> {E(t)}</li>' for w, t in C.ROADMAP)
    srcs = "".join(f'<li><a href="{E(u)}">{E(t)}</a></li>' for t, u in C.GOVUK.values())
    return page("about.html", "About this app", f'''
<h1>About the DAM Policy Explorer</h1>
<p class="lead">A one-stop shop for the Data Asset Management Policy, made for DAM Policy coordinators and usable by anyone.</p>

<h2 id="why">Why we made it</h2>
<p>Coordinators told us the policy material was spread across GOV.UK, the Knowledge Hub, slide decks, recordings and email, and that some of it was hard to find or read. They asked for simpler, clearer answers in one place. This app brings it together and says where every answer comes from.</p>

<h2 id="how">How we work</h2>
<p>We follow the <a href="{E(C.GOVUK["standard"][1])}">Service Standard</a>, the <a href="https://gds-way.digital.cabinet-office.gov.uk/">GDS Way</a> and the <a href="https://www.gov.uk/guidance/content-design/writing-for-gov-uk">GOV.UK guidance on writing</a>. That means we start from users' needs, write in plain English, make every page work without JavaScript, test with assistive technology and publish what we change.</p>

<h2 id="channels">Where you can use it</h2>
<ul class="tiles channels">
<li>{ic("i-dashboard")}<div><h3>Any web browser</h3><p>Current versions of Edge, Chrome, Safari and Firefox, on computers, tablets and phones. Pages work without JavaScript.</p></div></li>
<li>{ic("i-people")}<div><h3>Microsoft Teams</h3><p>As a personal app in the Teams sidebar, on desktop, web and mobile. Its colours follow your Teams theme, including high contrast. You can also pin it in a channel as a website tab.</p></div></li>
<li>{ic("i-mail")}<div><h3>Outlook and the Microsoft 365 app</h3><p>The same app opens in Outlook and the Microsoft 365 app, once your administrator has made it available.</p></div></li>
<li>{ic("i-download")}<div><h3>Installed, and offline</h3><p>Install it from your browser's menu, like an app. After your first visit, the pages you have opened work without a connection.</p></div></li>
<li>{ic("i-folder")}<div><h3>SharePoint and intranets</h3><p>Link to it, or embed a page using SharePoint's embed web part, where your organisation allows it.</p></div></li>
<li>{ic("i-doc")}<div><h3>Print and PDF</h3><p>Every page prints cleanly, with hidden sections opened and link addresses shown.</p></div></li>
</ul>

<h2 id="patterns" data-count="{len(C.PATTERNS)}">What we learned from similar services</h2>
<p>We looked at how other governments and regulators help people put a data policy into practice, and used what works.</p>
<ul class="patterns">{"".join(f'<li><a href="{E(u)}">{E(t)}</a><span>{E(d)}</span></li>' for t, u, d in C.PATTERNS)}</ul>

<h2 id="transparency">Transparency: how it was made</h2>
<ul>
<li><b>Sources.</b> Facts about the policy come only from GOV.UK. Answers from GDS that are not yet published are labelled with the date they were given. Suggested practice is labelled as such.</li>
<li><b>Needs.</b> The questions this app answers come from the GDS question register. Names and organisations are removed.</li>
<li><b>Contact form.</b> Messages go to a Microsoft Form that only GDS can see. Your email address is asked for only if you want a reply, and is used only to reply.</li>
<li><b>Use of AI.</b> Built with the help of an AI assistant (Claude, made by Anthropic), which also drew the icons and illustrations. A person is responsible for the content.</li>
<li><b>Checks.</b> Every build is tested for accessibility (WCAG 2.2 AA) at phone, tablet and desktop widths, in light, dark and high contrast, and for broken links and out-of-date wording.</li>
</ul>
<h3 id="sources-h">Sources</h3><ul>{srcs}</ul>

<h2 id="privacy">Privacy</h2>
<p>There are no cookies, no tracking and no analytics. Your display settings, your progress through the return and your list of tested assets are saved only in your own browser, on this device. Files you check are read by your browser and are never uploaded. To remove everything, choose <b>Reset to standard</b> in Display settings and clear the list on the asset test page.</p>

<h2 id="selfcheck">Self-check</h2>
<p>Each time it opens, the app checks itself and reports here.</p>
<div data-selfcheck><p>The self-check needs JavaScript.</p></div>

<h2 id="schedule">Updates</h2>
<p>New or changed answers, including changes to the GDS FAQs, reach you, Teams and the Copilot assistant through a new release of this explorer, recorded under <a href="#changes">What changed</a>. We re-read the GOV.UK sources and the question register at least every {C.STALE_AFTER_DAYS} days. If a page has not been checked for longer than that, it shows a warning at the top. Sources were last checked on {long_date(C.CONTENT_CHECKED)}.</p>

<h2 id="roadmap">Roadmap</h2>
<ul class="roadmap">{road}</ul>

<h2 id="changes">What changed</h2>
<ul class="changes">{"".join(f'<li><span class="when">{long_date(d)}</span> <b>Version {v}.</b> {E(t)}</li>' for d, v, t in C.CHANGES)}</ul>

<h2 id="contact">Contact</h2>
<p><a href="{E(C.CONTACT)}">Use our contact form</a> to ask a question, report a problem or suggest a change. It is a Microsoft Form: you do not need to sign in, and only GDS sees what you send. Give a work email address only if you want a reply.</p>
''', "About the DAM Policy Explorer: why it exists, how it was made, privacy, roadmap and changes.")

def accessibility():
    return page("accessibility.html", "Accessibility and inclusion", f'''
<h1>Accessibility and inclusion</h1>
<p class="lead">We want everyone to be able to use this app, whatever their needs, device or way of working.</p>

<h2 id="use">Using this app</h2>
<ul>
<li>Change colours (including high contrast), text size, spacing and animation in <b>Display settings</b> at the top of every page.</li>
<li>Zoom up to 400% without anything being cut off or needing sideways scrolling.</li>
<li>Use the whole app with a keyboard, a screen reader, voice control or a switch.</li>
<li>Read every page with JavaScript turned off. Only the interactive tools need it.</li>
<li>Point at, or tab to, any word with a dotted underline to see what it means.</li>
<li>Print any page: hidden sections open when you print.</li>
</ul>

<h2 id="inclusion">Inclusion</h2>
<ul>
<li>We write in plain English, test our pages for reading age, and explain every specialist term.</li>
<li>We make no assumptions about where people work, their size of organisation or their maturity with data. Small arm's length bodies are as much our users as large departments.</li>
<li>Answers do not depend on knowing who to ask. Everything we tell one coordinator, we publish for all.</li>
<li>The app works on slow connections and older devices: there are no web fonts, no tracking and no large downloads.</li>
</ul>

<h2 id="status">How accessible it is</h2>
<p>This app aims to meet the <a href="https://www.w3.org/TR/WCAG22/">Web Content Accessibility Guidelines version 2.2</a> to level AA. Every build is checked with an automated tool (axe-core) at three screen widths and in light, dark and high contrast. Automated tools find only some problems, so we will also test with people who use assistive technology.</p>
<h3 id="known">Known issues</h3>
<ul>
<li>The contact form is a Microsoft Form. If it does not work with your assistive technology, ask your organisation's DAM Policy coordinator to pass your message on.</li>
<li>Links to GOV.UK open in a new tab, because the app may be running inside Microsoft Teams. Each such link says so.</li>
<li>We have not yet tested with users of assistive technology. This is on our <a href="about.html#roadmap">roadmap</a>.</li>
</ul>

<h2 id="feedback">Tell us about a problem</h2>
<p>If something does not work for you, <a href="{E(C.CONTACT)}">use our contact form</a>. Tell us the page and what happened.</p>
<h2 id="enforcement">Enforcement</h2>
<p>The Equality and Human Rights Commission is responsible for enforcing the Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility Regulations 2018. If you are not happy with how we respond to your complaint, contact the <a href="https://www.equalityadvisoryservice.com/">Equality Advisory and Support Service</a>.</p>
<p class="small muted">This statement was prepared on {long_date(C.BUILD_DATE)}.</p>
''', "How accessible and inclusive the DAM Policy Explorer is, and how to tell us about a problem.")

# ---------- base pages, rewrapped ----------
BANNED_FIX = [(r"(?:the )?GDS Government Data directorate - Data Quality (?:&amp;|&) Management team", "the GDS team"),
              (r"[Tt]he Data Quality (?:&amp;|&) Management team", "The GDS team"),
              (r"Data Quality (?:&amp;|&) Management team(?:\\nGDS Government Data directorate)?", "GDS team"),
              (r'\sonsubmit="return false"', ""),
              (r' You can also <a href="docs/process-map\.mmd" download>download it as a file</a>\.', ""),
              (r"https://github\.com/cyberdudeuk/dam-return-and-desk/issues/new\?template=contact\.yml", C.CONTACT.replace("&", "&amp;")),
              (r"https://github\.com/cyberdudeuk/dam-return-and-desk/blob/main/docs/sources\.md", "about.html#sources-h"),
              (r"https://github\.com/cyberdudeuk/dam-return-and-desk", "about.html")]

def rewrap(fname, title, desc, scripts):
    s = (SRC / fname).read_text()
    main = re.search(r'<main id="main" class="page">(.*?)</main>', s, re.S).group(1)
    main = re.sub(r'<nav class="crumbs".*?</nav>', "", main, flags=re.S)
    for a, b in BANNED_FIX: main = re.sub(a, b, main)
    main = re.sub(r'\sstyle="[^"]*"', "", main)
    return page(fname, title, main, desc, scripts=scripts)

def externalise(doc):
    def fix(m):
        tag = m.group(0)
        if 'target=' in tag: return tag
        return tag[:-1] + ' target="_blank" rel="noopener noreferrer">'
    doc = re.sub(r'<a [^>]*href="https?://[^"]*"[^>]*>', fix, doc)
    return re.sub(r'(<a [^>]*target="_blank"[^>]*>)(.*?)</a>', lambda m: m.group(0) if "new tab" in m.group(2) else f'{m.group(1)}{m.group(2)}<span class="vh"> (opens in a new tab)</span></a>', doc, flags=re.S)

GLOSS_ON = {"critical data asset": "critical-data-asset", "data owner": "data-owner", "data steward": "data-steward", "arm's length bodies": "arms-length-body",
            "data catalogue": "data-catalogue", "data quality action plan": "dqap", "metadata": "metadata", "legal gateway": "legal-gateway", "OFFICIAL": "official"}
def link_terms(doc, fname):
    if fname == "glossary.html": return doc
    gl = {k: d for k, _, d in C.GLOSSARY}
    head, sep, rest = doc.partition('<main id="main" class="xmain" tabindex="-1">')
    body, sep2, tail = rest.partition("</main>")
    for phrase, key in GLOSS_ON.items():
        pat = re.compile(r'(?<![\w-])(' + re.escape(phrase) + r')(?![\w-])', re.I if phrase != "OFFICIAL" else 0)
        parts = re.split(r'(<[^>]+>)', body); depth = 0; done = False; outp = []
        for p in parts:
            if p.startswith("<"):
                t = re.match(r'</?(\w+)', p)
                if t and t.group(1) in ("a", "h1", "h2", "h3", "summary", "label", "legend", "button", "th", "dt", "script", "option", "figcaption", "caption"):
                    depth += -1 if p.startswith("</") else 1
                outp.append(p); continue
            if not done and depth == 0 and pat.search(p):
                p = pat.sub(lambda m: f'<a class="term" href="glossary.html#t-{key}" data-def="{E(gl[key])}">{m.group(1)}</a>', p, count=1); done = True
            outp.append(p)
        body = "".join(outp)
    return head + sep + body + sep2 + tail

def colophon():
    import segno, barcode, io
    from barcode.writer import SVGWriter
    segno.make(HOME_URL or f"DAM Policy Explorer {C.VERSION}", error="m").save(str(OUT / "assets" / "qr.svg"), scale=4, border=2, dark="#0b0c0c", light="#ffffff")
    buf = io.BytesIO(); barcode.get("code128", f"DPE {C.VERSION}", writer=SVGWriter()).write(buf, {"module_height": 12, "font_size": 8, "text_distance": 4, "quiet_zone": 2})
    (OUT / "assets" / "barcode.svg").write_bytes(buf.getvalue())

def main():
    global SPRITE
    SPRITE = sprite()
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    shutil.copytree(SRC / "templates", OUT / "templates")
    for f in ("style.css", "checker.js", "page.js", "process.js", "process-ui.js"):
        t = (SRC / "assets" / f).read_text()
        for a, b in BANNED_FIX: t = re.sub(a, b, t)
        (OUT / "assets" / f).write_text(t)
    for f in (ROOT / "assets").iterdir(): shutil.copy(f, OUT / "assets" / f.name)
    pages = {
        "index.html": home(), "policy.html": policy(), "asset-test.html": asset_test(), "questions.html": questions(), "embed.html": embed(),
        "resources.html": resources(), "glossary.html": glossary(), "people.html": people(), "capabilities.html": capabilities(), "ask.html": ask(), "track.html": track(), "guide.html": guide(), "about.html": about(), "accessibility.html": accessibility(),
        "return.html": rewrap("return.html", "Your return", "Make your organisation's data asset return in twelve steps.", ("checker.js", "page.js", "explorer.js")),
        "team.html": rewrap("team.html", "For the GDS team", "How the GDS team processes returns and answers questions.", ("checker.js", "process.js", "process-ui.js", "page.js", "explorer.js")),
    }
    for f, doc in pages.items():
        doc = link_terms(externalise(doc), f)
        (OUT / f).write_text(doc)
    colophon()
    if HOME_URL.startswith("https://") and "claude.ai" not in HOME_URL and not PREVIEW:
        import subprocess
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "package_teams.py"), HOME_URL.rstrip("/")], check=True, capture_output=True)
        (OUT / "downloads").mkdir(exist_ok=True); shutil.copy(ROOT / "dist" / "dam-policy-explorer-teams.zip", OUT / "downloads" / "dam-policy-explorer-teams.zip")
    # Azure Static Web Apps: security headers, and only Microsoft 365 hosts may embed the app (Teams, Outlook, Microsoft 365 app, SharePoint)
    fa = "'self' https://teams.microsoft.com https://*.teams.microsoft.com https://*.cloud.microsoft https://*.office.com https://outlook.office.com https://outlook.office365.com https://*.microsoft365.com https://*.sharepoint.com"
    (OUT / "staticwebapp.config.json").write_text(json.dumps({
        "globalHeaders": {"Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors " + fa,
                          "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                          "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()", "Cross-Origin-Opener-Policy": "same-origin"},
        "mimeTypes": {".webmanifest": "application/manifest+json", ".ics": "text/calendar", ".csv": "text/csv"},
        "routes": [{"route": "/sw.js", "headers": {"Cache-Control": "no-cache"}}],
        "responseOverrides": {"404": {"rewrite": "/index.html"}}}, indent=1))
    ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DAM Policy Explorer//EN", "CALSCALE:GREGORIAN",
           "BEGIN:VEVENT", "UID:dpe-ready-2026@dam-policy-explorer", "DTSTAMP:20261118T000000Z", "DTSTART;VALUE=DATE:20261218", "DTEND;VALUE=DATE:20261219",
           "SUMMARY:DAM Policy: aim to be ready for the Baseline Return",
           "DESCRIPTION:GDS asks organisations to be ready before the Christmas break. The Baseline Return is due in January 2027 (programme plan\\; check the exact date with your lead coordinator).",
           "BEGIN:VALARM", "TRIGGER:-P14D", "ACTION:DISPLAY", "DESCRIPTION:Two weeks until the DAM Policy readiness date", "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    if not PREVIEW: (OUT / "assets" / "dam-key-dates.ics").write_text("\r\n".join(ics) + "\r\n")
    plain = lambda h: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()
    index = [{"t": q["q"], "x": plain(q["a"]), "u": "questions.html#q-" + q["id"], "k": "Answer", "p": q["prov"]} for q in C.QA]
    index += [{"t": t, "x": d, "u": "glossary.html#t-" + k, "k": "Glossary", "p": ""} for k, t, d in C.GLOSSARY]
    index += [{"t": f"{c} {n}", "x": f"{C.CAP_GROUPS[g]}. {C.CAP_LINK[l]}", "u": C.cap_url(c), "k": "Capability", "p": "practice"} for c, g, n, l in C.CAPS]
    index += [{"t": x["name"], "x": x["role"] + " " + " ".join(x["goals"]), "u": "people.html#p-" + x["id"], "k": "Role", "p": "practice"} for x in C.PERSONAS]
    index += [{"t": m, "x": f, "u": "policy.html#myths", "k": "Myth and fact", "p": pv} for m, f, pv in C.MYTHS]
    data = {"version": C.VERSION, "checked": C.CONTENT_CHECKED, "needs": C.NEEDS, "qa": [{k: v for k, v in q.items() if k != "a"} for q in C.QA], "index": index, "prov": {k: v[0] for k, v in C.PROV.items()},
            "glossary": [{"id": k, "term": t} for k, t, _ in C.GLOSSARY], "pages": list(pages)}
    (OUT / "explorer-data.json").write_text(json.dumps(data, indent=1))
    # installable app: manifest and offline cache list
    files = sorted(str(f.relative_to(OUT)) for f in OUT.rglob("*") if f.is_file() and f.name != "sw.js")
    (OUT / "manifest.webmanifest").write_text(json.dumps({"name": "DAM Policy Explorer", "short_name": "DAM Explorer", "description": "Everything for the Data Asset Management Policy, in one place.",
        "start_url": "index.html", "scope": "./", "display": "standalone", "background_color": "#ffffff", "theme_color": "#0b55a3", "lang": "en-GB",
        "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}, {"src": "assets/app-icon.svg", "sizes": "any", "type": "image/svg+xml"}]}, indent=1))
    files.append("manifest.webmanifest")
    sw = (OUT / "assets" / "sw.js").read_text().replace("__VERSION__", C.VERSION).replace("__FILES__", json.dumps(files))
    (OUT / "assets" / "sw.js").unlink(); (OUT / "sw.js").write_text(sw)
    print(f"built {len(pages)} pages into {OUT}")

if __name__ == "__main__":
    main()
