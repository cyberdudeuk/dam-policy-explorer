"""Functional checks for the data quality action plan tool (dqap.html), run by tests/check.py.

Workbooks are built here from data/dqap-template.json (the pinned shape of the GOV.UK template), so the tests need
neither the network nor a copy of GDS's file. Each check names the requirement or defect it guards.
"""
import datetime
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = json.loads((ROOT / "data" / "dqap-template.json").read_text())
DQ = "https://cyberdudeuk.github.io/dam-policy-explorer/vocab/dq#"


def serial(day):
    return (datetime.date.fromisoformat(day) - datetime.date(1899, 12, 30)).days


def workbook(path, examples=False, results=True):
    """A filled-in DQAP in the template's shape. examples=True leaves the template's example rows in."""
    import openpyxl
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for name in TPL["sheets"]: wb.create_sheet(name)
    det = wb["Details"]
    for lab, val in zip(TPL["details"], ["Vehicle keeper records", "Keeper name and address for every registered vehicle", "Data steward", "Quarterly", serial("2027-03-31"), "Licensing", ""]):
        det.append([lab, val])
    cov = wb["Cover page"]; cov.append(["Step", "Description", "Complete?"])
    for st, desc in TPL["cover"]: cov.append([st, desc, "Yes" if st == "6" else ""])
    def table(name, rows):
        t = TPL["tables"][name]; ws = wb[name]; ws.append(["Title row"]); ws.append(t["header"])
        for g in t["guide"]: ws.append([g])
        if examples and t["examples"]:
            ws.append(["Examples below"])
            for e in t["examples"]: ws.append(e.split(" | "))
        for r in rows: ws.append(r)
    table("Data Criticality Matrix", [["R1", "Postcode", "Data steward", "Yes", 4, "Licensing", "C", "Licensing", "Keeper form", "Contact keepers"]])
    table("Data Issues Log", [["I1", serial("2026-10-01"), "Missing postcodes"]])
    table("Rules", [] if examples else [[1, "Contact keepers", "Postcode", "Complete", "Completeness", "Postcode is not blank", "Percentage of records with a postcode", "Count blanks", 0.98],
                                         [2, "Contact keepers", "Postcode", "Valid", "Validity", "Postcode is a valid UK format", "Percentage of valid postcodes", "Pattern match", 0.95]])
    res = wb["Results"]; res.append(["Title row"])
    if results and not examples:
        res.append(["ID", "Rule", "Metric", "Target", serial("2026-07-01"), serial("2026-10-01")])
        res.append([1, "Postcode is not blank", "Percentage of records with a postcode", 0.98, 0.95, 0.97])
        res.append([2, "Postcode is a valid UK format", "Percentage of valid postcodes", 0.95, 0.96, 0.97])
    else:
        res.append(["ID", "Rule", "Metric", "Target"])
    table("Causes", [] if examples else [["Missing postcodes", "High", "Postcodes left blank at registration", "Optional field on the form", "The form allows a blank postcode"]])
    table("Actions", [] if examples else [["Missing postcodes", "Make postcode mandatory on the form", "Service owner", serial("2027-01-31"), serial("2027-02-28"), "In progress"]])
    wb.save(path)


def dqap_functional(browser, base):
    fails = []
    tmp = Path(tempfile.mkdtemp())
    good, bad, prot = tmp / "good.xlsx", tmp / "examples.xlsx", tmp / "protected.xlsx"
    workbook(good); workbook(bad, examples=True, results=False)
    prot.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"\0" * 512)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.goto(base + "dqap.html"); pg.wait_for_function("document.querySelector('[data-rows=items]') && fetch")
    pg.wait_for_timeout(300)
    # FD1: a complete plan on the GOV.UK template passes every check (policy section 6; DQAP guide steps 1 to 7)
    pg.set_input_files("#dq-file", str(good)); pg.wait_for_selector("#dq-result:not([hidden]) .dq-checks")
    out = pg.inner_text("[data-dq-out]")
    if "10 of 10 in place" not in out: fails.append("FD1 a complete plan is not 10 of 10: " + out[:300])
    if "the GOV.UK template" not in out: fails.append("FD1 the GOV.UK template was not recognised")
    if "Below target" not in out or "Meets target" not in out: fails.append("FD1 rules are not compared with their targets")
    # D-35: the template stores 98% as 0.98; the form asks for a percentage
    if pg.input_value("[data-rows=rules] .dq-row [data-f=target]") != "98": fails.append("FD1 an imported target is not shown as a percentage")
    # FD2: the plan is written as DQV linked to the DCAT record (DQV, DCAT 3 section 14)
    pg.fill("#dq-iri", "https://catalogue.example.gov.uk/dataset/vehicle-keepers")
    with pg.expect_download() as dl: pg.click("[data-dqv]")
    try:
        import rdflib
        g = rdflib.Graph().parse(data=Path(dl.value.path()).read_text(), format="json-ld")
        q = lambda s: list(g.query("PREFIX dqv:<http://www.w3.org/ns/dqv#> PREFIX dcat:<http://www.w3.org/ns/dcat#> PREFIX oa:<http://www.w3.org/ns/oa#> PREFIX odrl:<http://www.w3.org/ns/odrl/2/> PREFIX prov:<http://www.w3.org/ns/prov#> " + s))
        ds = "https://catalogue.example.gov.uk/dataset/vehicle-keepers"
        if len(q(f"SELECT ?m WHERE {{ <{ds}> a dcat:Dataset; dqv:hasQualityMeasurement ?m . ?m a dqv:QualityMeasurement; dqv:computedOn <{ds}>; dqv:isMeasurementOf ?x; dqv:value ?v . ?x a dqv:Metric }}")) != 4:
            fails.append("FD2 DQV: expected 4 measurements linked to the dataset and their metrics")
        dims = {str(r[0]) for r in q("SELECT ?d WHERE { ?x a dqv:Metric; dqv:inDimension ?d }")}
        if dims != {DQ + "completeness", DQ + "validity"}: fails.append(f"FD2 DQV: metric dimensions are {dims}")
        if len(q(f"SELECT ?c WHERE {{ ?p a dqv:QualityPolicy; odrl:obligation ?d . ?d odrl:target <{ds}>; odrl:constraint ?c . ?c prov:wasDerivedFrom ?m; odrl:rightOperand ?v }}")) != 2:
            fails.append("FD2 DQV: expected 2 targets as policy duties on the dataset")
        if len(q(f"SELECT ?a WHERE {{ <{ds}> dqv:hasQualityAnnotation ?a . ?a a dqv:QualityAnnotation; oa:motivatedBy dqv:qualityAssessment; oa:hasTarget <{ds}>; oa:hasBody ?b }}")) != 1:
            fails.append("FD2 DQV: expected 1 issue annotation on the dataset")
        vocab = rdflib.Graph().parse(base + "vocab/dq.ttl", format="turtle")
        for d_ in dims:
            if (rdflib.URIRef(d_), rdflib.RDF.type, rdflib.URIRef("http://www.w3.org/ns/dqv#Dimension")) not in vocab: fails.append(f"FD2 {d_} is not a dimension in vocab/dq.ttl")
    except Exception as e:  # noqa: BLE001 - any parse failure is a test failure
        fails.append(f"FD2 the DQV download is not valid JSON-LD: {e}")
    # FD3: template examples left in, and nothing measured, are reported, not passed
    pg.set_input_files("#dq-file", str(bad)); pg.wait_for_timeout(800)
    out = pg.inner_text("[data-dq-out]")
    if "example row" not in out: fails.append("FD3 example rows left in the template were not reported")
    if "Missing Step 3" not in out.replace("\n", " "): fails.append("FD3 a plan with no results was not reported as missing step 3")
    # FD4: a file protected by a sensitivity label says why it cannot be read (it does not crash or guess)
    pg.set_input_files("#dq-file", str(prot)); pg.wait_for_timeout(500)
    if "protected" not in pg.inner_text("[data-dq-out]"): fails.append("FD4 a protected file did not get the protected-file message")
    # FD5: a plan built on the page is checked the same way and kept on the device
    pg.click("[data-clear-plan]"); pg.fill("#dq-title", "Test asset"); pg.click("[data-add=rules]")
    row = pg.locator("[data-rows=rules] .dq-row").first
    row.locator("[data-f=rule]").fill("Not blank"); row.locator("[data-f=dim]").select_option("completeness"); row.locator("[data-f=metric]").fill("Share filled"); row.locator("[data-f=target]").fill("90")
    pg.click("[data-check]"); out = pg.inner_text("[data-dq-out]")
    if "Partly" not in out or "Step 2: Rules set" not in out: fails.append("FD5 a built plan was not checked")
    pg.reload(); pg.wait_for_timeout(500)
    if pg.input_value("#dq-title") != "Test asset": fails.append("FD5 the built plan was not kept on this device")
    # FD6: the equivalence self-assessment needs all seven steps (policy section 6)
    for st in range(1, 8): pg.check(f"input[name=eq{st}][value=yes]")
    pg.click("[data-equiv]")
    if "covers all seven steps" not in pg.inner_text("[data-eq-out]"): fails.append("FD6 seven yes answers did not give an equivalent")
    pg.check("input[name=eq5][value=partly]"); pg.click("[data-equiv]")
    t = pg.inner_text("[data-eq-out]")
    if "6 of 7" not in t or "Step 5" not in t: fails.append("FD6 a partly answer was not shown as a gap")
    ctx.close()
    return fails
