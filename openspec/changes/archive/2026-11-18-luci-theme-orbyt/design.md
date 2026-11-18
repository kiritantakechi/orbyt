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
- A theme for LuCI's Lua compatibility pages beyond what their CBI markup shares with the JavaScript views, their GIF icons (`luci-compat`'s `cbi/*.gif`) included: no view in LuCI's feed draws them but one application's apply button.
- Branding images: the brand mark is text in a tinted square, as in the mockup.

## Decisions

### D1. A LuCI package in this repository's feed

`feed/luci/luci-theme-orbyt` builds on `$(TOPDIR)/feeds/luci/luci.mk` and depends on `luci-base`. Its files: the three templates under `ucode/template/themes/orbyt/`, `htdocs/luci-static/orbyt/{cascade.css,logo.svg}`, `htdocs/luci-static/resources/menu-orbyt.js`, `htdocs/luci-static/resources/view/orbyt/sysauth.js`, and `root/etc/uci-defaults/31_luci-theme-orbyt`. `config/system.seed` selects it beside LuCI.

### D2. The page's shell

The header draws the mockup's shell: a `<aside>` sidebar with the brand (the hostname and the board's model) and an empty `<nav>` for the menu, a top bar with the page's place in the menu, LuCI's `#indicators` and the light/dark switch, and `#maincontent` with LuCI's warnings (no password set, recovery mode, no JavaScript) and `#tabmenu`. The footer closes `#maincontent`, shows LuCI's and OpenWrt's versions as links, and loads `menu-orbyt`. A `blank_page` (the login) gets the shell's neither half.

The login template keeps LuCI's form (`luci_username`, `luci_password`, the extra authentication fields) and draws it as the mockup's card; its view focuses the password and shows LuCI's spinner while it logs in.

### D3. Dark mode is LuCI's `data-darkmode`

An inline script at the top of `<head>`, before the stylesheet, sets `data-darkmode` on `:root`: `true` or `false` as the user pinned it in this browser (`localStorage`, key `luci-theme-orbyt`), else as `prefers-color-scheme` says, and follows the preference while nothing is pinned. The switch writes the key, or removes it for automatic. The stylesheet defines its tokens for light on `:root` and for dark on `:root[data-darkmode="true"]`, so that the theme and LuCI's modules turn dark together, from one attribute. A browser without storage stays automatic.

Alternatives considered:
- Separate light and dark theme entries, as bootstrap registers: the choice would be per router rather than per browser, and a second mechanism beside the switch.

### D4. The menu as a sidebar

`menu-orbyt.js` reads LuCI's menu: the first level of the mode (`admin`) becomes the sidebar's groups (Status, System, Services, Network, and those applications add), their children the groups' links, and the third level the tabs in `#tabmenu`, as bootstrap draws them. The group of the current page is open; the others open and close on click, remembered in the browser. The page's place in the top bar comes from the same path. Below 800 pixels the sidebar is a drawer behind a menu button, closed by the button, a click beside it or Escape.

### D5. One stylesheet, by LuCI's classes

`cascade.css` starts from the mockup's tokens (palette in light and dark, fonts, radii, shadow) and styles, in this order: the base elements, the shell, the menu, the top bar and indicators, then LuCI's widgets by their classes: sections and maps, values and fields, inputs, checkboxes, dropdowns (`.cbi-dropdown`), dynamic lists, tables (both `<table>` and LuCI's `.table/.tr/.td` boxes), buttons and their kinds, labels and badges (`.label`, `.ifacebadge`, `.zonebadge`), alerts, the modal and its overlay, tooltips, spinners and progress bars, the tab menus, and the status pages' boxes. A media query at 800 pixels gives the phone layout; `prefers-reduced-motion` stops the transitions.

### D6. Coverage measured against bootstrap

A test reads the class names in the selectors of bootstrap's stylesheet (from the build tree's luci feed) and of the theme's, and requires each of bootstrap's either in the theme's or in a reviewed list, `tests/firmware/web-theme-exceptions.toml`, each with its reason: bootstrap's own chrome, which the sidebar replaces (its top bar, dropdown menus, breadcrumb), and classes of markup LuCI no longer produces. A class the theme styles that bootstrap does not is the theme's own business.

### D7. Nothing external

The theme uses the system's fonts (a stack with the CJK fonts of each platform), its own SVG icons (inline in the menu, files of its own for LuCI's icons, D10) and its own logo. A test searches the theme's files for resources from another host: `src`, `href` of stylesheets and icons, and CSS `url()`; the footer's links to LuCI and OpenWrt are links, not resources. On the emulator, the login page it serves is searched the same way.

### D8. The default, once

`31_luci-theme-orbyt`, after bootstrap's in name order: when `luci.themes.Orbyt` is not set, it sets it and sets `luci.main.mediaurlbase` to `/luci-static/orbyt`. On a fresh install this replaces bootstrap's default; on the first boot of an upgrade that brings the theme, the kept configuration lacks `themes.Orbyt`, and the theme becomes the default once; later upgrades keep `themes.Orbyt` and whatever theme the administrator chose.

### D9. Tests and their evidence

- `tests/firmware/test_web_theme.py` on the emulator: a fresh install's page uses `/luci-static/orbyt/`; with `themes.Orbyt` removed and bootstrap set, the uci-defaults script makes the theme the default; with bootstrap chosen, a configuration-preserving upgrade keeps it; the login page loads nothing from another host; every icon under LuCI's `icons/` and `cbi/` on the router has its glyph in the served stylesheet, no glyph names an icon LuCI no longer ships, and every glyph is served (D10). Without the emulator: the coverage of D6 and the theme's files of D7.
- Light and dark, phone width, and how LuCI's icons and graphs look: verified in a browser against the emulator's LuCI, reached from the VM through a forwarded port, with screenshots of the overview, an interface form, the login, the port status and a realtime graph, light and dark, at desktop and at 375 pixels; recorded in `tests/verified-elsewhere.toml` with their date.

### D10. LuCI's icons in glyphs of the theme's own

LuCI's views draw luci-base's icons as `<img>` of `/luci-static/resources/icons/<name>.svg` (a device's type, with `_disabled` when it is down; ports with and without link, and with power over Ethernet; signal strength in five steps and none; loading) and the file browser's as `cbi/{file,folder,link}.svg`: 32 pictures in a glossy desktop style of their own. The theme redraws them by CSS alone: such an image's own picture moves out of its box (`object-position`), and its background, in a token's color, shows through a glyph of the theme's as a mask. The glyphs are line icons on the menu's 24-pixel grid, files under `/luci-static/orbyt/icons/`, each named after LuCI's icon; a device's `_disabled` icon shares its glyph, a port without link shows the bare Ethernet socket and one with link the plugged one, and the signal steps fill as many bars as they reach. The color tells the state: the accent for a device up, a linked port and a signal; faint for a device down, a port without link and no signal; the muted tone for the file browser's files and links. Light and dark follow from the tokens, without a file per mode. An icon under those paths the stylesheet does not name gets a generic glyph: luci-base is the only package that installs there, and the test of D9 fails on a new icon at the bump that brings it.

Alternatives considered:
- Files of the theme at LuCI's paths: they would conflict with luci-base's, and replace bootstrap's icons too.
- `content: url()` on the images: the glyph replaces the picture, but cannot take the mode's or the state's color; a file per mode and state would be needed.
- A script swapping each image's `src`: the stock pictures flash before it runs, it watches every page's changes, and LuCI's views keep references to their images.
- Making LuCI resolve its icons through the theme: a change to luci-base for one theme's look.

### D11. LuCI's own colors in the theme's palette

Three kinds of color come from LuCI's views rather than from a stylesheet, and the theme maps each to its tokens, overriding the inline style:
- The realtime graphs (load, bandwidth, connections, wireless) draw an SVG in a white box with a black border, blue, green and red lines (the load's in three reds) with legends underlined in the same colors, and labels in light gray with a shadow. The theme gives the box, grid and labels the mode's surface, line and muted colors, and the series three colors of its own, `--chart-1` to `--chart-3` (blue, orange, aqua; each mode's steps validated as a categorical set against that mode's surface), keyed by the color LuCI writes on a line and on its legend alike, so that the two always match: blue and the load's first red to the first, red and the second to the second, green and the third to the third. Red is not a series color: the theme keeps it for errors.
- Firewall zone colors (`--zone-color-rgb`, the zone's configured color, inline) fill a zone's badge and an interface box's head in full, a pastel meant for light pages. The theme tints the surface with the zone's color (45% in light, 24% in dark) and draws an edge in the full color, so a zone keeps its color in both modes; a zone's bar in the port status, an empty badge, keeps the full color.
- States set as inline colors (the port status's power over Ethernet in `#000`, `#888` and `#d9534f`; the password's strength in red, orange and green) take the ink, faint, critical, warning and accent tokens, which turn dark with the mode.

## Risks / Trade-offs

- [LuCI changes its markup or menu API upstream] → The coverage test fails at the bump that brings new classes; the menu script uses the same API as bootstrap's.
- [Applications with their own stylesheets assume bootstrap's look] → They keep working: LuCI applications style their own markup; dark mode reaches them through `data-darkmode`.
- [A stored choice in one browser surprises another] → The choice is per browser by design, as the mockup has it; automatic is the default everywhere.
- [LuCI renames an icon, changes a graph's inline colors or its markup] → A new icon fails the test of D9 at the bump and shows the generic glyph until it has its own; a graph whose colors change keeps LuCI's own colors until the stylesheet maps them, which the browser look at a bump catches.
