"""The patch files of the repository and their upstream status.

See docs/patches.md.
"""

import itertools
import re

from orbyt_tests.model.repository import REPO_DIR, repository_files

DOC = REPO_DIR / "docs" / "patches.md"
# OpenEmbedded's vocabulary (docs/patches.md).
STATUS = re.compile(r"Pending|Submitted \[.+\]|Backport \[.+\]|Inappropriate \[.+\]")
MEANT_FOR_UPSTREAM = ("Pending", "Submitted")
TRAILER = re.compile(r"^([A-Za-z][A-Za-z0-9-]*): (.+)$")


def upstream_status(text: str) -> str | None:
    """Return the Upstream-Status trailer of a patch's text, or None.

    A git format-patch file carries it at the end of its message, before
    the ``---`` line; a plain diff in its header, before the diff
    itself.
    """
    if text.startswith("From ") and "\n---\n" in text:
        message = text.split("\n---\n", 1)[0]
        part = message.rstrip("\n").split("\n\n")[-1]
    else:
        part = re.split(r"(?m)^(?:diff |--- |Index: )", text, maxsplit=1)[0]
    found: list[str] = [
        match.group(2)
        for line in part.splitlines()
        if (match := TRAILER.match(line)) and match.group(1) == "Upstream-Status"
    ]
    return found[-1] if found else None


def write_ups(doc: str) -> dict[str, str]:
    """Return the write-ups of the patch documentation.

    Each write-up maps its title to the patch file it names.
    """
    section = doc.split("\n## Patches meant for upstream\n", 1)[-1]
    found: dict[str, str] = {}
    for block in re.split(r"(?m)^### ", section)[1:]:
        title, _, body = block.partition("\n")
        named = re.search(r"(?m)^Patch: `([^`]+)`", body)
        found[title.strip()] = named.group(1) if named else ""
    return found


def unstated(patches: dict[str, str | None]) -> list[str]:
    """Return the patches without a status in the vocabulary."""
    return [
        path
        for path, status in patches.items()
        if status is None or not STATUS.fullmatch(status)
    ]


def without_write_up(
    patches: dict[str, str | None], titles: dict[str, str]
) -> list[str]:
    """Return the patches meant for upstream that no write-up names."""
    named = set(titles.values())
    return [
        path
        for path, status in patches.items()
        if status is not None
        and status.split(" ")[0] in MEANT_FOR_UPSTREAM
        and path not in named
    ]


def without_patch(patches: dict[str, str | None], titles: dict[str, str]) -> list[str]:
    """Return the write-ups that name no patch meant for upstream."""
    return [
        title
        for title, path in titles.items()
        if (patches.get(path) or "").split(" ")[0] not in MEANT_FOR_UPSTREAM
    ]


def repository_patches() -> dict[str, str | None]:
    """Return every patch file of the repository and its status."""
    return {
        path: upstream_status((REPO_DIR / path).read_text())
        for path in sorted(repository_files("*.patch", "*.diff"))
    }


# The sections of a write-up, in their order; the third has a plural
# form for a patch that adds several (docs/patches.md).
SECTIONS = (
    ("Problem",),
    ("Why it matters here",),
    ("What the patch does", "What the patches do"),
    ("Verification log",),
)
# Where a write-up's patch lives, in the order of the documentation's
# groups.
GROUPS = (
    "patches/openwrt/",
    "patches/packages/",
    "patches/luci/",
    "patches/daeuniverse/",
    "patches/qemu/",
    "feed/",
    "docs/upstream/",
)


def misshapen(doc: str) -> list[str]:
    """Return what departs from the write-ups' shape.

    That is a write-up without one of its sections, or with them out of
    order, each named by its patch; and write-ups out of the order of
    their patches' groups and files.
    """
    problems: list[str] = []
    order: list[str] = []
    section = doc.split("\n## Patches meant for upstream\n", 1)[-1]
    for block in re.split(r"(?m)^### ", section)[1:]:
        body = re.split(r"(?m)^## ", block)[0]
        named = re.search(r"(?m)^Patch: `([^`]+)`", body)
        patch = named.group(1) if named else block.partition("\n")[0]
        order.append(patch)
        reached = 0
        for labels in SECTIONS:
            starts = [
                found.start()
                for label in labels
                if (found := re.search(rf"(?m)^{re.escape(label)}:( |$)", body))
            ]
            if not starts:
                problems.append(f"{patch}: no {labels[0]}")
            elif min(starts) < reached:
                problems.append(f"{patch}: {labels[0]} out of order")
            else:
                reached = min(starts)

    def place(patch: str) -> tuple[int, str]:
        group = next(
            (i for i, g in enumerate(GROUPS) if patch.startswith(g)), len(GROUPS)
        )
        return group, patch

    problems += [
        f"{before} before {after}"
        for before, after in itertools.pairwise(order)
        if place(before) > place(after)
    ]
    return problems
