# Tasks

## 1. The firmware tests (design D1, D2, D5)

- [ ] 1.1 Check each of LRNG's interfaces on its own, with `/proc/sys/kernel/random/boot_id` as the control (`tests/firmware/test_base_system.py`).

  Verify: on the emulator, the old check passes for `boot_id` and an absent path together, the new check fails on `boot_id` alone, and "Check installed packages and executables" passes.

- [ ] 1.2 Quote the values `setenv` writes (`tests/wrt_tests/device/ab.py`), and read the stored boot command back before the reboot in "Custom boot command in persistent environment" (`tests/firmware/test_boot_rollback.py`).

  Verify: on the emulator, with the old `setenv` a value with a space leaves `wrt_boot` unset, with the new one it reads back whole; `test_boot_rollback.py` passes.

- [ ] 1.3 Install the virtual package with the running kernel's own vermagic first, as the control of the refusal (`tests/firmware/test_kernel.py`).

  Verify: the kernel tests pass on the emulator.

## 2. The network tests (design D3, D4, D6)

- [ ] 2.1 Count the IPv4 packets that enter a device, at `pppoe-wan` for the PPP half of "Inbound packet with spoofed destination" (`tests/network/test_nat.py`).

  Verify: the NAT tests pass on the emulator.

- [ ] 2.2 Require the two uploads' rates together to lie between 80 % and 105 % of the shaped rate (`tests/network/test_qos.py`).

  Verify: the QoS tests pass on the emulator; with the test's rate set above what the emulator carries (a scratch run, never committed), the uploads fall below the band.

- [ ] 2.3 Have `internet_zone` wait for the router's DNS answer for `direct.example.net` (`tests/wrt_tests/services/fixtures.py`).

  Verify: the network suite passes on the emulator.

## 3. Traps and containers (design D7, D8)

- [ ] 3.1 Add to `tests/unit/test_ubsan.py` the tests of `Traps` on a console record: a trap, then a reboot's banner, is reported; a trap in both the console and the kernel log is reported once, whole. Then have `Traps` read the console's record besides the kernel log (`tests/wrt_tests/device/ubsan.py`, `fixtures.py`).

  Verify: `spec-coverage --change test-controls` reports "A trap before a reboot" covered; the new tests fail before `Traps` changes and pass after; `just check` passes.

- [ ] 3.2 Connect from the container to the internet probe server first, as the control of the refused connection to the LAN (`tests/services/test_containers.py`).

  Verify: the container tests pass on the emulator.

## 4. Verification

- [ ] 4.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub. The queue of 2026-11-17 is then done.
