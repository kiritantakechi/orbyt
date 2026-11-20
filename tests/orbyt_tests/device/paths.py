"""Paths on the router that the harness and the tests share.

What the tests bring to the router, or have it write for them, goes to
its scratch directory, /tmp: RAM, which a reboot clears and the
emulator's snapshot takes back (test-hygiene D5).
"""

from pathlib import PurePosixPath

SCRATCH = PurePosixPath("/tmp")  # noqa: S108 (a path on the router)
# The health check's checks, and the result of its last run
# (orbyt-ab's ab.uc).
HEALTH_CHECKS = PurePosixPath("/etc/healthcheck.d")
HEALTH_RESULT = "/var/run/orbyt-healthcheck.json"
# Where an upgrade's image goes before sysupgrade writes it.
UPGRADE_IMAGE = str(SCRATCH / "sysupgrade.tar.gz")


def scratch(name: str) -> str:
    """Return the path of ``name`` in the router's scratch directory."""
    return str(SCRATCH / name)


def health_check(name: str) -> str:
    """Return the path of the health check named ``name``."""
    return str(HEALTH_CHECKS / name)
