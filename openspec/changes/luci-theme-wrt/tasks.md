# Tasks

## 1. The tests (design D6, D7, D8, D9)

- [ ] 1.1 Add `tests/firmware/test_web_theme.py`: the default on a fresh install, the upgrade that brings the theme (the uci-defaults script with `themes.Wrt` removed), an administrator's choice across a configuration-preserving upgrade, the login page without external resources, the coverage against bootstrap's stylesheet with `tests/firmware/web-theme-exceptions.toml`, and the theme's files without external resources.

  Verify: `spec-coverage --change luci-theme-wrt` reports every scenario covered or verified elsewhere; before 2.1 the tests fail (no theme).

## 2. The theme (design D1 to D5, D8)

- [ ] 2.1 Add `feed/luci/luci-theme-wrt`: the package, the templates, the stylesheet from the approved mockup's tokens, the menu and login scripts, and the uci-defaults script; select it in `config/system.seed`; describe it in `docs/`.

  Verify: the R4S builds; the tests of 1.1 pass on the emulator; `just check` passes.

## 3. In a browser (design D9)

- [ ] 3.1 Look at the emulator's LuCI in a browser: the overview, an interface form, the login, LuCI's apply dialog and a dropdown, light and dark, at desktop width and at 375 pixels; fix what does not hold; record the scenarios of light and dark and of phone width in `tests/verified-elsewhere.toml`.

  Verify: each view holds the mockup's design and LuCI's function, in both modes and both widths.

## 4. Verification

- [ ] 4.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub; then start dynamic-dns.
