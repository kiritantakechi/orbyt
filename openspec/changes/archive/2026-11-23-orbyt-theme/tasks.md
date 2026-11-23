# Tasks

## 1. The test (design D6)

- [x] 1.1 Add the mark's scenario to `tests/firmware/test_web_theme.py`: the login page and a page after logging in hold the mark and link `/luci-static/orbyt/mark.svg` as their icon, which the router serves.

  Verify: `spec-coverage --change orbyt-theme` reports it covered; on the emulator it fails before 2.3 and passes after. Seen: `spec-coverage --change orbyt-theme` reports the scenario covered; on 2026-11-23, on the R4S image of 83fd67f, the lockup's template replaced by its source without the lines that print the mark, the login page rendered with its lockup and no mark, and the test failed; with the image's template back, it passed, as it had in the R4S's whole suite.

## 2. The theme (design D1 to D5)

- [x] 2.1 Rewrite the tokens, the base and the shell of `cascade.css` (D1, D2, D5), and the header, footer and sidebar in the templates and `menu-orbyt.js`: the lockup, the indicators, the switch and logout in the header; text entries with the brand rule; the breadcrumb; the drawer below 800 pixels.

  Verify: `just check` passes; the coverage test's list of bootstrap classes holds. Seen 2026-11-22: `just check` passes at 83fd67f; the coverage test passed in the R4S's whole suite at 83fd67f.

- [x] 2.2 Restyle LuCI's widgets on the new tokens (D3), keeping the functional rules.

  Verify: the theme's tests pass on the emulator. Seen 2026-11-22: the theme's tests passed in the R4S's whole suite at 83fd67f.

- [x] 2.3 Add the mark (D4): inline in the header and the login, `mark.svg` as the pages' icon.

  Verify: 1.1 passes on the emulator. Seen 2026-11-22: the mark's test passed in the R4S's whole suite at 83fd67f.

- [x] 2.4 Bring the theme to TouhouAsia of 2026-11-19 (D1 to D3): the aside as a table of contents, the breadcrumb's links, no rule under the page's title, the components' metrics and states, forced colors; drop the rules for the classes nothing names, recording bootstrap's in the exceptions.

  Verify: `just check` passes; the coverage test holds with the new exceptions on the emulator. Seen 2026-11-22: `just check` passes at 83fd67f; the coverage test, with the exceptions, passed in the R4S's whole suite at 83fd67f.

- [x] 2.5 Fold the first design's lasting decisions into D7 to D10 (the package and its default, the coverage and nothing from outside, LuCI's icons, LuCI's own colors), point the theme's citations at them, and remove the archived change.

  Verify: no file names the archived change or its decisions; `just check` passes.

- [x] 2.6 The theme's own debt (D1, D4): one focus ring and the secondary role defined once; the ink on a zone's color a token; TouhouAsia's spacing scale and radii as tokens and the table's tracking on every rule that sets a size; `!important` stated where it stands; the mark's one file, `mark.svg`, printed inline by one lockup template.

  Verify: with the tokens put back as values, the stylesheet is the one before; in a static preview of LuCI's markup, light and dark at 1280, 900 and 375 pixels, every element's computed style is the one before but the tracking's, and the mark's colors are the same; on the emulator, the theme's tests pass. Seen 2026-11-22: the stylesheet with its tokens put back as values is the one before; in the preview, 197 elements light and dark at 1280, 900 and 375 pixels differ only in the tracking the table gives and the error badge's radius, 9 px against the pill, which draws the same on its 18 px; the mark's stops are the same in both modes, and its file follows the browser's preference as the icon; the theme's tests passed in the R4S's whole suite at 83fd67f.

## 3. In a browser (design D6)

- [x] 3.1 Look at the emulator's LuCI against the canvas: the overview, an interface form, the login, the apply dialog, a dropdown, the firewall zones and a realtime graph, light and dark, at 1024, 900 and 375 pixels; fix what does not hold; re-date the browser-verified scenarios.

  Verify: each view holds the canvas's look and LuCI's function in both modes and both widths. Seen 2026-11-23 on the R4S image of 83fd67f: the overview, an interface form with its device dropdown, the login, the apply dialog, the firewall's zones and the load and bandwidth graphs, light and dark, at 1024, 900 and 375 pixels. Three did not hold and are fixed, each seen again with the stylesheet in place: at phone width the tabs wrapped to a second row, leaving the active tab's rule off the hairline (now one row that scrolls sideways), the login's lockup lost its name and hostname with the header's (now the header's alone), and a page first drawn wider than a phone kept LuCI's inline width on its actions cells and grew wider than the window (now the stacked cell takes the row). The browser-verified scenarios are re-dated.

## 4. Verification

- [ ] 4.1 CI's release verification: the one run on the stack's final head builds and tests both boards with this change (2026-11-19: CI runs only to verify a release; changes are verified locally until then).

  Verify: every job passes; the run is recorded in `docs/ci.md` for this change.

## Workflow follow-up

- The stack (orbyt-brand, orbyt-theme, nixpkgs-2605, python-style, then firmware-, patch-, test- and tooling-hygiene) is verified locally on its final head, then archived change by change in that order there; main fast-forwards to it and is pushed, Codeberg first, then GitHub, whose run on main is the release verification.
- Then dynamic-dns, rebased onto the renamed main.
