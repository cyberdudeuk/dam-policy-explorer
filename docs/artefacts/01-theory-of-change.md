---
artefact:id: P03-TOC-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P03 DAM Policy Explorer
grade: G3
profile: public sector > central > work
---

# Theory of change: DAM Policy Explorer

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Problem
DAM Policy coordinators need one place to understand what the policy asks, answer their questions and work through their return, inside the Microsoft 365 tools they already use.

## Long-term outcome
Coordinators complete accurate returns sooner, with fewer repeated questions, because answers and the return walkthrough are where they work.

## Chain

| Inputs | Activities | Outputs | Short-term outcomes | Medium-term outcomes |
|---|---|---|---|---|
| GOV.UK DAM Policy pages; the FAQ and question register; the return template; Microsoft 365 (Teams, Outlook, Copilot); Azure Static Web Apps | Build a static explorer with role home pages, searchable questions and answers, and a step-by-step return walkthrough; package it as a Microsoft 365 app with a Copilot declarative agent; prototype a Power App | Static site (src/ built to out/); Teams and Microsoft 365 app package; Copilot agent definition; Power App screens (pa/) | Fewer repeated questions; coordinators use 'Your return' to prepare returns | Returns arrive more complete; the question register feeds FAQ updates within a cycle |

## Assumptions (proposed; each one testable)

| # | Assumption | How to test it | Evidence today |
|---|---|---|---|
| A1 | Coordinators prefer to work inside Teams and Outlook | Usability sessions inside Teams | S03: people use intranets and Copilot (moderate) |
| A2 | A Copilot agent grounded on GOV.UK gives correct answers with citations | Answer-accuracy test set against GOV.UK | Not tested |
| A3 | SharePoint lists can be the single content source | Graph export spike into tools/content.py | Planned in docs/microsoft-delivery.md |

## Measures (proposed)
- Share of FAQ answers citing a GOV.UK section (checkable)
- Questions arriving that the FAQ already answers (from the question register)
- Return completeness for users of the walkthrough versus others (aggregate only)

No target is set before a baseline exists.

## What would prove this wrong
If coordinators don't open it from Teams, publish it only as a web page linked from the playbooks and drop the Microsoft 365 package.

## Status
Prototype, in development; version 1.3.0, 19 Nov 2026 (V: README). Live site: https://cyberdudeuk.github.io/dam-policy-explorer/
