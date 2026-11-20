---
artefact:id: P03-LLD-001
artefact:version: 1.0.0
artefact:as-of: 2026-11-20
artefact:review-date: 2027-02-20
project: P03 DAM Policy Explorer
grade: G3
profile: public sector > central > work
---

# Low-level design (LLD): DAM Policy Explorer

> **How to read this.** Facts marked V were read from this repository on 20 November 2026. Assumptions, measures and risks are proposals written for this kit, not findings. U means unconfirmed. Where another document in this repository already covers a topic, this one links to it rather than repeating it.

## Build and check commands (V: README)
```
python3 -I tools/build.py
python3 -I tests/check.py --negative
python3 -I tools/package_teams.py https://host
```

## Scripts (V: file tree)
- `tools/build.py`
- `tools/content.py`
- `tools/examples.py`
- `tools/pa_relay.py`
- `tools/package_teams.py`
- `tools/powerapp.py`

## Tests (V: file tree)
- `tests/check.py`
- `tests/check_powerapp.py`

## Workflows (V: .github/workflows)
- `build-check-deploy.yml`

## Repository size
72 files tracked on 20 November 2026.

## Documentation kit
- `docs/artefacts/manifest.yaml` lists every core document, where it is, and its review date.
- `tools/artefact_check.py` checks the kit (rules AC-01 to AC-08, each with a negative test). Run `python3 tools/artefact_check.py --self-test` then `python3 tools/artefact_check.py .`.

## Handover
Someone new can rebuild and verify with the commands above, then read [03-prd.md](03-prd.md) and [05-sad.md](05-sad.md).
