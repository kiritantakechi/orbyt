# Tasks

## 1. The environment before the first boot script (design D2)

- [ ] 1.1 Move `31-wrt-ab` into the preinit hook `/lib/preinit/81_wrt_ab_environment` (a subshell function on `preinit_main`, its messages on the kernel log), delete the uci-defaults script, and update `docs/ab-layout.md` where it names it.

  Verify: `just check` passes (shellcheck); no file in the repository names `31-wrt-ab` but the archived changes; on the emulator, `test_boot_rollback.py`'s two tests of "The system writes the environment where the bootloader reads it" pass.

## 2. The trial supervisor (design D1)

- [ ] 2.1 Add the tests of "A boot script hangs during a trial boot" and "The environment at the first boot script" to `tests/firmware/test_boot_rollback.py` (design D5).

  Verify: `spec-coverage --change trial-guards` reports both covered; on the emulator, before 2.2, both fail (the hung trial slot never reboots; no line of `wrt-trial`).

- [ ] 2.2 Add `wrt-trial` (ucode), its init script at `START=00`, the `trial` section of `/etc/config/wrt-ab` with `deadline 900`, the package's description and release; describe the deadline in `docs/ab-layout.md`.

  Verify: the tests of 2.1 and the rest of `test_boot_rollback.py` pass on the emulator; `just check` passes.

## 3. Upgrades and confirmations during a trial (design D3, D4)

- [ ] 3.1 Add the tests of "Upgrade during a trial boot" (`tests/firmware/test_ab_upgrade.py`) and "A switch written during the checks" (`tests/firmware/test_health_check.py`).

  Verify: `spec-coverage --change trial-guards` reports both covered; before 3.2, both fail on the emulator (the upgrade writes the other slot; the health check confirms the running one).

- [ ] 3.2 Have `platform_check_image` refuse an image while the environment names the running slot on trial, and `wrt-healthcheck` read the environment again before it confirms; describe both in `docs/ab-layout.md`.

  Verify: the tests of 3.1 and the rest of `test_ab_upgrade.py` and `test_health_check.py` pass on the emulator; `just check` passes.

## 4. Verification

- [ ] 4.1 Build both boards and run the `upgrade` and `boot` suites (`firmware/test_ab_upgrade.py firmware/test_ab_layout.py firmware/test_boot_rollback.py firmware/test_health_check.py`) on the emulator for the R4S, then CI's build on this change's branch for both boards.

  Verify: every test passes locally and in CI; the CI run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub; then start push-isolation.
