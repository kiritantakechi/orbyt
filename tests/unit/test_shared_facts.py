"""Facts the firmware must state in more than one place agree.

A value read at a different time, or in another language, is written
again where it is read; each copy is bound to its source here
(firmware-hygiene D5, D7).
"""

import os
import re
from pathlib import Path

import pytest

from orbyt_tests.device.ab import PARTITIONS
from orbyt_tests.model.repository import FEED_DIR, REPO_DIR

AB = FEED_DIR / "utils" / "orbyt-ab" / "files"
AB_CONFIG = AB / "etc" / "config" / "orbyt-ab"
UBOOT = REPO_DIR / "uboot"
CONFIG = REPO_DIR / "config"
IMAGES = (
    REPO_DIR
    / "patches"
    / "openwrt"
    / "0004-rockchip-A-B-factory-and-single-slot-upgrade-images.patch"
)


def _option(name: str) -> int:
    """Return a numeric option of orbyt-ab's shipped configuration."""
    found = re.search(
        rf"^\toption {name} '(\d+)'$", AB_CONFIG.read_text(), re.MULTILINE
    )
    assert found is not None, name
    return int(found[1])


def test_the_trial_deadline_falls_back_to_the_shipped_one() -> None:
    trial = (AB / "usr" / "sbin" / "orbyt-trial").read_text()
    found = re.search(r"^const DEADLINE = (\d+);$", trial, re.MULTILINE)
    assert found is not None
    assert int(found[1]) == _option("deadline")


def test_the_health_check_falls_back_to_the_shipped_limits() -> None:
    check = (AB / "usr" / "sbin" / "orbyt-healthcheck").read_text()
    fallbacks = dict(re.findall(r"setting\('(\w+)', (\d+)\)", check))
    assert fallbacks.keys() == {"total", "interval", "timeout"}
    for name, value in fallbacks.items():
        assert int(value) == _option(name), name


def test_the_slot_status_states_u_boot_s_boot_limit() -> None:
    status = (AB / "usr" / "sbin" / "orbyt-slot").read_text()
    stated = re.search(r"^const BOOTLIMIT = (\d+);$", status, re.MULTILINE)
    built = re.search(
        r"^CONFIG_BOOTCOUNT_BOOTLIMIT=(\d+)$",
        (UBOOT / "orbyt-ab.config").read_text(),
        re.MULTILINE,
    )
    assert stated is not None
    assert built is not None
    assert stated[1] == built[1]


def test_the_slots_partitions_agree() -> None:
    # U-Boot: slot b boots from 3 and 4, any other from 1 and 2.
    environment = (UBOOT / "orbyt-ab.env").read_text()
    u_boot = re.search(
        r'test "\$\{boot_slot\}" = b; then\s+'
        r"setenv orbyt_bp (\d); setenv orbyt_rp (\d);\s+else\s+"
        r"setenv boot_slot a; setenv orbyt_bp (\d); setenv orbyt_rp (\d);",
        environment,
    )
    assert u_boot is not None
    b_boot, b_root, a_boot, a_root = map(int, u_boot.groups())
    assert {"a": (a_boot, a_root), "b": (b_boot, b_root)} == PARTITIONS
    # The upgrade's shell: the same, slot by slot.
    shell = (AB / "lib" / "functions" / "orbyt-ab.sh").read_text()
    cases = {
        which: (int(boot), int(root))
        for which, boot, root in re.findall(
            r"^\t\t(a|\*)\) echo (\d) (\d) ;;$", shell, re.MULTILINE
        )
    }
    assert {"a": cases["a"], "b": cases["*"]} == PARTITIONS
    # The image: a boot and a root partition for slot A, then slot B.
    images = IMAGES.read_text()
    sizes = re.findall(r'-p "\$\{(BOOT|ROOT)SIZE\}m"', images)
    assert sizes == ["BOOT", "ROOT", "BOOT", "ROOT"]
    assert "for slot in A B; do" in images
    assert [number for which in ("a", "b") for number in PARTITIONS[which]] == list(
        range(1, 5)
    )


@pytest.mark.build_tree
def test_ci_leaves_out_the_kmods_the_kernel_cannot_build() -> None:
    # A kmod whose symbol config/kernel.config leaves out has no module
    # to package: ci.seed excludes exactly those from "every kmod"
    # (firmware-hygiene D7).
    tree = Path(os.environ["ORBYT_WORKDIR"]) / "openwrt"
    left_out = set(
        re.findall(
            r"^# (CONFIG_\w+) is not set$",
            (CONFIG / "kernel.config").read_text(),
            re.MULTILINE,
        )
    )
    kmods = {}
    for definitions in (tree / "package" / "kernel" / "linux" / "modules").glob("*.mk"):
        text = definitions.read_text().replace("\\\n", " ")
        for name, body in re.findall(
            r"^define KernelPackage/(\S+)\n(.*?)^endef", text, re.MULTILINE | re.DOTALL
        ):
            if found := re.search(r"^\s*KCONFIG:=(.*)$", body, re.MULTILINE):
                kmods[name] = set(re.findall(r"CONFIG_\w+", found[1]))
    unbuildable = {name for name, symbols in kmods.items() if symbols & left_out}
    excluded = set(
        re.findall(
            r"^# CONFIG_PACKAGE_kmod-(\S+) is not set$",
            (CONFIG / "ci.seed").read_text(),
            re.MULTILINE,
        )
    )
    assert unbuildable
    assert excluded == unbuildable
