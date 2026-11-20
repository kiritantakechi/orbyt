"""Where the repository is: its root, tests directory and feed.

And its files, as the code standards' checks see them.
"""

from pathlib import Path

from orbyt_tests.model import process

REPO_DIR = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_DIR / "tests"
FEED_DIR = REPO_DIR / "feed"


def feed_variable(package: str, name: str) -> str:
    """Return what ``package``'s Makefile in our feed sets ``name`` to.

    ``package`` is a feed path such as net/honk. The value of its first
    ``name:=value`` line, as written.
    """
    makefile = (FEED_DIR / package / "Makefile").read_text(encoding="utf-8")
    for line in makefile.splitlines():
        key, separator, value = line.partition(":=")
        if separator and key == name:
            return value
    msg = f"feed/{package}/Makefile sets no {name}"
    raise LookupError(msg)


def repository_files(*pathspecs: str) -> list[str]:
    """Return the repository's files that ``pathspecs`` match, or all.

    They are its tracked and new files, not ignored ones, relative to
    its root, as scripts/lib/core.sh's repo_files lists them before it
    leaves some out.
    """
    listed = process.run(
        *("git", "-C", REPO_DIR, "ls-files", "-z"),
        *("--cached", "--others", "--exclude-standard", "--", *pathspecs),
    )
    return [name for name in listed.split("\0") if name and (REPO_DIR / name).is_file()]
