# Proposal

## Why

The image's web interface wears LuCI's stock bootstrap theme: a top bar of dropdown menus, no dark mode of its own choice, and a layout made for desktops first. The router has grown its own services (honk, the data disk, containers, the A/B slots) and gains more (dynamic DNS, a Cloudflare tunnel, certificates, traffic accounting, UPnP, a terminal); their pages deserve an interface designed for this router, which reads well by day and by night and on a phone. The design was settled with the maintainer on 2026-11-17 in an interactive mockup (`luci-theme-orbyt`, its first version): a sidebar of LuCI's menu, a top bar with the page's place, LuCI's pending changes and a light/dark switch, and the page's sections as cards, on a green-tinted canvas with an emerald accent.

## What Changes

- **A theme of the image's own, `luci-theme-orbyt`**, in this repository's feed: LuCI's header, footer and login templates, its stylesheet, and a menu script that renders LuCI's menu as a sidebar and its third level as tabs.
- **Light and dark by the browser's setting, or as the user pins it** in the top bar, kept in that browser; dark mode is LuCI's own `data-darkmode` attribute, which LuCI's modules already style by.
- **Usable at phone width**: the sidebar becomes a drawer, forms stack, wide tables scroll in their own box.
- **Every widget LuCI's applications use** is styled: the theme covers every class bootstrap's stylesheet styles, which a test checks against bootstrap's own.
- **LuCI's own icons and colors in the theme's style**: the device, port, signal, loading and file-browser icons LuCI draws are redrawn in the theme's own icon set, colored by what they tell (up in the accent, down faint), and LuCI's realtime graphs, firewall zone colors and the state colors its views set inline take the theme's palette in light and dark, without changing a view.
- **Nothing from outside the router**: system fonts, the theme's own icons, no external stylesheet, script or image.
- **The default once it arrives**: a fresh install and the first boot of an upgrade that brings it use it; afterwards an administrator's choice of theme stays. bootstrap stays installed beside it.

## Capabilities

### New Capabilities
- `firmware/web-theme`: the look of the web interface: the image's own theme as LuCI's default, light and dark, phone width, widget coverage, and no external resources.

### Modified Capabilities

None.

## Impact

- `feed/luci/luci-theme-orbyt` (new): `Makefile` on LuCI's `luci.mk`, `ucode/template/themes/orbyt/{header,footer,sysauth}.ut`, `htdocs/luci-static/orbyt/{cascade.css,logo.svg,icons/*.svg}`, its Simplified Chinese strings in `po/`, `htdocs/luci-static/resources/menu-orbyt.js`, `htdocs/luci-static/resources/view/orbyt/sysauth.js`, `root/etc/uci-defaults/31_luci-theme-orbyt`.
- `config/system.seed`: the theme package.
- Tests: `tests/firmware/test_web_theme.py` (the default theme and an administrator's choice across an upgrade, on the emulator; widget coverage against bootstrap's stylesheet; a glyph for every icon LuCI installs; no external resources in the theme's files or the pages it serves).
- `docs/`: the theme in the services or base-system documentation.
