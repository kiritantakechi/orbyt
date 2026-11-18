"""ops/config-push: the private configuration, encrypted, pushed with config-push.

The module's private repository is config-init's, filled in as an
administrator fills it: the ISP account, WireGuard's key, the tailnet
login (a preauth key of the emulated internet's headscale) and a share
user in the encrypted secrets, honk's test configuration encrypted
beside them. It is pushed once to the module's router, online and
trusting the emulated internet, over SSH with the harness's key; each
test pushes what it changed and discards it after. The upgrade to the
other slot comes last.
"""

import hashlib
import json
import shlex
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest

from orbyt_tests import spec
from orbyt_tests.device.trust import trust_ca
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox.isp import LOGIN
from orbyt_tests.services.config import ConfigRepository
from orbyt_tests.services.datapath import (
    NATIVE_API,
    NATIVE_API_TOKEN,
    PROXY_CONFIG,
    PROXY_HEALTHCHECK,
    wait_proxy,
)
from orbyt_tests.services.vpn import HEADSCALE_URL, clear, key_pair, preauth_key

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from pathlib import Path

    from orbyt_tests.device.router import Router
    from orbyt_tests.services.datapath import Online

CAPABILITY = "ops/config-push"
SHARE_USER = {"name": "pushed", "password": "pushed-secret-1"}
# A share user a later push adds, so that it writes the SMB users again.
ADDED_SHARE_USER = {"name": "added", "password": "added-secret-2"}
# An address the LAN cannot come up with (netifd: INVALID_ADDRESS).
BAD_LAN_ADDRESS = "10.0.0.300/24"
# The requirement on honk's settings that the firmware sets, and
# config-push's refusal.
FIRMWARE_SETTINGS = "Proxy user config cannot set the firmware's settings"
FIRMWARE_SETTINGS_REFUSAL = (
    "lan_interface, wan_interface and data_dir are the firmware's"
)
SERVICES = ("honk", "network", "smb", "tailscale")
# The processes the services' reloads restart: honk's, the WAN's pppd,
# the SMB server's and tailscaled.
RESTARTED = ("honk-core", "pppd", "ksmbd.mountd", "tailscaled")
ROOT_PASSWORD = "not-for-config-push"  # noqa: S105 (the test router's, for a password to refuse)
# A password gitleaks' generic rule surely catches in plain text. A
# random one now and then falls short of its entropy threshold, or holds
# one of its stop words.
PLAIN_SECRET = "vZ8qK3wT9mX2pL7nR4cB"  # noqa: S105  # gitleaks:allow (only scanned for)
UPGRADE_IMAGE = "/tmp/sysupgrade.tar.gz"  # noqa: S108 (a path on the router)
TAILSCALE_TIMEOUT = 180
# Where the router records, while a push runs, the modes of its upload
# and the command lines of its processes.
UPLOAD = "/tmp/orbyt-push"  # noqa: S108 (a path on the router)
MODES = "/tmp/push-modes"  # noqa: S108 (a path on the router)
COMMANDS = "/tmp/push-commands"  # noqa: S108 (a path on the router)
# A fifth of a second: the router's BusyBox sleep takes whole seconds
# only, and fails at once on a fraction.
PAUSE = "ucode -e 'sleep(200)'"
WATCH = (
    f"while :; do ls -ldn {UPLOAD} 2>/dev/null; ls -lnR {UPLOAD}/new 2>/dev/null; {PAUSE};"
    f" done >{MODES} & while :; do for cmdline in /proc/[0-9]*/cmdline; do"
    f" tr '\\0' ' ' <$cmdline; echo; done 2>/dev/null; {PAUSE}; done >{COMMANDS}"
)
# Modes of a file and of a directory that root alone can read.
ROOT_ONLY = ("-rw-------", "drwx------")
# The tailscale CLI and ksmbd.adduser, links to the binaries that act by
# the name they run under, and where the arguments of their runs are
# recorded.
TAILSCALE = "/usr/sbin/tailscale"
TAILSCALE_ARGUMENTS = "/tmp/tailscale-arguments"  # noqa: S108 (a path on the router)
ADDUSER = "/usr/sbin/ksmbd.adduser"
ADDUSER_ARGUMENTS = "/tmp/adduser-arguments"  # noqa: S108 (a path on the router)
# An auth key headscale refuses.
REFUSED_KEY = "tskey-auth-refused-0000"
# A docroot uhttpd refuses to start with.
NO_DOCROOT = "/nonexistent"
# A command procd runs ahead of uhttpd's reload, for longer than a
# daemon may take to restart: procd runs its trigger commands one at a
# time.
AHEAD = "orbyt-test-ahead"
AHEAD_SECONDS = 30
# A group honk's configuration routes to and no group block declares.
MISSING_GROUP = "no-such-group"


@dataclass(frozen=True, slots=True)
class Pushed:
    """The module's repository, pushed to its router, and the secrets pushed."""

    online: Online
    repository: ConfigRepository
    identity: Path
    wireguard_key: str

    @property
    def router(self) -> Router:
        """The router pushed to."""
        return self.online.router

    def push(self) -> subprocess.CompletedProcess[str]:
        """Push the repository as it is now."""
        return self.repository.push(self.router.address, self.identity)


def _state(router: Router) -> dict[str, str]:
    """Return what a push changes on the router, and the processes a reload restarts."""
    return {
        "pushed": router.run("cat /etc/orbyt-config/* /etc/honk/* | sha256sum"),
        "uci": router.run("uci export | sha256sum"),
        **{name: router.run(f"pidof {name} || true") for name in RESTARTED},
    }


def _secrets(
    pushed: Pushed,
    auth_key: str,
    share_users: tuple[dict[str, str], ...] = (SHARE_USER,),
) -> dict[str, object]:
    """Return the module's secrets with another Tailscale auth key and ``share_users``."""
    user, password = LOGIN
    return {
        "pppoe": {"username": user, "password": password},
        "wireguard": {"private_key": pushed.wireguard_key},
        "tailscale": {"auth_key": auth_key, "login_server": HEADSCALE_URL},
        "smb": {"users": list(share_users)},
    }


@contextmanager
def _recorded(router: Router, program: str, arguments: str) -> Generator[None]:
    """Have every run of ``program`` record its arguments in ``arguments`` meanwhile.

    ``program`` is a link to a binary that acts by the name it runs
    under: a wrapper in its place records the arguments, then runs the
    binary under that name with the same standard input.
    """
    name = PurePosixPath(program).name
    real = f"/tmp/orbyt-test-{name}"  # noqa: S108 (a path on the router)
    target = router.run(f"readlink {program}")
    router.run(
        f"mkdir -p {real} && ln -sf $(readlink -f {program}) {real}/{name}"
        f" && cat >{real}/wrapper <<'EOF'\n"
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >>{arguments}\n'
        f'exec {real}/{name} "$@"\n'
        "EOF\n"
        f"chmod 755 {real}/wrapper && ln -sf {real}/wrapper {program}"
    )
    try:
        yield
    finally:
        router.run(f"ln -sf {target} {program}")


def _pwddb_entry(router: Router, database: str, user: str) -> str:
    """Return ``user``'s line of the ksmbd password database at ``database``."""
    return router.run(f"grep '^{user}:' {database}")


def _assert_put_back(result: subprocess.CompletedProcess[str], name: str) -> None:
    """Assert that the push failed, and says that ``name``'s previous configuration is back."""
    assert result.returncode != 0, result.stderr
    assert f"{name} did not come back with the new configuration" in result.stderr, (
        result.stderr
    )
    assert "the previous one is back" in result.stderr, result.stderr


def _refused(pushed: Pushed, config: str) -> subprocess.CompletedProcess[str]:
    """Push honk's configuration as ``config``; assert that the push failed and changed nothing."""
    router = pushed.router
    before = _state(router)
    pushed.repository.write_proxy("config", config)
    try:
        result = pushed.push()
    finally:
        pushed.repository.discard()
    assert result.returncode != 0, result.stderr
    assert _state(router) == before
    return result


def _proxy_sha256(router: Router) -> str:
    return router.run("sha256sum /etc/honk/config.dae | cut -d' ' -f1")


@pytest.fixture(scope="module")
def pushed(
    trusted_ca: Online, harness_key: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Pushed]:
    """Fill in the repository, push it once, and wait until the tailnet has the router."""
    online = trusted_ca
    network = online.network
    clear(network)
    # tailscaled loads the trusted CAs once: after the test CA came.
    online.router.run("/etc/init.d/tailscale restart")
    repository = ConfigRepository.create(tmp_path_factory.mktemp("config"))
    user, password = LOGIN
    private, _ = key_pair()
    repository.write_secrets(
        {
            "pppoe": {"username": user, "password": password},
            "wireguard": {"private_key": private},
            "tailscale": {
                "auth_key": preauth_key(network),
                "login_server": HEADSCALE_URL,
            },
            "smb": {"users": [SHARE_USER]},
        }
    )
    repository.write_proxy("config", PROXY_CONFIG)
    repository.commit("the router's configuration")
    result = Pushed(online, repository, harness_key, private)
    first = result.push()
    assert first.returncode == 0, first.stderr
    yield result
    clear(network)


@spec(CAPABILITY, "Secrets stored encrypted", "Scan the private repository")
def test_no_secret_in_the_history(pushed: Pushed, tmp_path: Path) -> None:
    def leaks(directory: Path) -> str | None:
        """Return gitleaks' findings in the history of ``directory``, or None."""
        report = tmp_path / f"{directory.name}.json"
        scan = subprocess.run(
            ["gitleaks", "git", "--no-banner", "--report-path", report, directory],
            capture_output=True,
            text=True,
            check=False,
        )
        return None if scan.returncode == 0 else report.read_text() + scan.stderr

    repository = pushed.repository
    assert leaks(repository.directory) is None
    # The scanner does find a secret that went in plain.
    plain = ConfigRepository(tmp_path / "plain", repository.age_key)
    subprocess.run(
        ["git", "clone", "-q", repository.directory, plain.directory], check=True
    )
    (plain.directory / "secrets" / "pppoe.yaml").write_text(
        f"password: '{PLAIN_SECRET}'\n"
    )
    plain.commit("a secret in plain text")
    assert leaks(plain.directory) is not None


@spec(CAPABILITY, "Validate before pushing", "Syntax error in the proxy config")
def test_a_proxy_syntax_error_changes_nothing(pushed: Pushed) -> None:
    result = _refused(pushed, PROXY_CONFIG.replace("routing {", "routing {{", 1))
    assert "honk does not accept the configuration" in result.stderr
    assert "is unchanged" in result.stderr
    assert pushed.router.returncode(f"test -e {UPLOAD}") != 0


@spec(CAPABILITY, "Validate before pushing", "Configuration the proxy would refuse")
def test_a_configuration_honk_refuses_changes_nothing(pushed: Pushed) -> None:
    # It parses, and names a group no group block declares.
    result = _refused(pushed, PROXY_CONFIG.replace("-> proxy", f"-> {MISSING_GROUP}"))
    assert "honk does not accept the configuration" in result.stderr
    # honk's reason, by its code: its check names no value.
    assert "error[unknown-routing-target]" in result.stderr


@spec(CAPABILITY, "Validate before pushing", "Proxy files in dae's layout")
def test_a_repository_in_dae_s_layout_changes_nothing(pushed: Pushed) -> None:
    router = pushed.router
    before = _state(router)
    directory = pushed.repository.directory
    (directory / "dae").mkdir()
    (directory / "dae" / "config.dae.enc").write_bytes(
        (directory / "honk" / "config.dae.enc").read_bytes()
    )
    try:
        result = pushed.push()
    finally:
        pushed.repository.discard()
    assert result.returncode != 0, result.stderr
    assert "git mv dae honk" in result.stderr, result.stderr
    assert _state(router) == before


@spec(CAPABILITY, "Repeatable push results", "Repeated push")
def test_a_repeated_push_restarts_nothing(pushed: Pushed) -> None:
    router = pushed.router
    before = _state(router)
    result = pushed.push()
    assert result.returncode == 0, result.stderr
    for service in SERVICES:
        assert f"{service}: unchanged" in result.stderr
    assert _state(router) == before


@spec(CAPABILITY, "Validate before pushing", "A configuration that validates")
def test_a_push_leaves_no_change_uncommitted(pushed: Pushed) -> None:
    router = pushed.router
    key = shlex.quote(pushed.wireguard_key)
    # The WireGuard key, changed on the router since the push: the
    # network batch changes it again, though the push's files are as
    # they were. uci records no change for a value an option already
    # holds.
    router.run(
        "uci set network.wg0.private_key=changed-on-the-router && uci commit network"
    )
    try:
        result = pushed.push()
        assert result.returncode == 0, result.stderr
        for service in SERVICES:
            assert f"{service}: unchanged" in result.stderr
        assert router.run("uci changes") == ""
        # No file of uci's change directory holds a secret of the push.
        assert router.returncode(f"grep -rqF -- {key} /tmp/.uci") != 0
    finally:
        router.run(f"uci set network.wg0.private_key={key} && uci commit network")


@spec(
    CAPABILITY,
    "A push commits only its own changes",
    "Uncommitted change to a pushed package",
)
def test_a_push_beside_an_uncommitted_change_to_its_package_is_refused(
    pushed: Pushed,
) -> None:
    router = pushed.router
    key = shlex.quote(pushed.wireguard_key)
    # The WireGuard key, changed on the router since the push, for the
    # network batch to change network; and an uncommitted change to it,
    # as LuCI holds a change until it is saved.
    router.run(
        "uci set network.wg0.private_key=changed-on-the-router && uci commit network"
        " && uci set network.wan.mtu=1400"
    )
    try:
        before = _state(router)
        result = pushed.push()
        assert result.returncode != 0, result.stderr
        assert "uncommitted changes to network" in result.stderr, result.stderr
        assert "is unchanged" in result.stderr, result.stderr
        assert _state(router) == before
        assert "network.wan.mtu='1400'" in router.run("uci changes network")
    finally:
        router.run(
            f"uci revert network && uci set network.wg0.private_key={key} && uci commit network"
        )


@spec(
    CAPABILITY,
    "A push commits only its own changes",
    "Uncommitted change to another package",
)
def test_an_uncommitted_change_to_another_package_stays(pushed: Pushed) -> None:
    router = pushed.router
    committed = router.run("sha256sum /etc/config/system")
    router.run("uci set system.@system[0].description=uncommitted")
    # A changed batch, of uhttpd's configuration, that sets uhttpd's
    # home to what it is.
    home = router.run("uci get uhttpd.main.home")
    template = pushed.repository.directory / "uci" / "uhttpd.uci.tmpl"
    template.write_text(f"set uhttpd.main.home='{home}'\n")
    try:
        result = pushed.push()
        assert result.returncode == 0, result.stderr
        assert "uhttpd: pushed" in result.stderr, result.stderr
        changes = router.run("uci changes").splitlines()
        assert len(changes) == 1, changes
        assert changes[0].startswith("system."), changes
        assert changes[0].endswith(".description='uncommitted'"), changes
        assert router.run("sha256sum /etc/config/system") == committed
    finally:
        pushed.repository.discard()
        router.run("uci revert system")


@spec(CAPABILITY, "Roll back on service failure", "Service reload fails")
def test_a_service_that_fails_is_put_back(pushed: Pushed) -> None:
    router = pushed.router
    before = (
        router.run("uci get network.lan.ipaddr"),
        router.run("cat /etc/orbyt-config/network"),
    )
    # A batch uci takes but the LAN cannot come up with: without the
    # rollback, the router would be out of reach from the LAN.
    template = pushed.repository.directory / "uci" / "network.uci.tmpl"
    template.write_text(
        f"{template.read_text()}set network.lan.ipaddr='{BAD_LAN_ADDRESS}'\n"
    )
    try:
        result = pushed.push()
    finally:
        pushed.repository.discard()
        # The LAN was gone for a while, and the harness's connection
        # with it.
        router.disconnect()
    _assert_put_back(result, "network")
    assert (
        router.run("uci get network.lan.ipaddr"),
        router.run("cat /etc/orbyt-config/network"),
    ) == before
    assert (
        json.loads(router.run("ubus call network.interface.lan status"))["up"] is True
    )


@spec(CAPABILITY, "Secrets stored encrypted", "Secrets on the device")
def test_secrets_on_the_device_are_root_s(pushed: Pushed) -> None:
    router = pushed.router
    auth_key = preauth_key(pushed.online.network)
    # Another share user too: the push writes the SMB users again.
    pushed.repository.write_secrets(
        _secrets(pushed, auth_key, (SHARE_USER, ADDED_SHARE_USER))
    )
    router.detach(WATCH)
    try:
        with (
            _recorded(router, TAILSCALE, TAILSCALE_ARGUMENTS),
            _recorded(router, ADDUSER, ADDUSER_ARGUMENTS),
        ):
            result = pushed.push()
    finally:
        router.run(f"pkill -f '{MODES}' || true; pkill -f '{COMMANDS}' || true")
        pushed.repository.commit("another tailnet key and share user")
    assert result.returncode == 0, result.stderr
    # The entries of the listings: a file's line starts with "-", a
    # directory's with "d".
    modes = [
        line.split()[0]
        for line in router.run(f"cat {MODES}").splitlines()
        if line[:1] in {"-", "d"}
    ]
    assert modes
    assert set(modes) <= set(ROOT_ONLY), modes
    assert router.returncode(f"[ -e {UPLOAD} ]") != 0
    files = router.run("ls /etc/honk/* /etc/orbyt-config/tailscale.key").split()
    assert {router.run(f"ls -ln {file}").split()[0] for file in files} == {ROOT_ONLY[0]}
    # The key reaches tailscale in its file, and no command line sampled
    # holds it.
    assert "--auth-key=file:" in router.run(f"cat {TAILSCALE_ARGUMENTS}")
    assert auth_key not in router.run(f"cat {TAILSCALE_ARGUMENTS} {COMMANDS}")
    # A share user's password reaches ksmbd.adduser on its standard
    # input, never on a command line, and is the one it stores when
    # given it as -p's argument.
    added, password = ADDED_SHARE_USER["name"], ADDED_SHARE_USER["password"]
    assert added in router.run(f"cat {ADDUSER_ARGUMENTS}").split()
    assert password not in router.run(f"cat {ADDUSER_ARGUMENTS} {COMMANDS}")
    reference = "/tmp/orbyt-test-pwddb"  # noqa: S108 (a path on the router)
    router.run(
        f": >{reference} && ksmbd.adduser -P {reference} -p {shlex.quote(password)} {added} >&2"
    )
    entry = _pwddb_entry(router, "/etc/ksmbd/ksmbdpwd.db", added)
    assert entry == _pwddb_entry(router, reference, added), entry


@spec(CAPABILITY, "Roll back on service failure", "Tailscale login fails")
def test_a_refused_tailscale_login_is_put_back(pushed: Pushed) -> None:
    router = pushed.router
    until(
        lambda: _tailscale_running(router),
        timeout=TAILSCALE_TIMEOUT,
        what="tailscale up",
    )
    before = (
        router.run("tailscale ip -4"),
        router.run("cat /etc/orbyt-config/tailscale"),
    )
    pushed.repository.write_secrets(_secrets(pushed, REFUSED_KEY))
    try:
        result = pushed.push()
    finally:
        pushed.repository.discard()
    _assert_put_back(result, "tailscale")
    until(
        lambda: _tailscale_running(router),
        timeout=TAILSCALE_TIMEOUT,
        what="tailscale back",
    )
    assert (
        router.run("tailscale ip -4"),
        router.run("cat /etc/orbyt-config/tailscale"),
    ) == before


@contextmanager
def _command_ahead_of_reloads(router: Router, package: str) -> Generator[None]:
    """Have procd run a slow command, ahead of the reloads, on a change to ``package``."""
    condition = [
        "if",
        ["eq", "package", package],
        ["run_script", "/bin/sleep", str(AHEAD_SECONDS)],
    ]
    service = {"name": AHEAD, "triggers": [["config.change", condition, 0]]}
    router.run(f"ubus call service set {shlex.quote(json.dumps(service))}")
    try:
        yield
    finally:
        router.run(f'ubus call service delete \'{{"name": "{AHEAD}"}}\'')


@spec(
    CAPABILITY,
    "Roll back on service failure",
    "A service that stops with its new configuration",
)
def test_a_service_that_stops_is_put_back(pushed: Pushed) -> None:
    router = pushed.router
    before = router.run("uci get uhttpd.main.home")
    assert router.returncode("pidof uhttpd >/dev/null") == 0
    template = pushed.repository.directory / "uci" / "uhttpd.uci.tmpl"
    template.write_text(f"set uhttpd.main.home='{NO_DOCROOT}'\n")
    try:
        with _command_ahead_of_reloads(router, "uhttpd"):
            result = pushed.push()
    finally:
        pushed.repository.discard()
    _assert_put_back(result, "uhttpd")
    assert router.run("uci get uhttpd.main.home") == before
    until(
        lambda: router.returncode("pidof uhttpd >/dev/null") == 0,
        timeout=TAILSCALE_TIMEOUT,
        what="uhttpd running",
    )


@spec(CAPABILITY, "Roll back on service failure", "honk off before a failed push")
def test_a_honk_that_was_off_is_put_back_off(pushed: Pushed) -> None:
    router = pushed.router
    router.run("/etc/init.d/honk disable && /etc/init.d/honk stop")
    # A honk that does not come back while it starts at boot: its check
    # fails then, and passes once it is off again, as its own check
    # does.
    router.run(
        f"cp {PROXY_HEALTHCHECK} {PROXY_HEALTHCHECK}.real && printf '%s\\n' '#!/bin/sh'"
        f" '/etc/init.d/honk enabled || exit 0' 'exit 1' >{PROXY_HEALTHCHECK}"
    )
    pushed.repository.write_proxy("config", f"{PROXY_CONFIG}# Pushed again.\n")
    try:
        result = pushed.push()
        _assert_put_back(result, "honk")
        assert router.returncode("/etc/init.d/honk enabled") != 0
        assert router.run("pidof honk-core || true") == ""
        assert (
            _proxy_sha256(router) == hashlib.sha256(PROXY_CONFIG.encode()).hexdigest()
        )
    finally:
        pushed.repository.discard()
        router.run(
            f"mv {PROXY_HEALTHCHECK}.real {PROXY_HEALTHCHECK}"
            " && /etc/init.d/honk enable && /etc/init.d/honk start"
        )
        wait_proxy(router)


@spec(CAPABILITY, FIRMWARE_SETTINGS, "User config sets lan_interface")
def test_lan_interface_is_the_firmware_s(pushed: Pushed) -> None:
    result = _refused(
        pushed,
        PROXY_CONFIG.replace("global {\n", "global {\n    lan_interface: br-lan\n", 1),
    )
    assert FIRMWARE_SETTINGS_REFUSAL in result.stderr


@spec(CAPABILITY, FIRMWARE_SETTINGS, "User config sets data_dir")
def test_data_dir_is_the_firmware_s(pushed: Pushed) -> None:
    result = _refused(
        pushed,
        PROXY_CONFIG.replace("global {\n", "global {\n    data_dir: '/etc/honk'\n", 1),
    )
    assert FIRMWARE_SETTINGS_REFUSAL in result.stderr


# The spellings honk takes a boolean as true in, case aside.
TRUE_SPELLINGS = ("true", "Yes", "ON", "1")


@spec(
    CAPABILITY,
    "The proxy's native API only with a token",
    "Native API with password login",
)
@pytest.mark.parametrize("spelling", TRUE_SPELLINGS)
def test_the_native_api_takes_no_password_login(pushed: Pushed, spelling: str) -> None:
    api = NATIVE_API.replace(
        f"secret: '{NATIVE_API_TOKEN}'", f"password_auth: {spelling}"
    )
    result = _refused(pushed, PROXY_CONFIG + api)
    assert "native API needs a token" in result.stderr


@spec(
    CAPABILITY,
    "The proxy's native API only with a token",
    "Native API with configuration writes",
)
@pytest.mark.parametrize("spelling", TRUE_SPELLINGS)
def test_the_native_api_writes_no_configuration(pushed: Pushed, spelling: str) -> None:
    api = NATIVE_API.replace(
        "enabled: true\n", f"enabled: true\n        config_write: {spelling}\n", 1
    )
    result = _refused(pushed, PROXY_CONFIG + api)
    assert "configuration writes stay off" in result.stderr


@spec(
    CAPABILITY,
    "The proxy's native API only with a token",
    "Native API with a blank token",
)
def test_the_native_api_takes_no_blank_token(pushed: Pushed) -> None:
    # A real token, then a blank one: honk would take the last.
    api = NATIVE_API.replace(
        f"secret: '{NATIVE_API_TOKEN}'",
        f"secret: '{NATIVE_API_TOKEN}'\n        secret: ' '",
    )
    result = _refused(pushed, PROXY_CONFIG + api)
    assert "its secret is blank" in result.stderr


@spec(CAPABILITY, "SSH key authentication only", "No SSH key configured")
def test_no_password_login(pushed: Pushed, tmp_path: Path) -> None:
    router = pushed.router
    # A key the router does not know; root has a password it could log
    # in with.
    unknown = tmp_path / "unknown"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", unknown], check=True
    )
    router.run(
        f"printf '%s\\n%s\\n' {ROOT_PASSWORD} {ROOT_PASSWORD} | passwd root >/dev/null"
    )
    passwords = "logread -e 'Bad password' | wc -l"
    before = (_state(router), router.run(passwords))
    try:
        result = pushed.repository.push(router.address, unknown)
    finally:
        router.run("passwd -d root >/dev/null")
    assert result.returncode != 0
    assert "cannot log in" in result.stderr
    # Not one password was tried.
    assert (_state(router), router.run(passwords)) == before


def _tailscale_running(router: Router) -> bool:
    status = router.run("tailscale status --json 2>/dev/null || true")
    state: object = json.loads(status).get("BackendState") if status else None
    return state == "Running"


@spec(
    CAPABILITY,
    "Configuration persists across A/B upgrades",
    "Upgrade to the other slot",
)
def test_the_configuration_survives_an_upgrade(
    pushed: Pushed, upgrade_image: Path
) -> None:
    router = pushed.router
    until(
        lambda: _tailscale_running(router),
        timeout=TAILSCALE_TIMEOUT,
        what="tailscale up",
    )
    tailnet_address = router.run("tailscale ip -4")
    router.put(upgrade_image, UPGRADE_IMAGE)
    router.reboot(f"sysupgrade {UPGRADE_IMAGE}")
    pushed.online.reconnected()
    # The sandbox's CA is no configuration of the router's, and the
    # upgrade kept none of it: it comes again, and tailscaled, which
    # reads it once, anew.
    trust_ca(router, pushed.online.network.workdir)
    router.run("/etc/init.d/tailscale restart")
    user, password = LOGIN
    assert router.run("uci get network.wan.username") == user
    assert router.run("uci get network.wan.password") == password
    assert router.run("uci get network.wg0.private_key") == pushed.wireguard_key
    assert _proxy_sha256(router) == hashlib.sha256(PROXY_CONFIG.encode()).hexdigest()
    assert router.returncode("/etc/init.d/honk enabled") == 0
    wait_proxy(router)
    until(
        lambda: _tailscale_running(router),
        timeout=TAILSCALE_TIMEOUT,
        what="tailscale up",
    )
    assert router.run("tailscale ip -4") == tailnet_address
    assert (
        router.returncode(f"grep -q '^{SHARE_USER['name']}:' /etc/ksmbd/ksmbdpwd.db")
        == 0
    )
    # The new slot knows what was pushed: pushing again changes nothing.
    again = pushed.push()
    assert again.returncode == 0, again.stderr
    for service in SERVICES:
        assert f"{service}: unchanged" in again.stderr
