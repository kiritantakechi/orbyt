"""emu-prepare: a build's outputs as what the emulator boots.

(r4s-build-foundation D14, r4s-ab-rollback D7, board-model D7)

``emu-prepare`` turns the outputs of a build into what the emulator
boots, as the board the build is for: the factory image as the board's
kind of boot disk (an SD card or an eMMC), which every test run overlays
with copy-on-write; the emulator's U-Boot as firmware; a device tree
with the board's identity, which U-Boot hands on to the kernel it starts
from the slot; and the labgrid target description of the machine, from
the board's description. The output directory is keyed by the image, the
firmware and the board, and reused; directories of builds that have
since changed are removed.
"""

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import yaml

from orbyt_tests.model import process
from orbyt_tests.model.boards import Board, load
from orbyt_tests.model.data import DataError, read_json, write_json
from orbyt_tests.model.image import gunzip_first_member
from orbyt_tests.model.outputs import (
    MANIFEST_FILE,
    SOURCE_FILE,
    EmulationSource,
    Manifest,
    sha256,
)
from orbyt_tests.sandbox.net import ROUTER_ADDRESS, segments, taps

FACTORY_IMAGE = "targets/*-factory.img.gz"
FIRMWARE = "u-boot-qemu.bin"
# The files of an emulator directory.
DISK_FILE = "disk.raw"
OVERLAY_FILE = "overlay.qcow2"
FIRMWARE_FILE = "u-boot.bin"
DTB_FILE = "board.dtb"
TARGET_FILE = "target.yaml"
QEMU = "qemu-system-aarch64"
MACHINE = "virt,gic-version=3"
# The boot disk's device, which throttled_writes() slows down.
BOOT_DISK_ID = "boot-disk"


@dataclass(frozen=True, slots=True)
class BootDisk:
    """A kind of boot disk as the emulator attaches it.

    ``device`` is QEMU's device on the SD host controller, ``size`` the
    disk's size, a power of two as QEMU wants it.
    """

    device: str
    size: int


# An SD card as small as an image must fit, and an eMMC as large as the
# boards'.
BOOT_DISKS = {"sd": BootDisk("sd-card", 4 << 30), "emmc": BootDisk("emmc", 32 << 30)}


@dataclass(frozen=True, slots=True)
class Machine:
    """The QEMU machine that stands in for a board (board-model D7)."""

    board: Board

    def dump_dtb(self, output: Path, firmware: Path) -> None:
        """Write the device tree QEMU generates for this machine.

        The machine runs ``firmware``.

        The firmware belongs to the machine: with one, QEMU replaces the
        PL061 GPIO with an ACPI event device, and a device tree without
        it would describe a device the kernel faults on.
        """
        emulator, cores = self.board.emulator, len(self.board.soc.cores)
        process.run(
            QEMU,
            *("-machine", f"{MACHINE},dumpdtb={output}"),
            *("-cpu", emulator.cpu, "-m", emulator.memory, "-smp", str(cores)),
            *("-bios", str(firmware)),
            "-nographic",
        )

    def description(self, directory: Path) -> dict[str, Any]:
        """Return the labgrid target description of the machine.

        The machine boots ``directory``'s files.

        The boot disk is the board's kind on an SD host controller; each
        of the board's ports is a virtio NIC in the board's order, on
        its segment's tap. The xHCI controller takes the USB data disks
        the tests plug in and out (r4s-services D10).
        """
        emulator = self.board.emulator
        nics = [
            argument
            for index, (segment, tap) in enumerate(
                zip(segments(self.board), taps(self.board), strict=True)
            )
            for argument in (
                f"-netdev tap,id={segment},ifname={tap},script=no,downscript=no",
                (
                    f"-device virtio-net-pci,netdev={segment},"
                    f"mac=52:54:00:0a:00:{0x10 + index:02x}"
                ),
            )
        ]
        arguments = (
            f"-smp {len(self.board.soc.cores)}",
            f"-drive if=none,id=disk,format=qcow2,file={directory / OVERLAY_FILE}",
            "-device sdhci-pci",
            (
                f"-device {BOOT_DISKS[self.board.boot_disk].device}"
                f",id={BOOT_DISK_ID},drive=disk"
            ),
            *nics,
            "-device i6300esb",
            "-device qemu-xhci,id=xhci",
            "-action watchdog=reset",
        )
        return {
            "targets": {
                "main": {
                    "resources": {
                        "NetworkService": {
                            "address": ROUTER_ADDRESS,
                            "username": "root",
                        },
                    },
                    "drivers": {
                        "QEMUDriver": {
                            "qemu_bin": "qemu",
                            "machine": MACHINE,
                            "cpu": emulator.cpu,
                            "memory": emulator.memory,
                            "bios": "bios",
                            "dtb": "dtb",
                            "extra_args": " ".join(arguments),
                        },
                        # The first boot of a slot creates dropbear's
                        # host keys, which takes a while under TCG,
                        # before the first connection is accepted.
                        "SSHDriver": {"connection_timeout": 120.0},
                    },
                },
            },
            "images": {
                "bios": str(directory / FIRMWARE_FILE),
                "dtb": str(directory / DTB_FILE),
            },
            "tools": {"qemu": QEMU},
        }


@dataclass(frozen=True, slots=True)
class Build:
    """The outputs of one build that the emulator boots.

    The build's manifest lists them.
    """

    directory: Path
    board: Board
    image: Path
    firmware: Path

    @classmethod
    def read(cls, directory: Path) -> Self:
        """Find the board, the factory image and the firmware.

        Check both against the manifest.
        """
        images = sorted(directory.glob(FACTORY_IMAGE))
        if len(images) != 1:
            msg = f"expected one {FACTORY_IMAGE} in {directory}, found {len(images)}"
            raise SystemExit(msg)
        manifest = read_json(directory / MANIFEST_FILE, Manifest)
        build = cls(directory, load(manifest.board), images[0], directory / FIRMWARE)
        for path in (build.image, build.firmware):
            name = path.relative_to(directory).as_posix()
            if sha256(path) != manifest.files.get(name):
                msg = f"{name} does not match {directory / MANIFEST_FILE}"
                raise SystemExit(msg)
        return build


def prepare(build: Build, root: Path) -> Path:
    """Build (or reuse) a build's emulator directory and return it."""
    machine = Machine(build.board)
    image_sha256, firmware_sha256 = sha256(build.image), sha256(build.firmware)
    identity = f"{image_sha256} {firmware_sha256} {build.board.model_dump_json()}"
    directory = root / hashlib.sha256(identity.encode()).hexdigest()[:16]
    if not (directory / SOURCE_FILE).is_file():
        root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"{directory.name}.", dir=root))
        disk_file, disk = work / DISK_FILE, BOOT_DISKS[build.board.boot_disk]
        with build.image.open("rb") as source, disk_file.open("wb") as target:
            gunzip_first_member(source, target)
        if disk_file.stat().st_size > disk.size:
            msg = (
                f"{build.image.name} is larger than a"
                f" {disk.size >> 30} GiB {disk.device}"
            )
            raise SystemExit(msg)
        os.truncate(disk_file, disk.size)
        shutil.copyfile(build.firmware, work / FIRMWARE_FILE)

        dtb = work / DTB_FILE
        machine.dump_dtb(dtb, work / FIRMWARE_FILE)
        process.run(
            "fdtput", "-t", "s", str(dtb), "/", "compatible", build.board.board_name
        )
        process.run("fdtput", "-t", "s", str(dtb), "/", "model", build.board.model)
        # Each core's capacity as on the SoC, so that the kernel knows
        # the big cores.
        cpus = sorted(
            (
                node
                for node in process.run("fdtget", "-l", str(dtb), "/cpus").split()
                if "@" in node
            ),
            key=lambda node: int(node.partition("@")[2], 16),
        )
        for node, capacity in zip(cpus, build.board.soc.cores, strict=True):
            process.run(
                "fdtput",
                "-t",
                "u",
                str(dtb),
                f"/cpus/{node}",
                "capacity-dmips-mhz",
                str(capacity),
            )

        source = EmulationSource(
            build=build.directory,
            board=build.board.id,
            image=build.image,
            image_sha256=image_sha256,
            firmware=build.firmware,
            firmware_sha256=firmware_sha256,
        )
        write_json(work / SOURCE_FILE, source)
        shutil.rmtree(directory, ignore_errors=True)
        work.rename(directory)
    description = machine.description(directory)
    (directory / TARGET_FILE).write_text(yaml.safe_dump(description, sort_keys=False))
    return directory


def _current(record: Path) -> bool:
    """Return whether an emulator directory's build still has its files.

    The build is the one the directory was made from.

    A record or a manifest that no longer reads as one names a build
    that changed.
    """
    try:
        source = read_json(record, EmulationSource)
        files = read_json(source.build / MANIFEST_FILE, Manifest).files
    except FileNotFoundError, DataError:
        return False
    return all(
        files.get(path.relative_to(source.build).as_posix()) == digest
        for path, digest in (
            (source.image, source.image_sha256),
            (source.firmware, source.firmware_sha256),
        )
    )


def prune(root: Path) -> None:
    """Remove the emulator directories of changed or gone builds."""
    for record in root.glob(f"*/{SOURCE_FILE}"):
        if not _current(record):
            shutil.rmtree(record.parent)


def main(argv: list[str] | None = None) -> int:
    """emu-prepare: print the emulator directory for a build."""
    parser = argparse.ArgumentParser(prog="emu-prepare", description=main.__doc__)
    parser.add_argument("build", type=Path, help="the output directory of a build")
    parser.add_argument(
        "root", type=Path, help="directory that holds prepared emulators"
    )
    args = parser.parse_args(argv)
    prune(args.root)
    directory = prepare(Build.read(args.build), args.root)
    sys.stdout.write(f"{directory}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
