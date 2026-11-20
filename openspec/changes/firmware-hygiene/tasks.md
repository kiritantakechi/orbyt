# Tasks

## 1. The A/B upgrade handed off by name (design D1)

- [ ] 1.1 Add the hand-off scenario to `tests/firmware/test_ab_upgrade.py`: with the A/B upgrade's file renamed to sort first, a valid image is written to the inactive slot only and an image for another device is refused before anything is written.

  Verify: `spec-coverage --change firmware-hygiene` reports it covered; on the emulated R4S it fails before 1.2 (the stock whole-disk check refuses the valid image) and passes after.

- [ ] 1.2 Rename `z-orbyt-ab.sh` to `orbyt-ab.sh` with its functions as `orbyt_ab_check_image`, `orbyt_ab_do_upgrade` and `orbyt_ab_copy_config`; make patch 0004 change rockchip's `platform.sh` into the hand-off, keeping `REQUIRE_IMAGE_METADATA=1`; update docs/ab-layout.md, docs/patches.md's 0004 entry and orbyt-brand D1's citation.

  Verify: `just patch` applies; `firmware/test_ab_upgrade.py`, `test_boot_rollback.py` and the release suite's upgrade from local files pass on the emulated R4S.

## 2. Boot order and readiness (D2, D3, D4)

- [ ] 2.1 Add the boot-order test (the image's first boot script is `S00orbyt-trial`) and drop the health check init's claim to run last.

  Verify: the test passes on the image; `spec-coverage` covers "The trial watchdog starts first".

- [ ] 2.2 Add `honk_holds` to honk's package, use it in `50-honk`, and make `orbyt-sync` wait for it on `podman0` when honk is enabled; reword `fetch`'s retry as a transport retry.

  Verify: the device-sync scenario "The sync starts before the proxy" passes on the emulator (the sync started with honk stopped sends nothing until honk holds the bridge); the release suite passes.

- [ ] 2.3 Pin procd's removal of a replaced service's cgroup on the emulator (the window the honk init's comment describes), fix it in procd, and drop honk's `service_started` setup.

  Verify: with every CPU busy, 20 rounds of `/etc/init.d/honk restart` keep honk's cpuset; the transparent proxy suite passes; docs/patches.md records the window and the evidence.

## 3. Defaults, helpers and layout facts (D5, D6, D7)

- [ ] 3.1 Move each option default into the code that reads it and drop the copies from the shipped config files (orbyt-sync, orbyt-ab, einat); name `bootlimit` in `uboot/orbyt-ab.env` and read it in `orbyt-slot`.

  Verify: `just check`; the health check, device-sync and NAT tests pass on the emulator; `orbyt-slot` prints the bootlimit U-Boot uses.

- [ ] 3.2 Export the result path and the monotonic clock from `orbyt.ab` and use them; use `orbyt_data_mounted` and `ORBYT_DATA` wherever the test or the path is spelled out; run the health check's checks as argument vectors, after checking how the image's ucode reports a killed child.

  Verify: the base system's ucode compile test passes; the health check suite passes on the emulator.

- [ ] 3.3 Share the rockchip boards' U-Boot watchdog block, fix the R4S-only comments, and add the partition-map consistency test.

  Verify: both boards' U-Boot configs are unchanged (`diffconfig` compared before and after); the unit test passes and fails when one copy of the map is changed.

- [ ] 3.4 honk's keep.d entry from its package (START and STOP), the seeds' append form for `ubsan.seed`, the kmod exclusion test, `release.seed` renamed `device-sync.seed`.

  Verify: the image's sysupgrade.conf list holds the same paths as before; the ubsan and ci profiles merge to the same `.config` as before; the unit tests pass.

- [ ] 3.5 orbyt-data writes its fstab stub alone; ksmbd's hardening through its UCI options or an owned template.

  Verify: the file-sharing and data-disk suites pass on the emulator; the image's ksmbd.conf is unchanged.

## 4. Leftovers (D8)

- [ ] 4.1 The keyring's build check, `manifest`'s strict mode, orbyt-metrics' description, the partition pair read with `read`, the `shellcheck source=` placements, the VPN zones' comment.

  Verify: `just check`; an orbyt-keyring build without keys fails.

## 5. Verification

- [ ] 5.1 `just check`, the unit and quality suites, and the firmware, release, services and network suites on the emulated R4S, the Mac's load gated and sampled.

  Verify: every test passes; the run's load samples are recorded with the results.

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification (2026-11-19: CI only for releases); its run is recorded for this change in docs/ci.md.
- Archive after orbyt-brand, orbyt-theme, nixpkgs-2605 and python-style, in that order, then patch-hygiene, test-hygiene and tooling-hygiene follow.
