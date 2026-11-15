"""Where the repository is: its root, the directory of the tests, and its feed."""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_DIR / "tests"
FEED_DIR = REPO_DIR / "feed"


def feed_variable(package: str, name: str) -> str:
    """Return what the Makefile of our feed's ``package`` (net/honk, ...) sets ``name`` to.

    The value of its first ``name:=value`` line, as written.
    """
    makefile = (FEED_DIR / package / "Makefile").read_text(encoding="utf-8")
    for line in makefile.splitlines():
        key, separator, value = line.partition(":=")
        if separator and key == name:
            return value
    msg = f"feed/{package}/Makefile sets no {name}"
    raise LookupError(msg)
