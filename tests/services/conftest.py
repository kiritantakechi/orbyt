"""Fixtures of the services tests (r4s-services D10).

They are what an administrator sets up.

An SMB user, the WireGuard tunnel and the tailnet: each is written the
way the config push or an administrator would, since the image presets
none of it. A module's router returns to its snapshot afterwards, so
only what lives outside it (wg-peer, ts-peer, headscale, the LAN host's
server) is put back.
"""

import sys
from typing import TYPE_CHECKING

import pytest

from orbyt_tests.sandbox.net import LAN_PREFIX, PROXIED_TARGET
from orbyt_tests.services.vpn import Tailnet, WireGuard

if TYPE_CHECKING:
    from collections.abc import Iterator

    from orbyt_tests.sandbox.net import Netns, Network
    from orbyt_tests.services.datapath import Online


@pytest.fixture(scope="module")
def lan_host(network: Network) -> Iterator[Netns]:
    """Run a probe server on client-a, a host of the LAN."""
    client = network["client-a"]
    server = client.spawn(sys.executable, "-m", "orbyt_tests.sandbox.netprobe", "serve")
    yield client
    server.terminate()
    server.wait()


@pytest.fixture(scope="module")
def wireguard(online: Online) -> Iterator[WireGuard]:
    """Connect wg-peer, routing the LAN and the proxied target.

    Both go through the tunnel.
    """
    with WireGuard.connect(online, [LAN_PREFIX, f"{PROXIED_TARGET[0]}/32"]) as tunnel:
        yield tunnel


@pytest.fixture(scope="module")
def tailnet(trusted_ca: Online) -> Iterator[Tailnet]:
    """Log the router and ts-peer into headscale."""
    with Tailnet.join(trusted_ca) as joined:
        yield joined
