# Design

## Context

- The theme, `luci-theme-orbyt`, is one stylesheet of about 3,300 lines over LuCI's markup: tokens, the shell, the menu, then LuCI's widgets by class, the functional rules bootstrap needs (dropdowns, tooltips, the modal, tab panes, the file browser, tables stacked on phones) among them. Its tests check the stylesheet's coverage of bootstrap's classes, LuCI's icons against its glyphs, the default theme and that nothing loads from outside.
- The approved canvas holds the look: a desktop page (sidebar, overview, ports, interfaces, an edit form), a phone page (drawer, breadcrumb) and the mark. Its tokens are TouhouAsia's semantic layer (`project/tokens.css` of the design system).
- On 2026-11-19 the maintainer updated TouhouAsia (version 1795018428-c32c) and asked for the theme to follow it, and to drop what it carries without use. The update defines the interface: an aside of 256 px (`Sidebar`), a table of contents with the brand rule on its hairline, the breadcrumb, tabs, fields, choices, tags and callouts with their states (`components/bundle.css`, `docs/06-interface.md`, `docs/07-states.md`), and two tokens, the selection and the link's hover. It still defines no modal, dropdown, toast, density mode, icon set or CJK fonts; a router's admin pages need all of them but the icon set, which the theme has already (glyphs for LuCI's icons).
- The theme's first design, an archived change of 2026-11-18, holds the decisions the theme's code cites for its package, its default, its coverage test, LuCI's icons and LuCI's own colors. The maintainer had it removed on 2026-11-19 with the rest of the old name's leftovers; the decisions that hold are this design's D7 to D10, and the code cites them here.
- Of the 182 classes the stylesheet styled, 14 are named by no view, script or template of LuCI's feed or this repository's: bootstrap's legacy (`cbi-select`, `tab-pane`, `pull-left` and others) and four column widths no view uses.

## Goals / Non-Goals

**Goals:**
- The canvas's look on every LuCI page, light and dark, desktop and phone, with TouhouAsia's interface components where LuCI has their counterpart.
- TouhouAsia's hard rules kept where LuCI's markup allows: no shadows, color-only states, never a faded state, one action color, 4.5:1 text contrast, the focus ring, the brand rule only on the reader's place.
- No rule for a class nothing draws.

**Non-Goals:**
- Changing LuCI's views: as before, the theme styles the markup they produce.
- Fonts in the image (the maintainer chose system fonts first).
- TouhouAsia's own artwork, which is its brand's, not Orbyt's.

## Decisions

### D1. The tokens

The theme's variables take TouhouAsia's semantic values, light on `:root` and dark on `:root[data-darkmode="true"]` as before (LuCI's own modules read that attribute):

| Role | Light | Dark |
|---|---|---|
| ground | `#ffffff` | `#040d1a` |
| second ground, panels | `#f0fdf4` | `#0b1d33` |
| raised (fields, tiles) | `#ffffff` | `#07182b` |
| text, secondary, tertiary | `#0f172a`, `#334155`, `#64748b` | `#f1f5f9`, `#cbd5e1`, `#94a3b8` |
| accent, hover, subtle | `#047857`, `#065f46`, `#ecfdf5` | `#10b981`, `#34d399`, rgba(16,185,129,.14) |
| border, brand hairline, strong | `#e2e8f0`, `#a7f3d0`, `#64748b` | rgba(241,245,249,.12), rgba(100,255,218,.16), `#64748b` |
| rule, focus | `#059669`, `#047857` | `#10b981`, `#64ffda` |
| selection, link hover | `#a7f3d0`, `#065f46` | rgba(100,255,218,.24), `#64ffda` |
| warning, danger, info | `#b45309`, `#b91c1c`, `#1d4ed8` with their 50 tints | `#fbbf24`, `#f87171`, `#93c5fd` with tints at 14% (info's of `#60a5fa`) |

The sizes take TouhouAsia's too: its spacing scale (4 to 64 px) as `--space-*`, its radii (4 px, 8 px, the pill), its 40 and 32 px controls, and its focus ring, a 2 px gap in the ground's color and 2 px of the focus color, as one token. A component's own metrics, as its gaps of 6 and 10 px, stay with the component, as in TouhouAsia's components; each rule that sets a font size sets its tracking from TouhouAsia's table. `!important` stands only where bootstrap's own functional rules have it and against a style LuCI writes inline.

The bootstrap compatibility variables LuCI's modules read point at these; `--disabled-opacity` stays for LuCI applications' own styles, which the theme's rules never use. Motion is TouhouAsia's: color, background, border and shadow transitions only, 140 ms, ease-out, the drawer's slide 220 ms, none under reduced motion.

### D2. The layout

A 64 px header across the page: the lockup (the mark, "Orbyt", the hostname and model below it), LuCI's indicators as tags, the light/dark switch (three text pills, the chosen one in the accent's tint) and logout. Below it the sidebar, TouhouAsia's aside of 256 px on the page's own ground with a hairline at its edge (the system has no colored sidebar), holding the menu as its table of contents: each of the menu's first level an eyebrow (monospace capitals in the accent), its pages as entries hanging from a hairline, the current one in the text color at 600 with the 3 px brand rule on the hairline; no icons, as TouhouAsia has no icon set. The content beside it, at most 1200 px: the breadcrumb (the levels above as links, ` / ` between them, the page in the text color), LuCI's tab menu, the view. The page's title has no rule under it: the brand rule marks only the reader's place, the menu's entry and the tab. Below 1024 pixels, TouhouAsia's medium width, the sidebar becomes a drawer behind a menu button in the header, closed by the button, a tap beside it or Escape, as before: beside the aside's 256 px a narrower window left the page less room than a phone has, and the interfaces table overflowed its panel at 900. Below 800 pixels the switch and logout move into the drawer's foot, and the header's lockup drops the hostname; below 480 pixels the header's lockup is the mark alone. The login's lockup keeps its name and hostname at every width: there is room on the card, and they say which router one logs into.

Dark mode is LuCI's own attribute: an inline script at the top of `<head>`, before the stylesheet, sets `data-darkmode` on `:root` from the choice pinned in this browser (`localStorage`, key `luci-theme-orbyt`), else from `prefers-color-scheme`, which it follows while nothing is pinned; the switch writes the key, or removes it for automatic. The theme and LuCI's modules turn dark together, from one attribute, and a browser without storage stays automatic. The login keeps LuCI's form (`luci_username`, `luci_password`, the authentication plugins' fields) as a card under the lockup; its view focuses the password and shows LuCI's spinner while it logs in. A `blank_page` (the login) gets neither the header nor the sidebar.

TouhouAsia's 72 px header and 40 px page titles are for documents; an admin page takes the 64 px header, 28 px page titles and 20 px section titles, and keeps its 40 px fields, with 32 px buttons inside tables.

### D3. LuCI's widgets by role

- Sections: the panel recipe, second ground, brand hairline, 8 px radius, 24 px padding; the section's title in 20/800.
- Buttons: TouhouAsia's `Button`, pills of 40 px (32 px small and inside tables), 20 px padding (16 small), label 14/600. `cbi-button-apply` and `important` are the primary (accent fill); edit, add, save, action and neutral buttons the secondary (an outline of the text at 26%, which hovers to the accent's edge and tint and keeps its ink); `cbi-button-remove`, `negative` and reset the danger ink; a link-like button the ghost. Disabled: the neutral fill and the faint ink, none for a button without a frame.
- Fields: `TextField` and `Select`: 40 px, 8 px radius, the strong border, the raised ground, the value at 15 px under a 14/500 label; hover takes the secondary ink's border, focus the accent's with the ring; an invalid one (`cbi-input-invalid`, `aria-invalid`) keeps the danger border while focused; a disabled one the neutral fill and faint ink.
- Choices: `Checkbox` (4 px radius, 1.5 px strong edge, the accent fill and its ink's check when checked) and `RadioGroup` (an accent ring and dot), 10 px from their labels; disabled on the neutral fill, a checked one in the faint ink.
- Tables: TouhouAsia's `SpecTable`: heads in the eyebrow's monospace capitals at 12 px (the system's 10 px leaves CJK heads too small), a strong line under them, hairline rows, tabular figures, the first and last columns flush with the panel; no row hover, as a row is not a control. On a phone, rows stack as LuCI expects, and the actions cell takes the row whatever width LuCI fixed on it where the page was first drawn (`stabilizeActionColumnWidth`).
- Tabs: `Tabs`: 15/500 text 24 px apart on a hairline, the selected one at 600 with the 3 px brand rule over the hairline, no fill. One row, as TouhouAsia's tab strip: tabs that outgrow it scroll sideways, so that the rule stays on the hairline, which a wrapped second row left it above; the strip's scrollbar is hidden, as it would lie on the hairline, and a tab takes the focus ring inside its edge, which the strip would clip outside.
- Alerts: `Callout`: the tone's tint and a border of its ink at 30%, never a colored edge, 16 by 20 px padding; LuCI's message carries the word.
- LuCI's icons keep their size: under `img`'s `max-width: 100%` a table sized its column as if an icon had no width, and the interface's badge overflowed its frame.
- Labels and badges: `Tag`, 22 px soft pills in the tone's tint; zones a neutral chip with a dot of the zone's color (D10). LuCI's indicators are tags too.
- Code and command output (`pre`): `CodeBlock`'s panel, monospace at 13/1.65.
- Forced colors: the brand rules, the radio's dot, the check and LuCI's icons redrawn in the system's inks; tags and callouts take an edge.
- What nothing draws goes: a rule for a class no view, script or template of LuCI's feed or this repository's names is dropped, and where bootstrap styles the class, `tests/firmware/web-theme-exceptions.toml` records why the theme does not.

### D4. The mark

The ring node on a 64 grid: a ring of radius 21 and width 6.5, a node of radius 6.4 at 1:30 cut free by a 9.6 gap, filled with the stream gradient (light `#059669`, `#10b981`, `#1e40af`; dark `#64ffda`, `#10b981`, `#0284c7`). `mark.svg` is its one file, geometry and colors: the pages' icon, and the lockup's mark, which the lockup's template (`lockup.ut`, the header's and the login's) prints inline. Its stops take `light-dark()` of the two inks, so that inline they follow the page's color scheme, pinned or automatic, and as the icon, which cannot read the page, the browser's.

### D5. Fonts

`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Inter, sans-serif`; monospace `ui-monospace, "SF Mono", Menlo, Consolas, "Monaspace Neon Var", monospace`. Weights 400, 500, 600 and 800; tracking by size, as TouhouAsia sets it.

### D6. Tests and evidence

- `test_web_theme.py` on the emulator: a fresh install's page uses `/luci-static/orbyt/`; with `themes.Orbyt` removed and bootstrap set, the uci-defaults script makes the theme the default; with bootstrap chosen, an upgrade that keeps the configuration keeps it; the login page loads nothing from another host; every icon LuCI installs has its glyph (D9); the login page and a page after login hold the mark and link `/luci-static/orbyt/mark.svg` as their icon, which is served. Without the emulator: the coverage of D8 and the theme's files loading nothing from outside.
- In a browser, against the emulator's LuCI, reached from the Mac through a port forwarded into the test's network namespace: the overview, an interface form, the login, the apply dialog, a dropdown, the firewall zones and a realtime graph, light and dark, at 1024, 900 and 375 pixels; the browser-verified scenarios re-dated in `tests/verified-elsewhere.toml`.

### D7. The package and its default

`feed/luci/luci-theme-orbyt` builds on the luci feed's `luci.mk` and depends on `luci-base`; `config/system.seed` selects it beside LuCI. Its files: the templates under `ucode/template/themes/orbyt/` (header, footer, login, mark), `htdocs/luci-static/orbyt/` (the stylesheet, `mark.svg`, the icons' glyphs), `menu-orbyt.js`, the login's view `view/orbyt/sysauth.js`, and `root/etc/uci-defaults/31_luci-theme-orbyt`. That script, after bootstrap's in name order, sets `luci.themes.Orbyt` and makes `/luci-static/orbyt` LuCI's `mediaurlbase` when `themes.Orbyt` is not set: on a fresh install, and once on the first boot of an upgrade that brings the theme; later upgrades keep whatever theme the administrator chose.

### D8. Coverage against bootstrap, and nothing from outside

A test reads the class names in the selectors of bootstrap's stylesheet and of the theme's, as the router serves them, and requires each of bootstrap's in the theme's or in `tests/firmware/web-theme-exceptions.toml` with its reason (bootstrap's own chrome, which the header and the sidebar replace, and the classes no LuCI source names, D3); an entry the theme now styles, or bootstrap no longer does, fails it too. The theme uses the system's fonts, its own mark and its own glyphs; a test searches its files for resources from another host (`src`, `href` of stylesheets and icons, CSS `url()`, imports), and on the emulator the login page it serves. The footer's links to LuCI and OpenWrt are links, not resources.

### D9. LuCI's icons in glyphs of the theme's own

LuCI's views draw luci-base's icons as `<img>` of `/luci-static/resources/icons/<name>.svg` (a device's type, `_disabled` when it is down, ports with and without link, signal strength, loading) and the file browser's `cbi/{file,folder,link}.svg`. The theme redraws them in CSS alone: the image's own picture moves out of its box (`object-position`), and its background, in a token's color, shows through a glyph of the theme's as a mask. The glyphs are line icons on a 24-pixel grid under `/luci-static/orbyt/icons/`, each named after LuCI's icon; a device's `_disabled` icon shares its glyph, and the color tells the state: the accent when up, the off ink when down. An icon named nowhere gets the generic glyph, and a glyph keeps its size (D3). Files at LuCI's paths would replace bootstrap's icons too; a script swapping each `src` would flash the stock pictures.

### D10. LuCI's own colors in the theme's palette

Three kinds of color come from LuCI's views rather than a stylesheet, and the theme maps each to its tokens over the inline style:
- The realtime graphs draw an SVG in a white box with a black border, blue, green and red lines (the load's in three reds) with legends underlined alike. The box, grid and labels take the mode's ground, line and muted ink, and the series three colors of the theme's (`--chart-1` to `--chart-3`: blue, orange, aqua, each mode's set validated against its ground), keyed by the color LuCI writes on a line and its legend alike. Red stays the color of errors.
- A firewall zone's color (`--zone-color-rgb`, inline) is a pastel for light pages: a zone's badge is a neutral chip with a dot of its color (D3), and a zone's bar and an empty badge keep the color whole, their text in the dark ink in both modes.
- States set as inline colors (the port status's power over Ethernet, the password's strength) take the ink, faint, danger, warning and accent tokens, which turn dark with the mode.

## Risks / Trade-offs

- [System fonts differ by platform] → The stack names each platform's own; metrics stay close, and the layout does not depend on a font's width.
- [Monospace for every figure is impossible over LuCI's markup] → Only `code`, `pre` and LuCI's own monospace classes take it.
- [TouhouAsia changes its tokens] → The theme carries the values, recorded here; a change is a decision for the theme, not a dependency.
