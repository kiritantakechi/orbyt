# Design

## Context

- `model.poll.until` is used 14 times; nine other waits are hand-made loops on `time.monotonic()` (ISP session and hang-up, `Netns` start, disk unplug, `Router.put`, `wait_ssh`, `wait_ready`, `wait_rebooted`, the drill), with poll intervals from 0.01 to 5 s, and seven callers attach diagnostics by hand (`except TimeoutError: error.add_note(...)`).
- Six subprocess wrappers differ in what they return and report; only `Netns.run` notes stderr. pytest 9 matches `pytest.raises(match=...)` against an exception's notes too.
- `Network.__enter__` builds bridges, taps and namespaces into an `ExitStack` that `__exit__` closes; Python does not call `__exit__` when `__enter__` raises, so a failure halfway leaves them. `Tailnet.join` undoes nothing on failure, `WireGuard.connect` does. The sandbox's daemons count as up when they have not exited within 0.5 s.
- Fourteen tests prefix `sleep 1;` to `Router.detach`, so that the SSH command returns before a reboot cuts its connection.
- Test modules whose last test leaves a Pod or the data disk for the module, or whose first test makes the module's first pull: test_dns, test_transparent_proxy, test_containers, test_data_disk, test_config_push, test_file_sharing.
- Constants written many times: `UPGRADE_IMAGE` in six files with the same five-step upgrade; `Path(__file__).resolve().parents[2]` in seventeen; `10.0.0.1` as four names; `pppoe-wan` 24 times; the ISP's resolver; the sandbox's directory layout in four modules, one in the device layer; EROFS' superblock offsets in `device/ab.py` (as `dd` offsets) and `sandbox/oci.py` (as a struct).
- `tests/build/test_boards.py`'s "Two boards in one tree" and "A fragment leaves a question for the next" skip without a build tree, which CI's system suite never has.
- `toolchain-key.sh`'s seven scenarios in `verified-elsewhere.toml` are dated experiments; the script is a function of git trees and files.

## Goals / Non-Goals

**Goals:**
- Every wait on a condition, through one helper; every failure carrying what explains it; every setup undone; every test runnable alone.
- One home for each fact the tests share.

**Non-Goals:**
- What the tests assert about the firmware, beyond the asymmetries and weak asserts named here.
- The harness's four layers: they stay as code-standards defines them; `model` keeps the repository checks, which read the repository as data, and their command-line tools share one report function instead of three `print`s.
- Test names' possessive `_s_`: the project's naming, applied throughout.
- Scenarios that the emulator cannot show and whose tests say so (a temperature series with no sensor, LuCI's 403 at the login).

## Decisions

### D1. One process wrapper

`model.process.run(*argv, timeout, input=None, env=None) -> str` captures both streams and, on failure, adds them as notes to the `CalledProcessError` (and the command line to the `TimeoutExpired`). `Netns.run`, `Router.run`'s local helpers, `keys._run`, `pki._openssl`, `vpn._wg`, `emu.run` and the direct `subprocess.run` calls with `check=True` use it. Tests that expect a failure match its output: the probe's refusal, ping's "Frag needed" with the path MTU, the signer's message (which replaces the separate `stderr` assert).

### D2. One form of wait

`until` gains `notes: Callable[[], Iterable[str]] | None`, called once when the limit passes and attached to the `TimeoutError`, and accepts a deadline shared by consecutive waits. The nine loops become `until` calls; `wait_rebooted` and `wait_ready` share one budget. The hand-attached diagnostics move into `notes`. `Router.detach` starts its command once the shell that launched it has exited (`while kill -0 $$; do sleep 1; done; command`), so callers no longer prefix `sleep 1;`. The tests' fixed sleeps become waits: the BBR test waits for the established flow; the health check's failing rounds come from a check that counts its own runs and passes at the round the test names; the tc hook test compares the programs' run counters over a bounded window; "stays at the prompt" names its duration and why.

### D3. Setups undone

`Network.__enter__` closes its stack when the setup fails halfway, as Python calls no `__exit__` for an `__enter__` that raised; `Netns` kills its holder before raising. `WireGuard.connect` and `Tailnet.join` are context managers whose end, or a failure on the way, undoes what they did (wg-peer's tunnel; ts-peer's login and the tailnet's nodes); the router's side goes back with its snapshot. The proxy's fixture calls `proxy_start` and a new `proxy_stop`, which waits until honk's process and programs are gone. The toolchain tests run their scripts in a host environment of their own, so that collecting them needs no build environment. Each sandbox daemon declares how it is ready (a port it listens on, a file it writes); `_daemon` waits for that with `until` and fails at once, with its output, if the process exits.

### D4. Independent tests

The modules that hand state from one test to the next stop doing so. The data disk's state is what a test asks for, the disk in (`pod`) or a boot without it (`without_disk`): function fixtures that bring the router there from whatever the test before left, so that the tests without the disk still share one boot while it stays out, and the `if port is None` repeats go. The file sharing module drains procd's trigger queue once after its setup and after each test (an autouse fixture), not at a test's start. The pull test pulls an image of its own (a stamped layer), so that it writes all of it whether or not the app Pod's image came first. The app Pod stays a module fixture that the module's end takes down with the router's reset; the tests after its first use pass beside it. The order comments go. Verified by running each module's tests one by one (`-k`), each module whole, and each module with its formerly last (or first) test run first.

### D5. Each fact once

- The router's paths in `device/paths.py` (`/tmp` once, with the one `noqa: S108`), `Router.upgrade(image, *options)` for the put, detach, wait sequence; `wait_logged(router, text)` for the health check's log waits.
- The repository's paths from `model.repository`; `ROUTER_ADDRESS`, a `LAN` network and `WAN_DEVICE` in one module; the ISP's resolver imported from `sandbox/isp`.
- The sandbox's layout as one object the network owns (`pki`, `inet`, a namespace's directory), passed to the device layer's trust and to the registry push; no `{workdir}/../pki` strings.
- `model/erofs.py`: the superblock's layout, from which `oci.py` reads and `ab.py` derives its `dd` offsets; one partition table.
- Each limit stays beside the wait it bounds, one name per fact: the share user's fixture moves into the one module that uses it (one `SMB_TIMEOUT`), and the boot limit is `device/ab`'s `BOOT_LIMIT`, which the unit test binds to U-Boot's and orbyt-slot's. A module of all the timeouts was weighed and dropped: of the harness's twenty limits five are used outside their module, the values stay as they are, and a limit read away from its wait loses its reason.

### D6. Modules with one job

`device/emu.py` splits into `device/prepare.py` (the build step and its command) and the runtime (`Console`, `Emulator`); helpers no caller uses go. `sandbox/releases.py` splits into its store (what tests change) and its server (built with `functools.partial`); its download log gets a lock. The router's clock moves to `device/clock.py`. The ISP's scripts and the containers' stress driver become files beside their modules, checked by shellcheck. The fake `gh` becomes `model/fake_gh.py`, reading its state from JSON; `Repository` is no longer frozen. `netprobe`'s `send` takes a count.

### D7. Asserts that prove their scenario

The download's shaping gets the upload's lower bound; MSS clamping and DNS learning get their IPv6 cases (if qosify learns AAAA answers, which its spec requires of DNS names, both families); a trial's failure asserts the reboot into the other slot and the failed check named in the result; the native API's "no answer" is a named constant. Duplicate tests become one test with two markers or get a check of their own. `test_nat`'s `Listener` resend: the loss it compensates is measured on the emulated path; with no loss, the resend goes, otherwise its cause is recorded beside it.

### D8. Build-tree tests and the cache key

A `build_tree` mark; CI's system suite runs `-m "not build_tree"`, and the firmware job runs `just test <board> -m build_tree` after its build. "Two boards in one tree" asserts what one board's build shows: its directories carry its board's id and no other's. A unit test builds a small git tree and checks that each input of `toolchain-key.sh` moves the key and that nothing else does; verified-elsewhere keeps only the CI runs.

### D9. Leftovers

PyYAML declared; tach pinned exactly (a tool); labgrid stays a range (a library, pinned by the lock); `LG_EMU_DIR` becomes `ORBYT_EMU_DIR`; the library code's `assert`s raise; `ubsan.report` returns its message and the device fixture fails the test; `BOOT_DISK` and `Router.poll` renamed where they clash (`BOOT_DEVICE`, `try_run`); `Router.poll` catches labgrid's connection failure, `ExecutionError` and timeouts only; one `GIT_IDENTITY`, one `repo_files`; the module order the conventions give; `LONG_DEVICE` named for its length.

## Risks / Trade-offs

- [A wide refactor of the harness] → each layer's change is followed by the suites that use it on the emulator before the next; the unit suite and `testing/` cover the helpers.
- [Waits replacing sleeps change timing] → each new wait keeps the old limit or a longer one; the suites run with the Mac's load sampled.
