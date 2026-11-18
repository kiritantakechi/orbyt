"""Release keys made for the test, and what the tests sign with them.

A release is signed with an apk key (EC P-256, package indexes) and a
firmware key (usign, images and the manifest). ``Keys.make`` creates
both and a keyring that mirrors the image's trust anchors (etc/apk/keys,
etc/usign/keys), as orbyt-keyring holds the production ones;
``orbyt_tests.device.trust`` puts it on a router. ``sign`` runs
scripts/release-sign.sh, the script CI signs releases with, on a build
with these keys. See r4s-release-pipeline D7.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from orbyt_tests.model.repository import REPO_DIR

RELEASE_SIGN = REPO_DIR / "scripts" / "release-sign.sh"
APK_KEYS = Path("etc/apk/keys")
FIRMWARE_KEYS = Path("etc/usign/keys")


def _run(*command: str | Path) -> str:
    return subprocess.run(
        [str(arg) for arg in command], check=True, capture_output=True, text=True
    ).stdout.strip()


@dataclass(frozen=True, slots=True)
class Keys:
    """A pair of release keys and the keyring that trusts them."""

    apk: Path
    firmware: Path
    keyring: Path

    @classmethod
    def make(cls, directory: Path, name: str = "test") -> Self:
        """Create an apk key, a firmware key and their keyring.

        The files are made in ``directory``.
        """
        (directory / "keyring" / APK_KEYS).mkdir(parents=True)
        (directory / "keyring" / FIRMWARE_KEYS).mkdir(parents=True)
        apk = directory / f"{name}.apk.key"
        firmware = directory / f"{name}.fw.key"
        _run(
            "openssl",
            "ecparam",
            "-name",
            "prime256v1",
            "-genkey",
            "-noout",
            "-out",
            apk,
        )
        _run(
            *("openssl", "ec", "-in", apk, "-pubout"),
            *("-out", directory / "keyring" / APK_KEYS / f"orbyt-{name}.pem"),
        )
        public = directory / f"{name}.fw.pub"
        _run("usign", "-G", "-s", firmware, "-p", public, "-c", f"Orbyt {name} key")
        fingerprint = _run("usign", "-F", "-p", public)
        shutil.copy(public, directory / "keyring" / FIRMWARE_KEYS / fingerprint)
        return cls(apk, firmware, directory / "keyring")

    @property
    def fingerprint(self) -> str:
        """The firmware key's usign fingerprint.

        Devices know the key by this name.
        """
        return _run("usign", "-F", "-s", self.firmware)

    def sign_file(self, path: Path) -> Path:
        """Sign ``path`` with the firmware key; return the signature.

        A release's manifest is signed the same way.

        The signature is a file of its own, never written through a
        link.
        """
        signature = path.with_name(f"{path.name}.sig")
        signature.unlink(missing_ok=True)
        _run("usign", "-S", "-m", path, "-s", self.firmware, "-x", signature)
        return signature

    def trust_also(self, other: Keys) -> None:
        """Add ``other``'s public keys to this keyring.

        That is what happens during a key rotation.
        """
        for anchors in (APK_KEYS, FIRMWARE_KEYS):
            for key in (other.keyring / anchors).iterdir():
                shutil.copy(key, self.keyring / anchors / key.name)


def sign(build: Path, signed: Path, keys: Keys) -> Path:
    """Sign ``build``'s outputs into ``signed``; return ``signed``.

    release-sign.sh does the signing.
    """
    _run(
        *(RELEASE_SIGN, build, signed),
        *("--apk-key", keys.apk, "--fw-key", keys.firmware, "--keyring", keys.keyring),
    )
    return signed
