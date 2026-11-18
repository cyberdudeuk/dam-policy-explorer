# DAM Policy Explorer

A one-stop shop for the UK government Data Asset Management (DAM) Policy, made for DAM Policy coordinators and usable by anyone. Built to the Service Standard, the GDS Way and WCAG 2.2 AA, for delivery on Microsoft 365 (Teams, Outlook, Microsoft 365 app, Copilot) via Azure Static Web Apps.

- Build: `python3 -I tools/build.py [--home-url URL]` → `out/`
- Check: `python3 -I tests/check.py --negative` (static, functional, 3 widths × 3 themes with axe-core, and negative tests)
- Package for Microsoft 365: `python3 -I tools/package_teams.py https://host`
- Content and provenance: `tools/content.py`. Defects: `docs/defect-register.md`. Delivery: `docs/microsoft-delivery.md`.
