"""The emulated ISP between the router's WAN and the emulated internet.

(r4s-ebpf-datapath D11)

The ``isp`` namespace is the BRAS. rp-pppoe's pppoe-server runs in user
mode (a pty per session, so the host needs only ppp_generic and
ppp_async, never pppoe.ko) and hands each session the next address of
its pool: every redial gets a new address. pppd runs four scripts per
session, the isp-*.sh files beside this module:

- ``ip-up`` and ``ip-down`` keep a registry for the tests, one file per
  session (named after its pppd) with its PPP interface and the address
  the peer got;
- ``ipv6-up`` gives the session the WAN prefix for SLAAC (radvd) and a
  delegated prefix (kea-dhcp6), and ``ipv6-down`` stops both. The
  prefixes stay the same across redials, so only the IPv4 address moves.

Everything is keyed by the session's pppd, never by its interface: a
redial may get the same interface name while the previous session is
still going down.

pppd reads its options and secrets from fixed paths under /etc/ppp, and
looks up root's home for ``~/.ppprc``; the sandbox mounts what
``configure`` writes there (``orbyt_tests.sandbox.net``). The server
options name the scripts, so that a pppd dialing from a test runs none
of them.
"""

import ipaddress
import os
import shlex
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from orbyt_tests.model.poll import until

if TYPE_CHECKING:
    from collections.abc import Generator

    from orbyt_tests.sandbox.net import Netns

# The account the router dials with; the image carries none (the config
# push writes the real one).
LOGIN = ("orbyt", "sandbox")
BRAS_ADDRESS = "192.0.2.1"
POOL_START = "192.0.2.64"
POOL_SIZE = 64
MTU = 1492
# The resolver the ISP hands out, served on the emulated internet.
RESOLVER = ("203.0.113.53", "2001:db8:ffff::53")
# SLAAC on every session's link, and the prefix delegated to the router.
WAN_PREFIX = "2001:db8:0:1::/64"
WAN_GATEWAY = "2001:db8:0:1::1"
DELEGATED_PREFIX = ipaddress.IPv6Network("2001:db8:100::/56")
SESSION_TIMEOUT = 60
# The ISP's pppd log, in its working directory.
PPPD_LOG = "pppd.log"
# What pppd runs of each session, isp-<name>.sh beside this module.
SCRIPTS = ("ip-up", "ip-down", "ipv6-up", "ipv6-down")


@dataclass(frozen=True, slots=True)
class Session:
    """A PPP session as the ISP sees it."""

    interface: str
    pid: int
    peer: str


class Isp:
    """The tests' handle on the ISP: its sessions, and hanging up."""

    def __init__(self, netns: Netns, workdir: Path) -> None:
        """Wrap the ``isp`` namespace.

        ``workdir`` is the one ``configure`` was given.
        """
        self.netns = netns
        self.registry = workdir / "sessions"
        self.log_file = workdir / PPPD_LOG

    def log(self, lines: int) -> str:
        """Return the last ``lines`` lines of the ISP's pppd log."""
        return "\n".join(
            self.log_file.read_text(encoding="utf-8", errors="replace").splitlines()[
                -lines:
            ]
        )

    def sessions(self) -> list[Session]:
        """Return the sessions whose IPCP is up."""
        found = []
        for entry in sorted(self.registry.iterdir()):
            if entry.suffix:
                continue
            interface, peer = entry.read_text().split()
            found.append(Session(interface, int(entry.name), peer))
        return found

    def session(self, peer: str) -> Session:
        """Return the session that gave ``peer`` its address."""
        return until(
            lambda: next((s for s in self.sessions() if s.peer == peer), None),
            timeout=SESSION_TIMEOUT,
            every=0.5,
            what=f"session of the ISP's for {peer}",
            notes=lambda: [f"the ISP's sessions: {self.sessions()}"],
        )

    @contextmanager
    def blocking(self, destination: str) -> Generator[None]:
        """Refuse what the customers send to ``destination``.

        This is how an ISP that filters ``destination`` behaves.
        """
        first = ipaddress.IPv4Address(POOL_START)
        (pool,) = ipaddress.summarize_address_range(first, first + POOL_SIZE - 1)
        rule = ("from", str(pool), "to", destination, "prohibit")
        self.netns.run("ip", "rule", "add", *rule)
        try:
            yield
        finally:
            self.netns.run("ip", "rule", "del", *rule)

    def hang_up(self, session: Session) -> None:
        """End a session from the ISP side.

        pppd sends LCP terminate and PADT.
        """
        os.kill(session.pid, signal.SIGTERM)
        until(
            lambda: not (self.registry / str(session.pid)).exists(),
            timeout=SESSION_TIMEOUT,
            every=0.2,
            what=f"end of session {session}",
        )


def _script(name: str) -> Path:
    """Return the session script ``name``."""
    return Path(__file__).with_name(f"isp-{name}.sh")


def configure(etc: Path, workdir: Path) -> None:
    """Write the ISP's /etc/ppp to ``etc``, the rest to ``workdir``.

    The session scripts read what they need from ``workdir``'s
    isp.env, which pppd names them as their ipparam. pppd gives them a
    bare PATH: isp.env holds the test environment's.
    """
    etc.mkdir(parents=True)
    (workdir / "sessions").mkdir(parents=True)
    settings = {
        "PATH": os.environ["PATH"],
        "REGISTRY": workdir / "sessions",
        "SESSIONS": workdir,
        "WAN_GATEWAY": WAN_GATEWAY,
        "WAN_PREFIX": WAN_PREFIX,
        "DELEGATED_PREFIX": DELEGATED_PREFIX,
        "DELEGATED_NETWORK": DELEGATED_PREFIX.network_address,
        "DELEGATED_LENGTH": DELEGATED_PREFIX.prefixlen,
        "RESOLVER6": RESOLVER[1],
    }
    (workdir / "isp.env").write_text(
        "".join(
            f"export {name}={shlex.quote(str(value))}\n"
            for name, value in settings.items()
        )
    )
    (etc / "options").write_text("")
    secrets = etc / "pap-secrets"
    secrets.write_text(f"{LOGIN[0]} * {LOGIN[1]} *\n")
    secrets.chmod(0o600)
    (etc / "pppoe-server-options").write_text(
        "\n".join(
            (
                "# The ISP's side of every session (pppoe-server -O).",
                "require-pap",
                f"mtu {MTU}",
                f"mru {MTU}",
                f"ms-dns {RESOLVER[0]}",
                "lcp-echo-interval 5",
                "lcp-echo-failure 3",
                "noccp",
                "novj",
                "+ipv6",
                "debug",
                f"logfile {workdir / PPPD_LOG}",
                f"ipparam {workdir}",
                *(f"{name}-script {_script(name)}" for name in SCRIPTS),
                "",
            )
        )
    )
