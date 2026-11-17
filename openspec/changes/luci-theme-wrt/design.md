# Design

## Context

- A LuCI theme is a package of LuCI's `luci.mk`: ucode templates `themes/<name>/header.ut`, `footer.ut` and `sysauth.ut`, its media under `/luci-static/<name>/` (the stylesheet `cascade.css`), and scripts under `/luci-static/resources/`. The header opens the page and the footer closes it; LuCI fills `#maincontent` with the view, `#tabmenu` with the third menu level, and `#indicators` with its own indicators, the pending uci changes among them. A theme's menu script reads LuCI's menu (`ui.menu.load()`) and draws it.
- The stock theme, bootstrap, registers `luci.themes.Bootstrap` and, on a fresh install only, sets `luci.main.mediaurlbase` (`/etc/uci-defaults/30_luci-theme-bootstrap`); uci-defaults scripts run in name order on every first boot, an upgrade's included, with the kept configuration. Its stylesheet is 2,655 lines, the reference for which classes LuCI's applications draw.
- LuCI's modules (the dashboard, the DSL graphs, the VLAN editor) style their dark mode by `:root[data-darkmode="true"]`, which bootstrap's header sets from the browser's preference.
- luci-app-honk, outside LuCI's feed, builds on `$(TOPDIR)/feeds/luci/luci.mk`; this repository's feed can do the same.
- The approved mockup (2026-11-17, its first version) fixes the palette, the layout, and LuCI's classes for each element.

## Goals / Non-Goals

**Goals:**
- The mockup's design on every LuCI page, light and dark, desktop and phone.
- A stylesheet that covers what bootstrap covers, so that any LuCI application works under it.
- Nothing loaded from outside the router.

**Non-Goals:**
- Redesigning LuCI's views: the theme styles the markup LuCI's views produce, and changes no view.
- A theme for LuCI's Lua compatibility pages beyond what their CBI markup shares with the JavaScript views.
- Branding images: the brand mark is text in a tinted square, as in the mockup.

## Decisions

### D1. A LuCI package in this repository's feed

`feed/luci/luci-theme-wrt` builds on `$(TOPDIR)/feeds/luci/luci.mk` and depends on `luci-base`. Its files: the three templates under `ucode/template/themes/wrt/`, `htdocs/luci-static/wrt/{cascade.css,logo.svg}`, `htdocs/luci-static/resources/menu-wrt.js`, `htdocs/luci-static/resources/view/wrt/sysauth.js`, and `root/etc/uci-defaults/31_luci-theme-wrt`. `config/system.seed` selects it beside LuCI.

### D2. The page's shell

The header draws the mockup's shell: a `<aside>` sidebar with the brand (the hostname and the board's model) and an empty `<nav>` for the menu, a top bar with the page's place in the menu, LuCI's `#indicators` and the light/dark switch, and `#maincontent` with LuCI's warnings (no password set, recovery mode, no JavaScript) and `#tabmenu`. The footer closes `#maincontent`, shows LuCI's and OpenWrt's versions as links, and loads `menu-wrt`. A `blank_page` (the login) gets the shell's neither half.

The login template keeps LuCI's form (`luci_username`, `luci_password`, the extra authentication fields) and draws it as the mockup's card; its view focuses the password and shows LuCI's spinner while it logs in.

### D3. Dark mode is LuCI's `data-darkmode`

An inline script at the top of `<head>`, before the stylesheet, sets `data-darkmode` on `:root`: `true` or `false` as the user pinned it in this browser (`localStorage`, key `luci-theme-wrt`), else as `prefers-color-scheme` says, and follows the preference while nothing is pinned. The switch writes the key, or removes it for automatic. The stylesheet defines its tokens for light on `:root` and for dark on `:root[data-darkmode="true"]`, so that the theme and LuCI's modules turn dark together, from one attribute. A browser without storage stays automatic.

Alternatives considered:
- Separate light and dark theme entries, as bootstrap registers: the choice would be per router rather than per browser, and a second mechanism beside the switch.

### D4. The menu as a sidebar

`menu-wrt.js` reads LuCI's menu: the first level of the mode (`admin`) becomes the sidebar's groups (Status, System, Services, Network, and those applications add), their children the groups' links, and the third level the tabs in `#tabmenu`, as bootstrap draws them. The group of the current page is open; the others open and close on click, remembered in the browser. The page's place in the top bar comes from the same path. Below 800 pixels the sidebar is a drawer behind a menu button, closed by the button, a click beside it or Escape.

### D5. One stylesheet, by LuCI's classes

`cascade.css` starts from the mockup's tokens (palette in light and dark, fonts, radii, shadow) and styles, in this order: the base elements, the shell, the menu, the top bar and indicators, then LuCI's widgets by their classes: sections and maps, values and fields, inputs, checkboxes, dropdowns (`.cbi-dropdown`), dynamic lists, tables (both `<table>` and LuCI's `.table/.tr/.td` boxes), buttons and their kinds, labels and badges (`.label`, `.ifacebadge`, `.zonebadge`), alerts, the modal and its overlay, tooltips, spinners and progress bars, the tab menus, and the status pages' boxes. A media query at 800 pixels gives the phone layout; `prefers-reduced-motion` stops the transitions.

### D6. Coverage measured against bootstrap

A test reads the class names in the selectors of bootstrap's stylesheet (from the build tree's luci feed) and of the theme's, and requires each of bootstrap's either in the theme's or in a reviewed list, `tests/firmware/web-theme-exceptions.toml`, each with its reason: bootstrap's own chrome, which the sidebar replaces (its top bar, dropdown menus, breadcrumb), and classes of markup LuCI no longer produces. A class the theme styles that bootstrap does not is the theme's own business.

### D7. Nothing external

The theme uses the system's fonts (a stack with the CJK fonts of each platform), inline SVG icons and its own logo. A test searches the theme's files for resources from another host: `src`, `href` of stylesheets and icons, and CSS `url()`; the footer's links to LuCI and OpenWrt are links, not resources. On the emulator, the login page it serves is searched the same way.

### D8. The default, once

`31_luci-theme-wrt`, after bootstrap's in name order: when `luci.themes.Wrt` is not set, it sets it and sets `luci.main.mediaurlbase` to `/luci-static/wrt`. On a fresh install this replaces bootstrap's default; on the first boot of an upgrade that brings the theme, the kept configuration lacks `themes.Wrt`, and the theme becomes the default once; later upgrades keep `themes.Wrt` and whatever theme the administrator chose.

### D9. Tests and their evidence

- `tests/firmware/test_web_theme.py` on the emulator: a fresh install's page uses `/luci-static/wrt/`; with `themes.Wrt` removed and bootstrap set, the uci-defaults script makes the theme the default; with bootstrap chosen, a configuration-preserving upgrade keeps it; the login page loads nothing from another host. Without the emulator: the coverage of D6 and the theme's files of D7.
- Light and dark, and phone width: verified in a browser against the emulator's LuCI, reached from the VM through a forwarded port, with screenshots of the overview, an interface form and the login, light and dark, at desktop and at 375 pixels; recorded in `tests/verified-elsewhere.toml` with their date.

## Risks / Trade-offs

- [LuCI changes its markup or menu API upstream] → The coverage test fails at the bump that brings new classes; the menu script uses the same API as bootstrap's.
- [Applications with their own stylesheets assume bootstrap's look] → They keep working: LuCI applications style their own markup; dark mode reaches them through `data-darkmode`.
- [A stored choice in one browser surprises another] → The choice is per browser by design, as the mockup has it; automatic is the default everywhere.
