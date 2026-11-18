# Proposal

## Why

The project is Orbyt now (orbyt-brand), and its web theme still wears the first design: green-tinted greys, a text badge for a logo, filled highlights. The maintainer asked on 2026-11-18 for a modern, beautiful redesign after their TouhouAsia design system, and approved it on a design canvas the same day (https://claude.ai/artifact/RHUvMJ5hZ3M9m2w4N38aZs): sidebar navigation, system fonts with Inter as fallback, and the ring-node mark. On 2026-11-19 they updated TouhouAsia with its interface components (the aside, the table of contents, the breadcrumb, tabs, fields, choices, tags, callouts and their states) and asked for the theme to follow it and to drop what it carries without use.

## What Changes

- **TouhouAsia's tokens and rules for the theme**: white with a mint second ground in light, night navy in dark; emerald as the one action color (aqua for focus in dark); flat surfaces with hairlines and no shadows; 8 px radii for rectangles, pills for buttons and tags; the 3 px brand rule marks the current place (menu entry, tab, page title); states change color only.
- **The approved layout**: a header across the page with Orbyt's lockup, LuCI's indicators, the light/dark switch and logout; the menu as a sidebar of text entries below it, a drawer behind a menu button below 800 pixels; the page's place as a breadcrumb.
- **Orbyt's mark** (the ring node) at the head of every page, on the login page and as the pages' icon, in the mode's colors.
- **System fonts first, Inter as fallback**, and figures in the system's monospace: no font is carried in the image.
- **Nothing the theme does not use**: the rules for classes no LuCI view, script or template names go, recorded against bootstrap's where it styles them.
- **LuCI's widgets restyled** on the new tokens: buttons by role (the page's apply as the one primary, edit and add as secondary, remove and reset in danger ink), inputs and selects as 40 px fields, tables with a strong header line and hairline rows, callouts labelled by tone instead of a colored edge, firewall zones as neutral chips with a dot of the zone's color.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `firmware/web-theme`: a new requirement, Orbyt's mark in the interface. The other requirements hold as they are; the browser-verified scenarios are verified again on the new look.

## Impact

- `feed/luci/luci-theme-orbyt`: `cascade.css` rewritten on the new tokens (its functional rules for LuCI's widgets kept), the templates (header with the lockup and the page icon, sidebar, login), `menu-orbyt.js` (text entries, breadcrumb, drawer), the mark's files under `htdocs/luci-static/orbyt/`.
- `tests/firmware/test_web_theme.py`: the mark's scenario; the coverage and no-external-resource tests apply unchanged.
- `tests/verified-elsewhere.toml`: the browser-verified scenarios re-dated after the new look's check.
- `docs/services.md`: the web interface's description.
