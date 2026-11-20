---
artefact:id: P03-SAD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P03 DAM Policy Explorer
grade: G3
profile: public sector > central > work
---

# Solution architecture (SAD): DAM Policy Explorer

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Context
DAM Policy coordinators need one place to understand what the policy asks, answer their questions and work through their return, inside the Microsoft 365 tools they already use.

The solution is described in [03-prd.md](03-prd.md). It connects with: GOV.UK DAM Policy pages; Microsoft 365 / Teams / Outlook; Microsoft 365 Copilot; Azure Static Web Apps; SharePoint lists (FAQ, question register, return log); Power Automate; DAM capability playbooks.

## Architecturally significant decisions
These are the decisions already recorded in this repository (V):

- None recorded as ADR files. Decisions so far are in the README and commit history; record the next one as `docs/adr/0001-...md`.

## Quality attributes

| Attribute | How it is met |
|---|---|
| WCAG 2.2 AA at 3 widths x 3 themes with axe-core, plus negative tests | WCAG 2.2 AA at 3 widths x 3 themes with axe-core, plus negative tests (V: README) |
| HTTPS headers in staticwebapp.config.json | HTTPS headers in staticwebapp.config.json |
| Content OGL v3 | Content OGL v3; code MIT |
| Contact | By form only; no email address anywhere (estate rule) |
| Documentation | This kit, checked in CI by `tools/artefact_check.py` |

## Constraints
- Prototype, in development; version 1.3.0, 19 Nov 2026 (V: README).
- No personal data unless a DPIA has been done first.
- Contact by form only.

## Risks (proposed ratings)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Copilot answers drift from policy | Medium | High | Ground on GOV.UK only; cite; test set |
| No hosting subscription yet | High | Medium | GitHub Pages meanwhile |
| Overlap with the DAM Policy portal dashboard and CDO Connect Hub | High | Medium | Estate decision D5; one content master per type |
