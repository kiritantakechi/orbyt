# Tasks

## 1. The test (design D6)

- [ ] 1.1 Add the mark's scenario to `tests/firmware/test_web_theme.py`: the login page and a page after logging in hold the mark and link `/luci-static/orbyt/mark.svg` as their icon, which the router serves.

  Verify: `spec-coverage --change orbyt-theme` reports it covered; on the emulator it fails before 2.3 and passes after.

## 2. The theme (design D1 to D5)

- [ ] 2.1 Rewrite the tokens, the base and the shell of `cascade.css` (D1, D2, D5), and the header, footer and sidebar in the templates and `menu-orbyt.js`: the lockup, the indicators, the switch and logout in the header; text entries with the brand rule; the breadcrumb; the drawer below 800 pixels.

  Verify: `just check` passes; the coverage test's list of bootstrap classes holds.

- [ ] 2.2 Restyle LuCI's widgets on the new tokens (D3), keeping the functional rules.

  Verify: the theme's tests pass on the emulator.

- [ ] 2.3 Add the mark (D4): inline in the header and the login, `mark.svg` as the pages' icon.

  Verify: 1.1 passes on the emulator.

- [ ] 2.4 Bring the theme to TouhouAsia of 2026-11-19 (D1 to D3): the aside as a table of contents, the breadcrumb's links, no rule under the page's title, the components' metrics and states, forced colors; drop the rules for the classes nothing names, recording bootstrap's in the exceptions.

  Verify: `just check` passes; the coverage test holds with the new exceptions on the emulator.

- [x] 2.5 Fold the first design's lasting decisions into D7 to D10 (the package and its default, the coverage and nothing from outside, LuCI's icons, LuCI's own colors), point the theme's citations at them, and remove the archived change.

  Verify: no file names the archived change or its decisions; `just check` passes.

## 3. In a browser (design D6)

- [ ] 3.1 Look at the emulator's LuCI against the canvas: the overview, an interface form, the login, the apply dialog, a dropdown, the firewall zones and a realtime graph, light and dark, at 1024, 900 and 375 pixels; fix what does not hold; re-date the browser-verified scenarios.

  Verify: each view holds the canvas's look and LuCI's function in both modes and both widths.

## 4. Verification

- [ ] 4.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- After orbyt-brand is merged: rebase onto main, sync the delta spec, archive, merge and push Codeberg first, then GitHub; then dynamic-dns, rebased onto the renamed main.
