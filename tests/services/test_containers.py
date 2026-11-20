"""services/containers: podman on the data disk.

It sits behind fw4, einat and honk like the LAN.

The app Pod (orbyt_tests.services.app) runs from the test image in the
emulated internet's registry: uhttpd serving a page of the data disk, at
a fixed address. Probes from inside it use busybox's nc against the
probe servers, and its nslookup.
"""

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from orbyt_tests import spec
from orbyt_tests.device.paths import scratch
from orbyt_tests.device.storage import MOUNT
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox.net import DIRECT_TARGET, PROXIED_TARGET, PROXY
from orbyt_tests.sandbox.netprobe import HTTP_PORT, PORT
from orbyt_tests.services import app
from orbyt_tests.services.datapath import (
    EINAT_PORTS,
    PROXY_HOOKS_L2,
    PROXY_NFQUEUE_TABLE,
    hooks,
    proxy_pid,
    wait_proxy,
)

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router
    from orbyt_tests.device.storage import Disk
    from orbyt_tests.sandbox.net import Netns
    from orbyt_tests.sandbox.netprobe import Seen
    from orbyt_tests.services.datapath import Online

CAPABILITY = "services/containers"
STORAGE = f"{MOUNT}/containers/storage"
# How long orbyt-sync may take to give up on a release service it cannot
# reach.
SYNC_TIMEOUT = 300
EXPOSED_PORT = 8080
FIREWALL_TIMEOUT = 30
# Nothing of an app may be in the image (the app containers' spec).
NATIVE_APPS = ("qbittorrent", "libtorrent", "qt6", "qt5", "qtbase")
# podman commands started at once, how many each runs in a row, and how
# often, on a scratch storage whose run root keeps moving
# (podman-at-once.sh beside this module says how).
AT_ONCE = 8
IN_A_ROW = 3
ROUNDS = 10
AT_ONCE_DRIVER = Path(__file__).with_name("podman-at-once.sh")
SCRATCH = "/var/run/concurrency"


@pytest.fixture(scope="module")
def pod(app_pod: Online, proxy: Online) -> Online:
    """Return the router with the app Pod running and honk on.

    Honk splits the Pod's traffic.
    """
    del proxy  # running for the module
    return app_pod


@pytest.fixture(scope="module")
def storage(trusted_ca: Online, data_disk: Disk) -> Online:
    """Return the router trusting the registry, with the data disk."""
    del data_disk  # podman's storage
    return trusted_ca


def _from_container(pod: Online, host: str, port: int = PORT) -> Seen:
    """Ask a probe server about a connection from the app container."""
    output = pod.router.run(f"podman exec {app.CONTAINER} nc {host} {port} </dev/null")
    return cast("Seen", json.loads(output))


def _netns(router: Router) -> str:
    """Return where podman registered the app container's netns."""
    return router.run(
        f"podman inspect --format '{{{{.NetworkSettings.SandboxKey}}}}' {app.CONTAINER}"
    )


def _restart_proxy(router: Router) -> None:
    """Restart honk; return once the new one serves."""
    running = proxy_pid(router)
    router.run("/etc/init.d/honk restart")
    wait_proxy(router, replacing=running)


def _fetch(client: Netns, url: str) -> str | None:
    """Return the body at ``url``, or None when the request fails."""
    try:
        return client.run("curl", "--silent", "--fail", "--max-time", "5", url)
    except subprocess.CalledProcessError:
        return None


def _image_field(router: Router, image: str, field: str) -> str:
    """Return a field of ``image``, as podman image inspect names it."""
    return router.run(f"podman image inspect --format '{{{{{field}}}}}' {image}")


@spec(CAPABILITY, "Container storage on the data disk", "Pull an image")
def test_pull_goes_to_the_data_disk(storage: Online, fresh_image: str) -> None:
    router = storage.router
    mark = scratch(f"pull-{time.time_ns()}")
    # An image of its own, so that the pull writes all of it, whatever
    # the module pulled before.
    router.run(f"touch {mark} && podman pull --quiet {fresh_image}", timeout=300)
    try:
        assert router.run("podman info --format '{{.Store.GraphRoot}}'") == STORAGE
        layer = _image_field(router, fresh_image, ".GraphDriver.Data.UpperDir")
        assert layer.startswith(f"{STORAGE}/")
        # The boot disk's overlay took no part of it: what little came
        # there since came from elsewhere (ksmbd starting on the same
        # mount writes a few bytes).
        size = int(_image_field(router, fresh_image, ".Size"))
        written = router.run(
            f"find /overlay/upper -newer {mark} -type f -exec cat {{}} + | wc -c"
        )
        assert int(written) < size // 100
    finally:
        router.run(f"podman rmi {fresh_image} >/dev/null")


@spec(CAPABILITY, "Single firewall and single NAT", "Check the ruleset")
def test_ruleset_is_fw4_only(pod: Online, lan_host: Netns) -> None:
    del lan_host  # serving on client-a
    router = pod.router
    # fw4's table, and honk's, a datapath component's.
    tables = set(router.run("nft list tables").splitlines())
    assert tables == {"table inet fw4", f"table {PROXY_NFQUEUE_TABLE}"}
    ruleset = router.run("nft list ruleset")
    assert "netavark" not in ruleset
    assert "chain forward_podman" in ruleset
    # The zone: the LAN reaches containers, containers never reach the
    # LAN.
    assert _fetch(pod.client("client-b"), f"http://{app.ADDRESS}/") == f"{app.POD}\n"
    lan = pod.addresses("client-a")[0]
    assert pod.client("client-b").probe("tcp", lan)["address"]  # the LAN host answers
    # The same nc of the container connects where it may, the internet's
    # probe server, and not to the LAN host.
    assert _from_container(pod, DIRECT_TARGET[0])["address"] == pod.wan_address
    refused = router.returncode(
        f"podman exec {app.CONTAINER} nc {lan} {PORT} </dev/null"
    )
    assert refused != 0


@spec(CAPABILITY, "Single firewall and single NAT", "Container reaches the internet")
def test_container_reaches_the_internet(pod: Online) -> None:
    seen = _from_container(pod, DIRECT_TARGET[0])
    assert seen["address"] == pod.wan_address
    # einat's port, not the container's own (masquerade would keep that
    # one).
    assert seen["port"] in EINAT_PORTS


@spec(CAPABILITY, "Single firewall and single NAT", "Expose a container port")
def test_exposed_port(pod: Online) -> None:
    router = pod.router
    router.run(
        "uci -q batch <<'EOF' && /etc/init.d/firewall reload\n"
        "set firewall.web=redirect\n"
        "set firewall.web.name='web'\n"
        "set firewall.web.src='wan'\n"
        f"set firewall.web.src_dport='{EXPOSED_PORT}'\n"
        "set firewall.web.dest='podman'\n"
        f"set firewall.web.dest_ip='{app.ADDRESS}'\n"
        f"set firewall.web.dest_port='{HTTP_PORT}'\n"
        "set firewall.web.proto='tcp'\n"
        "commit firewall\n"
        "EOF"
    )
    try:
        page = until(
            lambda: _fetch(
                pod.network["inet"], f"http://{pod.wan_address}:{EXPOSED_PORT}/"
            ),
            timeout=FIREWALL_TIMEOUT,
            what="the forwarded port",
        )
        assert page == f"{app.POD}\n"
    finally:
        router.run(
            "uci delete firewall.web && uci commit firewall"
            " && /etc/init.d/firewall reload"
        )


@spec(
    CAPABILITY,
    "Container traffic uses the transparent proxy",
    "Container reaches a proxied target",
)
def test_container_reaches_a_proxied_target(pod: Online) -> None:
    assert hooks(pod.router, "podman0") == PROXY_HOOKS_L2
    assert _from_container(pod, PROXIED_TARGET[0])["address"] == PROXY[0]
    assert _from_container(pod, DIRECT_TARGET[0])["address"] == pod.wan_address


@spec(
    CAPABILITY,
    "Container traffic uses the transparent proxy",
    "honk restarts beside the Pods",
)
def test_honk_restarts_beside_the_pods(pod: Online) -> None:
    router = pod.router
    app.wait_running(router)
    # Registered before honk started (the module's fixtures start it
    # second).
    before = _netns(router)
    _restart_proxy(router)
    assert router.returncode(f"test -e {before}") == 0, router.run("ls -la /run/netns")
    # A restarted Pod registers its next one while honk runs.
    router.run(f"podman pod restart {app.POD}", timeout=app.START_TIMEOUT)
    app.wait_running(router)
    during = _netns(router)
    _restart_proxy(router)
    assert router.returncode(f"test -e {during}") == 0, router.run("ls -la /run/netns")


@spec(
    CAPABILITY, "Declarative definition and autostart on boot", "Declaration unchanged"
)
def test_unchanged_declaration_is_not_rebuilt(pod: Online) -> None:
    router = pod.router
    before = app.wait_running(router)
    since = app.started(router)
    # What a mount of the data disk triggers: it stops the Pods, then
    # starts the startup flow, which procd runs after the script
    # returned. A new start shows the flow ran; the same container, that
    # it rebuilt nothing (test-fidelity D7).
    router.run("/etc/init.d/orbyt-containers restart")
    until(
        lambda: app.started(router) != since and app.running(router),
        timeout=app.START_TIMEOUT,
        what=f"{app.CONTAINER} started again",
    )
    assert app.running(router) == before


@spec(
    CAPABILITY,
    "Declarative definition and autostart on boot",
    "A declaration that cannot start",
)
def test_a_declaration_that_cannot_start_keeps_no_other_down(pod: Online) -> None:
    router = pod.router
    app.wait_running(router)
    # Before the app's by name, a Pod of an image no registry has:
    # nothing listens at its registry's port.
    missing = "a-missing"
    declared = f"{app.PODS}/{missing}.yaml"
    router.run(
        "printf %s"
        f" {shlex.quote(app.declaration('localhost:1/none:1', missing))}"
        f" >{declared}"
    )
    try:
        router.run(f"podman pod stop {app.POD} >/dev/null", timeout=120)
        said = router.run("orbyt-containers apply 2>&1; echo exit=$?", timeout=300)
    finally:
        router.run(f"rm -f {declared}")
    assert said.endswith("exit=1"), said
    assert f"orbyt-containers: {missing} did not come up" in said, said
    assert f"orbyt-containers: {app.POD} is up" in said, said
    assert app.running(router) is not None


def _service_running(router: Router, name: str) -> bool:
    """Return whether a procd instance of the service ``name`` runs."""
    services = json.loads(
        router.run(f'ubus call service list \'{{"name": "{name}"}}\'')
    )
    instances = services.get(name, {}).get("instances", {})
    return any(instance["running"] for instance in instances.values())


@spec(
    CAPABILITY,
    "Declarative definition and autostart on boot",
    "A service's container ended",
)
def test_the_network_s_dns_outlives_a_service_s_container(pod: Online) -> None:
    router = pod.router
    app.wait_running(router)
    # orbyt-sync runs a container on podman's network, and ends with it;
    # procd then kills what is left in the service's cgroup. Nothing can
    # be fetched here.
    router.run("/etc/init.d/orbyt-sync restart")
    until(
        lambda: not _service_running(router, "orbyt-sync"),
        timeout=SYNC_TIMEOUT,
        what="orbyt-sync ended",
    )
    router.run(f"podman pod stop {app.POD} >/dev/null", timeout=120)
    router.run(f"podman pod start {app.POD} >/dev/null", timeout=120)
    app.wait_running(router)
    # The network's DNS answers the Pod: its own name resolves inside
    # it.
    answer = router.run(f"podman exec {app.CONTAINER} nslookup {app.POD} {app.GATEWAY}")
    assert app.ADDRESS in answer, answer


@spec(CAPABILITY, "Declarative definition and autostart on boot", "Start on boot")
def test_pod_starts_on_boot(pod: Online) -> None:
    before = app.wait_running(pod.router)
    pod.reboot()
    after = app.wait_running(pod.router)
    assert after == before  # the same container, started again
    assert _fetch(pod.client(), f"http://{app.ADDRESS}/") == f"{app.POD}\n"


@spec(CAPABILITY, "App containers stay out of the firmware", "Check the image")
def test_no_native_apps(pod: Online) -> None:
    listed = pod.router.run("apk list --installed").splitlines()
    installed = [line.split()[0] for line in listed]
    assert "podman" in {name.rsplit("-", 2)[0] for name in installed}
    assert not [name for name in installed if name.startswith(NATIVE_APPS)]


@spec(
    CAPABILITY,
    "Container storage on the data disk",
    "Runtime commands at the same time",
)
def test_runtime_commands_at_the_same_time(online: Online, data_disk: Disk) -> None:
    del data_disk  # the scratch storage's place
    root = f"{STORAGE}-concurrency"
    # Through /run -> /var/run -> /tmp/run, then the changing symlink.
    runroot = "/run/concurrency/link/runroot"
    driver = scratch(AT_ONCE_DRIVER.name)
    online.router.put(AT_ONCE_DRIVER, driver)
    arguments = shlex.join([SCRATCH, root, runroot, str(AT_ONCE), str(IN_A_ROW)])
    try:
        reports = [
            online.router.run(f"sh {driver} round {arguments}", timeout=300)
            for _ in range(ROUNDS)
        ]
    finally:
        online.router.run(f"sh {driver} clean {arguments}")
    failed = [report for report in reports if not report.endswith("failed=0")]
    assert not failed, (
        f"{len(failed)} of {ROUNDS} rounds had commands fail; the first: {failed[0]}"
    )
    leaked = [report for report in reports if "left mounted: " in report]
    assert not leaked, (
        f"{len(leaked)} of {ROUNDS} rounds left mounts behind; the first: {leaked[0]}"
    )
