"""UB-indicative warnings and their reviews.

A build's report (``warnings.json``, written by ``scripts/build.sh``)
holds every warning of a UB-indicative option in the build of a package
its image ships. The register (``tests/reviewed-warnings.toml``) holds
the warnings reviewed as not undefined behavior, each with its reason. A
review matches a warning on package, option, file and function, never on
the line, so that it survives upstream moving code around. A review that
names boards matches only their builds' warnings: what GCC finds can
depend on the optimization, and so on the board's ``-mcpu``. See spec
quality/undefined-behavior.
"""

from datetime import date
from typing import TYPE_CHECKING, Annotated, override

from pydantic import BaseModel, ConfigDict, Field

from orbyt_tests.model import boards
from orbyt_tests.model.data import read_json, read_toml
from orbyt_tests.model.repository import TESTS_DIR

if TYPE_CHECKING:
    from pathlib import Path

REGISTER = TESTS_DIR / "reviewed-warnings.toml"
REPORT_FILE = "warnings.json"

type Key = tuple[str, str, str, str]


class _Located(BaseModel):
    """What locates a warning: package, option, file and function.

    The function is empty outside any.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    package: Annotated[str, Field(min_length=1)]
    option: Annotated[str, Field(pattern=r"^-W[a-z0-9-]+$")]
    file: Annotated[str, Field(min_length=1)]
    function: str

    @property
    def key(self) -> Key:
        """Return what a review and a warning match on."""
        return (self.package, self.option, self.file, self.function)

    def _function(self) -> str:
        return f", function {self.function}" if self.function else ""


class Diagnostic(_Located):
    """A UB-indicative warning of a build's report."""

    line: Annotated[int, Field(gt=0)]

    @override
    def __str__(self) -> str:
        """Render as ``package: option at file:line, function f``."""
        where = f"{self.file}:{self.line}{self._function()}"
        return f"{self.package}: {self.option} at {where}"


class Review(_Located):
    """A warning reviewed as not undefined behavior: why, and when."""

    reason: Annotated[str, Field(min_length=1)]
    reviewed: date
    boards: Annotated[tuple[str, ...], Field(strict=False)] = ()

    def covers(self, board: str) -> bool:
        """Return whether the review applies to ``board``'s builds."""
        return not self.boards or board in self.boards

    @override
    def __str__(self) -> str:
        """Render as ``package: option in file, function f``."""
        return f"{self.package}: {self.option} in {self.file}{self._function()}"


def load_report(build_output: Path) -> list[Diagnostic]:
    """Return the UB-indicative warnings in ``build_output``."""
    return read_json(build_output / REPORT_FILE, list[Diagnostic])


def load_register(path: Path = REGISTER) -> list[Review]:
    """Return the reviews of ``path``.

    They name known boards and no warning twice.
    """
    reviews = read_toml(path, "warning", Review)
    known = {board.id for board in boards.load_all()}
    seen: set[Key] = set()
    for review in reviews:
        if unknown := set(review.boards) - known:
            msg = f"{review} names unknown boards: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        if review.key in seen:
            msg = f"{review} is reviewed twice"
            raise ValueError(msg)
        seen.add(review.key)
    return reviews


def unreviewed(
    report: list[Diagnostic], register: list[Review], board: str
) -> list[Diagnostic]:
    """Return ``board``'s build warnings that no review covers."""
    reviewed = {review.key for review in register if review.covers(board)}
    return [warning for warning in report if warning.key not in reviewed]


def stale(register: list[Review], report: list[Diagnostic], board: str) -> list[Review]:
    """Return the reviews for ``board`` matching no build warning."""
    found = {warning.key for warning in report}
    return [
        review
        for review in register
        if review.covers(board) and review.key not in found
    ]
