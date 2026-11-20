"""firmware/boot-rollback: the boot slot's choice and its rollback.

U-Boot picks the slot, counts trial boots and rolls back.
"""

import re
import shlex
import time
from pathlib import Path
from typing import TYPE_CHECKING

from orbyt_tests import spec
from orbyt_tests.device.ab import (
    BOOT_DISK,
    ENV_COPIES,
    ENV_SIZE,
    getenv,
    newest_env_copy,
    partition,
    region_sha256,
    setenv,
    slot,
    slot_sha256,
)
from orbyt_tests.device.emu import extract_fit_image, read_fit, run
from orbyt_tests.model.image import SECTOR, default_environment, read_mbr

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router
    from orbyt_tests.model.boards import Board

CAPABILITY = "firmware/boot-rollback"
UBOOT_DIR = Path(__file__).resolve().parents[2] / "uboot"
UBOOT_SECTOR = 16384
UBOOT_BANNER = r"U-Boot 20\d\d\.\d\d"
# How long the console stays silent at U-Boot's prompt to show that it
# stays: a reset would print U-Boot's banner again within seconds.
PROMPT_STAYS = 30
# Variables U-Boot itself defines for the slot logic, besides those of
# orbyt-ab.env.
LOGIC = ("bootcmd", "altbootcmd", "bootlimit")
# The variables a stored environment may set, as both bootloaders' flags
# list names them: the slot logic's state alone.
WRITABLE = '"boot_slot:sw,bootcount:dw,upgrade_available:dw"'
UPGRADE_IMAGE = "/tmp/sysupgrade.tar.gz"  # noqa: S108 (a path on the router)
BOOT_LIMIT = 3
PANIC_REBOOT = 10.0
# A stored boot command, which the bootloader must ignore.
HIJACK = "echo orbyt-hijacked"
# A trial deadline short enough for three hung boots in a test.
TRIAL_DEADLINE = 60
# A uci-defaults script, which the boot script S10boot runs, and an
# upgrade carries.
HANG = "/etc/uci-defaults/95-orbyt-test-hang"


def _names(env_file: Path) -> set[str]:
    """Return the variables an environment source file defines."""
    return set(re.findall(r"^([A-Za-z_]\w*)=", env_file.read_text(), re.MULTILINE))


def _trial(router: Router) -> None:
    """Put the running slot in the trial state.

    The health check is disabled, so it stays out of the way.
    """
    router.run("/etc/init.d/orbyt-healthcheck disable")
    setenv(router, boot_slot=slot(router), upgrade_available=1, bootcount=0)


def _env_sha256(router: Router) -> str:
    """Return the checksums of both copies of the environment."""
    return ",".join(
        region_sha256(router, BOOT_DISK, offset, offset + ENV_SIZE)
        for offset in ENV_COPIES
    )


def _corrupt(router: Router, offset: int) -> None:
    """Corrupt the environment's copy at ``offset``.

    Overwrite its CRC and its first variables.
    """
    router.run(
        f"dd if=/dev/urandom of={BOOT_DISK} bs=64"
        f" seek={offset // 64} count=1 conv=fsync"
    )


def _config(path: Path) -> dict[str, str]:
    """Return the options a Kconfig configuration sets."""
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line.startswith("CONFIG_")
    )


def _board_uboot(emulation_dir: Path, tmp_path: Path) -> tuple[Path, Path]:
    """Extract the U-Boot the factory image ships.

    Return its binary and its control device tree.
    """
    disk = emulation_dir / "disk.raw"
    with disk.open("rb") as raw:
        first = read_mbr(raw.read(SECTOR)).partitions[0].start
        raw.seek(UBOOT_SECTOR * SECTOR)
        itb = tmp_path / "u-boot.itb"
        itb.write_bytes(raw.read(first - UBOOT_SECTOR * SECTOR))
    fit = read_fit(itb)
    binary, dtb = tmp_path / "u-boot.bin", tmp_path / "u-boot.dtb"
    extract_fit_image(itb, fit.images["u-boot"], binary)
    extract_fit_image(itb, fit.selected("FDT"), dtb)
    return binary, dtb


@spec(CAPABILITY, "Slot selection from a persistent variable", "Select slot B")
def test_boot_slot_b(router: Router) -> None:
    setenv(router, boot_slot="b")
    router.reboot()
    assert slot(router) == "b"
    root = router.run(
        "sed -n 's/.*root=PARTUUID=\\([0-9a-f-]*\\).*/\\1/p' /proc/cmdline"
    )
    assert root.endswith("-04")
    assert router.run("awk '$2 == \"/rom\" { print $1 }' /proc/mounts") in {
        "/dev/root",
        partition(4),
    }


@spec(
    CAPABILITY,
    "Slot selection from a persistent variable",
    "Persistent variable missing or corrupted",
)
def test_corrupted_environment_boots_slot_a(router: Router) -> None:
    setenv(router, boot_slot="b")
    # Both copies corrupted: U-Boot falls back to its defaults.
    for offset in ENV_COPIES:
        _corrupt(router, offset)
    router.reboot()
    assert slot(router) == "a"


@spec(
    CAPABILITY,
    "Slot selection from a persistent variable",
    "Environment write cut short",
)
def test_cut_short_write_keeps_the_previous_state(router: Router) -> None:
    running = slot(router)
    _trial(router)
    # The confirmation, cut short: the copy it went to is corrupted, as
    # a reset in the middle of writing it leaves it.
    setenv(router, upgrade_available=0)
    _corrupt(router, newest_env_copy(router))
    router.reboot()
    # The trial as it was before: counted on, on the same slot.
    assert slot(router) == running
    assert (getenv(router, "upgrade_available"), getenv(router, "bootcount")) == (
        "1",
        "1",
    )


@spec(
    CAPABILITY,
    "The system writes the environment where the bootloader reads it",
    "The environment where the bootloader names it",
)
def test_the_environment_is_where_the_bootloader_names_it(router: Router) -> None:
    named = re.search(r"(?:^| )orbyt\.env=(\S+)", router.run("cat /proc/cmdline"))
    assert named is not None
    copies = [
        tuple(int(part, 16) for part in copy.split("@")) for copy in named[1].split(",")
    ]
    assert copies == [(ENV_SIZE, offset) for offset in ENV_COPIES]
    configured = [
        (device, int(offset, 16), int(size, 16))
        for device, offset, size, *_ in map(
            str.split, router.run("cat /etc/fw_env.config").splitlines()
        )
    ]
    assert configured == [(BOOT_DISK, offset, ENV_SIZE) for offset in ENV_COPIES]
    setenv(router, orbyt_probe="written")
    assert getenv(router, "orbyt_probe") == "written"


@spec(
    CAPABILITY,
    "The system writes the environment where the bootloader reads it",
    "A bootloader that names no environment",
)
def test_no_upgrade_without_the_bootloader_s_environment(
    router: Router, upgrade_image: Path
) -> None:
    named = router.run(
        "ucode -e \"import { environment } from 'orbyt.ab';"
        " printf('%J', environment('root=PARTUUID=x rw orbyt.slot=a'));\""
    )
    assert named == "null"
    # What a bootloader without orbyt.env= leaves: no configuration.
    router.run(
        "while uci -q delete ubootenv.@ubootenv[0]; do :; done && uci commit ubootenv"
        " && rm /etc/fw_env.config"
    )
    other = "b" if slot(router) == "a" else "a"
    before = slot_sha256(router, other)
    router.put(upgrade_image, UPGRADE_IMAGE)
    refused = router.run(f"sysupgrade {UPGRADE_IMAGE} 2>&1 || echo refused")
    assert "names no U-Boot environment" in refused
    assert refused.endswith("refused")
    assert slot_sha256(router, other) == before


@spec(
    CAPABILITY,
    "The system writes the environment where the bootloader reads it",
    "The environment at the first boot script",
)
def test_the_first_boot_script_reads_the_environment(
    router: Router, upgrade_image: Path
) -> None:
    other = "b" if slot(router) == "a" else "a"
    router.put(upgrade_image, UPGRADE_IMAGE)
    previous_boot = router.boot_id()
    # No configuration kept: nothing carries the environment's access
    # over.
    router.detach(f"sysupgrade -n {UPGRADE_IMAGE}")
    router.wait_rebooted(previous_boot)
    assert slot(router) == other
    # orbyt-trial, the first boot script, names the trial only when it
    # read it.
    assert f"orbyt-trial: slot {other} is on trial" in router.run("dmesg")


@spec(
    CAPABILITY,
    "Persistent environment cannot override boot logic",
    "Custom boot command in persistent environment",
)
def test_stored_boot_command_is_ignored(router: Router) -> None:
    console = router.emulator.console
    since = console.mark()
    setenv(router, boot_slot="b", bootcmd=HIJACK, orbyt_boot=HIJACK)
    # The boot that follows reads an environment that holds them.
    assert (getenv(router, "bootcmd"), getenv(router, "orbyt_boot")) == (HIJACK, HIJACK)
    router.reboot()
    assert slot(router) == "b"
    assert "orbyt-hijacked" not in console.text(since)


@spec(
    CAPABILITY,
    "Trial boot counting and automatic rollback",
    "New slot fails repeatedly",
)
def test_rollback_after_three_unconfirmed_boots(
    router: Router, upgrade_image: Path
) -> None:
    # The new slot inherits a configuration that keeps its web server
    # off the LAN, so its health check fails every time, quickly.
    router.run(
        "uci set uhttpd.main.listen_http=127.0.0.1:80"
        " && uci set orbyt-ab.healthcheck.total=10"
        " && uci set orbyt-ab.healthcheck.interval=5"
        " && uci commit"
    )
    console = router.emulator.console
    since = console.mark()
    router.put(upgrade_image, UPGRADE_IMAGE)
    router.detach(f"sysupgrade {UPGRADE_IMAGE}")
    console.wait_for(rf"Bootlimit \({BOOT_LIMIT}\) exceeded", since=since, timeout=1800)
    router.wait_ssh()
    router.wait_ready()
    assert slot(router) == "a"
    assert (getenv(router, "boot_slot"), getenv(router, "upgrade_available")) == (
        "a",
        "0",
    )
    assert getenv(router, "bootcount") == "0"
    # The failed slot booted exactly bootlimit times after the upgrade.
    assert len(re.findall(r"orbyt\.slot=b", console.text(since))) == BOOT_LIMIT


@spec(
    CAPABILITY,
    "Hangs and panics become reboots",
    "A boot script hangs during a trial boot",
)
def test_a_hung_trial_boot_rolls_back(router: Router, upgrade_image: Path) -> None:
    running = slot(router)
    other = "b" if running == "a" else "a"
    # A boot script that never returns on the trial slot, before the
    # health check starts; on the original slot it ends at once and
    # goes, as uci-defaults do.
    hang = "\n".join(
        (
            ". /lib/functions/orbyt-ab.sh",
            f'[ "$(orbyt_ab_slot)" = {other} ] || exit 0',
            "while :; do sleep 3600; done",
        )
    )
    router.run(
        f"printf '%s\\n' {shlex.quote(hang)} >{HANG}"
        f" && echo {HANG} >>/etc/sysupgrade.conf"
        " && uci set orbyt-ab.trial=trial"
        f" && uci set orbyt-ab.trial.deadline={TRIAL_DEADLINE}"
        " && uci commit orbyt-ab"
    )
    console = router.emulator.console
    since = console.mark()
    router.put(upgrade_image, UPGRADE_IMAGE)
    router.detach(f"sysupgrade {UPGRADE_IMAGE}")
    console.wait_for(rf"Bootlimit \({BOOT_LIMIT}\) exceeded", since=since, timeout=1800)
    router.wait_ssh()
    router.wait_ready()
    assert slot(router) == running
    assert (getenv(router, "boot_slot"), getenv(router, "upgrade_available")) == (
        running,
        "0",
    )
    text = console.text(since)
    assert len(re.findall(rf"orbyt\.slot={other}", text)) == BOOT_LIMIT
    reboots = re.findall(rf"orbyt-trial: slot {other}: .*; rebooting", text)
    assert len(reboots) == BOOT_LIMIT, reboots


@spec(
    CAPABILITY,
    "Trial boot counting and automatic rollback",
    "No counting during normal operation",
)
def test_confirmed_boot_writes_nothing(router: Router) -> None:
    assert getenv(router, "upgrade_available") in {None, "0"}
    before = (_env_sha256(router), getenv(router, "bootcount"))
    router.reboot()
    assert (_env_sha256(router), getenv(router, "bootcount")) == before


@spec(
    CAPABILITY,
    "Trial boot counting and automatic rollback",
    "Current slot fails to load",
)
def test_fallback_within_one_power_cycle(router: Router) -> None:
    emulator = router.emulator
    router.run(f"mount {partition(3)} /mnt && rm /mnt/kernel.img && umount /mnt")
    setenv(router, boot_slot="b")
    router.reboot()
    assert slot(router) == "a"
    assert getenv(router, "boot_slot") == "b"
    # With neither slot loadable U-Boot gives up at its prompt, and
    # stays there.
    router.run(
        f"mount {partition(1)} /mnt && rm /mnt/kernel.img && umount /mnt && sync"
    )
    since = emulator.console.mark()
    router.detach("reboot")
    emulator.console.wait_for(
        "neither slot boots, stopping at the prompt", since=since, timeout=300
    )
    prompt = emulator.console.mark()
    time.sleep(PROMPT_STAYS)
    assert not re.search(UBOOT_BANNER, emulator.console.text(prompt))


@spec(CAPABILITY, "Hangs and panics become reboots", "Kernel panic")
def test_panic_reboots_and_counts(router: Router) -> None:
    _trial(router)
    console = router.emulator.console
    previous_boot = router.boot_id()
    since = console.mark()
    router.detach("echo c > /proc/sysrq-trigger")
    console.wait_for(r"Kernel panic", since=since, timeout=60)
    panicked = time.monotonic()
    console.wait_for(UBOOT_BANNER, since=console.mark(), timeout=15)
    assert time.monotonic() - panicked < PANIC_REBOOT
    router.wait_rebooted(previous_boot)
    assert getenv(router, "bootcount") == "1"


@spec(
    CAPABILITY,
    "Hangs and panics become reboots",
    "Userspace stops feeding the watchdog",
)
def test_watchdog_resets_a_hung_userspace(router: Router) -> None:
    _trial(router)
    previous_boot = router.boot_id()
    router.run("ubus call system watchdog '{\"stop\": true}'")
    router.wait_rebooted(previous_boot)
    assert slot(router) == "a"
    assert getenv(router, "bootcount") == "1"


@spec(CAPABILITY, "Hangs and panics become reboots", "Watchdog armed before the kernel")
def test_watchdog_chain_configuration(
    build_output: Path, emulation_dir: Path, tmp_path: Path
) -> None:
    uboot = (build_output / "u-boot.config").read_text().splitlines()
    for line in (
        "CONFIG_WDT=y",
        "CONFIG_WATCHDOG_AUTOSTART=y",
        "CONFIG_WATCHDOG_TIMEOUT_MSECS=60000",
        "CONFIG_DESIGNWARE_WATCHDOG=y",
    ):
        assert line in uboot, line
    kernel = (build_output / "kernel.config").read_text().splitlines()
    for line in ("CONFIG_DW_WATCHDOG=y", "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y"):
        assert line in kernel, line
    binary, _ = _board_uboot(emulation_dir, tmp_path)
    assert (
        "watchdog.open_timeout=90"
        in default_environment(binary.read_bytes(), "orbyt_boot")["orbyt_boot"]
    )


@spec(
    CAPABILITY,
    "Same slot logic on the device and in the emulator",
    "Compare the two bootloaders",
)
def test_same_logic_in_both_bootloaders(
    board: Board, build_output: Path, emulation_dir: Path, tmp_path: Path
) -> None:
    binary, dtb = _board_uboot(emulation_dir, tmp_path)
    shipped = default_environment(binary.read_bytes(), "orbyt_boot")
    qemu = default_environment(
        (build_output / "u-boot-qemu.bin").read_bytes(), "orbyt_boot"
    )
    shared = _names(UBOOT_DIR / "orbyt-ab.env") | set(LOGIC)
    constants = _names(UBOOT_DIR / f"board-{board.id}.env")
    assert constants == _names(UBOOT_DIR / "board-qemu.env")
    assert {name: shipped[name] for name in shared} == {
        name: qemu[name] for name in shared
    }
    assert constants <= shipped.keys() & qemu.keys()
    # Each keeps both copies of its environment at the shared offsets of
    # the MMC device its constants boot from...
    for name, environment in (("u-boot.config", shipped), ("u-boot-qemu.config", qemu)):
        config = _config(build_output / name)
        assert config.get("CONFIG_ENV_IS_IN_MMC") == "y", name
        assert int(config["CONFIG_ENV_MMC_DEVICE_INDEX"]) == int(
            environment["orbyt_mmc"]
        ), name
        assert config.get("CONFIG_ENV_REDUNDANT") == "y", name
        offsets = (config["CONFIG_ENV_OFFSET"], config["CONFIG_ENV_OFFSET_REDUND"])
        assert tuple(int(offset, 16) for offset in offsets) == ENV_COPIES, name
        assert int(config["CONFIG_ENV_SIZE"], 16) == ENV_SIZE, name
        # The stored environment sets the slot logic's state and nothing
        # else.
        assert config.get("CONFIG_ENV_WRITEABLE_LIST") == "y", name
        assert config.get("CONFIG_ENV_FLAGS_LIST_STATIC") == WRITABLE, name
    # ...which the board's device tree makes its boot disk's controller:
    # an eMMC is soldered on, an SD card is not.
    assert run("fdtget", str(dtb), "/", "compatible").split()[0] == board.board_name
    controller = run(
        "fdtget", str(dtb), "/aliases", f"mmc{shipped['orbyt_mmc']}"
    ).strip()
    properties = run("fdtget", "-p", str(dtb), controller).split()
    assert ("non-removable" in properties) == (board.boot_disk == "emmc"), controller
