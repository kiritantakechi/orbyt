# Design

## Context

- The theme (luci-theme-wrt, renamed luci-theme-orbyt) is one stylesheet of about 3,300 lines over LuCI's markup: tokens, the shell, the menu, then LuCI's widgets by class, the functional rules bootstrap needs (dropdowns, tooltips, the modal, tab panes, the file browser, tables stacked on phones) among them. Its tests check the stylesheet's coverage of bootstrap's classes, LuCI's icons against its glyphs, the default theme and that nothing loads from outside.
- The approved canvas holds the look: a desktop page (sidebar, overview, ports, interfaces, an edit form), a phone page (drawer, breadcrumb) and the mark. Its tokens are TouhouAsia's semantic layer (`project/tokens.css` of the design system).
- TouhouAsia defines no sidebar, modal, dropdown, toast, density mode or icon set, and no CJK fonts; a router's admin pages need all of them except the icon set, which the theme has already (glyphs for LuCI's icons).

## Goals / Non-Goals

**Goals:**
- The canvas's look on every LuCI page, light and dark, desktop and phone.
- TouhouAsia's hard rules kept where LuCI's markup allows: no shadows, colour-only states, one action colour, 4.5:1 text contrast, the focus ring.

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
| warning, danger, info | `#b45309`, `#b91c1c`, `#1d4ed8` with their 50 tints | `#fbbf24`, `#f87171`, `#93c5fd` at 14% |

The bootstrap compatibility variables LuCI's modules read point at these. Motion is TouhouAsia's: colour, background, border and shadow transitions only, 80 to 220 ms, ease-out, none under reduced motion.

### D2. The layout

A 64 px header across the page: the lockup (the mark, "Orbyt", the hostname and model below it), LuCI's indicators, the light/dark switch and logout. Below it the sidebar, 240 px, on the second ground: the menu's first level as small group labels, their pages as text entries, the current one in the text colour with a 3 px vertical brand rule; no icons, as TouhouAsia has no icon set. The content beside it, at most 1200 px: the breadcrumb (`/` separated), LuCI's tab menu, the view. Below 800 pixels the sidebar becomes a drawer behind a menu button in the header, closed by the button, a tap beside it or Escape, as before.

TouhouAsia's 72 px header and 40 px page titles are for documents; an admin page takes the 64 px header, 28 px page titles and 16 px section titles, and keeps its 40 px fields, with 32 px buttons inside tables.

### D3. LuCI's widgets by role

- Sections: the panel recipe, second ground, brand hairline, 8 px radius, 24 px padding; the section's title in 16/800.
- Buttons: pills, label weight 600. `cbi-button-apply` and `important` are the primary (accent fill); edit, add, save, action and neutral buttons the secondary (an outline of the text at 26%); `cbi-button-remove`, `negative` and reset the danger ink; a link-like button the ghost.
- Fields: 40 px, 8 px radius, the strong border, the raised ground; an invalid one takes the danger border (LuCI's `cbi-input-invalid`).
- Tables: a strong line under the header row, hairline rows; figures in monospace where LuCI marks them as such (`code`, `pre`).
- Tabs: text with the 3 px brand rule under the active one, no fill.
- Alerts: the tone's tint and a border of its ink at 30%, never a coloured edge; LuCI's message carries the word.
- Labels and badges: soft pills in the tone's tint; zones a neutral chip with a dot of the zone's colour (replacing luci-theme-wrt D11's tint).

### D4. The mark

The ring node on a 64 grid: a ring of radius 21 and width 6.5, a node of radius 6.4 at 1:30 cut free by a 9.6 gap, filled with the stream gradient (light `#059669`, `#10b981`, `#1e40af`; dark `#64ffda`, `#10b981`, `#0284c7`). Inline in the header and the login, its colours from the mode's tokens; `mark.svg` as the pages' icon, which picks its inks by `prefers-color-scheme` (an icon file cannot read the page's pinned mode).

### D5. Fonts

`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Inter, sans-serif`; monospace `ui-monospace, "SF Mono", Menlo, Consolas, "Monaspace Neon Var", monospace`. Weights 400, 500, 600 and 800; tracking by size, as TouhouAsia sets it.

### D6. Tests and evidence

- `test_web_theme.py`: the mark's scenario: the login page and a page after login both hold the mark and link `/luci-static/orbyt/mark.svg` as their icon, and the icon is served. The coverage, glyph and no-external-resource tests run unchanged.
- In a browser, against the emulator: the overview, an interface form, the login, the apply dialog, a dropdown, the firewall zones and a realtime graph, light and dark, at 1024 and 375 pixels; the browser-verified scenarios re-dated in `tests/verified-elsewhere.toml`.

## Risks / Trade-offs

- [System fonts differ by platform] → The stack names each platform's own; metrics stay close, and the layout does not depend on a font's width.
- [Monospace for every figure is impossible over LuCI's markup] → Only `code`, `pre` and LuCI's own monospace classes take it.
- [TouhouAsia changes its tokens] → The theme carries the values, recorded here; a change is a decision for the theme, not a dependency.
