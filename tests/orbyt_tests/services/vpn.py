"""The router's VPNs and their peers (r4s-services D6, D10).

The peers are on the emulated internet.

The image presets no keys: the tests write them the way the config push
does. ``WireGuard`` gives the router's wg0 its key and wg-peer as its
one peer, whose end is a wireguard link of the host kernel in wg-peer's
namespace. ``Tailnet`` logs the router and ts-peer into headscale with a
preauth key; the router advertises the LAN and itself as an exit node,
and headscale approves both, as an administrator would.
"""

import json
import shlex
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, cast

from orbyt_tests.model import process
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox.internet import HEADSCALE
from orbyt_tests.sandbox.net import LAN_PREFIX

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from orbyt_tests.device.router import Router
    from orbyt_tests.sandbox.net import Netns, Network
    from orbyt_tests.services.datapath import Online

WG_PORT = 51820
# The router's and wg-peer's addresses in the tunnel
# (92-orbyt-services).
WG_ADDRESSES = ("10.9.0.1", "10.9.0.2")
HEADSCALE_URL = f"https://{HEADSCALE[0]}"
TAILNET_USER = "orbyt"
ROUTER_ROUTES = (LAN_PREFIX, "0.0.0.0/0", "::/0")
TAILSCALE_TIMEOUT = 120
HANDSHAKE_TIMEOUT = 60


def _wg(*args: str, key: str | None = None) -> str:
    return process.run("wg", *args, stdin=key).strip()


def key_pair() -> tuple[str, str]:
    """Return a new WireGuard private key and its public key."""
    private = _wg("genkey")
    return private, _wg("pubkey", key=private)


@dataclass(frozen=True, slots=True)
class WireGuard:
    """wg-peer connected to the router's wg0."""

    peer: Netns

    @classmethod
    @contextmanager
    def connect(cls, online: Online, routes: Sequence[str]) -> Generator[Self]:
        """Key both ends and bring the tunnel up for the context.

        wg-peer routes ``routes`` through it.

        The context's end takes wg-peer's tunnel down again, as does a
        failure on the way, so that the session's namespace holds none
        for the next one (test-hygiene D3). The router's end goes back
        with its snapshot.
        """
        router_private, router_public = key_pair()
        peer_private, peer_public = key_pair()
        online.router.run(
            "uci -q batch <<'EOF' && /etc/init.d/network reload\n"
            f"set network.wg0.private_key='{router_private}'\n"
            "set network.wg0.disabled='0'\n"
            "set network.wg_peer=wireguard_wg0\n"
            "set network.wg_peer.description='wg-peer'\n"
            f"set network.wg_peer.public_key='{peer_public}'\n"
            f"add_list network.wg_peer.allowed_ips='{WG_ADDRESSES[1]}/32'\n"
            "commit network\n"
            "EOF"
        )
        peer = online.network["wg-peer"]
        key = online.network.workdir / "wg-peer" / "private.key"
        key.write_text(peer_private)
        key.chmod(0o600)
        peer.run("ip", "link", "add", "wg0", "type", "wireguard")
        tunnel = cls(peer)
        try:
            peer.run(
                *("wg", "set", "wg0", "private-key", str(key), "peer", router_public),
                *(
                    "endpoint",
                    f"{online.wan_address}:{WG_PORT}",
                    "allowed-ips",
                    "0.0.0.0/0",
                ),
                *("persistent-keepalive", "5"),
            )
            peer.run("ip", "addr", "add", f"{WG_ADDRESSES[1]}/24", "dev", "wg0")
            peer.run("ip", "link", "set", "wg0", "up")
            for route in routes:
                peer.run("ip", "route", "add", route, "dev", "wg0")
            # Past the limit, both ends as they stand, their private
            # keys hidden by wg.
            until(
                tunnel.handshaken,
                timeout=HANDSHAKE_TIMEOUT,
                what="a WireGuard handshake",
                notes=lambda: [
                    f"wg-peer:\n{peer.run('wg', 'show', 'wg0')}",
                    f"router:\n{online.router.run('wg show wg0; ifstatus wg0')}",
                ],
            )
            yield tunnel
        finally:
            peer.run("ip", "link", "del", "wg0")

    def handshaken(self) -> bool:
        """Return whether wg-peer has handshaken with the router."""
        handshakes = self.peer.run("wg", "show", "wg0", "latest-handshakes").split()
        return len(handshakes) == 2 and handshakes[1] != "0"  # noqa: PLR2004


def _headscale(network: Network, *args: str) -> Any:  # noqa: ANN401 (JSON)
    config = network.workdir / "inet" / "headscale.yaml"
    output = network["inet"].run(
        "headscale", f"--config={config}", *args, "--output=json"
    )
    return json.loads(output) if output.strip() else None


def _nodes(network: Network) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", _headscale(network, "nodes", "list") or [])


def _node(network: Network, name: str) -> int:
    (node,) = (
        node
        for node in _nodes(network)
        if name in (node.get("given_name"), node.get("name"))
    )
    return int(node["id"])


def _peer_tailscale(network: Network, *args: str, timeout: float = 60) -> str:
    socket = network.workdir / "ts-peer" / "tailscaled.sock"
    return network["ts-peer"].run(
        "tailscale", f"--socket={socket}", *args, timeout=timeout
    )


def clear(network: Network) -> None:
    """Remove every node from headscale, routes withdrawn first.

    The tailnet starts empty.

    headscale (0.27) lets go of the routes a node serves when their
    approval changes or the node goes offline, not when it is deleted: a
    router deleted while it serves the LAN route would keep the next one
    from ever serving it.
    """
    for node in _nodes(network):
        identifier = f"--identifier={node['id']}"
        _headscale(network, "nodes", "approve-routes", identifier, "--routes=")
        _headscale(network, "nodes", "delete", identifier, "--force")


def preauth_key(network: Network) -> str:
    """Return a new reusable preauth key of the tailnet's user.

    The key is valid for an hour.
    """
    users = cast("list[dict[str, Any]]", _headscale(network, "users", "list") or [])
    if not any(user["name"] == TAILNET_USER for user in users):
        _headscale(network, "users", "create", TAILNET_USER)
        users = cast("list[dict[str, Any]]", _headscale(network, "users", "list"))
    (user,) = (user for user in users if user["name"] == TAILNET_USER)
    created = _headscale(
        network,
        "preauthkeys",
        "create",
        f"--user={user['id']}",
        "--reusable",
        "--expiration=1h",
    )
    return str(created["key"])


@dataclass(frozen=True, slots=True)
class Tailnet:
    """The router and ts-peer logged into headscale."""

    network: Network
    router: Router
    router_address: str

    @property
    def peer(self) -> Netns:
        """ts-peer's namespace."""
        return self.network["ts-peer"]

    def peer_tailscale(self, *args: str, timeout: float = 60) -> str:
        """Run the tailscale CLI against ts-peer's tailscaled."""
        return _peer_tailscale(self.network, *args, timeout=timeout)

    @classmethod
    @contextmanager
    def join(cls, online: Online) -> Generator[Self]:
        """Log the router and ts-peer into the tailnet for the context.

        The router is a subnet router and exit node.

        The tailnet starts empty: a node an earlier module left behind
        goes first. The context's end logs ts-peer out and empties the
        tailnet again, as does a failure on the way (test-hygiene D3).
        The router's login goes back with its snapshot.
        """
        clear(online.network)
        try:
            yield cls._log_in(online)
        finally:
            _peer_tailscale(online.network, "logout")
            clear(online.network)

    @classmethod
    def _log_in(cls, online: Online) -> Self:
        key = preauth_key(online.network)
        login = (
            f"--login-server={HEADSCALE_URL}",
            f"--auth-key={key}",
            "--accept-dns=false",
        )
        # tailscaled loads the trusted CAs once: after the test CA came.
        online.router.run("/etc/init.d/tailscale restart")
        online.router.run(
            shlex.join(
                [
                    *("tailscale", "up", *login, "--hostname=router", "--timeout=60s"),
                    f"--advertise-routes={LAN_PREFIX}",
                    "--advertise-exit-node",
                ]
            ),
            timeout=TAILSCALE_TIMEOUT,
        )
        _headscale(
            online.network,
            *(
                "nodes",
                "approve-routes",
                "--identifier",
                str(_node(online.network, "router")),
            ),
            f"--routes={','.join(ROUTER_ROUTES)}",
        )
        tailnet = cls(
            online.network, online.router, online.router.run("tailscale ip -4")
        )
        tailnet.peer_tailscale(
            *("up", *login, "--hostname=ts-peer", "--timeout=60s"),
            *("--accept-routes", "--netfilter-mode=off"),
            timeout=TAILSCALE_TIMEOUT,
        )
        until(
            lambda: (
                LAN_PREFIX in tailnet.peer.run("ip", "route", "show", "table", "52")
            ),
            timeout=TAILSCALE_TIMEOUT,
            what="the LAN route at ts-peer",
            notes=lambda: [
                tailnet.peer_tailscale("status"),
                json.dumps(_headscale(online.network, "nodes", "list-routes")),
            ],
        )
        # A route is not yet a path: the first packets wait for the
        # tunnel.
        until(
            tailnet.reachable,
            timeout=TAILSCALE_TIMEOUT,
            what="the router over the tailnet",
        )
        return tailnet

    def reachable(self) -> bool:
        """Return whether the router answers.

        The probe is ts-peer's tailscale ping.
        """
        try:
            self.peer_tailscale("ping", "--c=1", "--timeout=5s", self.router_address)
        except subprocess.CalledProcessError:
            return False
        return True

    def use_exit_node(self, *, on: bool) -> None:
        """Have ts-peer send its internet traffic through the router.

        With ``on`` false, it stops.
        """
        self.peer_tailscale("set", f"--exit-node={self.router_address if on else ''}")
