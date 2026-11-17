# Design

## Context

- The tests drive the emulated router over SSH (`router.run`, `router.returncode`, `router.poll`), the LAN clients and the ISP in network namespaces (`online.client()`, `isp`), and read the serial console's record (`router.emulator.console`: `mark()`, `text(since)`), which a thread drains into memory and a log for as long as the session runs, across reboots, power cuts and returns to the snapshot.
- `wrt_tests.device.ab.setenv` runs `wrt_ab_setenv` with its pairs joined by spaces, unquoted; `wrt_ab_setenv` feeds `printf '%s %s\n' "$@"` to `fw_setenv -s -`, which reads a name and the rest of the line as its value.
- The `ubsan` image turns on `debug.exception-trace`; arm64 reports each unhandled trap with `pr_info` (`<comm>[<pid>]: unhandled exception: … User debug trap …`, then the registers). The image keeps the kernel's console level at 7 (`CONFIG_CONSOLE_LOGLEVEL_DEFAULT`, no `quiet`, no sysctl lowering `kernel.printk`), so the reports reach the console. `wrt_tests.device.ubsan.parse` reads them with or without the console's timestamps.
- qosify shapes `pppoe-wan` with cake; `tc -s qdisc show` counts, per qdisc, the packets the shaper held back (`overlimits`).
- dnsmasq's init script reloads through procd, which restarts the instance after the command returns; until then the old instance listens.

## Goals / Non-Goals

**Goals:**
- Each of the eight tests fails when what it checks is broken, and shows in the same run that the thing it watches took part.

**Non-Goals:**
- New behavior of the image: every change is to the tests and their harness.
- Traps the kernel's rate limit keeps from the log (ten in five seconds): the same limit applies to `dmesg`, and a burst of traps fails the test with the first ten.

## Decisions

### D1. Each path absent on its own (T1)

The test checks every path of LRNG's interfaces with `[ -e <path> ]` on its own and expects each absent; as its control, the same check finds `/proc/sys/kernel/random/boot_id`, the standard interface beside LRNG's, present.

### D2. `setenv` quotes its values (T2)

`setenv` quotes each value for the shell (`shlex.quote`), so that `wrt_ab_setenv` receives a name and its whole value as two words. The test of a stored boot command reads `bootcmd` and `wrt_boot` back with `getenv` before it reboots, so that the boot that ignores them follows an environment that holds them.

### D3. The PPP half counts its packets (T4)

`_frames_at` becomes a counter of the IPv4 packets that enter a device (`meta protocol ip`, which a PPP device's packets carry without an Ethernet header, as the WAN port's do with one). The PPP half counts at `pppoe-wan` and asserts that its packet arrived, as the Ethernet half asserts its frame.

### D4. The shaper is what limited the uploads (T5)

Besides being fair to each other, the two uploads' rates together must lie between 80 % and 105 % of the shaped rate: below goes cake's overhead and TCP's back-off, above iperf's own count of what it sent. Uploads that something slower than the shaper holds back, the emulator's speed, fall below it and fail. Measured on the VM (2026-11-17): shaped at 20 Mbit, 9.19 + 9.19 Mbit, 92 %; shaped at 900 Mbit, the emulator carried them at 44.0 + 47.6 Mbit, so the test's 20 Mbit has more than four times its rate in hand.

Alternatives considered:
- Cake's `overlimits`, the packets its shaper held back: it rose at both rates (47,543 at 20 Mbit, 12,167 at 900 Mbit), bursts of segmentation offload outrunning any rate for a moment.
- Cake's drops (803 and 1): its AQM drops on a standing queue, but a single drop at 900 Mbit leaves no clean threshold.

### D5. The same install with the running kernel's vermagic (T6)

Before the refused install, the test installs the virtual package with the running kernel's own dependency, as the installed kernel package provides it (`apk info --provides kernel`), checks it is installed and deletes it; then the foreign vermagic must be refused.

### D6. Waiting for the answer the exception lets through (T8)

`internet_zone` waits until the router's DNS answers a LAN client's query for `direct.example.net` with its documentation-range address, which the rebind protection blocks until the restarted dnsmasq has the exception; a listening socket alone no longer ends the wait.

### D7. Traps from the console's record too (T9)

`Traps` reads the console's record besides `dmesg`. The record holds every report the kernel printed in the session, whether the router rebooted, lost its SSH session or returned to its snapshot since, and reading it needs no answer from the router; `dmesg`, when the router answers, holds the current boot's reports whole at once, where the console may still be receiving one at a test's end. A report is one trap by its process, pid and kernel time, taken from `dmesg` first, and returned once. The fixtures keep calling it after booting, after each test and around each module.

Alternatives considered:
- The console alone: a report still on its way over the serial line when a test ends would fail the next test instead.
- Reading `dmesg` before each reboot: the reboots happen inside tests, and a panic or a watchdog reset gives no time.
- Failing a test whose read of `dmesg` fails: a test that reboots the router would still lose the traps before its reboot.

### D8. The container's `nc` connects where it may (T10)

Before the refused connection to the LAN host, the same `podman exec <container> nc` connects to the internet probe server the container reaches in "Container reaches the internet", and gets its answer.

### D9. Showing each test fixed

For each test, a run before its change and one after, on the emulator, or for D7 the unit tests of `Traps`:
- T1: the old check, given `/proc/sys/kernel/random/boot_id` and an absent path, passes; the new one fails on the present path.
- T2: with the old `setenv`, `wrt_boot` reads back unset; with the new one, it holds the value.
- T4, T5, T8: the new assertions hold on the image as it is; T5's fail with the shaper set above what the emulator carries (at 900 Mbit the uploads reached 92 Mbit together).
- T6, T10: the controls pass on the image as it is.
- T9 (`tests/unit/test_ubsan.py`): a console record with a trap, then a reboot's banner, reports the trap; one record read twice reports each trap once.

## Risks / Trade-offs

- [A host too slow to carry 16 Mbit through the emulator] → Then the test fails, as it should: its fairness would not be the shaper's.
- [The console falls behind under load] → Its thread drains it continuously; a report not yet read when a test ends is read after the next test, as a trap in a fixture is.
