---
artefact:id: P03-PRD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P03 DAM Policy Explorer
grade: G3
profile: public sector > central > work
---

# Product requirements (PRD): DAM Policy Explorer

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Problem and outcome
DAM Policy coordinators need one place to understand what the policy asks, answer their questions and work through their return, inside the Microsoft 365 tools they already use.

Outcome sought: Coordinators complete accurate returns sooner, with fewer repeated questions, because answers and the return walkthrough are where they work. See [01-theory-of-change.md](01-theory-of-change.md).

## Users
- DAM Policy lead coordinators in departments and ALBs
- Anyone with a question about the policy
- The central team answering questions

User evidence: [02-ur-bundle.md](02-ur-bundle.md).

## Scope
**In:**
- Role home pages
- Search across questions and answers
- 'Your return' step-by-step walkthrough
- Team page
- Accessibility statement
- Microsoft 365 app package and Copilot agent
- Power App prototype

**Out:**
- Submitting returns (the existing mailbox and Power Automate flow does that)
- Being policy: GOV.UK is the authority
- Storing personal data

## Requirements
Derived from what this repository says it does (V: README and ADRs). The last column is the check that proves each one, where one exists. U means no check was found that clearly covers it; that is a gap to close, not a pass.

| ID | Requirement | Priority | Verified by |
|---|---|---|---|
| P03-R01 | Role-based home pages that start each user at their task | Must | tests/check.py |
| P03-R02 | Search the questions and answers | Must | tests/check.py |
| P03-R03 | 'Your return': work through the return step by step | Must | tests/check.py; tests/fixtures/invented-return.csv |
| P03-R04 | Every answer cites the GOV.UK source | Must | tools/content.py provenance (U: confirm a check enforces it) |
| P03-R05 | Package for Microsoft 365 (Teams, Outlook, M365 app) with a Copilot declarative agent | Should | tools/package_teams.py |
| P03-R06 | Power App version of the explorer | Could | tests/check_powerapp.py |
| P03-R07 | Contact by form only; no email address published | Must | tests/check.py (U: confirm email rule) |
| P03-R08 | Single content source in SharePoint lists, exported by Graph | Should | Not built (docs/microsoft-delivery.md: next) |

## Non-functional requirements
- WCAG 2.2 AA at 3 widths x 3 themes with axe-core, plus negative tests (V: README)
- HTTPS headers in staticwebapp.config.json
- Content OGL v3; code MIT

## Status
Prototype, in development; version 1.3.0, 19 Nov 2026 (V: README)
