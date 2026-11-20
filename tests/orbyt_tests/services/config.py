"""The private configuration and config-push (r4s-release-pipeline D6).

Here they are as the tests drive them.

``ConfigRepository.create`` runs scripts/config-init.sh with an age key
of the test's own. Its secrets, honk's configuration and uci templates
are then written the way an administrator does, sops encrypting each
file for the recipient in .sops.yaml, and ``push`` runs
scripts/config-push.sh against the router.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from orbyt_tests.model import git, process
from orbyt_tests.model.repository import REPO_DIR

if TYPE_CHECKING:
    from pathlib import Path

SCRIPTS = REPO_DIR / "scripts"
PUSH_TIMEOUT = 900


@dataclass(frozen=True, slots=True)
class ConfigRepository:
    """A private configuration repository and its secrets' age key."""

    directory: Path
    age_key: Path

    @classmethod
    def create(cls, workdir: Path) -> Self:
        """Run config-init in ``workdir``/config, with a new age key."""
        repository = cls(workdir / "config", workdir / "age.txt")
        process.run(
            SCRIPTS / "config-init.sh",
            repository.directory,
            env=repository.environment(),
        )
        return repository

    def environment(self) -> dict[str, str]:
        """Return the environment config-init and config-push run in."""
        return {
            **os.environ,
            "SOPS_AGE_KEY_FILE": str(self.age_key),
            "ORBYT_CONFIG_DIR": str(self.directory),
        }

    def _encrypt(self, name: str, plain: bytes) -> None:
        """Write the file ``name`` encrypted, as sops does.

        ``name`` is relative to the repository.
        """
        encrypted = subprocess.run(
            ["sops", "encrypt", "--filename-override", name, "/dev/stdin"],
            input=plain,
            check=True,
            capture_output=True,
            cwd=self.directory,
            env=self.environment(),
        ).stdout
        (self.directory / name).write_bytes(encrypted)

    def write_secrets(self, secrets: dict[str, Any]) -> None:
        """Replace the secrets.

        YAML is JSON's superset: JSON goes in as it is.
        """
        self._encrypt("secrets/secrets.enc.yaml", json.dumps(secrets).encode())

    def write_proxy(self, name: str, text: str) -> None:
        """Replace a file of honk's configuration."""
        self._encrypt(f"honk/{name}.dae.enc", text.encode())

    def commit(self, message: str) -> None:
        """Commit everything, as an administrator does after editing."""
        git.commit(self.directory, message)

    def discard(self) -> None:
        """Drop every change since the last commit."""
        git.run(self.directory, "reset", "-q", "--hard")
        git.run(self.directory, "clean", "-q", "-d", "--force")

    def push(self, host: str, identity: Path) -> subprocess.CompletedProcess[str]:
        """Run config-push against ``host`` with ``identity``."""
        return subprocess.run(
            [SCRIPTS / "config-push.sh", host, "--identity", identity],
            capture_output=True,
            text=True,
            check=False,
            env=self.environment(),
            timeout=PUSH_TIMEOUT,
        )
