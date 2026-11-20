"""The emulated board: power, disk snapshots and the serial console.

(design D14, r4s-ab-rollback D7)

``Emulator`` drives the machine that ``emu-prepare``
(orbyt_tests.device.prepare) made a directory for; ``Console`` drains
its serial console.
"""

import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pexpect import TIMEOUT

from orbyt_tests.device.prepare import BOOT_DISK_ID, DISK_FILE, OVERLAY_FILE
from orbyt_tests.model import process
from orbyt_tests.model.poll import until

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from labgrid import Target
    from labgrid.driver import QEMUDriver

# QEMU's own account of the machine, beside the console log: its
# watchdog's actions and the shutdowns it is asked for, with the time,
# so that a reset the console does not explain is named there
# (trial-boot-resilience D5). QEMU writes each run's anew; the session's
# log keeps every run's.
QEMU_LOG = "qemu.log"
QEMU_RUN_LOG = "qemu-run.log"
QEMU_TRACES = ("watchdog_perform_action", "qemu_system_shutdown_request")
UNPLUG_TIMEOUT = 30


class ConsoleEndedError(Exception):
    """The console ended or cannot be read: no more output will come."""


class Console:
    """Drain the serial console for as long as the machine runs.

    QEMU's PL011 writes one byte at a time, and on the labgrid socket
    every byte takes a whole socket-buffer slot, so an unread console
    stalls the guest within a few hundred bytes. A thread reads it
    continuously into memory and a log file; tests wait for console
    output against that record. A console that ends, as QEMU exits, or
    cannot be read ends the waits at once (test-fidelity D12).
    """

    def __init__(self, read: Callable[[int, float], bytes], log: Path) -> None:
        """Read the console with ``read(size, timeout)`` into memory.

        The console is also appended to ``log``.

        ``read`` raises pexpect's TIMEOUT when nothing came, and returns
        nothing once the console has ended.
        """
        self._read = read
        self._log = log
        self._data = bytearray()
        self._changed = threading.Condition()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # Why the console gave out, and the error that did it, if one
        # did.
        self._ended: tuple[str, BaseException | None] | None = None

    def start(self) -> None:
        """Start draining; call after the machine is powered on."""
        self._stop.clear()
        with self._changed:
            self._ended = None
        self._thread = threading.Thread(target=self._drain, name="console", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop draining; call before the machine is powered off."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _drain(self) -> None:
        with self._log.open("ab") as log:
            while not self._stop.is_set():
                try:
                    chunk = self._read(4096, 0.2)
                except TIMEOUT:
                    continue
                # Whatever stops the reading is the waits' to raise:
                # unread, it would end this thread alone, and every wait
                # at its time limit.
                except Exception as error:  # noqa: BLE001
                    self._end("the console cannot be read", error)
                    return
                if not chunk:
                    self._end("the console ended: QEMU closed it", None)
                    return
                log.write(chunk)
                log.flush()
                with self._changed:
                    self._data += chunk
                    self._changed.notify_all()

    def mark(self) -> int:
        """Return the current end of the record.

        wait_for() can search from here.
        """
        with self._changed:
            return len(self._data)

    def text(self, since: int = 0) -> str:
        """Return the console output after ``since``, as text."""
        with self._changed:
            return self._data[since:].decode(errors="replace")

    def _end(self, reason: str, error: BaseException | None) -> None:
        with self._changed:
            self._ended = (reason, error)
            self._changed.notify_all()

    def wait_for(self, pattern: str, *, since: int, timeout: float) -> str:
        """Wait until regex ``pattern`` appears after ``since``.

        Raise ConsoleEndedError at once when the console ended without
        it.
        """
        regex = re.compile(pattern.encode())
        deadline = time.monotonic() + timeout
        with self._changed:
            while (match := regex.search(self._data, since)) is None:
                if self._ended is not None:
                    reason, error = self._ended
                    msg = f"{reason}, without {pattern!r}"
                    raise ConsoleEndedError(msg) from error
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    msg = f"the console never showed {pattern!r}"
                    raise TimeoutError(msg)
                self._changed.wait(remaining)
            return match.group().decode(errors="replace")


@dataclass(frozen=True, slots=True)
class PluggedDisk:
    """A disk plugged in on an emulator xHCI port: image and port."""

    image: Path
    port: int


class Emulator:
    """Power, disk snapshots and serial console of the board."""

    SNAPSHOT = "booted"

    def __init__(self, target: Target, directory: Path, console_log: Path) -> None:
        """Bind to the QEMUDriver of ``target``.

        ``directory`` is the prepared one.
        """
        self.target = target
        self.qemu: QEMUDriver = target.get_driver("QEMUDriver", activate=False)
        self.console = Console(self._read_console, console_log)
        # The machines powered on so far: a limit set on one ends with
        # it.
        self.runs = 0
        self.log = console_log.with_name(QEMU_LOG)
        self.run_log = console_log.with_name(QEMU_RUN_LOG)
        traces = (f"-trace {event}" for event in QEMU_TRACES)
        self.qemu.extra_args = " ".join(
            (str(self.qemu.extra_args), *traces, f"-msg timestamp=on -D {self.run_log}")
        )
        self.disk = directory / DISK_FILE
        self.overlay = directory / OVERLAY_FILE
        # The disks plug_disk() plugged in, by name: they stay through a
        # power cut.
        self.plugged: dict[str, PluggedDisk] = {}

    def reset_disk(self) -> None:
        """Start from the shipped disk again, on a fresh overlay.

        The overlay is copy-on-write.
        """
        process.run(
            "qemu-img",
            *("create", "-q", "-f", "qcow2"),
            *("-b", str(self.disk), "-F", "raw", str(self.overlay)),
        )

    def _read_console(self, size: int, timeout: float) -> bytes:
        # _read is the console primitive every labgrid console driver
        # implements; read() would record each call as a test step.
        return cast("bytes", self.qemu._read(size=size, timeout=timeout))  # noqa: SLF001

    def power_on(self) -> None:
        """Start the machine and drain its console.

        The disks plugged in are plugged in again: QEMU starts anew,
        without the devices added while it ran, where a power cut leaves
        a disk in its port (test-fidelity D17).
        """
        self.target.activate(self.qemu)
        self.qemu.on()
        self.runs += 1
        for name, disk in self.plugged.items():
            self._attach(name, disk)
        self.console.start()

    def power_cut(self) -> None:
        """Kill the machine without any shutdown.

        The disk keeps what was written.
        """
        self.console.stop()
        self.qemu.off()
        if self.run_log.exists():
            with self.log.open("a", encoding="utf-8") as log:
                log.write(self.run_log.read_text(encoding="utf-8"))
            self.run_log.unlink()

    def logged(self) -> str:
        """Return what QEMU logged in this session.

        That includes the running machine's log.
        """
        return "".join(
            path.read_text(encoding="utf-8")
            for path in (self.log, self.run_log)
            if path.exists()
        )

    def _monitor(self, command_line: str) -> None:
        # HMP reports failures as output text, not as a QMP error.
        output = str(
            self.qemu.monitor_command(
                "human-monitor-command", {"command-line": command_line}
            )
        )
        if output.strip():
            msg = f"{command_line}: {output.strip()}"
            raise RuntimeError(msg)

    def save(self) -> None:
        """Snapshot memory and disk of the running machine."""
        self._monitor(f"savevm {self.SNAPSHOT}")

    def restore(self) -> None:
        """Return to the snapshot taken by save()."""
        self._monitor(f"loadvm {self.SNAPSHOT}")

    def _limit_writes(self, bps: int) -> None:
        limits = dict.fromkeys(("bps", "bps_rd", "iops", "iops_rd", "iops_wr"), 0)
        self.qemu.monitor_command(
            "block_set_io_throttle", {"id": BOOT_DISK_ID, "bps_wr": bps, **limits}
        )

    @contextmanager
    def throttled_writes(self, bps: int) -> Generator[None]:
        """Limit boot disk writes to ``bps`` bytes/s in the block.

        The limit ends with the context, however it ends, or with the
        power cut that ends the QEMU holding it (test-fidelity D11).
        """
        run = self.runs
        self._limit_writes(bps)
        try:
            yield
        finally:
            if self.runs == run and self.qemu.status:
                self._limit_writes(0)

    def write_limit(self) -> int:
        """Return the boot disk's write limit in bytes per second.

        Return 0 for none.
        """
        blocks = cast("list[dict[str, Any]]", self.qemu.monitor_command("query-block"))
        # A device's qdev is its id, or its QOM path, which holds the
        # id.
        (disk,) = (
            block
            for block in blocks
            if BOOT_DISK_ID in block.get("qdev", "").split("/")
        )
        return int(disk["inserted"]["bps_wr"])

    def send_keys(self, text: str) -> None:
        """Type on the serial console."""
        self.qemu.write(text.encode())

    def plug_disk(self, name: str, image: Path, port: int) -> None:
        """Plug ``image`` in as a USB SSD on xHCI port ``port``.

        The disk is UAS, as the boards' data disks are.

        The disk's SCSI product name is ``name``, which the guest shows
        as its model. The machine's snapshot holds no such disk (a raw
        image takes no internal snapshot), so a disk must be unplugged
        before the machine is restored.
        """
        disk = PluggedDisk(image, port)
        self._attach(name, disk)
        self.plugged[name] = disk

    def _attach(self, name: str, disk: PluggedDisk) -> None:
        file = {"driver": "file", "filename": str(disk.image)}
        self.qemu.monitor_command(
            "blockdev-add", {"driver": "raw", "node-name": name, "file": file}
        )
        uas = {
            "driver": "usb-uas",
            "id": f"{name}-uas",
            "bus": "xhci.0",
            "port": str(disk.port),
        }
        self.qemu.monitor_command("device_add", uas)
        scsi = {
            "driver": "scsi-hd",
            "id": f"{name}-hd",
            "bus": f"{name}-uas.0",
            "drive": name,
            "product": name,
        }
        self.qemu.monitor_command("device_add", scsi)
        # A hot-plugged usb-uas waits for its disk: only now it appears
        # on the port.
        self.qemu.monitor_command(
            "qom-set",
            {
                "path": f"/machine/peripheral/{name}-uas",
                "property": "attached",
                "value": True,
            },
        )

    def unplug_disk(self, name: str) -> None:
        """Pull a disk plug_disk() plugged in."""
        del self.plugged[name]
        self.qemu.monitor_command("device_del", {"id": f"{name}-uas"})
        # The drive is free once the disk device has let it go, which
        # QEMU finishes a little after the device is gone.
        until(
            lambda: not self._drive_in_use(name),
            timeout=UNPLUG_TIMEOUT,
            every=0.2,
            what=f"unplug of {name}",
        )
        self.qemu.monitor_command("blockdev-del", {"node-name": name})

    def _drive_in_use(self, name: str) -> bool:
        """Return whether a block backend still holds drive ``name``."""
        blocks = self.qemu.monitor_command("query-block")
        return any(
            block.get("inserted", {}).get("node-name") == name for block in blocks
        )
