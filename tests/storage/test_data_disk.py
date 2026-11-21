"""storage/data-disk: the USB data disk and its dependents.

The tests cover what waits for the disk and what goes on without it.

The module's data disk is a blank image made the data disk with
``orbyt-data init`` (the ``data_disk`` fixture); the app Pod is declared
on it, so that the container service has something to start. A spare
disk comes and goes for the tests that need a second one. Each test asks
for the state it needs, the disk in (``pod``) or a boot without it
(``without_disk``), and the fixture brings the router there from
whatever state the test before left: the tests without the disk share
one boot while it stays out, and a test with the disk after them has it
plugged back in, as a disk that comes late is. The data disk is pulled
out only while the router is off, as a disk is best moved: pulled out
while in use, it would lose what was not written out yet.
"""

import json
import re
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from orbyt_tests import spec
from orbyt_tests.device.paths import HEALTH_RESULT, scratch
from orbyt_tests.device.storage import (
    MOUNT,
    PLUG_TIMEOUT,
    SUBVOLUMES,
    Disk,
    announce,
    boot_disk_entries,
    device,
    initialize,
    mount_options,
    removed,
    subvolumes,
    wait_mounted,
)
from orbyt_tests.model.poll import until
from orbyt_tests.model.repository import REPO_DIR
from orbyt_tests.sandbox.net import DIRECT_NAME, DIRECT_TARGET, PROXIED_TARGET, PROXY
from orbyt_tests.services import app
from orbyt_tests.services.datapath import (
    PROXY_TIMEOUT,
    proxy_pid,
    proxy_start,
    proxy_stop,
    wait_proxy,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from orbyt_tests.device.emu import Emulator
    from orbyt_tests.device.router import Router
    from orbyt_tests.services.datapath import Online

CAPABILITY = "storage/data-disk"
SERVICES_DOC = REPO_DIR / "docs" / "services.md"
LOG = f"{MOUNT}/logs/messages"
SNAPSHOTS = f"{MOUNT}/.snapshots"
SNAPSHOTTED = ("containers", "shares")
KEEP_DAYS = 7
DAYS_RUN = 9  # more than eight days
# The days the system stays off, more than the snapshots' week.
DAYS_OFF = 10
CRONTAB = "/etc/crontabs/root"
CRON_TIMEOUT = 90
HEALTHCHECK = (
    "uci set orbyt-ab.healthcheck.total=30 && uci set orbyt-ab.healthcheck.interval=3"
    " && uci commit orbyt-ab && orbyt-healthcheck"
)
# honk's state database, in its data directory on the data disk or in
# RAM (/var/lib/honk, which the kernel names by /var's target, /tmp).
PROXY_STATE = {
    "data disk": f"{MOUNT}/honk/state/honk.db",
    "RAM": scratch("lib/honk/state/honk.db"),
}


def _disk_in(online: Online, disk: Disk) -> Online:
    """Plug the data disk back in if a test left it out; return online.

    The disk is then mounted, with the app Pod on it running.
    """
    if disk.port is None:
        disk.plug(1)
        wait_mounted(online.router)
        app.wait_running(online.router)
    return online


@pytest.fixture
def pod(app_pod: Online, data_disk: Disk) -> Online:
    """Return the module's router online, the data disk in.

    The app Pod is on its data disk.
    """
    return _disk_in(app_pod, data_disk)


@pytest.fixture
def spare(emulator: Emulator, tmp_path: Path) -> Iterator[Disk]:
    """Provide a second blank disk, pulled out after the test."""
    disk = Disk.blank(emulator, tmp_path, "spare")
    yield disk
    disk.unplug()


@pytest.fixture(scope="module")
def rebooted(app_pod: Online, data_disk: Disk) -> str:
    """Log a line persistently, then reboot; return the line."""
    pod = _disk_in(app_pod, data_disk)
    router = pod.router
    line = f"before the reboot {time.time_ns()}"
    router.run(f"logger -t data-disk-test {line!r}")
    until(
        lambda: router.returncode(f"grep -qF {line!r} {LOG}") == 0,
        timeout=30,
        what="the line in the persistent log",
    )
    pod.reboot()
    return line


def _services(router: Router) -> dict[str, bool]:
    """Return which of the services on the data disk run.

    Asking podman itself would have it create its storage wherever the
    data disk is not: a running container is a conmon.
    """
    return {
        "containers": router.returncode("pidof conmon >/dev/null") == 0,
        "file sharing": router.returncode("pidof ksmbd.mountd >/dev/null") == 0,
        "persistent log": router.returncode(f"test -e {LOG}") == 0,
    }


def _proxy_state(router: Router) -> str | None:
    """Return where the running honk keeps its state.

    The place is told by the database honk holds open.
    """
    files = router.run('pid=$(pidof honk-core) && ls -l "/proc/${pid}/fd" || true')
    return next(
        (place for place, path in PROXY_STATE.items() if f"-> {path}" in files), None
    )


def _proxy_on(router: Router, place: str) -> None:
    """Wait until honk has set up its datapath.

    Its state must be in ``place``.
    """
    until(
        lambda: _proxy_state(router) == place,
        timeout=PROXY_TIMEOUT,
        what=f"honk with its state in {place}",
    )
    wait_proxy(router)


def _kept(router: Router) -> dict[str, list[str]]:
    """Return the days of each snapshotted subvolume's snapshots.

    The days are read once cron's job is done. The job runs as a child
    of crond, both of its commands.
    """
    if router.returncode('pgrep -P "$(pidof crond)" >/dev/null') == 0:
        return {}
    return {
        subvolume: [
            path.rsplit("/", 1)[1][:8]
            for path in router.run(f"orbyt-snap list {subvolume}").splitlines()
        ]
        for subvolume in SNAPSHOTTED
    }


@spec(CAPABILITY, "Btrfs data disk and subvolume layout", "Check mounts")
def test_mounts(rebooted: str, pod: Online, spare: Disk) -> None:
    del rebooted  # the boot to check
    router = pod.router
    options = mount_options(router)
    assert options is not None
    assert {"compress=zstd:3", "noatime", "space_cache=v2"} <= options
    assert {*SUBVOLUMES, ".snapshots"} <= subvolumes(router)
    for subvolume in SUBVOLUMES:
        assert (
            router.returncode(f"btrfs subvolume show {MOUNT}/{subvolume} >/dev/null")
            == 0
        )

    # orbyt-data init erases nothing that was not confirmed.
    spare.plug(3)
    assert initialize(router, spare, answer="no") != 0
    assert (
        initialize(router, spare, answer=device(router, spare).removeprefix("/dev/"))
        != 0
    )
    assert spare.blank_still


@spec(CAPABILITY, "Persistent logs on the data disk", "View logs after reboot")
def test_logs_survive_reboot(rebooted: str, pod: Online) -> None:
    router = pod.router
    assert router.returncode(f"cat {LOG}* | grep -qF {rebooted!r}") == 0
    assert router.run("uci get system.@system[0].log_size") == "65536"


@spec(CAPABILITY, "Periodic read-only snapshots", "Manual snapshot")
def test_manual_snapshot(pod: Online) -> None:
    router = pod.router
    before = int(router.run("date +%s"))
    taken = router.run("orbyt-snap now").splitlines()
    after = int(router.run("date +%s"))
    assert [path.split("/")[-2] for path in taken] == list(SNAPSHOTTED)
    for path in taken:
        at = datetime.strptime(path.rsplit("/", 1)[1], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=UTC
        )
        assert before <= at.timestamp() <= after
        assert router.run(f"btrfs property get -ts {path} ro") == "ro=true"
    assert set(router.run("orbyt-snap list").splitlines()) >= set(taken)


@spec(CAPABILITY, "Periodic read-only snapshots", "Restore a file from a snapshot")
def test_restore_a_file(pod: Online) -> None:
    router = pod.router
    commands = _documented_restore()
    (file,) = re.findall(r"^file=(\S+)$", commands, re.MULTILINE)
    content = f"{time.time_ns()}"
    path = f"{MOUNT}/shares/{file}"
    router.run(
        f"mkdir -p {path.rsplit('/', 1)[0]} && echo {content} >{path} && orbyt-snap now"
    )
    router.run(f"rm {path}")
    router.run(commands)
    assert router.run(f"cat {path}") == content


def _documented_restore() -> str:
    """Return docs/services.md's commands for restoring a file."""
    text = SERVICES_DOC.read_text()
    section = text.split("### Restore a file from a snapshot", 1)[1]
    block = re.search(r"```sh\n(.*?)```", section, re.DOTALL)
    assert block is not None
    return str(block.group(1))


@spec(CAPABILITY, "Periodic read-only snapshots", "Expired snapshots are pruned")
def test_expired_snapshots_are_pruned(pod: Online) -> None:
    router = pod.router
    today = datetime.fromtimestamp(int(router.run("date +%s")), UTC).date()
    dates = [today + timedelta(days=day) for day in range(1, DAYS_RUN + 1)]
    days = [f"{date:%Y%m%d}" for date in dates]
    try:
        for date, day in zip(dates, days, strict=True):
            # Half a minute before the daily job (03:17). cron starts
            # afresh at the new time and runs a job only when its minute
            # begins, never late: a restart still running at 03:17:00 on
            # a busy emulator would miss it.
            router.run(
                f"date -u -s '{date} 03:16:30' >/dev/null && /etc/init.d/cron restart"
            )
            until(
                lambda d=day: d in _kept(router).get("shares", []),
                timeout=CRON_TIMEOUT,
                what=f"the daily job of {date}",
            )
    finally:
        router.run(
            f"date -u -s @{int(time.time())} >/dev/null && /etc/init.d/cron restart"
        )
    assert _kept(router) == dict.fromkeys(SNAPSHOTTED, days[-KEEP_DAYS:])


@spec(CAPABILITY, "Data disk identified by UUID", "Move to another USB port")
def test_moves_to_another_port(pod: Online, data_disk: Disk) -> None:
    def move() -> None:
        data_disk.unplug()
        data_disk.plug(2)

    pod.reboot(while_off=move)
    assert mount_options(pod.router) is not None
    assert {*SUBVOLUMES, ".snapshots"} <= subvolumes(pod.router)


@spec(
    CAPABILITY,
    "Dependent services wait for the mount",
    "Data disk removed while in use",
)
def test_nothing_written_without_the_disk_reaches_the_boot_disk(
    pod: Online, data_disk: Disk
) -> None:
    router = pod.router
    announce(router, data_disk, "remove")
    try:
        until(
            lambda: mount_options(router) is None,
            timeout=PLUG_TIMEOUT,
            what=f"{MOUNT} unmounted",
        )
        # As a podman command that outlived the disk recreates its graph
        # root.
        router.run(
            f"mkdir -p {MOUNT}/containers/storage "
            f"&& touch {MOUNT}/containers/storage/file"
        )
        assert boot_disk_entries(router) == []
    finally:
        announce(router, data_disk, "add")
        wait_mounted(router)
    for subvolume in SUBVOLUMES:
        assert (
            router.returncode(f"btrfs subvolume show {MOUNT}/{subvolume} >/dev/null")
            == 0
        )


@pytest.fixture
def without_disk(app_pod: Online, data_disk: Disk, proxy: Online) -> Online:
    """Return the router booted without the data disk, with honk on.

    The tests that need it share the boot while the disk stays out.
    """
    del proxy  # enabled, it starts with the boot
    if data_disk.port is not None:
        app_pod.reboot(while_off=data_disk.unplug)
        wait_proxy(app_pod.router)
    return app_pod


@spec(CAPABILITY, "Degraded mode without the data disk", "Boot without the data disk")
def test_boot_without_the_data_disk(without_disk: Online) -> None:
    router = without_disk.router
    client = without_disk.client()
    assert client.probe("tcp", DIRECT_TARGET[0])["address"] == without_disk.wan_address
    assert client.probe("tcp", PROXIED_TARGET[0])["address"] == PROXY[0]
    resolved = client.probe("resolve", DIRECT_NAME, "--server", router.address)
    assert resolved["answers"] == [DIRECT_TARGET[0]]
    assert mount_options(router) is None
    # The log service restarted without the disk (as any change to the
    # system configuration does) still keeps its file off the boot disk.
    router.run("/etc/init.d/log restart")
    services = _services(router)
    assert not any(services.values()), services
    assert boot_disk_entries(router) == []
    router.run(HEALTHCHECK, timeout=180)
    assert json.loads(router.run(f"cat {HEALTH_RESULT}"))["result"] == "pass"


@spec(
    CAPABILITY, "The proxy's state follows the data disk", "Boot without the data disk"
)
def test_the_proxy_keeps_its_state_in_ram_without_the_data_disk(
    without_disk: Online,
) -> None:
    router = without_disk.router
    _proxy_on(router, "RAM")
    assert without_disk.client().probe("tcp", PROXIED_TARGET[0])["address"] == PROXY[0]
    assert boot_disk_entries(router) == []


@spec(CAPABILITY, "Data disk identified by UUID", "Insert another disk")
def test_other_disk_is_not_mounted(without_disk: Online, spare: Disk) -> None:
    router = without_disk.router
    # The same label as the data disk, and a filesystem of its own
    # (another UUID).
    spare.plug(3)
    router.run(f"mkfs.btrfs -q -f -L orbytdata {device(router, spare)}", timeout=120)
    spare.unplug()
    removed(router, spare)
    spare.plug(3)
    path = device(router, spare)
    until(
        lambda: path in router.run("block info"),
        timeout=PLUG_TIMEOUT,
        what=f"{path} probed",
    )
    router.run("block mount")
    assert mount_options(router) is None
    assert router.returncode(f"grep -q '^{path} ' /proc/mounts") != 0


@spec(CAPABILITY, "Dependent services wait for the mount", "Data disk mounts late")
def test_data_disk_mounts_late(without_disk: Online, data_disk: Disk) -> None:
    router = without_disk.router
    services = _services(router)
    assert not any(services.values()), services
    data_disk.plug(1)
    wait_mounted(router)
    app.wait_running(router)
    until(
        lambda: all(_services(router).values()),
        timeout=app.START_TIMEOUT,
        what="every service on the data disk",
    )
    assert boot_disk_entries(router) == []


@spec(
    CAPABILITY,
    "The proxy's state follows the data disk",
    "Data disk mounted and unmounted",
)
def test_the_proxy_s_state_follows_the_data_disk(
    pod: Online, data_disk: Disk, proxy: Online
) -> None:
    del proxy  # honk on, with its state where the disk is
    router = pod.router
    _proxy_on(router, "data disk")
    announce(router, data_disk, "remove")
    try:
        until(
            lambda: mount_options(router) is None,
            timeout=PLUG_TIMEOUT,
            what=f"{MOUNT} unmounted",
        )
        _proxy_on(router, "RAM")
        assert boot_disk_entries(router) == []
    finally:
        announce(router, data_disk, "add")
        wait_mounted(router)
    _proxy_on(router, "data disk")
    assert pod.client().probe("tcp", PROXIED_TARGET[0])["address"] == PROXY[0]


def _proxy_triggered(router: Router) -> list[dict[str, object]]:
    """Return procd's trigger commands for honk yet to end."""
    return [
        command
        for command in router.trigger_commands()
        if "/etc/init.d/honk" in str(command["command"])
    ]


@spec(
    CAPABILITY,
    "The proxy's state follows the data disk",
    "Proxy stopped as the data disk goes",
)
def test_a_proxy_stopped_as_the_disk_goes_stays_stopped(
    pod: Online, data_disk: Disk, proxy: Online
) -> None:
    del proxy  # honk on, with its state where the disk is
    router = pod.router
    _proxy_on(router, "data disk")
    # honk held still, as a honk slow to shut down is: procd's stop of
    # it waits for its term timeout, through procd's run of the
    # unmount's command.
    router.run("kill -STOP $(pidof honk-core)")
    announce(router, data_disk, "remove")
    try:
        # honk's restart off the disk queued, and honk stopped before
        # procd has run it.
        until(
            lambda: _proxy_triggered(router),
            timeout=PLUG_TIMEOUT,
            every=0.2,
            what="honk's trigger command for the unmount",
        )
        proxy_stop(router)
        until(
            lambda: not _proxy_triggered(router),
            timeout=PROXY_TIMEOUT,
            what="honk's trigger commands run",
        )
        assert not proxy_pid(router)
    finally:
        announce(router, data_disk, "add")
        wait_mounted(router)
        proxy_start(router)


@spec(CAPABILITY, "Periodic read-only snapshots", "Snapshots after a long time off")
def test_snapshots_outlast_a_long_time_off(pod: Online) -> None:
    router = pod.router
    # The daily job's command, as root's crontab runs it.
    (job,) = [
        line.split(maxsplit=5)[5]
        for line in router.run(f"cat {CRONTAB}").splitlines()
        if "orbyt-snap" in line
    ]
    # Other tests may have left snapshots, of days still to come among
    # them: the scenario starts without any.
    router.run(
        f"for s in {SNAPSHOTS}/*/*; "
        'do [ ! -d "$s" ] || btrfs -q subvolume delete "$s"; done'
    )
    today = datetime.fromtimestamp(int(router.run("date +%s")), UTC).date()
    dates = [today + timedelta(days=day) for day in range(1, KEEP_DAYS + 1)]
    back = dates[-1] + timedelta(days=DAYS_OFF + 1)
    try:
        for date in [*dates, back]:
            # Off the job's own minute, so that cron does not run it
            # meanwhile.
            router.run(f"date -u -s '{date} 04:00:00' >/dev/null && {job}", timeout=120)
    finally:
        router.run(f"date -u -s @{int(time.time())} >/dev/null")
    days = [f"{date:%Y%m%d}" for date in [*dates[-(KEEP_DAYS - 1) :], back]]
    assert _kept(router) == dict.fromkeys(SNAPSHOTTED, days)
