# Defect register

Every defect has a root cause and a check that would have caught it. The check suite never shrinks. Each check has a negative test that breaks a copy of the build and proves the check fails.

| ID | Found | Defect | Root cause | Check |
|---|---|---|---|---|
| D-01 | 18 Nov 2026 | Contact and source links pointed to `cyberdudeuk/dam-return-and-desk`, which does not exist (404) | Earlier build linked a repository that was never created | S1 banned terms, S8 contact (href and data-contact) |
| D-02 | 18 Nov 2026 | The retired team name appeared in pages and scripts | Text carried over from the earlier build | S1 banned terms |
| D-03 | 18 Nov 2026 | Inline `onsubmit` handler on the team page broke under the security policy | Earlier build used an inline handler | S3 security policy |
| D-04 | 18 Nov 2026 | Link to `docs/process-map.mmd`, a file not in the app | Earlier build linked a repository file | S4 links |
| D-05 | 18 Nov 2026 | Scope described as "three tests", superseded by OFFICIAL plus four principles (GDS FAQs, Nov 2026) | Content predates the FAQ | S9 wording |
| D-06 | 18 Nov 2026 | Pages scrolled sideways at 320 px | Visually hidden text is absolutely positioned and escaped unpositioned table scroll areas | B1 reflow |
| D-07 | 18 Nov 2026 | Question summaries and roadmap rows overflowed at 320 px | Flex rows did not wrap | B1 reflow |
| D-08 | 18 Nov 2026 | App name had 1.1:1 contrast at 320 px | Header collapsed (see D-10) and the name sat over the navigation | B4 axe |
| D-09 | 18 Nov 2026 | Header search failed target size (WCAG 2.5.8) | Search box overlapped by the navigation (see D-10) | B4 axe |
| D-10 | 18 Nov 2026 | Header collapsed to 21 px | Class `.bar` used for both the header row and the chart track, which has a fixed height | S10 class collision |
| D-11 | 18 Nov 2026 | Contact check passed a wrong address in `data-contact` | Check looked at `href` only | S8, widened |
| D-12 | 18 Nov 2026 | On narrow screens the page contents list came before the page's main content | Drawer opened by default at every width | F12 (negative-tested) |
| D-13 | 18 Nov 2026 | Countdown showed 31 days on 18 Nov for 18 Dec | Counted to the end of the target day, not calendar days | F13 with a fixed clock (negative-tested) |
| D-14 | 18 Nov 2026 | The accessibility statement promised a reply "within 5 working days", which was never agreed | Written without a source | S11 no unagreed promises (negative-tested) |
| D-15 | 18 Nov 2026 | Navigation wrapped onto two rows between 832 and 1100 px | Nine items with long labels; menu folded only below 832 px | Labels shortened, menu folds below 992 px; B2 nav width |
| D-16 | 18 Nov 2026 | The Copilot agent was grounded on a SharePoint copy of the FAQ that people outside DSIT cannot open | Designed before access across departments was considered | S12 agent uses open sources only (negative-tested); package build refuses SharePoint |
| D-17 | 18 Nov 2026 | 39 "Copy a link" buttons had no tooltip | Tooltips were assigned once, before the script created those buttons | F16 tooltips on every control; applyTips runs again after generated controls |
