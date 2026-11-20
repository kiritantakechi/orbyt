"""git as the tests run it, in repositories of their own.

Every repository a test makes commits as the tests' own identity, with
none of the user's configuration (test-hygiene D9).
"""

import os
from typing import TYPE_CHECKING

from orbyt_tests.model import process

if TYPE_CHECKING:
    from pathlib import Path

IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@localhost",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@localhost",
    "GIT_CONFIG_GLOBAL": os.devnull,
}


def run(repository: Path, *args: str) -> str:
    """Run git in ``repository``; return its output, stripped."""
    return process.run(
        "git", "-C", repository, *args, env={**os.environ, **IDENTITY}
    ).strip()


def commit(repository: Path, message: str) -> str:
    """Commit everything in ``repository``; return the commit."""
    run(repository, "add", "-A")
    run(repository, "commit", "-q", "-m", message)
    return run(repository, "rev-parse", "HEAD")
