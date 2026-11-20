"""Run a CI script against a stand-in gh, with a repository as data.

The stand-in (``orbyt_tests.model.fake_gh``) answers for the
repository as GitHub's API would; a test reads what the script left of
it afterwards.
"""

import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from orbyt_tests.model.repository import REPO_DIR

if TYPE_CHECKING:
    from pathlib import Path

SCRIPTS = REPO_DIR / "scripts"
REPOSITORY = "owner/repository"
MAIN = "refs/heads/main"
# The commit a run is of, unless a test names another, and every
# branch's head unless the repository names another.
HEAD = "a" * 40
# The stand-in gh, which keeps the repository in github.json beside
# itself.
FAKE_GH = "orbyt_tests.model.fake_gh"


@dataclass(slots=True)
class Repository:
    """A repository: its branches, pull requests and caches.

    Its default branch is main.
    """

    branches: list[str] = field(default_factory=lambda: ["main"])
    # How each branch compares with main, as the compare API's status
    # names it.
    compare: dict[str, str] = field(default_factory=dict)
    # Each pull request's state by its number: open or closed.
    pulls: dict[str, str] = field(default_factory=dict)
    # Each branch's head commit, by its name; HEAD for a branch it does
    # not name.
    heads: dict[str, str] = field(default_factory=dict)
    # How two commits compare, by the compare API's path for them
    # (compared): its status and the files between them.
    changes: dict[str, dict[str, object]] = field(default_factory=dict)
    caches: list[dict[str, object]] = field(default_factory=list)

    def cache(self, ref: str, key: str, size: int = 0) -> None:
        """Add the newest cache of ``ref`` under ``key``."""
        self.caches.append(
            {"id": len(self.caches) + 1, "ref": ref, "key": key, "size": size}
        )

    def compared(
        self, base: str, head: str, status: str, files: list[dict[str, str]]
    ) -> None:
        """Have the compare API find ``head`` ``status`` of ``base``.

        ``files`` are the files between them.
        """
        path = f"repos/{REPOSITORY}/compare/{base}...{head}"
        self.changes[path] = {"status": status, "files": files}


def install(directory: Path, repository: Repository) -> Path:
    """Put the stand-in gh into ``directory``; return it.

    It answers for ``repository``.
    """
    directory.mkdir(exist_ok=True)
    described = directory / "github.json"
    command = shlex.join([sys.executable, "-I", "-m", FAKE_GH, str(described)])
    (directory / "gh").write_text(f'#!/bin/sh\nexec {command} "$@"\n')
    (directory / "gh").chmod(0o755)
    described.write_text(
        json.dumps({"repository": REPOSITORY, "head": HEAD, **asdict(repository)}),
        encoding="utf-8",
    )
    return directory


def run_script(
    workdir: Path, repository: Repository, script: str, *args: str, ref: str, **env: str
) -> tuple[subprocess.CompletedProcess[str], list[tuple[str, str]]]:
    """Run ``script`` of scripts/ on ``ref`` against ``repository``.

    The run is of the commit HEAD, unless ``env`` names another
    (GITHUB_SHA). Return its result and the caches it left, as (ref,
    key) pairs.
    """
    directory = install(workdir / "bin", repository)
    described = directory / "github.json"
    result = subprocess.run(
        [SCRIPTS / script, *args],
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PATH": f"{directory}{os.pathsep}{os.environ['PATH']}",
            "GH_REPO": REPOSITORY,
            "GITHUB_REF": ref,
            "GITHUB_SHA": HEAD,
            **env,
        },
    )
    caches = json.loads(described.read_text(encoding="utf-8"))["caches"]
    return result, [(str(cache["ref"]), str(cache["key"])) for cache in caches]
