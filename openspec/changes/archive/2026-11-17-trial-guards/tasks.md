# Tasks

## 1. The environment before the first boot script (design D2)

- [x] 1.1 Move `31-wrt-ab` into the preinit hook `/lib/preinit/81_wrt_ab_environment` (a subshell function on `preinit_main`, its messages on the kernel log), delete the uci-defaults script, and update `docs/ab-layout.md` where it names it.

  Verify: `just check` passes (shellcheck); no file in the repository names `31-wrt-ab` but the archived changes; on the emulator, `test_boot_rollback.py`'s two tests of "The system writes the environment where the bootloader reads it" pass.
  Result (2026-11-17): `just check` passes, the preinit hooks now among shellcheck's files (they have no shebang, so shfmt's file finder skipped them; 86_wrt_data_mountpoint gained a source directive); only this change's own artifacts name `31-wrt-ab`; both tests pass on the emulator, with the four modules of 4.1.

## 2. The trial supervisor (design D1)

- [x] 2.1 Add the tests of "A boot script hangs during a trial boot" and "The environment at the first boot script" to `tests/firmware/test_boot_rollback.py` (design D5).

  Verify: `spec-coverage --change trial-guards` reports both covered; on the emulator, before 2.2, both fail (the hung trial slot never reboots; no line of `wrt-trial`).
  Result (2026-11-17): both covered. The red run on main's image (load around 13 on the Mac) failed the first-boot test before its assertion, `sysupgrade -n`'s ubus call timing out, and a rerun without load stopped at the session's first boot; without `wrt-trial` its line cannot appear. The hang test's red run is that of 2.3: on an image without design D6 it never reached the rollback, locally and on both boards in CI.

- [x] 2.2 Add `wrt-trial` (ucode), its init script at `START=00`, the `trial` section of `/etc/config/wrt-ab` with `deadline 900`, the package's description and release; describe the deadline in `docs/ab-layout.md`.

  Verify: the tests of 2.1 and the rest of `test_boot_rollback.py` pass on the emulator; `just check` passes.
  Result (2026-11-17): the first-boot test and the rest of `test_boot_rollback.py` pass; the hang test failed until 2.3 (its first trial boot's reboot never completed); with 2.3, all pass; `just check` passes.

- [x] 2.3 Add the OpenWrt patch `patches/openwrt/0048` carrying the procd patch of design D6 (a shutdown cancels the boot scripts still running; procd's release), and its entry in `docs/patches.md`.

  Verify: with procd 6, the test of "A boot script hangs during a trial boot" fails on the emulator, its first trial boot staying in procd's shutdown; with procd 7 it passes, and so do the rest of `test_boot_rollback.py` and the suites of 4.1.
  Result (2026-11-17): with procd 6 the four modules gave 43 passed and the hang test failed after its 30 minutes, the first trial boot's reboot announced by `wrt-trial` at 60 s and never completed; a probe of that boot (never committed) printed the environment's copies, intact, every 5 s from the hung script, which ran on with the system at `- shutdown -` from 61 s to 659 s. CI run 43976186041 failed the same test on both boards (26 passed, 1 failed in each boot job). With procd 7 the hang test passes alone (each hung trial boot reboots 7 s after its deadline: SIGTERM, SIGKILL, reboot; the third exceeds the bootlimit and slot A is confirmed), and the four modules pass, 44 tests.

## 3. Upgrades and confirmations during a trial (design D3, D4)

- [x] 3.1 Add the tests of "Upgrade during a trial boot" (`tests/firmware/test_ab_upgrade.py`) and "A switch written during the checks" (`tests/firmware/test_health_check.py`).

  Verify: `spec-coverage --change trial-guards` reports both covered; before 3.2, both fail on the emulator (the upgrade writes the other slot; the health check confirms the running one).
  Result (2026-11-17): both covered; on main's image both failed: sysupgrade went on with the upgrade instead of refusing, so its command never returned, and the health check never logged that it left the switch in place.

- [x] 3.2 Have `platform_check_image` refuse an image while the environment names the running slot on trial, and `wrt-healthcheck` read the environment again before it confirms; describe both in `docs/ab-layout.md`.

  Verify: the tests of 3.1 and the rest of `test_ab_upgrade.py` and `test_health_check.py` pass on the emulator; `just check` passes.
  Result (2026-11-17): both pass with the rest of both modules; `just check` passes.

## 4. Verification

- [x] 4.1 Build both boards and run the `upgrade` and `boot` suites (`firmware/test_ab_upgrade.py firmware/test_ab_layout.py firmware/test_boot_rollback.py firmware/test_health_check.py`) on the emulator for the R4S, then CI's build on this change's branch for both boards.

  Verify: every test passes locally and in CI; the CI run is recorded in `docs/ci.md`.
  Result (2026-11-17): locally on the R4S, the four modules pass with procd 7, 44 tests in 1 h 30 min; with procd 6 the hang test had failed (2.3). CI run 44002274413 passed on both boards in its second attempt, the first failing the R6S's firmware job on a Nix download before it built; run 43976186041, before patch 0048, failed the hang test on both. Both recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub; then start push-isolation.
