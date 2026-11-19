# DAM Policy Explorer in Power Apps

The Power Apps version carries the same content as the web explorer, version for version. It is generated, not hand-built: `tools/powerapp.py` reads the built site (`out/`), `tools/content.py` and `tools/examples.py` and writes `pa/`.

Status on 19 November 2026: version 1.3.0 **published** at 16:14 and checked in the preview. The app icon is set. Teams: see "In Microsoft Teams".

## What is in it

Fourteen screens: splash (it stays until "Open the explorer" is pressed), Home, page, reader, questions, worked examples, glossary, search, asset test, My area, Matchmaker, tutorials, support and contact, What is new.

- **Six numbered sections on Home**, in the order a coordinator meets them: understand, decide what is in scope, make your return, find an answer, get help, your area.
- **Matchmaker** builds a search of the National Data Library at data.gov.uk from a description and optional publisher, topic and format. It opens data.gov.uk in the browser; only the `q` search parameter is confirmed, so the options are added as search words.
- **Tutorials and a one-minute tour.** The lightbulb in each header opens the tutorial for that screen.
- **Support and contact.** Contact is by the published contact form only. The app copies the message and opens the form; nothing is sent from the app.
- **My area** keeps progress, saved items, tested assets and role on the device (`SaveData`). Sign-in is the organisation's own (Microsoft Entra), which Power Apps enforces, so there is no login screen and no account store.
- **Release flags.** Each item that is new or changed since the previous release carries a NEW or UPDATED tag, and What is new lists them. The comparison uses `pa/baseline.json`.
- The old tracker screens and the SharePoint list connection are removed. "Track your return" is a content page from the web explorer, not the tracker.

## Design basis

- Not on service.gov.uk, so no crown, no GOV.UK logotype and no GDS Transport. GOV.UK patterns are used where they fit (one thing per page in forms, plain labels, yellow focus).
- One layout that follows the window: one column under 640 px wide, two from 640, top navigation and three columns from 900 and 1,100. A short window (under 550 px high, such as a phone held sideways) gets its own Home and splash layout. Forms and other long pages sit in one scrolling row, so they scroll as a whole at any size.
- Phone-layout canvas apps count two units to a pixel. Every length in the generator is written in pixels and doubled on output.
- Only real buttons and inputs take focus. Each card is one button whose text is its accessible name. Colour never carries meaning alone: every tag and status has words or an icon.
- Glass panels and backdrops are inline HTML and SVG; motion stops under "reduce motion".

## Building and pasting

1. `python -I tools/build.py --home-url <site>` then `python -I tools/powerapp.py`. It exits 1 on any failed check.
2. `python tools/pa_relay.py` builds a page with one copy button per file (the files are too large to type).
3. In Studio: paste `formulas.fx` into `App.Formulas` first. Then add a blank screen, delete the old screens, paste `all-screens.yaml` from the blank screen's menu, and delete the blank screen. To replace one screen, delete it and paste its file from another screen's menu.
4. Check `App.StartScreen` is `ScrSplash`, run the App checker, preview at phone, tablet and window size, both ways up.

### Checking the paste

Studio can change what is pasted (see D-PA14). After pasting, select each screen in the tree, copy it, and paste it into the "Check" box on the relay page. It compares every property with the build. On 19 November all 14 screens matched; the only lines reported were properties Studio leaves out because they equal the default (`=0`, `=true`, `=false`).

### After each release

The baseline (`pa/baseline.json`) is what the release before this one contained; the New and Updated flags are the difference. Leave it alone while this version is live. When work on the next version starts, check the published release out in another folder and run `DPE_ROOT=<that folder> python tools/powerapp.py --write-baseline pa/baseline.json`. The generator refuses to record a release as its own baseline, which would remove every flag (D-PA27).

## Known limits (19 November 2026)

| Limit | Effect | What would fix it |
|---|---|---|
| After a sheet closes (a filter list, a Home section, the contents list), keyboard focus goes back to the start of the screen, not to the button that opened it | Power Apps cannot set focus on a control inside a list or a scrolling page, which is where those buttons are. The next Tab starts from the header. | A platform change, or moving each opening button out of the scrolling page. |
| With a keyboard, a long section scrolls only once focus is inside the page | Tab to Save (the first stop in the page), then use the arrow keys or Page Down. The in-app guide says so. Previous, Contents and Next are at the end of each section. | A focus stop per block of text. |
| No test with assistive technology has been run on the Power Apps version | Screen-reader, voice-control and magnifier behaviour rests on Microsoft's guidance for canvas apps, not on observation. | A test session with people who use them, before the app is relied on. |
| Matchmaker results open on data.gov.uk | No results inside the app. | A custom connector to the data.gov.uk API. |
| My area is per device | Progress does not follow the user to another device. | A SharePoint list or Dataverse table; an owner decision. |
| Top-level screens (Home, lists, reading screens) are held inside the window at exactly 320 x 568 points, the size of the Studio canvas | Checked by eye at that size on 19 November: nothing overlaps. Any new content that overflows there would be squeezed instead of scrolling. | Move the screen into the scrolling row (see D-PA20, D-PA23). |
| Studio preview at "Window size" crops the left edge when the browser window is narrower than the preview pane | Preview only. Not seen at tablet or phone presets. | Check in the published player. |

Forms, My area, the asset test, the Matchmaker, tutorials, Support, the page reader and the answer screen scroll as one page at every size, including a phone held sideways, and with the keyboard (D-PA20 to D-PA24). While a sheet is open nothing behind it takes keyboard focus, and focus moves into the sheet when it opens (D-PA26).

### App checker (19 November 2026, the published build)

Formulas: no errors. Runtime 0. Data source 0.

- **Accessibility 600**, of two kinds only: "missing accessible label" (217) and "missing tab stop" (the rest). Every one is on a control that is deliberately not interactive: text, backdrops, accent bars, decorative icons, list containers.
  - **Why the count cannot be zero.** A probe screen holding one brand-new label with no properties set was flagged "missing tab stop" by the checker. It flags every control whose tab index is below zero and every icon, shape or image with an empty label, whether or not it is interactive. Microsoft's own guidance says the opposite of the "fix": set the tab index to -1 for anything that is not interactive, leave the label empty for decoration, and "ignore any [suggestions] that might do more harm than good" ([accessibility checker](https://learn.microsoft.com/power-apps/maker/canvas-apps/accessibility-checker), [create accessible canvas apps](https://learn.microsoft.com/power-apps/maker/canvas-apps/accessible-apps)). Making several hundred pieces of text into tab stops would make the app worse for keyboard users.
  - The generator enforces the real rule instead: anything with an action has a name and a tab stop (D-PA3), every button has text (D-PA1), and focus is always shown.
- **Performance 3** warnings: "too many controls on a screen" for Home, My area and Support. Advisory.

### Checked by eye (19 November 2026, last build)

At 320 x 568, mouse and keyboard only: Home and a section sheet (titles fit beside the UPDATED tag, D-PA25); the page reader (sections 1 to 4 of The policy: Tab to Save, the link in the text, Contents and Next; arrow keys and Page Down read a long section to its end; Next opens the following section at its top); the contents list (focus lands on Close, Tab moves to the first section, nothing behind it takes focus); Questions and its Topic list (focus moves into the list, Tab stays in it); an answer (Tab to Save, Page Down to the sources).

One build earlier, unchanged since except for tab stops behind sheets: at 375 x 667 My area (all four tabs), Worked examples, Support (all three tabs), the asset test, tutorials, Matchmaker step 1; phone held sideways: the asset test; tablet 768 x 1024 and 1024 x 768: Home, the asset test, My area. Every pasted screen was compared with the build, property by property: only values Studio leaves at their default differ.

Not observed: any screen reader, voice control or magnifier (see Known limits).

## Tests

- `python -I tools/powerapp.py` builds and runs every build check; it exits 1 on any failure.
- `python -I tests/check_powerapp.py` runs the build in a temporary folder and compares it with the committed `pa/`, unit-tests the unit scaling and the HTML cleaner, and runs one negative test per recorded defect (it breaks the generator on purpose and expects the build to fail). Both run in CI.
- The relay page's "Check" box compares each screen copied back from Studio with the build, property by property.

## Reporting a bug or suggesting an idea

Support has a Feedback tab: a box for the description, "Report a bug", "Suggest an idea or feature" and "See what has been reported". The buttons copy the description and open the matching issue form in the repository that hosts the web explorer (`.github/ISSUE_TEMPLATE/bug.yml`, `idea.yml`), with the app version filled in. Issues are public and need a free GitHub account; people without one are pointed to Contact us. Home lists it under Get help.

## In Microsoft Teams

Power Apps' "Add to Teams" builds a Teams package for the app itself: a personal app, and a tab people can add to a chat or a channel. In this tenant people cannot upload custom apps themselves (the install dialog has no Add button), so the package goes to the Teams administrators: Teams, Apps, Manage your apps, Upload an app, **Submit an app to your org**, then the zip from Power Apps' "Download app". Once approved it appears under "Built for your organisation" for everyone, and can be added as a tab with **+** in any chat or channel.

The app must also be shared with the people who will use it (Power Apps, Share). A Teams tab does not grant access to the app.

The separate package in `dist/` (`tools/package_teams.py`) wraps the web explorer, not the Power App.

## Not done by the generator (owner steps)

- Publishing, each release: done for 1.2.0 on 19 November 2026.
- Submit the Power App's Teams package to the Teams administrators (see above); it needs a file chosen on the owner's computer.
- Sharing, co-owner, and any move to a managed environment or solution.

## What an app like this should also have

Co-owner and a support route; solution-based release (dev, test, live) instead of editing live; usage analytics; testing with people who use screen readers, voice control and magnification; a privacy note covering device storage; a Welsh version; dark and high-contrast themes and a text-size control; a rating on answers; monitoring; and a stated update cadence tied to the web explorer's releases.
