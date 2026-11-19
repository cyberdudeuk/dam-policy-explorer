# DAM Policy Explorer in Power Apps

The Power Apps version carries the same content as the web explorer, version for version. It is generated, not hand-built: `tools/powerapp.py` reads the built site (`out/`), `tools/content.py` and `tools/examples.py` and writes `pa/`.

Status on 19 November 2026: the app's **draft** in Power Apps Studio holds this build (checked screen by screen, see "Checking the paste"). It is **not published**. The live version is still the earlier, unfinished tracker app until the owner publishes.

## What is in it

Fourteen screens: splash, Home, page, reader, questions, worked examples, glossary, search, asset test, My area, Matchmaker, tutorials, support and contact, What is new.

- **Six numbered sections on Home**, in the order a coordinator meets them: understand, decide what is in scope, make your return, find an answer, get help, your area.
- **Matchmaker** builds a search of the National Data Library at data.gov.uk from a description and optional publisher, topic and format. It opens data.gov.uk in the browser; only the `q` search parameter is confirmed, so the options are added as search words.
- **Tutorials and a one-minute tour.** The lightbulb in each header opens the tutorial for that screen.
- **Support and contact.** Contact is by the published contact form only. The app copies the message and opens the form; nothing is sent from the app.
- **My area** keeps progress, saved items, tested assets and role on the device (`SaveData`). Sign-in is the organisation's own (Microsoft Entra), which Power Apps enforces, so there is no login screen and no account store.
- **Release flags.** Each item that is new or changed since the previous release carries a NEW or UPDATED tag, and What is new lists them. The comparison uses `pa/baseline.json`.
- The old tracker screens and the SharePoint list connection are removed. "Track your return" is a content page from the web explorer, not the tracker.

## Design basis

- Not on service.gov.uk, so no crown, no GOV.UK logotype and no GDS Transport. GOV.UK patterns are used where they fit (one thing per page in forms, plain labels, yellow focus).
- One layout that follows the window: one column under 640 px wide, two from 640, top navigation and three columns from 900 and 1,100. A short window (under 550 px high, such as a phone held sideways) gets its own Home and splash layout.
- Phone-layout canvas apps count two units to a pixel. Every length in the generator is written in pixels and doubled on output.
- Only real buttons and inputs take focus. Each card is one button whose text is its accessible name. Colour never carries meaning alone: every tag and status has words or an icon.
- Glass panels and backdrops are inline HTML and SVG; motion stops under "reduce motion".

## Building and pasting

1. `python -I tools/build.py --home-url <site>` then `python -I tools/powerapp.py`. It exits 1 on any failed check.
2. `python tools/pa_relay.py` builds a page with one copy button per file (the files are too large to type).
3. In Studio: paste `formulas.fx` into `App.Formulas` first. Then add a blank screen, delete the old screens, paste `all-screens.yaml` from the blank screen's menu, and delete the blank screen.
4. Check `App.StartScreen` is `ScrSplash`, run the App checker, preview at phone, tablet and window size, both ways up.

### Checking the paste

Studio can change what is pasted (see D-PA14). After pasting, select each screen in the tree, copy it, and paste it into the "Check" box on the relay page. It compares every property with the build. On 19 November all 14 screens matched; the only lines reported were properties Studio leaves out because they equal the default (`=0`, `=true`, `=false`).

### After each release

Run `python tools/powerapp.py --write-baseline pa/baseline.json` **after** publishing, so the next release is compared with this one.

## Known limits (19 November 2026)

| Limit | Effect | What would fix it |
|---|---|---|
| Forms do not scroll on a very short window (phone held sideways): contact form, Matchmaker, asset test, My area, tutorial steps | The bottom of the form cannot be reached. A notice says so and asks the user to turn the device upright. Lists and reading screens are unaffected. | Rebuild each form inside a vertical container with scrolling. |
| Long text sections cannot be scrolled by keyboard (HTML viewer takes no focus) | Each has "Open the full page in the web explorer". | None inside a canvas app. |
| Matchmaker results open on data.gov.uk | No results inside the app. | A custom connector to the data.gov.uk API. |
| My area is per device | Progress does not follow the user to another device. | A SharePoint list or Dataverse table; an owner decision. |
| At exactly 320 px wide, some Home tile titles clip | iPhone SE (375 px) and wider are correct. | Smaller tile text under 360 px. |
| Studio preview at "Window size" crops the left edge when the browser window is narrower than the preview pane | Preview only. Not seen at tablet or phone presets. | Check in the published player. |

### App checker (draft, 19 November 2026)

Formulas 0, runtime 0, data source 0.

- Accessibility 587: 211 "missing accessible label" and 371 "missing tab stop", all on decorative or read-only controls (backdrops, accent bars, icons, text) that are deliberately out of the tab order, as Microsoft's guidance for decorative content says. 5 "focus isn't showing" on the five short-window notices, which cannot take focus. Open item: give them a focus border at the next build so the count is clean.
- Performance 11: 10 "use AllItemsCount instead of CountRows" on the empty-list messages. Open item for the next build.

## Not done by the generator (owner steps)

- Publish the app (replaces the live tracker app for everyone it is shared with).
- Upload the app icon (`assets/icon-512.png`) in Settings.
- Sharing, co-owner, and any move to a managed environment or solution.

## What an app like this should also have

Co-owner and a support route; solution-based release (dev, test, live) instead of editing live; usage analytics; testing with people who use screen readers, voice control and magnification; a privacy note covering device storage; a Welsh version; dark and high-contrast themes and a text-size control; a rating on answers; monitoring; and a stated update cadence tied to the web explorer's releases.
