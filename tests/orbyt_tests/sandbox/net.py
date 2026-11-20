"""The rootless network sandbox around the emulator (design D14).

``scripts/test.sh`` starts pytest inside ``unshare --user
--map-root-user --net --mount``, so everything here runs as root of a
private user namespace and changes nothing on the host. The topology is
data: bridges (with the emulator's taps and the test runner's address),
and network namespaces whose ports are veth pairs to the bridges, each
port with static addresses or a DHCP client, plus routes and daemons.
``topology`` makes it for a board: a segment per port of the board
(board-model D7), and the ISP and internet of ``UPSTREAM``.

```
client-a ─┐                                                      ┌ inet
client-b ─┼─ br-lan ─ LAN │ router │ WAN ─ br-wan ─ isp ─ br-inet┤
runner   ─┘ 10.0.0.0/24   │ (QEMU) │  PPPoE        (BRAS)        └ proxy
client-c ── br-lan2 ─ LAN │        │   (a second LAN port)
```

``inet`` runs netprobe, dns and iperf3; ``proxy`` is the socks5 exit.

A namespace is held by a ``sleep`` process started with ``unshare
--net``; commands enter it with ``nsenter``. No named namespaces, so no
/run/netns and no real root are needed.
"""

import itertools
import json
import signal
import string
import subprocess
import sys
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self, cast, override

from orbyt_tests.model import process
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox import internet, isp, netprobe
from orbyt_tests.sandbox.layout import Layout

if TYPE_CHECKING:
    from types import TracebackType

    from orbyt_tests.model.boards import Board

UDHCPC_SCRIPT = Path(__file__).with_name("udhcpc.sh")
# The LAN, the router's address on it (its default, which the harness
# logs in to) and the runner's.
LAN_PREFIX = "10.0.0.0/24"
ROUTER_ADDRESS = "10.0.0.1"
RUNNER_ADDRESS = "10.0.0.2"
# The router's PPPoE session with the ISP.
WAN_DEVICE = "pppoe-wan"
# How long a daemon may take to be ready, and how long one with no
# readiness of its own must run to count as started.
DAEMON_READY_TIMEOUT = 30
DAEMON_SETTLE = 0.5
# How long a new namespace's holder may take to unshare.
NAMESPACE_TIMEOUT = 5
# The emulated internet: probe targets the tests route differently
# (direct or through the proxy), the ISP's resolver, and the socks5
# exit.
INET_GATEWAY = ("203.0.113.1", "2001:db8:ffff::1")
DIRECT_TARGET = ("203.0.113.10", "2001:db8:ffff::10")
# The name the internet's DNS gives DIRECT_TARGET.
DIRECT_NAME = "direct.example.net"
PROXIED_TARGET = ("203.0.113.20", "2001:db8:ffff::20")
PROXY_GATEWAY = ("198.51.100.1", "2001:db8:53::1")
PROXY = ("198.51.100.53", "2001:db8:53::53")
PROXY_PORT = 1080
# The ports of the internet's DNS and HTTPS servers.
DNS_PORT = 53
HTTPS_PORT = 443
IPERF_PORTS = (5201, 5202)


@dataclass(frozen=True, slots=True)
class Bridge:
    """A bridge in the sandbox.

    ``tap`` is the emulator's port on it, if any.
    """

    name: str
    tap: str | None = None
    address: str | None = None


@dataclass(frozen=True, slots=True)
class Port:
    """A namespace's veth to a bridge.

    The port has static ``addresses``, a DHCP client, or neither.
    """

    bridge: str
    addresses: tuple[str, ...] = ()
    dhcp: bool = False


@dataclass(frozen=True, slots=True)
class Daemon:
    """A daemon of a namespace, and how it shows that it is ready.

    ``listening`` are the ``ss`` arguments that list the socket it
    serves on, ``makes`` a file it makes. In either, and in the
    command, ``{workdir}`` is replaced with the namespace's directory,
    and ``{pki}`` with the sandbox's test CA (a ``Pki``). With neither,
    the tests wait for its service themselves (the ISP's sessions), and
    the sandbox sees only that it does not exit at once (test-hygiene
    D3).
    """

    command: tuple[str, ...]
    listening: tuple[str, ...] = ()
    makes: str | None = None


def _socket(port: int, address: str | None) -> str:
    """Return the ``ss`` filter of a socket on a port and address."""
    return f"sport = :{port}" if address is None else f"src {address}:{port}"


def _tcp(port: int, address: str | None = None) -> tuple[str, ...]:
    """Return the ``ss`` arguments of a listening TCP socket."""
    return ("-Hltn", _socket(port, address))


def _udp(port: int, address: str | None = None) -> tuple[str, ...]:
    """Return the ``ss`` arguments of a bound UDP socket."""
    return ("-Hlun", _socket(port, address))


@dataclass(frozen=True, slots=True)
class Namespace:
    """A network namespace; its ports are eth0, eth1, ... in order.

    ``sysctls`` are ``key=value`` settings of the namespace, ``routes``
    are ``ip route add`` arguments, ``daemons`` what runs inside it.
    """

    name: str
    ports: tuple[Port, ...]
    sysctls: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    daemons: tuple[Daemon, ...] = ()


@dataclass(frozen=True, slots=True)
class Topology:
    """Everything the sandbox contains."""

    bridges: tuple[Bridge, ...]
    namespaces: tuple[Namespace, ...]


# The ISP and the internet behind the router's WAN port, the same for
# every board.
UPSTREAM = (
    Namespace(
        "isp",
        ports=(
            Port("br-wan"),
            Port(
                "br-inet",
                addresses=tuple(
                    f"{gateway}/{length}"
                    for gateways in (INET_GATEWAY, PROXY_GATEWAY)
                    for gateway, length in zip(gateways, (24, 64), strict=True)
                ),
            ),
        ),
        sysctls=(
            "net.ipv4.ip_forward=1",
            "net.ipv6.conf.all.forwarding=1",
            # A session's link-local address is its own: kea binds to it
            # as soon as IPv6CP is up, before duplicate detection would
            # end.
            "net.ipv6.conf.default.accept_dad=0",
        ),
        daemons=(
            Daemon(
                (
                    "pppoe-server",
                    "-F",
                    "-I",
                    "eth0",
                    "-L",
                    isp.BRAS_ADDRESS,
                    "-R",
                    isp.POOL_START,
                    "-N",
                    str(isp.POOL_SIZE),
                    "-O",
                    "/etc/ppp/pppoe-server-options",
                ),
            ),
        ),
    ),
    Namespace(
        "inet",
        ports=(
            Port(
                "br-inet",
                addresses=(
                    *(
                        f"{address}/{length}"
                        for addresses in (isp.RESOLVER, DIRECT_TARGET, PROXIED_TARGET)
                        for address, length in zip(addresses, (24, 64), strict=True)
                    ),
                    *(f"{address}/24" for _, address in internet.SERVERS),
                ),
            ),
        ),
        routes=tuple(f"default via {gateway}" for gateway in INET_GATEWAY),
        daemons=(
            Daemon(
                (
                    sys.executable,
                    "-m",
                    "orbyt_tests.sandbox.netprobe",
                    "serve",
                    "--port",
                    str(netprobe.PORT),
                ),
                listening=_tcp(netprobe.PORT),
            ),
            Daemon(
                (
                    "dnsmasq",
                    "--keep-in-foreground",
                    "--conf-file=/dev/null",
                    # Empty user and group: keep the sandbox's identity;
                    # setgroups is not allowed in a user namespace.
                    "--user=",
                    "--group=",
                    "--log-facility=-",
                    "--log-queries",
                    "--pid-file=",
                    "--bind-interfaces",
                    *(f"--listen-address={address}" for address in isp.RESOLVER),
                    "--no-resolv",
                    "--no-hosts",
                    # The one zone the internet serves, anything else
                    # is NXDOMAIN (host records win over address
                    # rules). Every name under any.example.net
                    # resolves, so each test query can be one no cache
                    # has seen. Not a .test zone: the router's dnsmasq
                    # keeps RFC 6761 names local and never forwards
                    # them.
                    "--address=/#/",
                    f"--address=/any.example.net/{DIRECT_TARGET[0]}",
                    f"--host-record={DIRECT_NAME},{DIRECT_TARGET[0]},{DIRECT_TARGET[1]}",
                    "--host-record=proxied.example.net,{},{}".format(*PROXIED_TARGET),
                    *(
                        f"--host-record={name},{address}"
                        for name, address in internet.SERVERS
                    ),
                ),
                listening=_udp(DNS_PORT, isp.RESOLVER[0]),
            ),
            *(
                Daemon(
                    ("iperf3", "--server", "--port", str(port)), listening=_tcp(port)
                )
                for port in IPERF_PORTS
            ),
            Daemon(
                ("registry", "serve", "{workdir}/registry.yml"),
                listening=_tcp(HTTPS_PORT, internet.REGISTRY[1]),
            ),
            Daemon(
                ("headscale", "serve", "--config", "{workdir}/headscale.yaml"),
                listening=_tcp(HTTPS_PORT, internet.HEADSCALE[1]),
            ),
            Daemon(
                (
                    *(
                        sys.executable,
                        "-m",
                        "orbyt_tests.sandbox.releases_api",
                        "{workdir}/releases",
                    ),
                    *(
                        "--address",
                        internet.RELEASES[1],
                        "--name",
                        internet.RELEASES[0],
                    ),
                    "--certificate={pki.certificate}",
                    "--key={pki.key}",
                ),
                listening=_tcp(HTTPS_PORT, internet.RELEASES[1]),
            ),
        ),
    ),
    Namespace(
        "proxy",
        ports=(
            Port(
                "br-inet",
                addresses=tuple(
                    f"{address}/{length}"
                    for address, length in zip(PROXY, (24, 64), strict=True)
                ),
            ),
        ),
        routes=tuple(f"default via {gateway}" for gateway in PROXY_GATEWAY),
        daemons=(
            Daemon(
                ("microsocks", "-i", "::", "-p", str(PROXY_PORT)),
                listening=_tcp(PROXY_PORT),
            ),
        ),
    ),
    # A remote WireGuard device; the tests make its tunnel, a wireguard
    # link of the host kernel, with the keys they push to the router.
    Namespace(
        "wg-peer",
        ports=(
            Port(
                "br-inet",
                addresses=tuple(
                    f"{address}/{length}"
                    for address, length in zip(internet.WG_PEER, (24, 64), strict=True)
                ),
            ),
        ),
        routes=tuple(f"default via {gateway}" for gateway in INET_GATEWAY),
    ),
    # A tailnet device: tailscaled on a TUN of its own, trusting the
    # test CA.
    Namespace(
        "ts-peer",
        ports=(
            Port(
                "br-inet",
                addresses=tuple(
                    f"{address}/{length}"
                    for address, length in zip(internet.TS_PEER, (24, 64), strict=True)
                ),
            ),
        ),
        routes=tuple(f"default via {gateway}" for gateway in INET_GATEWAY),
        daemons=(
            Daemon(
                (
                    "env",
                    "SSL_CERT_FILE={pki.ca}",
                    "tailscaled",
                    "--no-logs-no-support",
                    "--statedir={workdir}",
                    "--socket={workdir}/tailscaled.sock",
                    "--tun=tailscale0",
                    "--port=41641",
                ),
                makes="{workdir}/tailscaled.sock",
            ),
        ),
    ),
)


def segments(board: Board) -> tuple[str, ...]:
    """Return the segment each of the board's ports joins.

    The segments follow the board's order (board-model D7).

    The WAN port's segment is ``wan``, the LAN ports' are ``lan``,
    ``lan2``, ...
    """
    lans = itertools.chain(("lan",), (f"lan{number}" for number in itertools.count(2)))
    return tuple("wan" if port.role == "wan" else next(lans) for port in board.ports)


def taps(board: Board) -> tuple[str, ...]:
    """Return the emulator's tap of each of the board's ports."""
    return tuple(f"emu-{segment}" for segment in segments(board))


def topology(board: Board) -> Topology:
    """Return the sandbox around the emulated board.

    It has a segment per port, the LAN clients and the upstream.

    The runner, ``client-a`` and ``client-b`` share the first LAN port's
    segment; every further LAN port's segment has a client of its own,
    ``client-c`` on.
    """
    lans = [segment for segment in segments(board) if segment != "wan"]
    clients = zip(string.ascii_lowercase, (lans[0], *lans), strict=False)
    return Topology(
        bridges=(
            *(
                Bridge(
                    f"br-{segment}",
                    tap=tap,
                    address=f"{RUNNER_ADDRESS}/24" if segment == lans[0] else None,
                )
                for segment, tap in zip(segments(board), taps(board), strict=True)
            ),
            Bridge("br-inet"),
        ),
        namespaces=(
            *(
                Namespace(f"client-{letter}", ports=(Port(f"br-{segment}", dhcp=True),))
                for letter, segment in clients
            ),
            *UPSTREAM,
        ),
    )


def ip(*args: str) -> str:
    """Run ``ip`` in the sandbox's own namespace; return its output."""
    return process.run("ip", *args)


class Netns(AbstractContextManager["Netns"]):
    """A network namespace held open by a sleeping process."""

    def __init__(self, name: str) -> None:
        """Create the namespace; it lives until the context exits."""
        self.name = name
        self._daemons = ExitStack()
        own = Path("/proc/self/ns/net").stat().st_ino
        self._holder = subprocess.Popen(["unshare", "--net", "--", "sleep", "infinity"])
        try:
            until(
                lambda: Path(self.path).stat().st_ino != own,
                timeout=NAMESPACE_TIMEOUT,
                every=0.01,
                what=f"namespace {name}",
            )
        except BaseException:
            # What a setup starts, it ends when it fails
            # (test-hygiene D3).
            self._holder.kill()
            self._holder.wait()
            raise

    @property
    def path(self) -> str:
        """The namespace file of the holder process."""
        return f"/proc/{self._holder.pid}/ns/net"

    @property
    def pid(self) -> int:
        """The holder process's pid.

        ``ip link set ... netns <pid>`` moves links here.
        """
        return self._holder.pid

    def argv(self, *command: str) -> list[str]:
        """Prefix a command line to run it inside this namespace."""
        return ["nsenter", f"--net={self.path}", "--", *command]

    def run(self, *command: str, timeout: float = 30) -> str:
        """Run a command inside the namespace; return its output.

        A failure carries the command's output and the namespace's name.
        """
        try:
            return process.run(*self.argv(*command), timeout=timeout)
        except subprocess.CalledProcessError as error:
            error.add_note(f"in {self.name}")
            raise

    def spawn(
        self, *command: str, stdout: int | None = None
    ) -> subprocess.Popen[bytes]:
        """Start a long-running command inside the namespace.

        ``stdout`` may be, e.g., PIPE.
        """
        return subprocess.Popen(
            self.argv(*command), stdin=subprocess.DEVNULL, stdout=stdout
        )

    def probe(self, *args: str, timeout: float = 30) -> netprobe.Seen:
        """Run a netprobe client in the namespace; return its output."""
        output = self.run(
            sys.executable, "-m", "orbyt_tests.sandbox.netprobe", *args, timeout=timeout
        )
        return cast("netprobe.Seen", json.loads(output))

    def start(self, daemon: Daemon, layout: Layout) -> subprocess.Popen[bytes]:
        """Start ``daemon`` here; return it once it is ready.

        Its files are in the namespace's directory of ``layout``. It
        runs until the namespace's context exits. A daemon that exits
        while it starts fails the setup at once; its output is the test
        run's.
        """
        places = {"workdir": layout.namespace(self.name), "pki": layout.pki}
        command = tuple(argument.format(**places) for argument in daemon.command)
        started = self.spawn(*command)
        self._daemons.callback(started.wait)
        self._daemons.callback(started.terminate)

        def ready() -> bool:
            if (code := started.poll()) is not None:
                msg = f"{self.name}: {command[0]} exited with {code} while starting"
                raise RuntimeError(msg)
            if daemon.listening:
                return bool(self.run("ss", *daemon.listening).strip())
            if daemon.makes is not None:
                return Path(daemon.makes.format(**places)).exists()
            # Its service, the tests await themselves.
            try:
                started.wait(timeout=DAEMON_SETTLE)
            except subprocess.TimeoutExpired:
                return True
            return False

        until(
            ready,
            timeout=DAEMON_READY_TIMEOUT,
            every=0.1,
            what=f"{command[0]} ready in {self.name}",
        )
        return started

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the daemons, then the holder.

        The namespace disappears with the holder.
        """
        try:
            self._daemons.close()
        finally:
            self._holder.kill()
            self._holder.wait()


class Network(AbstractContextManager["Network"]):
    """The sandbox topology, built on entry and torn down on exit."""

    def __init__(self, topology: Topology, workdir: Path) -> None:
        """Remember what to build.

        ``workdir`` holds the sandbox's files, as ``layout`` lays out.
        """
        self.topology = topology
        self.layout = Layout(workdir)
        self._stack = ExitStack()
        self._namespaces: dict[str, Netns] = {}
        self._dhcp: dict[str, subprocess.Popen[bytes]] = {}

    def __getitem__(self, name: str) -> Netns:
        """Return a namespace of the topology by name."""
        return self._namespaces[name]

    @override
    def __enter__(self) -> Self:
        """Create bridges, taps and namespaces, then start services.

        The services are the DHCP clients and the daemons. A setup that
        fails halfway stops what it started before it fails: Python
        calls no ``__exit__`` for an ``__enter__`` that raised
        (test-hygiene D3).
        """
        try:
            self._isolate()
            ip("link", "set", "lo", "up")
            for bridge in self.topology.bridges:
                ip("link", "add", "name", bridge.name, "type", "bridge")
                if bridge.tap is not None:
                    ip("tuntap", "add", "dev", bridge.tap, "mode", "tap")
                    ip("link", "set", bridge.tap, "master", bridge.name, "up")
                ip("link", "set", bridge.name, "up")
                if bridge.address is not None:
                    ip("addr", "add", bridge.address, "dev", bridge.name)
            for namespace in self.topology.namespaces:
                self.add(namespace)
        except BaseException:
            self._stack.close()
            raise
        return self

    def _isolate(self) -> None:
        """Give the sandbox its own accounts, hosts and service setup.

        The setup covers the ISP's /etc/ppp and the servers'.

        The sandbox has one uid, 0, which is the invoking user outside.
        Its own passwd and group make every account that uid, with a
        private home: daemons that switch to an account (rp-pppoe drops
        to nobody) or read a dotfile (pppd reads ~/.ppprc) stay inside
        the sandbox. The host's name service cache would answer with the
        host's accounts, so its socket is hidden. Its own hosts file
        names the emulated internet's servers.
        """
        etc = self.layout.etc
        home = self.layout.home
        home.mkdir(parents=True)
        etc.mkdir()
        (etc / "passwd").write_text(
            f"root:x:0:0::{home}:/bin/sh\nnobody:x:0:0::/var/empty:/bin/false\n"
        )
        (etc / "group").write_text("root:x:0:\nnogroup:x:0:\n")
        isp.configure(etc / "ppp", self.layout.namespace("isp"))
        internet.configure(self.layout)
        for name in ("passwd", "group", "ppp", "hosts"):
            process.run("mount", "--bind", etc / name, f"/etc/{name}")
        if Path("/var/run/nscd/socket").exists():
            process.run("mount", "-t", "tmpfs", "tmpfs", "/var/run/nscd")

    def add(self, namespace: Namespace) -> Netns:
        """Add a namespace to the running sandbox.

        It lives as long as the sandbox. A namespace that fails to come
        up takes its daemons and itself down again (test-hygiene D3);
        its links go with it.
        """
        self.layout.namespace(namespace.name).mkdir(parents=True, exist_ok=True)
        with ExitStack() as stack:
            netns = stack.enter_context(Netns(namespace.name))
            netns.run("ip", "link", "set", "lo", "up")
            if namespace.sysctls:
                netns.run("sysctl", "-qw", *namespace.sysctls)
            clients = [
                self._connect(netns, f"eth{index}", port)
                for index, port in enumerate(namespace.ports)
            ]
            for route in namespace.routes:
                netns.run("ip", "route", "add", *route.split())
            for daemon in namespace.daemons:
                netns.start(daemon, self.layout)
            self._stack.enter_context(stack.pop_all())
        self._namespaces[namespace.name] = netns
        if client := next(filter(None, clients), None):
            self._dhcp[namespace.name] = client
        return netns

    def _connect(
        self, netns: Netns, device: str, port: Port
    ) -> subprocess.Popen[bytes] | None:
        """Connect ``netns``'s ``device`` to ``port``'s bridge.

        Return the DHCP client of a port that leases its address.
        """
        outside = f"v{device[-1]}-{netns.name}"
        ip(
            "link",
            "add",
            outside,
            "type",
            "veth",
            "peer",
            "name",
            device,
            "netns",
            str(netns.pid),
        )
        ip("link", "set", outside, "master", port.bridge, "up")
        netns.run("ip", "link", "set", device, "up")
        for address in port.addresses:
            # Static IPv6 addresses skip duplicate address detection:
            # nothing else in the sandbox claims them, and the tests
            # need them at once.
            netns.run(
                "ip",
                "addr",
                "add",
                address,
                "dev",
                device,
                *(("nodad",) if ":" in address else ()),
            )
        if port.dhcp:
            # A lease is the client's service, which the tests await.
            client = (
                *("udhcpc", "-f", "-i", device, "-s", str(UDHCPC_SCRIPT), "-A", "3"),
                *("-x", f"hostname:{netns.name}"),
            )
            return netns.start(Daemon(client), self.layout)
        return None

    def renew(self, name: str) -> None:
        """Have a namespace's DHCP client renew its lease now.

        udhcpc renews on SIGUSR1.
        """
        self._dhcp[name].send_signal(signal.SIGUSR1)

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop daemons and namespaces; links vanish with them."""
        self._stack.close()
