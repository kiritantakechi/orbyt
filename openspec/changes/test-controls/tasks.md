# Tasks

## 1. The firmware tests (design D1, D2, D5)

- [x] 1.1 Check each of LRNG's interfaces on its own, with `/proc/sys/kernel/random/boot_id` as the control (`tests/firmware/test_base_system.py`).

  Verify: on the emulator, the old check passes for `boot_id` and an absent path together, the new check fails on `boot_id` alone, and "Check installed packages and executables" passes.
  Result (2026-11-17): on the emulated R4S, a scratch test (never committed) found the old check, `ls /proc/sys/kernel/random/boot_id /proc/lrng_type`, failing as it does for two absent paths, and the new check finding `boot_id`; the test passes.

- [x] 1.2 Quote the values `setenv` writes (`tests/wrt_tests/device/ab.py`), and read the stored boot command back before the reboot in "Custom boot command in persistent environment" (`tests/firmware/test_boot_rollback.py`).

  Verify: on the emulator, with the old `setenv` a value with a space leaves `wrt_boot` unset, with the new one it reads back whole; `test_boot_rollback.py` passes.
  Result (2026-11-17): with the old form, `wrt_ab_setenv wrt_boot echo wrt-hijacked` wrote `wrt_boot=echo` and no `wrt-hijacked`; with the quoted value the test reads both variables back before its reboot and passes. The rest of `test_boot_rollback.py` uses no value with a space; its runs of 2026-11-17 for trial-guards stand.

- [x] 1.3 Install the virtual package with the running kernel's own vermagic first, as the control of the refusal (`tests/firmware/test_kernel.py`).

  Verify: the kernel tests pass on the emulator.
  Result (2026-11-17): both kmod tests pass on the emulated R4S, the control installing and deleting the virtual package with the running kernel's version (`apk list --installed kernel`).

## 2. The network tests (design D3, D4, D6)

- [x] 2.1 Count the IPv4 packets that enter a device, at `pppoe-wan` for the PPP half of "Inbound packet with spoofed destination" (`tests/network/test_nat.py`).

  Verify: the NAT tests pass on the emulator.
  Result (2026-11-17): the network suite passes, 63 tests, the spoofed-inbound test counting its packet at `pppoe-wan`.

- [x] 2.2 Require the two uploads' rates together to lie between 80 % and 105 % of the shaped rate (`tests/network/test_qos.py`).

  Verify: the QoS tests pass on the emulator; with the test's rate set above what the emulator carries (a scratch run, never committed), the uploads fall below the band.
  Result (2026-11-17): the QoS tests pass in the network suite. Measured first, in a scratch test (never committed): shaped at 20 Mbit the uploads made 9.19 + 9.19 Mbit, cake dropping 803 packets and its `overlimits` at 47,543; shaped at 900 Mbit the emulator carried them at 44.0 + 47.6 Mbit, below the band, cake dropping 1 and its `overlimits` at 12,167. The first form of the change, `overlimits` rising, passed at 900 Mbit too, and went (design D4).

- [x] 2.3 Have `internet_zone` wait for the router's DNS answer for `direct.example.net` (`tests/wrt_tests/services/fixtures.py`).

  Verify: the network suite passes on the emulator.
  Result (2026-11-17): the network suite passes, 63 tests, and the storage and services suites, 47; `direct.example.net` is now `DIRECT_NAME` beside `DIRECT_TARGET`.

## 3. Traps and containers (design D7, D8)

- [x] 3.1 Add to `tests/unit/test_ubsan.py` the tests of `Traps` on a console record: a trap, then a reboot's banner, is reported; a trap in both the console and the kernel log is reported once, whole. Then have `Traps` read the console's record besides the kernel log (`tests/wrt_tests/device/ubsan.py`, `fixtures.py`).

  Verify: `spec-coverage --change test-controls` reports "A trap before a reboot" covered; the new tests fail before `Traps` changes and pass after; `just check` passes.
  Result (2026-11-17): covered, by `tests/quality/test_undefined_behavior.py`'s test of a trap and a reboot, which runs in a `ubsan` build and skips in the others, and by the unit tests. Before the change the unit test of a trap before a reboot failed (no trap), after it all seven pass; `just check` passes.

- [x] 3.2 Connect from the container to the internet probe server first, as the control of the refused connection to the LAN (`tests/services/test_containers.py`).

  Verify: the container tests pass on the emulator.
  Result (2026-11-17): the storage and services suites pass, 47 tests, the ruleset test's container reaching the internet's probe server before it is refused the LAN host.

## 4. Verification

- [x] 4.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.
  Result (2026-11-17): CI run 44049652730 passed on both boards in its first attempt, every changed test among the suites; recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub. The queue of 2026-11-17 is then done.
