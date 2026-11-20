"""firmware/health-check: what makes a boot healthy.

LAN, SSH, the web UI and every registered check make a healthy boot.
"""

import json
import re
from typing import TYPE_CHECKING, cast

from orbyt_tests import spec
from orbyt_tests.device.ab import getenv, setenv, slot
from orbyt_tests.model.poll import until

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router

CAPABILITY = "firmware/health-check"
RESULT = "/var/run/orbyt-healthcheck.json"
CHECKS = "/etc/healthcheck.d"
FAILING = "/tmp/demo-fails"  # noqa: S108 (a path on the router)
# Limits short enough for a test and long enough for a check to fail
# twice. A test sets them without committing them: they hold for the
# health check it runs, which reads the changes in /tmp/.uci, and the
# boot it reboots into checks with the image's limits.
LIMITS = {"total": 6, "interval": 3, "timeout": 3}
QUICK = " && ".join(
    f"uci set orbyt-ab.healthcheck.{name}={value}" for name, value in LIMITS.items()
)
# Limits long enough for a check that fails after the clock was set,
# then passes.
SLOW = {"total": 60, "interval": 3, "timeout": 3}
DAY = 86400
# A directory ahead of the system's on PATH, holding a U-Boot tool that
# fails.
BROKEN = "/tmp/broken-tools"  # noqa: S108 (a path on the router)
# A service that comes up late: its check records each run, and passes
# once the service's mark exists.
LATE_RUNS = "/tmp/late-runs"  # noqa: S108 (a path on the router)
LATE_UP = "/tmp/late-up"  # noqa: S108 (a path on the router)
# Each run of a check that fails until FAILING goes.
DEMO_RUNS = "/tmp/demo-runs"  # noqa: S108 (a path on the router)


def _check(router: Router, broken: str | None = None) -> dict[str, object]:
    """Run the health check with short limits; return what it recorded.

    With ``broken``, that U-Boot tool fails for the health check at
    once, before it reads anything it is given.
    """
    path = ""
    if broken is not None:
        router.run(
            f"mkdir -p {BROKEN} && printf '#!/bin/sh\\nexit 1\\n' >{BROKEN}/{broken}"
            f" && chmod +x {BROKEN}/{broken}"
        )
        path = f"PATH={BROKEN}:$PATH "
    router.run(f"{QUICK} && {path}orbyt-healthcheck", timeout=120)
    return cast("dict[str, object]", json.loads(router.run(f"cat {RESULT}")))


def _register(router: Router, name: str, body: str) -> None:
    """Install a registered check."""
    router.run(
        f"printf '#!/bin/sh\\n%s\\n' '{body}' > {CHECKS}/{name}"
        f" && chmod +x {CHECKS}/{name}"
    )


@spec(CAPABILITY, "Built-in checks", "WAN down, everything else healthy")
def test_wan_is_not_a_criterion(router: Router) -> None:
    router.run("ifdown wan")
    assert json.loads(router.run("ifstatus wan"))["up"] is False
    result = _check(router)
    assert (result["result"], result["failed"]) == ("pass", [])


@spec(CAPABILITY, "Built-in checks", "Web server not up")
def test_web_server_down_fails(router: Router) -> None:
    router.run("/etc/init.d/uhttpd stop")
    result = _check(router)
    assert (result["result"], result["failed"]) == ("fail", ["web"])


@spec(CAPABILITY, "Components can register checks", "Registered check fails")
def test_failing_registered_check(router: Router) -> None:
    _register(router, "demo", "exit 1")
    result = _check(router)
    assert (result["result"], result["failed"]) == ("fail", ["demo"])


@spec(CAPABILITY, "Components can register checks", "Check times out")
def test_slow_registered_check(router: Router) -> None:
    _register(router, "slow", "sleep 600")
    result = _check(router)
    assert (result["result"], result["failed"]) == ("fail", ["slow"])


@spec(
    CAPABILITY, "Result handling by trial boot state", "Check passes during trial boot"
)
def test_pass_confirms_the_slot(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=2)
    assert _check(router)["result"] == "pass"
    assert (getenv(router, "upgrade_available"), getenv(router, "bootcount")) == (
        "0",
        "0",
    )
    router.reboot()
    assert slot(router) == running


@spec(
    CAPABILITY, "Result handling by trial boot state", "Check fails during trial boot"
)
def test_trial_failure_reboots(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    # Fails for this boot only: /tmp starts empty, so the next boot
    # passes and confirms.
    router.run(f"touch {FAILING}")
    _register(router, "demo", f"[ ! -e {FAILING} ]")
    previous_boot = router.boot_id()
    router.detach(f"{QUICK} && orbyt-healthcheck")
    router.wait_rebooted(previous_boot)
    confirmed = f"slot {running} passed its trial boot and is confirmed"
    router.run(
        f"until logread -e orbyt-healthcheck | grep -q '{confirmed}'; do sleep 2; done",
        timeout=300,
    )


@spec(CAPABILITY, "The trial watchdog starts first", "The image's boot scripts")
def test_the_trial_watchdog_is_the_first_boot_script(router: Router) -> None:
    scripts = router.run("ls /etc/rc.d | grep '^S'").split()
    assert scripts[0] == "S00orbyt-trial", scripts


@spec(
    CAPABILITY,
    "The trial watchdog starts first",
    "A service that starts after the health check",
)
def test_a_service_up_after_the_check_began_passes(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    _register(router, "late", f"echo ran >>{LATE_RUNS}; [ -e {LATE_UP} ]")
    limits = " && ".join(
        f"uci set orbyt-ab.healthcheck.{name}={value}" for name, value in SLOW.items()
    )
    router.detach(f"{limits} && orbyt-healthcheck")
    # The service comes up once the health check has found it down.
    until(
        lambda: router.poll(f"cat {LATE_RUNS}"),
        timeout=SLOW["total"],
        what="the health check's first run of the late check",
    )
    router.run(f"touch {LATE_UP}")
    confirmed = f"slot {running} passed its trial boot and is confirmed"
    until(
        lambda: confirmed in (router.poll("logread -e orbyt-healthcheck") or ""),
        timeout=SLOW["total"],
        what="the trial's confirmation",
    )
    # It ran once at least with the service down, then once with it up.
    assert len(router.run(f"cat {LATE_RUNS}").split()) > 1
    assert getenv(router, "upgrade_available") == "0"


@spec(
    CAPABILITY, "Result handling by trial boot state", "Clock set during a trial boot"
)
def test_a_clock_set_forward_does_not_end_a_trial(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    router.run(f"touch {FAILING}")
    _register(router, "demo", f"echo run >>{DEMO_RUNS}; [ ! -e {FAILING} ]")
    limits = " && ".join(
        f"uci set orbyt-ab.healthcheck.{name}={value}" for name, value in SLOW.items()
    )
    previous_boot = router.boot_id()
    router.detach(f"{limits} && orbyt-healthcheck")
    until(
        lambda: (
            router.returncode("pgrep -f /usr/sbin/orbyt-healthcheck >/dev/null") == 0
        ),
        timeout=30,
        what="the health check running",
    )
    # A day forward, as NTP sets a clock that lagged, while the check
    # still fails for two more rounds; then it passes, well within the
    # total time limit.
    router.run(f"date -s @$(($(date +%s) + {DAY})) >/dev/null")
    failed = len((router.poll(f"cat {DEMO_RUNS}") or "").split())
    until(
        lambda: len((router.poll(f"cat {DEMO_RUNS}") or "").split()) >= failed + 2,
        timeout=SLOW["total"],
        what="two more failing rounds of the check",
    )
    router.run(f"rm {FAILING}")
    confirmed = f"slot {running} passed its trial boot and is confirmed"
    router.run(
        f"until logread -e orbyt-healthcheck | grep -q '{confirmed}'; do sleep 1; done",
        timeout=SLOW["total"],
    )
    assert router.boot_id() == previous_boot


@spec(
    CAPABILITY,
    "Result handling by trial boot state",
    "A switch written during the checks",
)
def test_a_switch_written_during_the_checks_stays(router: Router) -> None:
    running = slot(router)
    other = "b" if running == "a" else "a"
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    router.run(f"touch {FAILING}")
    _register(router, "demo", f"[ ! -e {FAILING} ]")
    limits = " && ".join(
        f"uci set orbyt-ab.healthcheck.{name}={value}" for name, value in SLOW.items()
    )
    previous_boot = router.boot_id()
    router.detach(f"{limits} && orbyt-healthcheck")
    until(
        lambda: (
            router.returncode("pgrep -f /usr/sbin/orbyt-healthcheck >/dev/null") == 0
        ),
        timeout=30,
        what="the health check running",
    )
    # The other slot made the trial slot, as orbyt-slot switch writes it
    # before its reboot; then the check passes.
    setenv(router, boot_slot=other, upgrade_available=1, bootcount=0)
    router.run(f"rm {FAILING}")
    left = f"left the switch to slot {other} in place"
    router.run(
        f"until logread -e orbyt-healthcheck | grep -q '{left}'; do sleep 1; done",
        timeout=SLOW["total"],
    )
    assert (getenv(router, "boot_slot"), getenv(router, "upgrade_available")) == (
        other,
        "1",
    )
    assert (
        router.returncode("logread -e orbyt-healthcheck | grep -q 'is confirmed'") != 0
    )
    assert router.boot_id() == previous_boot


@spec(
    CAPABILITY,
    "Result handling by trial boot state",
    "Check fails on a confirmed system",
)
def test_confirmed_failure_only_records(router: Router) -> None:
    assert getenv(router, "upgrade_available") in {None, "0"}
    _register(router, "demo", "exit 1")
    previous_boot = router.boot_id()
    assert _check(router)["result"] == "fail"
    assert router.boot_id() == previous_boot
    assert (
        router.returncode("logread -e orbyt-healthcheck | grep -q 'is unhealthy: demo'")
        == 0
    )


@spec(
    CAPABILITY, "Result handling by trial boot state", "Environment that cannot be read"
)
def test_an_environment_that_cannot_be_read_is_a_failure(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    previous_boot = router.boot_id()
    result = _check(router, broken="fw_printenv")
    assert (result["result"], result["failed"]) == ("fail", ["environment"])
    assert router.boot_id() == previous_boot
    assert (getenv(router, "upgrade_available"), getenv(router, "bootcount")) == (
        "1",
        "0",
    )


@spec(
    CAPABILITY,
    "Result handling by trial boot state",
    "Confirmation that cannot be written",
)
def test_a_confirmation_that_cannot_be_written_is_a_failure(router: Router) -> None:
    running = slot(router)
    setenv(router, boot_slot=running, upgrade_available=1, bootcount=0)
    previous_boot = router.boot_id()
    result = _check(router, broken="fw_setenv")
    assert (result["result"], result["failed"]) == ("fail", ["confirm"])
    assert router.boot_id() == previous_boot
    assert getenv(router, "upgrade_available") == "1"
    assert (
        router.returncode("logread -e orbyt-healthcheck | grep -q 'is confirmed'") != 0
    )


@spec(CAPABILITY, "Slot status query", "Query status")
def test_slot_status(router: Router) -> None:
    _register(router, "demo", "exit 1")
    _check(router)
    status = dict(
        line.split(": ", 1) for line in router.run("orbyt-slot status").splitlines()
    )
    assert status["slot"] == slot(router)
    assert status["state"] == "confirmed"
    assert re.fullmatch(
        r"fail at \d{4}-\d\d-\d\d \d\d:\d\d:\d\d \(failed: demo\)", status["health"]
    )
