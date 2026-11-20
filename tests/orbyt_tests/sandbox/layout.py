"""Where the sandbox keeps its files, in its working directory.

Each namespace has a directory of its own for its daemons' files; the
sandbox's test CA, its own /etc files and its accounts' home lie beside
them (test-hygiene D5).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from orbyt_tests.sandbox.pki import Pki

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Layout:
    """The sandbox's working directory, and what lies where in it."""

    root: Path

    @property
    def pki(self) -> Pki:
        """The test CA and the servers' certificate."""
        return Pki(self.root / "pki")

    @property
    def etc(self) -> Path:
        """The sandbox's own files of /etc, bound over the host's."""
        return self.root / "etc"

    @property
    def home(self) -> Path:
        """The home of every account of the sandbox."""
        return self.root / "home"

    def namespace(self, name: str) -> Path:
        """Return the directory of the namespace ``name``."""
        return self.root / name

    @property
    def inet(self) -> Path:
        """The emulated internet's directory: its servers' files."""
        return self.namespace("inet")

    @property
    def releases(self) -> Path:
        """Where the stand-in for GitHub's Releases serves from."""
        return self.inet / "releases"
