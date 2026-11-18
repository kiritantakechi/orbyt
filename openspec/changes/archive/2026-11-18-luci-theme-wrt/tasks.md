# Tasks

## 1. The tests (design D6, D7, D8, D9)

- [x] 1.1 Add `tests/firmware/test_web_theme.py`: the default on a fresh install, the upgrade that brings the theme (the uci-defaults script with `themes.Wrt` removed), an administrator's choice across a configuration-preserving upgrade, the login page without external resources, the coverage against bootstrap's stylesheet with `tests/firmware/web-theme-exceptions.toml`, and the theme's files without external resources.

  Verify: `spec-coverage --change luci-theme-wrt` reports every scenario covered or verified elsewhere; before 2.1 the tests fail (no theme).
  Result (2026-11-18): every scenario covered or verified elsewhere (343 covered, 37 elsewhere, none missing). "The theme's files and pages" had two tests, which spec-coverage refuses; it became two scenarios, the theme's files (no emulator) and the login page. The tests were not run against an image without the theme: they were written with it, and a control run on the R6S's older image stopped in setup with the rest (see 2.1).

- [x] 1.2 Add to `tests/firmware/test_web_theme.py` the icons of LuCI against the theme's glyphs: every icon under `icons/` and `cbi/` on the router named in the served stylesheet, none stale, every glyph served (design D10).

  Verify: the test fails without 2.2's glyphs and passes with them.
  Result (2026-11-18): passes on both boards in CI (run 44196283518). Not run without the glyphs; its parsing, run on the Mac against luci-base's 32 icons copied from the build tree, found each named and none stale, and every glyph file present.

## 2. The theme (design D1 to D5, D8)

- [x] 2.1 Add `feed/luci/luci-theme-wrt`: the package, the templates, the stylesheet from the approved mockup's tokens, the menu and login scripts, and the uci-defaults script; select it in `config/system.seed`; describe it in `docs/`.

  Verify: the R4S builds; the tests of 1.1 pass on the emulator; `just check` passes.
  Result (2026-11-18): the R4S builds on the VM. The tests pass on both boards in CI run 44196283518, the theme's module in the system suite (the first run, 44147358978, had it in no suite and ran none of them). On the VM three runs stopped in setup, the router's first boot past the harness's 600 s for SSH, under a load of 8 to 26 from the Mac's own work; the R6S's image of 2026-11-16, without the theme, stopped the same way under the same load, which places the cause on the host. `just check` passes.

- [x] 2.2 Draw LuCI's icons in glyphs of the theme's own (`htdocs/luci-static/wrt/icons/`, the mask rules in `cascade.css`), and map LuCI's graph, zone and inline state colors to the theme's tokens (design D10, D11); give the theme its own Simplified Chinese strings where luci-base has none.

  Verify: the tests of 1.1 and 1.2 pass on the emulator; `just check` passes.
  Result (2026-11-18): as 2.1: the tests pass in CI on both boards, the VM's runs stopped by the host's load. The Simplified Chinese strings are the package `luci-i18n-wrt-zh-cn` (luci.mk names it after `wrt`), in the image; a work tree's build saw its `po/` only once the Makefile changed, OpenWrt's metadata cache keying on Makefiles.

## 3. In a browser (design D9)

- [x] 3.1 Look at the emulator's LuCI in a browser: the overview with its port status, an interface form, the login, LuCI's apply dialog and a dropdown, the firewall zones, a realtime graph, light and dark, at desktop width and at 375 pixels; fix what does not hold; record the scenarios of light and dark, of phone width, and of the icons' states and the graphs in `tests/verified-elsewhere.toml`.

  Verify: each view holds the mockup's design and LuCI's function, in both modes and both widths.
  Result (2026-11-17 and 2026-11-18): every view named holds in both modes and at 1024 and 375 pixels, after these fixes: the menu button showed at desktop width (`.icon-btn` came after it); Light and Dark were untranslated (luci-base has them only for another theme, so the theme has its own strings); a row without a title squeezed the interface dialog's DHCP server tab into the label's column; a heading after a table sat on it; the open dropdown cut its entries; a line break in a field left an empty line; a table's first row doubled the section's header line; inactive tab panes kept their cards' padding and border; selects in the firewall's zones shrank to one character; the closed drawer cast its shadow onto the page; stacked action cells aligned against their labels; the footer's separator led a line; the page's place wrapped the top bar at phone width. Recorded in `tests/verified-elsewhere.toml`: both scenarios of light and dark, phone width, a device up and one down, and a realtime graph.

## 4. Verification

- [x] 4.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.
  Result (2026-11-18): CI run 44219605027, at 83526b4 after the browser look's fixes, passed on both boards in its first attempt, the theme's tests in the system suite; check passed (run 44219609857), spec-coverage with none missing. Recorded in `docs/ci.md` with the two runs before it.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub; then start dynamic-dns.
