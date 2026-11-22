"""Write the bodies of the two Government Data portal pages that mirror the explorer and the capability playbooks.

The portal is a SharePoint site inside one department's tenant, so it is GDS's own front door, not the
cross-government source: the policy is on GOV.UK, and the explorer and playbooks stay public for everyone else.
These pages say so, carry the version and date they were made from, and link out for everything else.

    The build writes them to out/portal/, so they are published with the site and the portal can fetch them.
    python3 -I tools/portal_pages.py      ->  dist/portal/explorer.html and dist/portal/playbooks.html

Each file is the HTML for one SharePoint text web part (headings, paragraphs, lists and links only).
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import content as C   # noqa: E402

E = lambda s: html.escape(str(s), quote=True)
SITE = "https://cyberdudeuk.github.io/dam-policy-explorer/"
PB = "https://cyberdudeuk.github.io/dam-capability-playbooks/"
OUT = ROOT / "dist" / "portal"


def sentence(x):
    """The first whole sentence of a summary; nothing rather than a sentence cut off in the middle."""
    x = re.sub(r"(\.\.\.|…)\s*$", " <cut>", x.strip())   # summaries cut short at the source end in an ellipsis
    m = re.match(r"(.+?[^.][.!?])(\s|$)", x)
    return m.group(1) if m and "<cut>" not in m.group(1) else ""


def a(u, t): return f'<a href="{E(u)}">{E(t)}</a>'


def explorer():
    opens = [q for q in C.QA if q["prov"] == "open"]
    return f"""<h2>Everything about the DAM Policy, in one place</h2>
<p>The DAM Policy Explorer answers the questions coordinators, chief data officers, data owners and stewards ask about the Data Asset Management Policy. Every answer says where it comes from: the policy and its guidance on GOV.UK, or a position GDS has given coordinators. If anything here disagrees with GOV.UK, GOV.UK is right.</p>
<h2>Start here</h2>
<ul>
<li>{a(SITE + "policy.html#choice", "What the policy fixes, and what is up to you")}: {len(C.CHOICES)} decisions your organisation makes, each with its GOV.UK section</li>
<li>{a(SITE + "asset-test.html", "Test whether an asset is in scope")}</li>
<li>{a(SITE + "return.html", "Prepare your Baseline Return, step by step")}</li>
<li>{a(SITE + "questions.html", "Questions and answers")}: {len(C.QA)} answers, {len(opens)} still being decided</li>
<li>{a(SITE + "policy.html#authority", "Where the answers come from")}</li>
</ul>
<h2>The capability playbooks</h2>
<p>For how to build the governance, cataloguing and quality capabilities the policy depends on, see the {a("dam-capability-playbooks.aspx", "DAM capability playbooks page")}. Search in the explorer also finds them.</p>
<p><em>Made from DAM Policy Explorer version {E(C.VERSION)}. The explorer holds no personal data; what you enter in its tools stays on your device. To ask GDS a question, use the {a(C.CONTACT, "contact form")}.</em></p>
<h2>Use it here</h2>
<p>The app is below. It opens in Microsoft Power Apps with your work account. If it does not open, use the web version: {a(SITE, "open the DAM Policy Explorer")}.</p>"""


def playbooks():
    snap = json.loads((ROOT / "data" / "playbooks-snapshot.json").read_text())
    it = snap["items"]
    main = [i for i in it if "#" not in i["u"]]
    sup = [i for i in it if "sectors.html#" in i["u"]]
    mods = [i for i in it if "learning.html#" in i["u"]]
    li = lambda xs, strip="": "".join(f"<li>{a(i['u'], i['t'].replace(strip, ''))}{(': ' + E(sentence(i['x']))) if sentence(i['x']) else ''}</li>" for i in xs)
    return f"""<h2>Step-by-step guidance for governance, cataloguing and quality</h2>
<p>The DAM capability playbooks give step-by-step guidance on data governance, data cataloguing and data quality for critical data assets. They are a prototype, not government guidance: the policy and its guidance on GOV.UK are the authority.</p>
<p>This page lists what is in the playbooks and links to each part. The content itself stays in one place, the {a(PB, "public playbooks site")}, so that departments and arm's length bodies outside this site can use it too, and nothing is kept twice.</p>
<h2>The playbooks</h2>
<ul>{li(main)}</ul>
<h2>Sector supplements</h2>
<ul>{li(sup, "Sector supplement: ")}</ul>
<h2>Learning modules</h2>
<ul>{li(mods, "Learning module: ")}</ul>
<h2>Questions about the policy itself</h2>
<p>For what the policy asks and whether an asset is in scope, use the {a("DAM-Policy-Explorer.aspx", "DAM Policy Explorer")}.</p>
<p><em>Listed from playbooks version {E(snap["playbooks_version"])} ({E(snap["playbooks_as_of"])}), read on {E(snap["retrieved"])}. Source: {a(snap["source"], "the playbooks' published content")}. This page is regenerated when the playbooks publish a new version.</em></p>"""


def main(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    for name, body in (("explorer.html", explorer()), ("playbooks.html", playbooks())):
        if "@" in body.replace(C.CONTACT, ""):
            raise SystemExit(f"{name}: an address appeared in the page")   # contact by form only
        (out / name).write_text(body)
        print(f"{name}: {len(body)} characters")


if __name__ == "__main__":
    main()
