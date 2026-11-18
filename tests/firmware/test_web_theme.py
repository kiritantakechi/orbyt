"""firmware/web-theme: the image's own LuCI theme, its default, its coverage and its sources.

The coverage, LuCI's icons and the pages are read as the router serves
them, LuCI's stock theme beside the image's own; the theme's files are
read from this repository's feed. Light and dark, phone width, and how
the icons and graphs look are verified in a browser
(verified-elsewhere).
"""

import re
import tomllib
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from orbyt_tests import spec

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router

CAPABILITY = "firmware/web-theme"
REPO = Path(__file__).resolve().parents[2]
THEME_DIR = REPO / "feed" / "luci" / "luci-theme-orbyt"
EXCEPTIONS = Path(__file__).with_name("web-theme-exceptions.toml")
THEME = "/luci-static/orbyt"
STOCK = "/luci-static/bootstrap"
DEFAULTS = "/rom/etc/uci-defaults/31_luci-theme-orbyt"
UPGRADE_IMAGE = "/tmp/sysupgrade.tar.gz"  # noqa: S108 (a path on the router)
# What loads a resource, in markup, in a stylesheet and in a script,
# when it names another host: a scheme's // or a scheme-relative //.
# Links (<a href>) load nothing.
LOADS = (
    re.compile(
        r"<(?:link|script|img|source|iframe|object|embed)\b[^>]*\b(?:href|src)"
        r"\s*=\s*[\"']?\s*(?:[a-z]+:)?//",
        re.IGNORECASE,
    ),
    re.compile(r"url\(\s*[\"']?\s*(?:[a-z]+:)?//", re.IGNORECASE),
    re.compile(r"@import\s+(?:url\()?\s*[\"']?\s*(?:[a-z]+:)?//", re.IGNORECASE),
    re.compile(r"\b(?:fetch|import)\s*\(\s*[\"'`](?:[a-z]+:)?//", re.IGNORECASE),
)
SOURCES = (".ut", ".css", ".js", ".svg")
# The icons LuCI's pages draw, under its resources: luci-base's devices,
# ports, signal strength and loading, and the file browser's.
LUCI_ICONS = "cd /www/luci-static/resources && ls icons/*.svg cbi/*.svg"
GENERIC_GLYPH = "icons/generic.svg"
LUCI = "/cgi-bin/luci/"
PAGE = f"{LUCI}admin/status/overview"
# The mark is an inline <svg class="orbyt-mark">; the pages name the
# theme's own icon file as their icon.
MARK = 'class="orbyt-mark"'
ICON = re.compile(
    rf"<link\b[^>]*\brel=[\"']icon[\"'][^>]*\bhref=[\"']{re.escape(THEME)}/mark\.svg[\"']",
    re.IGNORECASE,
)


def _uncommented(css: str) -> str:
    """Return a stylesheet without its comments."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _classes(css: str) -> set[str]:
    """Return the class names in the selectors of a stylesheet."""
    text = _uncommented(css)
    selectors = (
        sel
        for sel in re.findall(r"([^{}]+)\{", text)
        if not sel.lstrip().startswith("@")
    )
    return {
        name for sel in selectors for name in re.findall(r"\.(-?[_a-zA-Z][\w-]*)", sel)
    }


def _glyphs(css: str) -> dict[str, str]:
    """Return LuCI's icons (``icons/<name>.svg``) a stylesheet gives a glyph, with its path."""
    text = _uncommented(css)
    return {
        icon: glyph.group(1)
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text)
        if (glyph := re.search(r"--glyph:\s*url\(([^)]+)\)", body))
        for icon in re.findall(r'/resources/((?:icons|cbi)/[\w.-]+\.svg)"', selector)
    }


def _loads(text: str) -> list[str]:
    """Return the references in ``text`` that load something from another host."""
    return [match.group(0) for pattern in LOADS for match in pattern.finditer(text)]


def _get(router: Router, path: str) -> str:
    status, body = router.http(path)
    assert status == HTTPStatus.OK, (path, status)
    return body


def _login(router: Router) -> str:
    """Log in to LuCI as root (the image has no password set) and return the session cookie."""
    connection = HTTPConnection(router.address, timeout=30)
    try:
        connection.request(
            "POST",
            LUCI,
            body=urlencode({"luci_username": "root", "luci_password": ""}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        cookie = connection.getresponse().getheader("Set-Cookie")
    finally:
        connection.close()
    assert cookie is not None, "the login set no session cookie"
    return cookie.split(";", 1)[0]


@spec(CAPABILITY, "The image's own theme by default", "Fresh install")
def test_a_fresh_install_uses_the_theme(router: Router) -> None:
    assert router.run("uci get luci.main.mediaurlbase") == THEME
    _, page = router.http("/cgi-bin/luci/")
    assert f"{THEME}/cascade.css" in page, page[:400]


@spec(
    CAPABILITY, "The image's own theme by default", "An upgrade that brings the theme"
)
def test_an_upgrade_that_brings_the_theme_makes_it_the_default(router: Router) -> None:
    # A configuration kept from an image without the theme: the stock
    # theme chosen, the image's unknown. The first boot of the new image
    # runs its uci-defaults.
    router.run(
        f"uci -q delete luci.themes.Orbyt; uci set luci.main.mediaurlbase={STOCK}"
        f" && uci commit luci && sh {DEFAULTS}"
    )
    assert router.run("uci get luci.main.mediaurlbase") == THEME


@spec(
    CAPABILITY,
    "The image's own theme by default",
    "An administrator's choice across an upgrade",
)
def test_an_administrators_theme_survives_an_upgrade(
    router: Router, upgrade_image: Path
) -> None:
    router.run(f"uci set luci.main.mediaurlbase={STOCK} && uci commit luci")
    router.put(upgrade_image, UPGRADE_IMAGE)
    previous_boot = router.boot_id()
    router.detach(f"sleep 1; sysupgrade {UPGRADE_IMAGE}")
    router.wait_rebooted(previous_boot)
    assert router.run("uci get luci.main.mediaurlbase") == STOCK


@spec(CAPABILITY, "Every widget styled", "Compare with the stock theme")
def test_every_class_of_the_stock_theme_is_styled(router: Router) -> None:
    stock = _classes(_get(router, f"{STOCK}/cascade.css"))
    ours = _classes(_get(router, f"{THEME}/cascade.css"))
    entries = tomllib.loads(EXCEPTIONS.read_text(encoding="utf-8"))["class"]
    reviewed = {entry["class"]: entry["reason"] for entry in entries}
    assert all(reason.strip() for reason in reviewed.values())
    assert sorted(stock - ours - reviewed.keys()) == []
    # An entry is stale once the theme styles its class, or the stock
    # theme no longer does.
    assert sorted(name for name in reviewed if name in ours or name not in stock) == []


@spec(
    CAPABILITY,
    "LuCI's icons and colors in the theme's style",
    "Every icon has its glyph",
)
def test_every_icon_of_luci_has_a_glyph(router: Router) -> None:
    shipped = set(router.run(LUCI_ICONS).split())
    glyphs = _glyphs(_get(router, f"{THEME}/cascade.css"))
    assert shipped
    assert sorted(shipped - glyphs.keys()) == []
    # A glyph is stale once LuCI no longer ships its icon.
    assert sorted(glyphs.keys() - shipped) == []
    glyph_paths = {*glyphs.values(), GENERIC_GLYPH}
    unserved = [
        path
        for path in glyph_paths
        if router.http(f"{THEME}/{path}")[0] != HTTPStatus.OK
    ]
    assert sorted(unserved) == []


@spec(CAPABILITY, "Nothing from outside the router", "The login page")
def test_the_login_page_loads_nothing_from_outside(router: Router) -> None:
    _, page = router.http("/cgi-bin/luci/")
    assert f"{THEME}/" in page
    assert _loads(page) == []
    assert _loads(_get(router, f"{THEME}/cascade.css")) == []


@spec(CAPABILITY, "Nothing from outside the router", "The theme's files")
def test_the_theme_files_load_nothing_from_outside() -> None:
    files = [path for path in THEME_DIR.rglob("*") if path.suffix in SOURCES]
    assert files
    found = {
        str(path.relative_to(THEME_DIR)): loads
        for path in files
        if (loads := _loads(path.read_text(encoding="utf-8")))
    }
    assert found == {}


@spec(CAPABILITY, "Orbyt's mark", "The mark on the pages")
def test_the_login_and_the_pages_carry_the_mark(router: Router) -> None:
    _, login = router.http(LUCI)
    status, page = router.http(PAGE, headers={"Cookie": _login(router)})
    assert status == HTTPStatus.OK, status
    pages = {"the login page": login, "a page after login": page}
    assert [name for name, text in pages.items() if MARK not in text] == []
    assert [name for name, text in pages.items() if not ICON.search(text)] == []
    assert "<svg" in _get(router, f"{THEME}/mark.svg")
