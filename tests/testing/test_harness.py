"""testing/harness: what checks the harness itself.

Scenarios and tests, the toolchain, data schemas, waits, failure
reports; and what bounds the harness's work on the router: commands
and login sessions that end with their time limit, setups undone when
they fail.
"""

import contextlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, cast

import pytest

from orbyt_tests import spec
from orbyt_tests.device.fixtures import claim
from orbyt_tests.device.paths import scratch
from orbyt_tests.device.router import SSH_PORT
from orbyt_tests.model import process
from orbyt_tests.model.boards import BOARDS_DIR, Description
from orbyt_tests.model.coverage import VerifiedElsewhere
from orbyt_tests.model.data import DataError, read_json, read_toml
from orbyt_tests.model.outputs import (
    EmulationSource,
    Manifest,
    Release,
    ToolchainRecord,
)
from orbyt_tests.model.poll import until
from orbyt_tests.model.repository import TESTS_DIR
from orbyt_tests.model.undefined_behavior import Diagnostic, Review
from orbyt_tests.sandbox.net import LAN_PREFIX, Daemon, Namespace, Netns, Port, ip
from orbyt_tests.services.fixtures import pytest_runtest_makereport
from orbyt_tests.services.vpn import WireGuard

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

    from orbyt_tests.device.emu import Emulator
    from orbyt_tests.device.router import Router
    from orbyt_tests.sandbox.net import Network
    from orbyt_tests.services.datapath import Online

CAPABILITY = "testing/harness"
# How long the kernel may take to destroy a namespace after its last
# process.
NAMESPACE_GONE = 10
FIXTURES = TESTS_DIR / "fixtures"
DEMO_SPEC = """## ADDED Requirements

### Requirement: Demo
#### Scenario: covered one
- **WHEN** a
- **THEN** b

#### Scenario: missing one
- **WHEN** a
- **THEN** b
"""
COVERED_TEST = """from orbyt_tests import spec


@spec("demo/widget", "Demo", "covered one")
def test_covered() -> None:
    pass
"""


def _python(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _tool(name: str) -> str:
    """Path of a tool installed in the tests' virtual environment."""
    return str(Path(sys.executable).with_name(name))


@pytest.fixture
def demo(tmp_path: Path) -> tuple[Path, Path]:
    """Return an OpenSpec tree with one change and a tests tree.

    The tests cover half of the change.
    """
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    spec_file = (
        openspec / "changes" / "demo-change" / "specs" / "demo" / "widget" / "spec.md"
    )
    spec_file.parent.mkdir(parents=True)
    spec_file.write_text(DEMO_SPEC)
    tests = tmp_path / "tests"
    (tests / "demo").mkdir(parents=True)
    (tests / "demo" / "test_widget.py").write_text(COVERED_TEST)
    return openspec, tests


def _coverage(
    openspec: Path, tests: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    return _python(
        *("-m", "orbyt_tests.model.coverage"),
        *("--openspec", str(openspec), "--tests", str(tests)),
        *args,
        cwd=tests,
    )


@spec(CAPABILITY, "One test per spec scenario", "Generate coverage report")
def test_coverage_report(demo: tuple[Path, Path]) -> None:
    openspec, tests = demo
    result = _coverage(openspec, tests, "--change", "demo-change")
    assert (
        "covered    demo/widget / Demo / covered one  demo/test_widget.py::test_covered"
        in (result.stdout)
    )
    assert "MISSING    demo/widget / Demo / missing one" in result.stdout
    assert "demo-change: no test for demo/widget / Demo / missing one" in result.stderr
    assert result.returncode == 1
    # Archived, the spec is the system as built: its scenarios need
    # their tests without being named.
    change = openspec / "changes" / "demo-change"
    (change / "specs" / "demo").rename(openspec / "specs" / "demo")
    shutil.rmtree(change)
    archived = _coverage(openspec, tests)
    assert "MISSING    demo/widget / Demo / missing one" in archived.stdout
    assert "error: no test for demo/widget / Demo / missing one" in archived.stderr
    assert archived.returncode == 1


@spec(CAPABILITY, "One test per spec scenario", "Marker names a missing scenario")
def test_dangling_marker_fails(demo: tuple[Path, Path]) -> None:
    openspec, tests = demo
    module = tests / "demo" / "test_widget.py"
    module.write_text(module.read_text().replace("covered one", "no such scenario"))
    result = _coverage(openspec, tests)
    assert result.returncode == 1
    assert "demo/test_widget.py::test_covered: @spec names no scenario" in result.stderr


def _wheel(directory: Path, name: str) -> Path:
    """Write a pure-Python wheel of ``name`` 1.0; return its path."""
    wheel = directory / f"{name}-1.0-py3-none-any.whl"
    dist_info = f"{name}-1.0.dist-info"
    files = {
        f"{name}/__init__.py": "",
        f"{dist_info}/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n",
        f"{dist_info}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: orbyt-tests\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n"
        ),
    }
    record = "".join(f"{path},,\n" for path in files) + f"{dist_info}/RECORD,,\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
        archive.writestr(f"{dist_info}/RECORD", record)
    return wheel


@spec(CAPABILITY, "Fixtures by layer", "Fixture defined in the root configuration")
def test_a_fixture_in_the_root_configuration_fails(demo: tuple[Path, Path]) -> None:
    openspec, tests = demo
    shutil.copytree(TESTS_DIR / "orbyt_tests", tests / "orbyt_tests")
    (tests / "conftest.py").write_text(
        "import pytest\n\n\n@pytest.fixture(scope='session')\n"
        "def local() -> int:\n    return 1\n"
    )
    result = _coverage(openspec, tests)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "conftest.py: defines the fixture local" in output, output


@spec(CAPABILITY, "Python toolchain locked by uv", "Lock file out of sync")
def test_stale_lock_is_rejected(tmp_path: Path) -> None:
    # Every script syncs or runs the tests project in locked mode ...
    scripts = (TESTS_DIR.parent / "scripts").glob("*.sh")
    uv_calls = [
        line
        for path in scripts
        for line in path.read_text().splitlines()
        if re.search(r"\buv (sync|run)\b", line) and "--no-sync" not in line
    ]
    assert uv_calls
    assert all("--locked" in line for line in uv_calls), uv_calls
    # ... and locked mode refuses a declaration the lock does not match.
    # The project is self-contained (a local wheel), so this holds
    # without any network.
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "probe-project"\nversion = "0"\ndependencies = []\n'
    )
    uv = ("uv", "--offline", "--directory", str(project))
    subprocess.run([*uv, "lock"], check=True, capture_output=True)
    wheel = _wheel(tmp_path, "probe")
    pyproject.write_text(
        pyproject.read_text().replace("[]", f'["probe @ {wheel.as_uri()}"]')
    )
    result = subprocess.run(
        [*uv, "sync", "--locked"], capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "needs to be updated" in result.stderr


@spec(CAPABILITY, "Python toolchain locked by uv", "Type error")
def test_type_error_is_reported(tmp_path: Path) -> None:
    shutil.copy(TESTS_DIR / "ty.toml", tmp_path / "ty.toml")
    (tmp_path / "broken.py").write_text('count: int = "three"\n')
    result = subprocess.run(
        [_tool("ty"), "check", "--output-format", "concise", "broken.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "broken.py:1:" in result.stdout


def _break(entry: dict[str, object], breakage: str) -> str:
    """Break ``entry`` in place; return the field that is wrong now."""
    if breakage == "unknown field":
        entry["colour"] = "red"
        return "colour"
    field = next(key for key, value in entry.items() if isinstance(value, str))
    entry[field] = 1
    return field


@dataclass(frozen=True, slots=True)
class _JsonFile:
    """A JSON data file the tests read, and how.

    One document, or a list of entries.
    """

    path: Path
    read: Callable[[Path], BaseModel | list[BaseModel]]

    def break_into(self, copy: Path, breakage: str) -> str:
        """Write a copy of the file with ``breakage``.

        Return where its problem lies.
        """
        match self.read(self.path):
            case list() as entries:
                dumped = [entry.model_dump(mode="json") for entry in entries]
                where = f"[0]: {_break(dumped[0], breakage)}"
                copy.write_text(json.dumps(dumped), encoding="utf-8")
            case document:
                dumped = document.model_dump(mode="json")
                where = _break(dumped, breakage)
                copy.write_text(json.dumps(dumped), encoding="utf-8")
        return where


@dataclass(frozen=True, slots=True)
class _TomlFile:
    """A TOML data file the tests read.

    The entries of one array of tables.
    """

    path: Path
    table: str
    model: type[BaseModel]

    def read(self, path: Path) -> list[BaseModel]:
        """Read ``path`` as this file is read."""
        return list(read_toml(path, self.table, self.model))

    def break_into(self, copy: Path, breakage: str) -> str:
        """Write a copy of the file, ``breakage`` in its first entry.

        Return where its problem lies.
        """
        text = self.path.read_text(encoding="utf-8")
        header = re.search(rf"^\[\[{self.table}\]\]\n", text, re.MULTILINE)
        assert header, self.path
        head, entry = text[: header.end()], text[header.end() :]
        if breakage == "unknown field":
            field, entry = "colour", f'colour = "red"\n{entry}'
        else:
            line = re.search(r'^(\w+) = ".*"$', entry, re.MULTILINE)
            assert line, self.path
            field = line.group(1)
            entry = f"{entry[: line.start()]}{field} = 1{entry[line.end() :]}"
        copy.write_text(head + entry, encoding="utf-8")
        return f"{self.table}[0]: {field}"


# Every data file the tests read (module-boundaries D7), a real one of
# each.
DATA_FILES = {
    "board description": _JsonFile(
        BOARDS_DIR / "r4s.json", lambda p: read_json(p, Description)
    ),
    "verified elsewhere": _TomlFile(
        TESTS_DIR / "verified-elsewhere.toml", "scenario", VerifiedElsewhere
    ),
    "reviewed warnings": _TomlFile(
        TESTS_DIR / "reviewed-warnings.toml", "warning", Review
    ),
    "manifest": _JsonFile(FIXTURES / "manifest.json", lambda p: read_json(p, Manifest)),
    "warnings report": _JsonFile(
        FIXTURES / "warnings.json", lambda p: list(read_json(p, list[Diagnostic]))
    ),
    "emulation source": _JsonFile(
        FIXTURES / "source.json", lambda p: read_json(p, EmulationSource)
    ),
    "toolchain record": _JsonFile(
        FIXTURES / "orbyt-toolchain.json", lambda p: read_json(p, ToolchainRecord)
    ),
    "release": _JsonFile(FIXTURES / "release.json", lambda p: read_json(p, Release)),
}


@spec(CAPABILITY, "One schema per data file", "Malformed data file")
@pytest.mark.parametrize("breakage", ["unknown field", "wrong type"])
@pytest.mark.parametrize("name", DATA_FILES)
def test_a_malformed_data_file_names_the_field(
    name: str, breakage: str, tmp_path: Path
) -> None:
    data = DATA_FILES[name]
    copy = tmp_path / data.path.name
    where = data.break_into(copy, breakage)
    with pytest.raises(DataError, match=re.escape(where)) as error:
        data.read(copy)
    problems = error.value.problems
    assert any(problem.startswith(f"{copy}: {where}: ") for problem in problems), (
        problems
    )


# Every kind of empty answer a probe may give while its condition does
# not hold.
EMPTY_ANSWERS = (None, False, 0, "", (), frozenset())


def _answers(*answers: object) -> Callable[[], object]:
    """Return a probe that gives ``answers`` one by one.

    Then it gives the last one forever.
    """
    remaining = list(answers)
    return lambda: remaining.pop(0) if len(remaining) > 1 else remaining[0]


@spec(CAPABILITY, "Waiting for a condition", "A probe answers empty first")
def test_a_wait_goes_on_through_empty_answers() -> None:
    assert (
        until(_answers("", [], "listening"), timeout=5, what="an answer", every=0)
        == "listening"
    )


@spec(CAPABILITY, "Waiting for a condition", "No answer within the time limit")
def test_a_wait_without_an_answer_names_what_it_waited_for() -> None:
    with pytest.raises(TimeoutError, match=re.escape("no listener within 0.2 s")):
        until(_answers(*EMPTY_ANSWERS), timeout=0.2, what="listener", every=0.01)


@spec(CAPABILITY, "Each wait has one form", "A wait that names its diagnostics")
def test_a_wait_past_its_limit_carries_what_its_caller_reports() -> None:
    with pytest.raises(
        TimeoutError, match=r"(?s)no listener within 0\.2 s.*ports: none"
    ):
        until(
            lambda: None,
            timeout=0.2,
            every=0.01,
            what="listener",
            notes=lambda: ["ports: none"],
        )

    def unreachable() -> list[str]:
        msg = "router gone"
        raise OSError(msg)

    # A report that fails says so, and the timeout stays the failure.
    with pytest.raises(
        TimeoutError, match=r"the report failed: OSError\('router gone'\)"
    ):
        until(lambda: None, timeout=0, what="listener", notes=unreachable)


@spec(
    CAPABILITY,
    "A failed command shows its output",
    "A command expected to fail fails otherwise",
)
def test_a_failed_command_carries_what_it_said() -> None:
    # The refusal a test expects, named by what the command said.
    with pytest.raises(subprocess.CalledProcessError, match="connection refused"):
        process.run("sh", "-c", "echo connection refused >&2; exit 1")
    # A timeout instead is no refusal, and its report shows what the
    # command said until then.
    with pytest.raises(subprocess.TimeoutExpired, match="still connecting"):
        process.run("sh", "-c", "echo still connecting; exec sleep 5", timeout=0.5)


# A server that binds its port a while after it starts.
SLOW_PORT = 7000
SLOW_SERVER = (
    sys.executable,
    "-c",
    (
        "import socket, time; time.sleep(2);"
        f" server = socket.create_server(('', {SLOW_PORT})); time.sleep(60)"
    ),
)


@spec(CAPABILITY, "The sandbox's daemons ready before use", "A daemon slow to bind")
def test_a_daemon_slow_to_bind_is_ready_once_started(tmp_path: Path) -> None:
    listening = ("-Hltn", f"sport = :{SLOW_PORT}")
    with Netns("slow") as netns:
        netns.start(Daemon(SLOW_SERVER, listening=listening), tmp_path)
        assert netns.run("ss", *listening).strip()


def _namespaces() -> set[str]:
    """Return the network namespaces the sandbox's processes are in."""
    held = set()
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            # A process may end while it is read.
            with contextlib.suppress(OSError):
                held.add(str((entry / "ns" / "net").readlink()))
    return held


@spec(
    CAPABILITY,
    "The sandbox's daemons ready before use",
    "A daemon that exits while it starts",
)
def test_a_namespace_whose_daemon_exits_is_taken_down(network: Network) -> None:
    held = _namespaces()
    broken = Namespace(
        "broken",
        ports=(Port("br-inet"),),
        daemons=(Daemon(("sh", "-c", "echo no configuration >&2; exit 3")),),
    )
    with pytest.raises(RuntimeError, match="broken: sh exited with 3 while starting"):
        network.add(broken)
    assert _namespaces() == held
    # The kernel destroys a namespace, and the veth pairs with an end
    # in it, after its last process.
    until(
        lambda: "v0-broken" not in ip("-o", "link", "show"),
        timeout=NAMESPACE_GONE,
        what="broken's link gone",
    )


# A detached command that ends without the reboot the harness then waits
# for.
NEVER_REBOOTING = "this command ends without a reboot"
SECTION = re.compile(r"(?ms)^--- (.+?)\n(.*?)(?=^--- |\Z)")


@spec(CAPABILITY, "Failures name the router's state", "A reboot that does not come")
def test_a_reboot_that_does_not_come_names_its_command(router: Router) -> None:
    previous_boot = router.boot_id()
    command = f"echo '{NEVER_REBOOTING}'; exit 3"
    router.detach(command)
    with pytest.raises(TimeoutError, match="no reboot of the router") as raised:
        router.wait_rebooted(previous_boot, timeout=10)
    command_note, output_note, console_note = raised.value.__notes__
    assert command_note == f"the reboot was to follow: {command}"
    assert output_note == f"its output, at {router.address}:\n{NEVER_REBOOTING}"
    assert console_note.startswith("the console since:")


# A lock that a process of a command holds, as orbyt-sync holds its own.
LOCK = scratch("orbyt-test.lock")
COMMAND_LIMIT = 3.0
LOCK_FREED = 10.0


@spec(
    CAPABILITY,
    "Commands on the router end with their time limit",
    "A command that overruns its time limit",
)
def test_a_command_past_its_time_limit_ends_on_the_router(router: Router) -> None:
    command = f"flock {LOCK} sleep 600 & wait"
    message = f"{command!r} did not finish within {COMMAND_LIMIT:g} s"
    with pytest.raises(TimeoutError, match=re.escape(message)):
        router.run(command, timeout=COMMAND_LIMIT)
    until(
        lambda: router.returncode(f"flock -n {LOCK} true") == 0,
        timeout=LOCK_FREED,
        what="the lock free",
    )


# Longer than a login takes on a busy host, zsh's first start included.
LOGIN_LIMIT = 90.0


@spec(
    CAPABILITY,
    "Commands on the router end with their time limit",
    "A login session that does not end",
)
def test_a_login_past_its_time_limit_shows_what_it_printed(router: Router) -> None:
    message = f"the login session did not end within {LOGIN_LIMIT:g} s"
    with pytest.raises(TimeoutError, match=re.escape(message)) as raised:
        router.login("echo session-started; sleep 600\n", timeout=LOGIN_LIMIT)
    assert "session-started" in str(raised.value)


# A limit far below what the disk takes: the test fails while it holds.
SLOWED_WRITES = 1 << 20


def _fail_while_slowed(emulator: Emulator) -> None:
    with emulator.throttled_writes(SLOWED_WRITES):
        msg = f"failed with writes limited to {emulator.write_limit()} B/s"
        raise RuntimeError(msg)


@spec(
    CAPABILITY,
    "What a test sets up, it takes down",
    "A test that fails while writes are slowed",
)
def test_writes_are_unlimited_after_a_failure(router: Router) -> None:
    with pytest.raises(RuntimeError, match=f"limited to {SLOWED_WRITES} B/s"):
        _fail_while_slowed(router.emulator)
    assert router.emulator.write_limit() == 0


# The tests above reset the router after them; the ones below use the
# module's router online, which a reset would take away (claim,
# test-fidelity D16).


def _call_report(
    item: object, outcome: Literal["passed", "failed"]
) -> pytest.TestReport:
    """Return what the services layer's report hook makes of a report.

    The report is a call's report on ``item``.
    """
    report = pytest.TestReport("demo", ("demo", 0, "demo"), {}, outcome, None, "call")
    call = pytest.CallInfo.from_call(lambda: None, "call")
    hook = pytest_runtest_makereport(cast("pytest.Item", item), call)
    next(hook)
    try:
        hook.send(report)
    except StopIteration as stopped:
        return cast("pytest.TestReport", stopped.value)
    msg = "the report hook did not return a report"
    raise AssertionError(msg)


@spec(
    CAPABILITY,
    "Failures name the router's state",
    "A failing test with the router online",
)
def test_a_failing_online_test_names_the_datapath(online: Online) -> None:
    item = SimpleNamespace(funcargs={"online": online})
    sections = dict(_call_report(item, "failed").sections)
    parts = dict(SECTION.findall(sections["datapath"]))
    assert "default via " in parts["client-a$ ip -6 route"]
    assert '"up": true' in parts["router$ ifstatus wan"]
    assert online.session.interface in parts["ISP sessions"]
    assert parts["ISP pppd log"].strip()
    assert _call_report(item, "passed").sections == []


# A table of the test's own on the router, which drops new connections
# to SSH: the router takes none, while the one open goes on
# (test-fidelity D14).
NO_NEW_SSH = "orbyt_test_no_new_ssh"
REPORT_SECONDS = 20.0


@spec(
    CAPABILITY,
    "Failures name the router's state",
    "A failing test with the router unreachable",
)
def test_a_report_of_an_unreachable_router_is_quick(online: Online) -> None:
    router = online.router
    hook = "{ type filter hook input priority -10; }"
    router.run(
        f"nft add table inet {NO_NEW_SSH}"
        f" && nft add chain inet {NO_NEW_SSH} input {shlex.quote(hook)}"
        f" && nft add rule inet {NO_NEW_SSH} input tcp dport {SSH_PORT}"
        " ct state new drop"
    )
    try:
        item = SimpleNamespace(funcargs={"online": online})
        started = time.monotonic()
        sections = dict(_call_report(item, "failed").sections)
        took = time.monotonic() - started
    finally:
        router.run(f"nft delete table inet {NO_NEW_SSH}")
    parts = dict(SECTION.findall(sections["datapath"]))
    assert parts["router"].startswith("(no new connection within")
    assert "default via " in parts["client-a$ ip -6 route"]
    assert online.session.interface in parts["ISP sessions"]
    assert took < REPORT_SECONDS


@spec(CAPABILITY, "What a test sets up, it takes down", "A setup that fails halfway")
def test_a_setup_that_fails_halfway_leaves_no_tunnel(online: Online) -> None:
    peer = online.network["wg-peer"]
    # A route the peer refuses, after its tunnel exists.
    with (
        pytest.raises(subprocess.CalledProcessError, match="no-such-route"),
        WireGuard.connect(online, ["no-such-route"]),
    ):
        pass
    assert peer.run("ip", "-o", "link", "show", "type", "wireguard") == ""
    with WireGuard.connect(online, [LAN_PREFIX]):
        pass
    assert peer.run("ip", "-o", "link", "show", "type", "wireguard") == ""


@spec(CAPABILITY, "Fixtures by layer", "A test that would reset a module's router")
def test_a_reset_of_a_module_s_router_is_refused() -> None:
    held = cast("Router", SimpleNamespace(holder="testing.test_demo"))
    with pytest.raises(
        pytest.fail.Exception, match=re.escape("testing.test_demo keeps the router")
    ):
        claim(held)
    claim(cast("Router", SimpleNamespace(holder=None)))
