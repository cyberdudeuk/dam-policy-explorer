# Contributing

Thank you for helping make the DAM Policy Explorer better for coordinators.

- **Questions, corrections and anything that should not be public:** use the
  [contact form](https://forms.cloud.microsoft/e/SLBvuPX7jK). You don't need a GitHub account.
- **Something does not work, or an idea:** open a [bug report](../../issues/new?template=bug.yml) or an
  [idea](../../issues/new?template=idea.yml). Issues are public: don't include personal data, department-sensitive
  detail or anything above OFFICIAL.
- **A change to the code or content:** fork the repository, change `tools/content.py` (content) or the code, run
  `python3 -I tests/check.py --negative`, and open a pull request. Every answer must cite its source; GOV.UK is the
  authority on the policy.
- **Fixing a defect:** add a check that would have caught it, with a negative test, and a line in
  `docs/defect-register.md`, in the same pull request.

By contributing you agree your contribution is published under this repository's licences: MIT for code and
OGL v3.0 for content.
