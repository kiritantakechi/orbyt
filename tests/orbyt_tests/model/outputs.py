"""The build's and the release's outputs as data (module-boundaries D7).

``scripts/build.sh`` writes a build's ``manifest.json``; a release
carries it as ``<device>-manifest.json``, and a drill base carries the
manifest of the build its image comes from. ``emu-prepare`` records what
an emulator directory was made from (``source.json``),
``scripts/toolchain-build.sh`` what a toolchain was built with
(``orbyt-toolchain.json``), and ``scripts/release-publish.sh`` what a
release is (``release.json``). Each is read through its model here,
strict about unknown fields and types (``orbyt_tests.model.data``).
"""

import hashlib
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer
from pydantic_core import PydanticCustomError

MANIFEST_FILE = "manifest.json"
SOURCE_FILE = "source.json"
TOOLCHAIN_FILE = "orbyt-toolchain.json"
RELEASE_FILE = "release.json"

type Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def sha256(path: Path) -> str:
    """Return the SHA-256 of a file, as the outputs record it."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _split(flags: object) -> object:
    """Split the compiler flags the scripts write as one string.

    The split is the one the compiler applies.
    """
    if not isinstance(flags, str):
        kind, msg = "string_type", "compiler flags are one string"
        raise PydanticCustomError(kind, msg)
    return tuple(flags.split())


type Flags = Annotated[
    tuple[str, ...], BeforeValidator(_split), PlainSerializer(" ".join, return_type=str)
]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Manifest(_Record):
    """A build's manifest.

    It records which board was built, from what, with which flags, and
    its files.
    """

    board: str
    device: str
    run: str
    profile: str
    build: str
    cflags: Flags
    kernel_cflags: Flags
    toolchain_cflags: Flags
    upstream_lock_sha256: Sha256
    patches_sha256: Sha256
    # This repository's commit, -dirty when the checkout differed from
    # it in any file, an untracked one that is not ignored included.
    commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}(-dirty)?$")]
    openwrt_head: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    kernel_version: str
    vermagic: str
    files: dict[str, Sha256]


class EmulationSource(_Record):
    """What an emulator directory was made from.

    That is a build's factory image and firmware.
    """

    build: Path
    board: str
    image: Path
    image_sha256: Sha256
    firmware: Path
    firmware_sha256: Sha256


class ToolchainRecord(_Record):
    """What a toolchain was built with.

    That is the flags, its C library, and Rust's standard library.

    ``environment`` names the host environment the host side was built
    in, by the fingerprint ``ORBYT_BUILD_INPUTS`` ends with
    (nixpkgs-2605 D4). ``rust_std`` is absent until the toolchain has
    built Rust's.
    """

    cflags: Flags
    libc: Sha256
    environment: Annotated[str, Field(pattern=r"^[0-9a-z]{32}-orbyt-build-inputs$")]
    rust_std: Sha256 | None = None


class Release(_Record):
    """A release: tag, prerelease flag, notes, boards and assets."""

    tag: Annotated[str, Field(min_length=1)]
    prerelease: bool
    notes: str
    boards: tuple[str, ...]
    assets: tuple[str, ...]
