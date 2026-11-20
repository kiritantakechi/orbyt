"""Read the pieces of the shipped images.

The parsers are pure functions over bytes or text, so the unit tests
cover them without an image: a gzip stream may be followed by fwtool
metadata, the disk has an MBR, U-Boot and the kernel are FITs, read from
their ``dumpimage -l`` listings, and U-Boot carries its default
environment as a run of strings. The readers at the end run the test
environment's tools on an image's files: dumpimage on a FIT, debugfs on
a boot partition. See design D14 and r4s-ab-rollback D7.
"""

import re
import struct
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO

from orbyt_tests.model import process

if TYPE_CHECKING:
    from pathlib import Path

# The hostname of a fresh configuration: the image's name (orbyt-brand
# D3).
DEFAULT_HOSTNAME = "orbyt"
SECTOR = 512
# Each slot's partitions on the boot disk: its boot partition (ext4, the
# kernel FIT), then its root (EROFS, then the overlay area)
# (r4s-ab-rollback D1).
SLOT_PARTITIONS = {"a": (1, 2), "b": (3, 4)}
_MBR_SIGNATURE = 0x1B8
_MBR_ENTRIES = 0x1BE
_MBR_ENTRY_SIZE = 16

_ENVIRONMENT_BLOCK = re.compile(rb"(?:[\x20-\x7e\t]+\0)+\0")
_ENVIRONMENT_ENTRY = re.compile(
    r"^(?P<name>[A-Za-z_][\w.#+-]*)=(?P<value>.*)$", re.DOTALL
)
_FIT_NODE = re.compile(
    r"^ (?P<kind>Image|Configuration) (?P<index>\d+) \((?P<name>[^)]+)\)$"
)
_FIT_DEFAULT = re.compile(r"^ Default Configuration: '(?P<name>[^']+)'$")
_FIT_PROPERTY = re.compile(r"^  (?P<key>\S[^:]*):\s+(?P<value>.*?)\s*$")
_FIT_CONTINUATION = re.compile(r"^ {3,}(?P<value>\S.*?)\s*$")


@dataclass(frozen=True, slots=True)
class Partition:
    """One primary MBR partition, numbered from 1."""

    number: int
    start: int
    size: int

    def read(self, disk: bytes) -> bytes:
        """Return the bytes of this partition."""
        return disk[self.start : self.start + self.size]


@dataclass(frozen=True, slots=True)
class Disk:
    """The partition table of a disk image."""

    signature: int
    partitions: tuple[Partition, ...]

    def partuuid(self, number: int) -> str:
        """Linux PARTUUID of an MBR disk's partition.

        The form is ``<signature>-<number>``.
        """
        return f"{self.signature:08x}-{number:02x}"

    def partition(self, number: int) -> Partition:
        """Return the partition with this number."""
        for partition in self.partitions:
            if partition.number == number:
                return partition
        msg = f"no partition {number}"
        raise LookupError(msg)


def gunzip_first_member(
    source: BinaryIO, target: BinaryIO, chunk: int = 1 << 20
) -> bytes:
    """Stream the first gzip member of ``source`` into ``target``.

    Return what follows that member. sysupgrade images carry fwtool
    metadata after the gzip stream, which gzip(1) reports as trailing
    garbage.
    """
    decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
    while not decompressor.eof and (block := source.read(chunk)):
        target.write(decompressor.decompress(block))
    if not decompressor.eof:
        msg = "truncated gzip stream"
        raise ValueError(msg)
    target.write(decompressor.flush())
    return decompressor.unused_data + source.read()


def read_mbr(disk: bytes) -> Disk:
    """Parse the MBR: signature and non-empty primary partitions."""
    if disk[510:512] != b"\x55\xaa":
        msg = "no MBR boot signature"
        raise ValueError(msg)
    (signature,) = struct.unpack_from("<I", disk, _MBR_SIGNATURE)
    partitions = []
    for index in range(4):
        start, sectors = struct.unpack_from(
            "<II", disk, _MBR_ENTRIES + index * _MBR_ENTRY_SIZE + 8
        )
        if sectors:
            partitions.append(Partition(index + 1, start * SECTOR, sectors * SECTOR))
    return Disk(signature, tuple(partitions))


def default_environment(binary: bytes, marker: str) -> dict[str, str]:
    """Read U-Boot's built-in environment from its binary.

    The environment is a run of ``name=value`` strings, each ending in a
    zero byte, with one more zero byte after the last. ``marker`` is a
    variable that only this environment defines; it picks the run out of
    the other strings of the binary.
    """
    for block in _ENVIRONMENT_BLOCK.finditer(binary):
        entries = block.group().decode("ascii").split("\0")
        if any(entry.startswith(f"{marker}=") for entry in entries):
            return {
                match["name"]: match["value"]
                for entry in entries
                if (match := _ENVIRONMENT_ENTRY.match(entry))
            }
    msg = f"no built-in environment with {marker}"
    raise LookupError(msg)


@dataclass(frozen=True, slots=True)
class FitNode:
    """One FIT image or configuration, with its listed properties."""

    index: int
    name: str
    properties: dict[str, list[str]]

    def __getitem__(self, key: str) -> str:
        """Return the first value of a property.

        Lists (Compatible, Loadables) have more.
        """
        return self.properties[key][0]


@dataclass(frozen=True, slots=True)
class Fit:
    """The images and configurations of a FIT, keyed by name."""

    images: dict[str, FitNode]
    configurations: dict[str, FitNode]
    default: str

    @property
    def configuration(self) -> FitNode:
        """Return the default configuration.

        It is the one bootm and SPL boot.
        """
        return self.configurations[self.default]

    def selected(self, key: str) -> FitNode:
        """Return the image the default configuration selects.

        ``key`` is Kernel, FDT, and so on.
        """
        name = self.configuration.properties.get(key, [""])[0]
        if name not in self.images:
            msg = f"configuration {self.default} selects no {key} image"
            raise LookupError(msg)
        return self.images[name]


def parse_fit(listing: str) -> Fit:
    """Parse a ``dumpimage -l`` listing of a FIT.

    Nodes start at one space of indent, their properties at two, and the
    further values of a list property (Compatible, Loadables) are
    indented deeper still.
    """
    nodes: dict[str, dict[str, FitNode]] = {"Image": {}, "Configuration": {}}
    default: str | None = None
    node: FitNode | None = None
    values: list[str] = []
    for line in listing.splitlines():
        if match := _FIT_NODE.match(line):
            node = FitNode(int(match["index"]), match["name"], {})
            nodes[match["kind"]][node.name] = node
        elif match := _FIT_DEFAULT.match(line):
            default, node = str(match["name"]), None
        elif node is not None and (match := _FIT_PROPERTY.match(line)):
            values = node.properties[match["key"]] = [match["value"]]
        elif node is not None and (match := _FIT_CONTINUATION.match(line)):
            values.append(match["value"])
    if default is None:
        msg = "the FIT has no default configuration"
        raise LookupError(msg)
    return Fit(nodes["Image"], nodes["Configuration"], default)


def boot_files(
    disk: Path, partition: int, names: tuple[str, ...], output: Path
) -> None:
    """Copy files of a disk's ext4 boot partition to ``output``."""
    with disk.open("rb") as raw:
        boot = read_mbr(raw.read(SECTOR)).partition(partition)
        raw.seek(boot.start)
        filesystem = output / "boot.ext4"
        filesystem.write_bytes(raw.read(boot.size))
    for name in names:
        file = output / name
        # debugfs exits 0 even when the file is missing; check the
        # result instead.
        process.run("debugfs", "-R", f"dump /{name} {file}", str(filesystem))
        if not file.is_file() or file.stat().st_size == 0:
            msg = f"{name} not found on partition {partition}"
            raise FileNotFoundError(msg)
    filesystem.unlink()


def read_fit(path: Path) -> Fit:
    """List a FIT image file."""
    return parse_fit(process.run("dumpimage", "-l", str(path)))


def extract_fit_image(path: Path, image: FitNode, output: Path) -> None:
    """Write one image of a FIT file to ``output``, as stored.

    The image stays compressed.
    """
    process.run(
        "dumpimage",
        "-T",
        "flat_dt",
        "-p",
        str(image.index),
        "-o",
        str(output),
        str(path),
    )
