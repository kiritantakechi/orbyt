"""The fixtures of the router online and what runs on it (module-boundaries D6).

A module dials in at the emulated ISP once; the transparent proxy (honk), the
emulated internet's names and CA, and the test app's Pod build on that session.
"""

import subprocess
from collections.abc import Generator  # noqa: TC003 (pluggy reads the hook's annotations)
from typing import TYPE_CHECKING, cast

import pytest

from orbyt_tests.device.trust import trust_ca
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox.net import DIRECT_NAME, DIRECT_TARGET
from orbyt_tests.services import app
from orbyt_tests.services.datapath import Online, proxy_start

if TYPE_CHECKING:
    from collections.abc import Iterator

    from orbyt_tests.device.router import Router
    from orbyt_tests.device.storage import Disk
    from orbyt_tests.sandbox.isp import Isp
    from orbyt_tests.sandbox.net import Network


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Add the datapath's state to the report of a test that failed with the router online.

    ``funcargs`` holds the values of the test's whole fixture closure, so a test
    on a fixture built on ``online`` has it too (failure-diagnostics D3). A
    teardown that fails, putting the router back, is such a failure as well.
    """
    del call
    report = yield
    if report.when in {"call", "teardown"} and report.failed:
        funcargs = getattr(item, "funcargs", {})
        online = next(
            (value for value in funcargs.values() if isinstance(value, Online)), None
        )
        if online is not None:
            report.sections.append(("datapath", online.state()))
    return report


@pytest.fixture(scope="module")
def online(module_router: Router, isp: Isp, network: Network) -> Online:
    """Dial in at the ISP for the module."""
    return Online.dial(module_router, isp, network)


@pytest.fixture(scope="module")
def internet_zone(online: Online) -> Online:
    """Let the emulated internet's answers through dnsmasq's rebind protection.

    Its addresses are documentation ranges, which the protection counts as
    private; an operator lets a local domain through the same way. dnsmasq
    restarts to take it after the reload has returned, the old instance
    listening meanwhile, so the fixture waits for the router to answer a LAN
    query with an address the protection held back (DNS to a private address
    passes honk natively).
    """
    router = online.router
    router.run(
        "uci add_list dhcp.@dnsmasq[0].rebind_domain=example.net && uci commit dhcp"
        " && /etc/init.d/dnsmasq reload"
    )
    until(
        lambda: _resolved(online, DIRECT_NAME) == [DIRECT_TARGET[0]],
        timeout=60,
        what=f"{DIRECT_NAME} resolved by dnsmasq with the exception",
    )
    return online


def _resolved(online: Online, name: str) -> list[str]:
    """Return the router's answers to a LAN client's query for ``name``; none while it restarts."""
    try:
        seen = online.client().probe("resolve", name, "--server", online.router.address)
    except subprocess.CalledProcessError:
        return []
    return cast("list[str]", seen["answers"])


@pytest.fixture(scope="module")
def proxy(online: Online) -> Iterator[Online]:
    """Run the transparent proxy, honk, with the test configuration for the module."""
    proxy_start(online.router)
    yield online
    online.router.run("/etc/init.d/honk stop; /etc/init.d/honk disable")


@pytest.fixture(scope="module")
def trusted_ca(internet_zone: Online) -> Online:
    """Have the router resolve and trust the emulated internet's servers (test CA)."""
    trust_ca(internet_zone.router, internet_zone.network.workdir)
    return internet_zone


@pytest.fixture(scope="module")
def app_pod(trusted_ca: Online, data_disk: Disk, app_image: str) -> Online:
    """Declare the app Pod on the data disk and wait until orbyt-containers has started it."""
    del data_disk  # requested for the Pod's place
    app.declare(trusted_ca.router, app_image)
    app.wait_running(trusted_ca.router)
    return trusted_ca
