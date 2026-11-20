"""The emulated router under test (design D13).

Commands run over SSH: the runner reaches the router's LAN address from
inside the sandbox. ``reset`` returns the emulator to its post-boot
snapshot.
"""

import json
import re
import shlex
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from labgrid.driver import ExecutionError

from orbyt_tests.device.clock import set_clock
from orbyt_tests.device.paths import UPGRADE_IMAGE, scratch
from orbyt_tests.model.poll import until
from orbyt_tests.sandbox.net import ip

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from labgrid import Target
    from labgrid.driver import SSHDriver

    from orbyt_tests.device.emu import Emulator

SSH_PORT = 22
# Terminal control in a login session's output: CSI sequences and
# carriage returns.
_TERMINAL_CONTROL = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\r")
BOOT_TIMEOUT = 600.0
READY_MARK = "- init complete -"
# The kernel's last words before the machine restarts.
RESTART_MARK = "reboot: Restarting system"
BOOT_ID = "cat /proc/sys/kernel/random/boot_id"
# A connection the router stopped answering: labgrid says so before it
# runs a command, and ssh exits with this status.
DEAD_CONNECTION = "Keepalive no longer running"
NO_CONNECTION = "Timeout while waiting for ssh connection"
SSH_FAILED = 255
# Each command runs in a session of its own, whose shell records its PID
# here: dropbear runs every command of a connection in the connection's
# one session, and labgrid gives up on a command past its time limit
# without ending it, which would go on holding what it holds, such as
# orbyt-sync's lock (test-fidelity D9).
COMMAND_PID = scratch("orbyt-tests.pid")
# How long a failure's report waits for a new connection to the router
# before it says that the router does not answer (test-fidelity D10).
REACHABLE_TIMEOUT = 5
# How long a new connection is tried: the emulator stops answering while
# the disk it runs from catches up with a burst of writes.
RECONNECT_TIMEOUT = 60.0
# How long a file's copy to the router may take.
COPY_TIMEOUT = 600
# How long an interactive login may take: zsh's first start after a boot
# builds its completion dump in /tmp, 21 to 26 s under TCG on an idle
# host and several times that on a busy one (2026-10-03); later logins
# take 7 to 9 s.
LOGIN_TIMEOUT = 180.0
# The serial console's shell answers a knock with this line, and a
# script's end with that one; the typed commands, which the console
# echoes, hold neither.
CONSOLE_READY = "console-ready"
CONSOLE_END = "console-end"
CONSOLE_KNOCK = 15.0
# preinit's offer of failsafe mode on the console, and its answer to the
# key.
FAILSAFE_PROMPT = r"Press the \[f\] key and hit \[enter\] to enter failsafe mode"
FAILSAFE_MARK = r"- failsafe -"
FAILSAFE_TIMEOUT = 120.0
# Where a detached command's output goes on the router, which the reboot
# it leads to clears; and how much of the console a reboot that does not
# come shows (failure-diagnostics D1, D2).
DETACHED_LOG = scratch("orbyt-detached.log")
CONSOLE_LINES = 60


def _port_open(address: str, port: int) -> bool:
    try:
        with socket.create_connection((address, port), timeout=2):
            return True
    except OSError:
        return False


@dataclass(frozen=True, slots=True)
class Detached:
    """A command detached on the router.

    It records what the command was, where it ran, and the console's
    mark then.
    """

    command: str
    address: str
    console_mark: int


class Router:
    """Run commands on the router and wait for it."""

    def __init__(self, target: Target, emulator: Emulator, key: Path) -> None:
        """Bind to the SSHDriver of ``target`` on ``emulator``.

        Log in with ``key``.

        root has no password on a fresh router, and dropbear lets it in
        without one; the key logs in once it has one.
        """
        self.target = target
        self.emulator = emulator
        self.key = key
        self.ssh: SSHDriver = target.get_driver("SSHDriver", activate=False)
        self.ssh.keyfile = str(key)
        self.address = str(target.get_resource("NetworkService").address)
        self.detached: Detached | None = None
        # The module whose fixtures keep the router from test to test,
        # if one does.
        self.holder: str | None = None

    def _connected(self) -> SSHDriver:
        self.target.activate(self.ssh)
        return self.ssh

    def disconnect(self) -> None:
        """Close the SSH connection, e.g. before the state jumps."""
        self.target.deactivate(self.ssh)

    def _run(self, command: str, timeout: float) -> tuple[list[str], list[str], int]:
        """Run ``command`` over SSH, on a new connection if one died.

        labgrid refuses a command on a dead connection before running
        it, so running it on a new one runs it once. Past ``timeout``
        the command's session goes, with every process in it, and the
        command fails as a timeout.
        """
        session = f"echo $$ >{COMMAND_PID}; exec setsid sh -c {shlex.quote(command)}"
        try:
            try:
                result = self._connected().run(session, timeout=timeout)
            except ExecutionError as error:
                if DEAD_CONNECTION not in str(error):
                    raise
                self.disconnect()
                result = self._connected().run(session, timeout=timeout)
        except subprocess.TimeoutExpired:
            # A router that does not take the kill has nothing running
            # for us either.
            self.try_run(f'kill -KILL -- -"$(cat {COMMAND_PID})"')
            msg = f"{command!r} did not finish within {timeout:g} s"
            raise TimeoutError(msg) from None
        return cast("tuple[list[str], list[str], int]", result)

    def run(self, command: str, *, timeout: float = 60) -> str:
        """Run a shell command on the router and return its stdout.

        Fail on a non-zero exit.
        """
        stdout, stderr, code = self._run(command, timeout)
        if code != 0:
            msg = f"{command!r} exited {code}: {'\n'.join(stderr)}"
            raise AssertionError(msg)
        return "\n".join(map(str, stdout))

    def try_run(self, command: str, *, timeout: float = 30) -> str | None:
        """Run a shell command if the router answers; return its stdout.

        Return None if the router does not answer or the command fails.

        For states the router passes through while it reboots, when SSH
        comes and goes, or hangs while the old system goes down.
        """
        try:
            stdout, _, code = self._connected().run(command, timeout=timeout)
        except ExecutionError:
            # A command cut short: its time limit, or its connection's.
            self.disconnect()
            return None
        except Exception as error:
            # A connection that never came up: labgrid raises it bare.
            if str(error) != NO_CONNECTION:
                raise
            self.disconnect()
            return None
        if code != 0:
            self.disconnect()
            return None
        return "\n".join(map(str, stdout))

    def returncode(self, command: str, *, timeout: float = 60) -> int:
        """Run a shell command on the router; return its exit status."""
        _, _, code = self._run(command, timeout)
        return int(code)

    def _ssh(self, *options: str) -> list[str]:
        return [
            "ssh",
            *options,
            "-o",
            "BatchMode=yes",
            "-i",
            str(self.key),
            f"root@{self.address}",
        ]

    def reachable(self, timeout: int = REACHABLE_TIMEOUT) -> bool:
        """Return whether the router takes a new SSH connection in time.

        The connection must open within ``timeout`` and run a command.

        A fresh connection, apart from labgrid's, which waits two
        minutes for one.
        """
        try:
            subprocess.run(
                [*self._ssh("-o", f"ConnectTimeout={timeout}"), "true"],
                capture_output=True,
                check=True,
                timeout=2 * timeout,
            )
        except subprocess.CalledProcessError, subprocess.TimeoutExpired:
            return False
        return True

    def login(self, script: str, *, timeout: float = LOGIN_TIMEOUT) -> str:
        """Log in interactively, type ``script``; return the output.

        The login has a terminal.

        This is a real login shell, unlike run(), so /etc/profile and
        the zsh hand-over apply. The script should end with ``exit``. A
        session still running at ``timeout`` is ended, and fails as a
        timeout with what it showed (test-fidelity D9).
        """
        with subprocess.Popen(
            self._ssh("-tt"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ) as session:
            stdin, stdout = session.stdin, session.stdout
            if stdin is None or stdout is None:
                msg = "ssh has no pipes"
                raise RuntimeError(msg)
            # Read while the session runs: a long output would fill the
            # pipe and stall ssh. The thread alone appends; the list is
            # read after it ended.
            output: list[str] = []
            reader = threading.Thread(
                target=lambda: output.append(stdout.read()), name="login"
            )
            reader.start()
            stdin.write(script)
            stdin.flush()
            # Keep stdin open: at end of input ssh would end the session
            # before the shell has read the script. The script's own
            # exit ends it.
            try:
                session.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # The router's shell goes with ssh: its pseudo-terminal
                # hangs up.
                session.kill()
                session.wait()
                reader.join()
                shown = _TERMINAL_CONTROL.sub("", "".join(output))
                msg = (
                    f"the login session did not end within {timeout:g} s;"
                    f" it showed:\n{shown}"
                )
                raise TimeoutError(msg) from None
            reader.join()
        return _TERMINAL_CONTROL.sub("", "".join(output))

    def console(self, script: str, *, timeout: float = LOGIN_TIMEOUT) -> str:
        """Run ``script`` in the serial console's shell; return output.

        For a router that ssh cannot reach. Enter activates the
        console's shell, whose login takes a while, so a knock repeats
        until the shell answers. A console that never answers, or never
        finishes, is said so after what it showed meanwhile.
        """
        console = self.emulator.console
        since = console.mark()
        deadline = time.monotonic() + timeout

        def shows(line: str, mark: int, limit: float) -> bool:
            remaining = min(limit, deadline - time.monotonic())
            try:
                console.wait_for(
                    rf"(?m)^{line}\r?$", since=mark, timeout=max(remaining, 0.0)
                )
            except TimeoutError:
                return False
            return True

        self.emulator.send_keys("\n")
        while True:
            mark = console.mark()
            self.emulator.send_keys(
                f"echo '{CONSOLE_READY[:4]}''{CONSOLE_READY[4:]}'\n"
            )
            if shows(CONSOLE_READY, mark, CONSOLE_KNOCK):
                break
            if time.monotonic() >= deadline:
                return f"{console.text(since)}\n(no shell answered on the console)"
        mark = console.mark()
        self.emulator.send_keys(
            f"{script}; echo '{CONSOLE_END[:4]}''{CONSOLE_END[4:]}'\n"
        )
        if not shows(CONSOLE_END, mark, timeout):
            return f"{console.text(since)}\n(the console did not finish the script)"
        return _TERMINAL_CONTROL.sub("", console.text(mark))

    def put(self, local: Path, remote: str) -> None:
        """Copy a local file to the router over ssh.

        dropbear has no sftp server.

        A connection the router does not take is tried again for a
        while; any other failure fails at once.
        """
        refused: list[str] = []

        def copied() -> bool:
            with local.open("rb") as source:
                copy = subprocess.run(
                    [*self._ssh(), f"cat > {shlex.quote(remote)}"],
                    stdin=source,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=COPY_TIMEOUT,
                )
            said = copy.stderr.decode(errors="replace").strip()
            if copy.returncode not in {0, SSH_FAILED}:
                failure = subprocess.CalledProcessError(copy.returncode, copy.args)
                failure.add_note(said)
                raise failure
            refused[:] = [said]
            return copy.returncode == 0

        until(
            copied,
            timeout=RECONNECT_TIMEOUT,
            every=2,
            what=f"copy of {local.name} to the router",
            notes=lambda: refused,
        )

    def wait_ssh(self, timeout: float = BOOT_TIMEOUT) -> None:
        """Wait until the router answers on SSH in any mode."""
        self.disconnect()
        until(
            lambda: _port_open(self.address, SSH_PORT),
            timeout=timeout,
            every=2,
            what=f"SSH at {self.address}:{SSH_PORT}",
        )

    def wait_ready(self, timeout: float = BOOT_TIMEOUT) -> None:
        """Wait until SSH answers and procd has run every init script.

        Then set the clock.
        """
        deadline = time.monotonic() + timeout
        self.wait_ssh(timeout)
        # procd logs through ulog, which writes to logd (not the kernel
        # log) once logd runs, as it does long before init completes.
        self.wait_logged(READY_MARK, timeout=deadline - time.monotonic(), every=2)
        set_clock(self)

    def logged(self, text: str, *, by: str | None = None) -> bool:
        """Return whether the system log holds ``text`` since the boot.

        ``by`` is a pattern of logread's -e that the line matches, such
        as its sender's name.
        """
        log = "logread" if by is None else f"logread -e {shlex.quote(by)}"
        return self.returncode(f"{log} | grep -qF -- {shlex.quote(text)}") == 0

    def wait_logged(
        self, text: str, *, by: str | None = None, timeout: float, every: float = 1
    ) -> None:
        """Wait until the system log holds ``text``.

        ``by`` narrows the log as ``logged`` does.
        """
        until(
            lambda: self.logged(text, by=by),
            timeout=timeout,
            every=every,
            what=f"{text!r} in the log",
        )

    def http(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        timeout: float = 30,
    ) -> tuple[int, str]:
        """GET ``path`` (POST ``data``) from the router's web server.

        Return the status and the body.
        """
        request = urllib.request.Request(
            f"http://{self.address}{path}", headers=headers or {}, data=data
        )
        try:
            # Always http://<router address>; no other scheme is ever
            # built.
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return int(response.status), str(
                    response.read().decode(errors="replace")
                )
        except urllib.error.HTTPError as error:
            return int(error.code), str(error.read().decode(errors="replace"))

    def detach(self, command: str) -> None:
        """Start a command that outlives the connection.

        Such commands are reboot, sysupgrade and the like.

        It starts once the shell that started it has exited, so that
        the command's answer is back over SSH before what it does to the
        router cuts the connection (test-hygiene D2). Its output goes to
        a file on the router, which the reboot it leads to clears; a
        command that does not reboot the router leaves it for the wait
        to show (failure-diagnostics D1).
        """
        self.detached = Detached(command, self.address, self.emulator.console.mark())
        self.run(
            f"(while kill -0 $$ 2>/dev/null; do sleep 1; done; {command})"
            f" >{DETACHED_LOG} 2>&1 </dev/null &"
        )

    def trigger_commands(self) -> list[dict[str, object]]:
        """Return the commands procd's triggers queued and not ended."""
        report = json.loads(self.run("ubus call service trigger_commands"))
        return cast("list[dict[str, object]]", report["commands"])

    def boot_id(self) -> str:
        """Return the kernel's boot ID, which changes at every boot."""
        return self.run(BOOT_ID)

    def wait_rebooted(self, previous_boot: str, timeout: float = BOOT_TIMEOUT) -> None:
        """Wait until the router has booted after ``previous_boot``.

        The router must also be ready.

        The old system may still answer while it shuts down, and the
        reboot may cut or hang the connection in the middle of a
        command; each only means waiting on. Only a new boot ID is the
        new system: waiting for it to be ready, which sets its clock,
        starts then, never on the old one.
        """
        deadline = time.monotonic() + timeout
        until(
            lambda: (
                (boot := self.try_run(BOOT_ID)) is not None and boot != previous_boot
            ),
            timeout=timeout,
            every=2,
            what="reboot of the router",
            notes=self._detached_notes,
        )
        self.wait_ready(deadline - time.monotonic())

    def _detached_notes(self) -> list[str]:
        """Return what the harness can see of the last detached command.

        (failure-diagnostics D2)

        The command, its output as the system it ran on still holds it,
        and the console since; a part that cannot be had says so.
        """
        detached = self.detached
        if detached is None:
            return ["no command was detached on the router"]
        with self.moved_to(detached.address):
            output = self.try_run(f"cat {DETACHED_LOG}")
        shown = (
            f"its output, at {detached.address}:\n{output}"
            if output is not None
            else f"no system answered at {detached.address}"
        )
        console = self.emulator.console.text(detached.console_mark)
        lines = _TERMINAL_CONTROL.sub("", console).splitlines()[-CONSOLE_LINES:]
        return [
            f"the reboot was to follow: {detached.command}",
            shown,
            "the console since:\n" + "\n".join(lines),
        ]

    def reboot_into_failsafe(self) -> None:
        """Reboot into failsafe mode and wait until SSH answers.

        Failsafe mode is taken at the console's offer.
        """
        console = self.emulator.console
        since = console.mark()
        self.detach("reboot")
        console.wait_for(FAILSAFE_PROMPT, since=since, timeout=BOOT_TIMEOUT)
        self.emulator.send_keys("f\n")
        console.wait_for(FAILSAFE_MARK, since=since, timeout=FAILSAFE_TIMEOUT)
        self.wait_ssh()

    def start_upgrade(self, image: Path, *options: str) -> None:
        """Copy ``image`` to the router and have sysupgrade write it.

        sysupgrade runs with ``options``; the caller waits for what
        comes of it.
        """
        self.put(image, UPGRADE_IMAGE)
        self.detach(shlex.join(["sysupgrade", *options, UPGRADE_IMAGE]))

    def upgrade(self, image: Path, *options: str) -> None:
        """Upgrade the router to ``image``; wait until it is back.

        sysupgrade runs with ``options``.
        """
        previous_boot = self.boot_id()
        self.start_upgrade(image, *options)
        self.wait_rebooted(previous_boot)

    def reboot(
        self, command: str = "reboot", *, while_off: Callable[[], object] | None = None
    ) -> None:
        """Run ``command`` and wait until the router is back.

        ``command`` must end in a reboot.

        ``while_off`` runs between the end of the old system and the
        next boot: hardware changed then is changed with the power off,
        after the old system has written out and unmounted everything.
        """
        previous_boot = self.boot_id()
        mark = self.emulator.console.mark()
        self.detach(command)
        if while_off is not None:
            self.emulator.console.wait_for(
                RESTART_MARK, since=mark, timeout=BOOT_TIMEOUT
            )
            while_off()
        self.wait_rebooted(previous_boot)

    @contextmanager
    def moved_to(self, address: str) -> Generator[None]:
        """Reach the router at another LAN address inside the block."""
        service = self.target.get_resource("NetworkService")
        original = self.address
        self.disconnect()
        service.address = self.address = address
        try:
            yield
        finally:
            self.disconnect()
            service.address = self.address = original

    def reset(self) -> None:
        """Return to the state right after boot, at the time of now.

        That state is the emulator's snapshot.

        The runner forgets the router's link-layer address: the router
        at its snapshot may have another one than since (failsafe
        mode's), and nothing on the link says so (snapshot-return D1).
        """
        self.disconnect()
        self.emulator.restore()
        ip("neigh", "flush", "to", self.address)
        set_clock(self)
