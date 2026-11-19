#!/usr/bin/env python3
"""Tests for the Power Apps generator (tools/powerapp.py).

1. The generator runs clean and its output equals the committed pa/ (so the pasted app can be traced to a commit).
2. Unit tests of the helpers that every screen depends on.
3. Negative tests: each check is proven able to fail. A copy of the generator is broken in one specific way and must
   exit 1 with the expected message. A check that cannot fail is not a check.
Run: python -I tests/check_powerapp.py
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile, filecmp, importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "tools" / "powerapp.py"
fails = []


def run(gen, out):
    env = {**os.environ, "DPE_PA_OUT": str(out), "DPE_ROOT": str(ROOT)}
    return subprocess.run([sys.executable, "-I", str(gen)], capture_output=True, text=True, env=env, cwd=ROOT)


def mutated(name, old, new, expect, count=1):
    """Break the generator in one way; it must fail and say why."""
    src = GEN.read_text()
    if src.count(old) < 1:
        fails.append(f"negative {name}: the text to break was not found (test out of date)"); return
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d); tools = d / "tools"; tools.mkdir()
        for f in (ROOT / "tools").glob("*.py"): shutil.copy(f, tools / f.name)
        (tools / "powerapp.py").write_text(src.replace(old, new, count))
        shutil.copytree(ROOT / "pa", tools.parent / "pa_ref")
        out = d / "out_pa"; out.mkdir(); shutil.copy(ROOT / "pa" / "baseline.json", out / "baseline.json")
        r = run(tools / "powerapp.py", out)
        if r.returncode == 0 or expect not in r.stdout + r.stderr:
            fails.append(f"negative {name}: expected failure containing {expect!r}, got exit {r.returncode}: {(r.stdout + r.stderr)[-200:]!r}")
        else: print(f"PASS negative: {name}")


# 1. clean run, and the committed build is current
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d); shutil.copy(ROOT / "pa" / "baseline.json", out / "baseline.json")
    r = run(GEN, out)
    if r.returncode != 0: fails.append("generator failed: " + r.stdout[-400:])
    else:
        print("PASS generator: all checks")
        for f in ["formulas.fx"] + [f"screens/{p.name}" for p in sorted((ROOT / "pa" / "screens").glob("*.yaml"))]:
            if not (out / f).exists() or not filecmp.cmp(out / f, ROOT / "pa" / f, shallow=False): fails.append(f"pa/{f} is not what the generator produces: regenerate and commit")
        if not fails: print("PASS committed pa/ equals the generator's output")

# 2. unit tests
spec = importlib.util.spec_from_file_location("powerapp", GEN); sys.path.insert(0, str(ROOT / "tools")); pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)
cases = [("12", "24"), ("nfCX + 8", "nfCX + 16"), ("nfRW * 0.5", "nfRW * 0.5"), ("Parent.Width / 2 - 21", "Parent.Width / 2 - 42"), ("CountRows(t) * pt(52)", "CountRows(t) * 104"),
         ("If(n > raw(2), raw(2), raw(1)) * pt(52)", "If(n > 2, 2, 1) * 104"), ("If(nfWide, 260, nfCW)", "If(nfWide, 520, nfCW)"), ("Label1.Y + 1.5", "Label1.Y + 3"), ("If(a, pt(14), 0)", "If(a, 28, 0)"), ("Max(pt(200), x - 8)", "Max(400, x - 16)")]
for src, want in cases:
    got = re.sub(r"\braw\((\d+)\)", r"\1", pa.scale(src))
    if got != want: fails.append(f"unit scale({src!r}) = {got!r}, expected {want!r}")
from bs4 import BeautifulSoup
_c = pa.clean(BeautifulSoup("<div><p onclick='x()'>a<script>alert(1)</script><iframe src='https://example.org'></iframe></p></div>", "html.parser").div)
if re.search(r"<script|<iframe|onclick|alert\(1\)", str(_c), re.I): fails.append(f"unit clean(): active content survived: {_c!r}")
if not any("unit" in f for f in fails): print(f"PASS unit: scale() {len(cases)} cases, clean() strips script")

# 3. negative tests
mutated("banned term reaches the app (D-02)", '"Report a bug"', '"Report a bug to the Data Management Team"', "banned")
mutated("duplicate control name (D-PA2)", 'label("SuFbNote"', 'label("SuNote"', "SuNote")
mutated("length used as a factor is not doubled (D-PA10)", "* pt(52))\"", "* 52)\"", "not scaled")
mutated("position that Studio would replace on paste (D-PA14)", 'for o in own: props[size] = str(props[size]).replace(o, f"({props[pos]})")', "pass", "D-PA14")
mutated("card second line overlaps the title (D-PA12)", "CARD_SUB = 36 ", "CARD_SUB = 48 ", "D-PA12")
mutated("link that is not https", 'REPO = "https://github.com', 'REPO = "http://github.com', "http")
mutated("sideways-scrolling list (D-PA7)", '"Vertical")\n\n\nSHORT_HINT', '"Horizontal")\n\n\nSHORT_HINT', "D-PA7")
mutated("page content row that cannot grow with its text (D-PA20)", '[end] + body, "VariableHeight")', '[end] + body, "Vertical")', "D-PA20")
mutated("page text squeezed by the window height (D-PA21)", 'label("TsTested", tested, Y="TsTestedH.Y + TsTestedH.Height + 4", Visible=has_t),', 'html_view("TsTested", tested, "TsTestedH.Y + TsTestedH.Height + 4", f"{PH} - Self.Y - 8", Visible=has_t),', "D-PA21")
mutated("answer rows too short for a long answer (D-PA22)", '"TemplateSize": f"pt(38) + Min(raw(4)', '"TemplateSize": "pt(60)", "X2": f"pt(38) + Min(raw(4)', "D-PA22")
mutated("long page squeezed into the window at the design size (D-PA23)", '"Parent.TemplateHeight" if guard else "Parent.Height"', '"Parent.Height"', "D-PA23")
mutated("count does not match the source", 'f += table("nfSupTabs"', 'QA.pop(); f += table("nfSupTabs"', "")

if fails:
    print("\n".join("FAIL " + f for f in fails)); sys.exit(1)
print("ALL PASS")
