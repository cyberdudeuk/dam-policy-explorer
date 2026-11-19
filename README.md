# DAM Policy Explorer

A one-stop shop for the UK government Data Asset Management (DAM) Policy, made for DAM Policy coordinators and usable by anyone. Built to the Service Standard, the GDS Way and WCAG 2.2 AA, for delivery on Microsoft 365 (Teams, Outlook, Microsoft 365 app, Copilot) via Azure Static Web Apps.

**Open it:** [cyberdudeuk.github.io/dam-policy-explorer](https://cyberdudeuk.github.io/dam-policy-explorer/) ·
**Version:** 1.3.0 (19 November 2026) ·
**Status:** prototype, in development. This is not policy: the GOV.UK pages on the Data Asset Management Policy are the authority.

## Quick start

1. **Coordinators:** open the explorer, start at the home page for your role, then use *Your return* to work through the return step by step.
2. **Anyone with a question:** search the questions and answers, or use the [contact form](https://forms.cloud.microsoft/e/SLBvuPX7jK). You don't need a GitHub account.
3. **Developers:** build and check it locally, as below.

## Build and check

- Build: `python3 -I tools/build.py [--home-url URL]` → `out/`
- Check: `python3 -I tests/check.py --negative` (static, functional, 3 widths × 3 themes with axe-core, and negative tests)
- Package for Microsoft 365: `python3 -I tools/package_teams.py https://host`
- Content and provenance: `tools/content.py`. Defects: `docs/defect-register.md`. Delivery: `docs/microsoft-delivery.md`.

Every push and pull request runs the full build and every check, including the negative tests, before anything is published.

## Licence

Code under the [MIT licence](LICENSE). Content under the [Open Government Licence v3.0](docs/CONTENT-LICENCE.md); material from GOV.UK remains Crown copyright and the GOV.UK page is the authority.

## Contributing, help and security

- [How to contribute](CONTRIBUTING.md) · [Getting help](SUPPORT.md) · [Reporting a security problem](SECURITY.md)
- Contact is by the [contact form](https://forms.cloud.microsoft/e/SLBvuPX7jK) only. No email address is published.
