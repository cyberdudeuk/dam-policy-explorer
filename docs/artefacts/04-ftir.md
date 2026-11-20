---
artefact:id: P03-FTIR-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P03 DAM Policy Explorer
grade: G3
profile: public sector > central > work
---

# Functional, technical and integration requirements (FTIR): DAM Policy Explorer

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

Requirements are stated once, in [03-prd.md](03-prd.md). This document says how each is met and checked.

## Functional

| ID | Requirement | Priority | Verified by | State |
|---|---|---|---|---|
| F01 | Role-based home pages that start each user at their task | Must | tests/check.py | Has a check |
| F02 | Search the questions and answers | Must | tests/check.py | Has a check |
| F03 | 'Your return': work through the return step by step | Must | tests/check.py; tests/fixtures/invented-return.csv | Has a check |
| F04 | Every answer cites the GOV.UK source | Must | tools/content.py provenance (U: confirm a check enforces it) | Check named; coverage unconfirmed (U) |
| F05 | Package for Microsoft 365 (Teams, Outlook, M365 app) with a Copilot declarative agent | Should | tools/package_teams.py | Has a check |
| F06 | Power App version of the explorer | Could | tests/check_powerapp.py | Has a check |
| F07 | Contact by form only; no email address published | Must | tests/check.py (U: confirm email rule) | Check named; coverage unconfirmed (U) |
| F08 | Single content source in SharePoint lists, exported by Graph | Should | Not built (docs/microsoft-delivery.md: next) | Not traced |

## Technical

| ID | Requirement | State |
|---|---|---|
| T01 | Code scanning | Not present |
| T02 | Dependency review on pull requests | Not present |
| T03 | OpenSSF Scorecard | Not present |
| T04 | Automated release | Not present |
| T05 | Published by workflow (Pages) | Present (V: .github/workflows) |
| T06 | Documentation kit checked in CI | Present (V: .github/workflows) |

Workflows present (V): `build-check-deploy.yml`.

Tests present (V): `check.py`, `check_powerapp.py`.

## Integration

| ID | Integration | Direction | State |
|---|---|---|---|
| I01 | GOV.UK DAM Policy pages | Link out and cite | Live |
| I02 | Microsoft 365 / Teams / Outlook | App package | Package ready; needs hosting |
| I03 | Microsoft 365 Copilot | Declarative agent | In package |
| I04 | Azure Static Web Apps | Hosting | Needs a subscription |
| I05 | SharePoint lists (FAQ, question register, return log) | Content source via Graph | Next |
| I06 | Power Automate | Returns workflow | Existing operating model |
| I07 | DAM capability playbooks | Links to steps | Live |
