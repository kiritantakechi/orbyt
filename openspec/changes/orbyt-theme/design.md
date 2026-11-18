# Design

## Context

- The theme (luci-theme-wrt, renamed luci-theme-orbyt) is one stylesheet of about 3,300 lines over LuCI's markup: tokens, the shell, the menu, then LuCI's widgets by class, the functional rules bootstrap needs (dropdowns, tooltips, the modal, tab panes, the file browser, tables stacked on phones) among them. Its tests check the stylesheet's coverage of bootstrap's classes, LuCI's icons against its glyphs, the default theme and that nothing loads from outside.
- The approved canvas holds the look: a desktop page (sidebar, overview, ports, interfaces, an edit form), a phone page (drawer, breadcrumb) and the mark. Its tokens are TouhouAsia's semantic layer (`project/tokens.css` of the design system).
- On 2026-11-19 the maintainer updated TouhouAsia (version 1795018428-c32c) and asked for the theme to follow it, and to drop what it carries without use. The update defines the interface: an aside of 256 px (`Sidebar`), a table of contents with the brand rule on its hairline, the breadcrumb, tabs, fields, choices, tags and callouts with their states (`components/bundle.css`, `docs/06-interface.md`, `docs/07-states.md`), and two tokens, the selection and the link's hover. It still defines no modal, dropdown, toast, density mode, icon set or CJK fonts; a router's admin pages need all of them but the icon set, which the theme has already (glyphs for LuCI's icons).
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

The bootstrap compatibility variables LuCI's modules read point at these; `--disabled-opacity` stays for LuCI applications' own styles, which the theme's rules never use. Motion is TouhouAsia's: color, background, border and shadow transitions only, 140 ms, ease-out, the drawer's slide 220 ms, none under reduced motion.

### D2. The layout

A 64 px header across the page: the lockup (the mark, "Orbyt", the hostname and model below it), LuCI's indicators as tags, the light/dark switch (three text pills, the chosen one in the accent's tint) and logout. Below it the sidebar, TouhouAsia's aside of 256 px on the page's own ground with a hairline at its edge (the system has no colored sidebar), holding the menu as its table of contents: each of the menu's first level an eyebrow (monospace capitals in the accent), its pages as entries hanging from a hairline, the current one in the text color at 600 with the 3 px brand rule on the hairline; no icons, as TouhouAsia has no icon set. The content beside it, at most 1200 px: the breadcrumb (the levels above as links, ` / ` between them, the page in the text color), LuCI's tab menu, the view. The page's title has no rule under it: the brand rule marks only the reader's place, the menu's entry and the tab. Below 800 pixels the sidebar becomes a drawer behind a menu button in the header, closed by the button, a tap beside it or Escape, as before; the switch and logout move into its foot.

TouhouAsia's 72 px header and 40 px page titles are for documents; an admin page takes the 64 px header, 28 px page titles and 20 px section titles, and keeps its 40 px fields, with 32 px buttons inside tables.

### D3. LuCI's widgets by role

- Sections: the panel recipe, second ground, brand hairline, 8 px radius, 24 px padding; the section's title in 20/800.
- Buttons: TouhouAsia's `Button`, pills of 40 px (32 px small and inside tables), 20 px padding (16 small), label 14/600. `cbi-button-apply` and `important` are the primary (accent fill); edit, add, save, action and neutral buttons the secondary (an outline of the text at 26%, which hovers to the accent's edge and tint and keeps its ink); `cbi-button-remove`, `negative` and reset the danger ink; a link-like button the ghost. Disabled: the neutral fill and the faint ink, none for a button without a frame.
- Fields: `TextField` and `Select`: 40 px, 8 px radius, the strong border, the raised ground, the value at 15 px under a 14/500 label; hover takes the secondary ink's border, focus the accent's with the ring; an invalid one (`cbi-input-invalid`, `aria-invalid`) keeps the danger border while focused; a disabled one the neutral fill and faint ink.
- Choices: `Checkbox` (4 px radius, 1.5 px strong edge, the accent fill and its ink's check when checked) and `RadioGroup` (an accent ring and dot), 10 px from their labels; disabled on the neutral fill, a checked one in the faint ink.
- Tables: TouhouAsia's `SpecTable`: heads in the eyebrow's monospace capitals at 12 px (the system's 10 px leaves CJK heads too small), a strong line under them, hairline rows, tabular figures, the first and last columns flush with the panel; no row hover, as a row is not a control.
- Tabs: `Tabs`: 15/500 text 24 px apart on a hairline, the selected one at 600 with the 3 px brand rule over the hairline, no fill.
- Alerts: `Callout`: the tone's tint and a border of its ink at 30%, never a colored edge, 16 by 20 px padding; LuCI's message carries the word.
- Labels and badges: `Tag`, 22 px soft pills in the tone's tint; zones a neutral chip with a dot of the zone's color (replacing luci-theme-wrt D11's tint). LuCI's indicators are tags too.
- Code and command output (`pre`): `CodeBlock`'s panel, monospace at 13/1.65.
- Forced colors: the brand rules, the radio's dot, the check and LuCI's icons redrawn in the system's inks; tags and callouts take an edge.
- What nothing draws goes: a rule for a class no view, script or template of LuCI's feed or this repository's names is dropped, and where bootstrap styles the class, `tests/firmware/web-theme-exceptions.toml` records why the theme does not.

### D4. The mark

The ring node on a 64 grid: a ring of radius 21 and width 6.5, a node of radius 6.4 at 1:30 cut free by a 9.6 gap, filled with the stream gradient (light `#059669`, `#10b981`, `#1e40af`; dark `#64ffda`, `#10b981`, `#0284c7`). Inline in the header and the login, its colors from the mode's tokens; `mark.svg` as the pages' icon, which picks its inks by `prefers-color-scheme` (an icon file cannot read the page's pinned mode).

### D5. Fonts

`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Inter, sans-serif`; monospace `ui-monospace, "SF Mono", Menlo, Consolas, "Monaspace Neon Var", monospace`. Weights 400, 500, 600 and 800; tracking by size, as TouhouAsia sets it.

### D6. Tests and evidence

- `test_web_theme.py`: the mark's scenario: the login page and a page after login both hold the mark and link `/luci-static/orbyt/mark.svg` as their icon, and the icon is served. The coverage, glyph and no-external-resource tests run unchanged.
- In a browser, against the emulator: the overview, an interface form, the login, the apply dialog, a dropdown, the firewall zones and a realtime graph, light and dark, at 1024 and 375 pixels; the browser-verified scenarios re-dated in `tests/verified-elsewhere.toml`.

## Risks / Trade-offs

- [System fonts differ by platform] → The stack names each platform's own; metrics stay close, and the layout does not depend on a font's width.
- [Monospace for every figure is impossible over LuCI's markup] → Only `code`, `pre` and LuCI's own monospace classes take it.
- [TouhouAsia changes its tokens] → The theme carries the values, recorded here; a change is a decision for the theme, not a dependency.
