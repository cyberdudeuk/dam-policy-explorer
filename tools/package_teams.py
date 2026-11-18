#!/usr/bin/env python3
"""Make the Microsoft 365 app package (Teams, Outlook, Microsoft 365 app, Copilot) once the explorer is hosted.
Usage: python3 -I tools/package_teams.py https://your-host.example [https://sharepoint-url-of-the-FAQ]  ->  dist/dam-policy-explorer-teams.zip
The FAQ address is internal, so it is passed in, never stored in the repository. Without it, the agent's SharePoint knowledge is left out.
Refuses a host that is not https, or one that does not match the domain list, so a broken package cannot be made."""
import json, sys, zipfile
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent.parent; T = ROOT / "teams"
def main():
    if len(sys.argv) not in (2, 3): sys.exit("give the https address where the explorer is hosted, and optionally the FAQ's SharePoint address")
    faq = sys.argv[2] if len(sys.argv) == 3 else ""
    host = sys.argv[1].rstrip("/"); u = urlparse(host)
    if u.scheme != "https" or not u.netloc: sys.exit("the host must be an https address")
    sub = lambda t: t.replace("{{HOST}}", host).replace("{{DOMAIN}}", u.netloc)
    man = json.loads(sub((T / "manifest.template.json").read_text())); agent = json.loads(sub((T / "declarativeAgent.template.json").read_text()).replace("{{FAQ_URL}}", faq))
    if not faq: agent["capabilities"] = [c for c in agent["capabilities"] if c["name"] != "OneDriveAndSharePoint"]
    assert "{{" not in json.dumps(man) + json.dumps(agent), "unfilled placeholder"
    assert len(man["name"]["short"]) <= 30 and len(man["description"]["short"]) <= 80 and len(man["description"]["full"]) <= 4000
    assert all(t.get("contentUrl", host).startswith(host) for t in man["staticTabs"])
    assert len(agent["conversation_starters"]) <= 6 and len(agent["instructions"]) <= 8000
    out = ROOT / "dist"; out.mkdir(exist_ok=True); z = out / "dam-policy-explorer-teams.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.writestr("manifest.json", json.dumps(man, indent=1)); f.writestr("declarativeAgent.json", json.dumps(agent, indent=1))
        f.write(T / "color.png", "color.png"); f.write(T / "outline.png", "outline.png")
    print(z)
if __name__ == "__main__": main()
