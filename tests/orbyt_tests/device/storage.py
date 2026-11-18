"""The USB data disk in the emulator (r4s-services D1, D10).

A disk is a sparse raw image on the runner that the tests plug into the
emulator's xHCI controller as a UAS device. The router shows its SCSI
product name as the disk's model, which is how the tests find its block
device. ``initialize`` runs ``orbyt-data init`` as an administrator
would: the device, then its name typed again to confirm. ``announce``
has the kernel announce the disk's block device again, added or removed,
as a plug or an unplug does, while the disk stays attached.
"""

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from orbyt_tests.model.poll import until

if TYPE_CHECKING:
    from pathlib import Path

    from orbyt_tests.device.emu import Emulator
    from orbyt_tests.device.router import Router

MOUNT = "/mnt/data"
# The boot disk's own directory under the mount point: the overlay's
# upper layer.
BOOT_DISK = f"/overlay/upper{MOUNT}"
SUBVOLUMES = ("containers", "downloads", "shares", "logs")
# Sparse: only what the router writes takes space on the runner.
SIZE = 8 << 30
PLUG_TIMEOUT = 60
INIT_TIMEOUT = 120


@dataclass
class Disk:
    """A USB SSD of the emulator: a sparse image, plugged in or not."""

    emulator: Emulator
    name: str
    image: Path
    port: int | None = None

    @classmethod
    def blank(cls, emulator: Emulator, directory: Path, name: str) -> Self:
        """Create a blank disk named ``name``.

        The name has at most 16 characters: it is a SCSI product.
        """
        image = directory / f"{name}.raw"
        with image.open("xb") as file:
            file.truncate(SIZE)
        return cls(emulator, name, image)

    def plug(self, port: int) -> None:
        """Plug the disk in on xHCI port ``port``."""
        self.emulator.plug_disk(self.name, self.image, port)
        self.port = port

    def unplug(self) -> None:
        """Pull the disk out, if it is plugged in."""
        if self.port is not None:
            self.emulator.unplug_disk(self.name)
            self.port = None

    @property
    def blank_still(self) -> bool:
        """Whether nothing was ever written to the disk.

        Its image has no blocks yet.
        """
        return self.image.stat().st_blocks == 0


def _models(disk: Disk) -> str:
    """Return the command that lists ``disk``'s model files.

    They are the model files of the disk's block devices.
    """
    # The SCSI model is padded with spaces.
    return (
        f"grep -l {shlex.quote(f'^{disk.name} *$')} /sys/block/sd*/device/model || true"
    )


def device(router: Router, disk: Disk) -> str:
    """Wait for ``disk``'s block device on the router; return it."""
    model = until(
        lambda: router.run(_models(disk)),
        timeout=PLUG_TIMEOUT,
        what=f"{disk.name}'s block device",
    )
    return f"/dev/{model.split('/')[3]}"


def removed(router: Router, disk: Disk) -> None:
    """Wait until ``disk``'s block device is gone from the router.

    The disk was pulled out first.

    The kernel lets a USB disk go a little after QEMU has: until then,
    device() could take the old block device for the one of the next
    plug (test-fidelity D8).
    """
    until(
        lambda: router.run(_models(disk)) == "",
        timeout=PLUG_TIMEOUT,
        what=f"{disk.name}'s block device gone",
    )


def announce(router: Router, disk: Disk, action: str) -> None:
    """Have the kernel announce ``action`` (add, remove) for ``disk``.

    The announcement is for the disk's block device.

    The hotplug handlers then mount or unmount it as they do for a plug
    or an unplug; a removal is preceded by a sync, as nothing can write
    to it after.
    """
    name = device(router, disk).removeprefix("/dev/")
    router.run(f"sync && echo {shlex.quote(action)} >/sys/class/block/{name}/uevent")


def boot_disk_entries(router: Router) -> list[str]:
    """Return what the boot disk holds at the data mount point."""
    return router.run(f"ls -A {BOOT_DISK} 2>/dev/null || true").split()


def mount_options(router: Router) -> set[str] | None:
    """Return the data disk's mount options, or None if unmounted."""
    options = router.run(
        f'awk \'$2 == "{MOUNT}" && $3 == "btrfs" {{ print $4 }}\' /proc/mounts'
    )
    return set(options.split(",")) if options else None


def wait_mounted(router: Router) -> set[str]:
    """Wait until the data disk is mounted; return its mount options."""
    return until(
        lambda: mount_options(router), timeout=PLUG_TIMEOUT, what=f"{MOUNT} mounted"
    )


def initialize(router: Router, disk: Disk, answer: str | None = None) -> int:
    """Run ``orbyt-data init`` on ``disk``; return its exit status.

    It answers the command's question.

    The answer is the device's own name unless ``answer`` says
    otherwise.
    """
    path = device(router, disk)
    typed = shlex.quote(path if answer is None else answer)
    return router.returncode(
        f"echo {typed} | orbyt-data init {path}", timeout=INIT_TIMEOUT
    )


def subvolumes(router: Router) -> set[str]:
    """Return the data disk's subvolume paths, relative to its top."""
    listing = router.run(f"btrfs subvolume list {MOUNT}")
    return {line.split(" path ", 1)[1] for line in listing.splitlines()}
