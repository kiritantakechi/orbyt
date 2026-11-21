# Tasks

## 1. The A/B upgrade handed off by name (design D1)

- [x] 1.1 Add the hand-off scenario to `tests/firmware/test_ab_upgrade.py`: with the A/B upgrade's file renamed to sort first, a valid image is written to the inactive slot only and an image for another device is refused before anything is written.

  Verify: `spec-coverage --change firmware-hygiene` reports it covered; on the emulated R4S it fails before 1.2 and passes after. Seen 2026-11-21 on the R4S's ci build of 5b320c3, its A/B file (`wrt-ab.sh`) renamed to sort first: platform.sh's own check passed the valid image and also an image for another device, and began its whole-disk upgrade of it; the suite's run passes it on the image with 0050.

- [x] 1.2 Rename `z-orbyt-ab.sh` to `orbyt-ab.sh` with its functions as `orbyt_ab_check_image`, `orbyt_ab_do_upgrade` and `orbyt_ab_copy_config`; add patch 0050 making rockchip's `platform.sh` the hand-off, keeping `REQUIRE_IMAGE_METADATA=1`; the tests source the upgrade files as sysupgrade does; update docs/ab-layout.md and orbyt-brand D1's citation.

  Verify: `just patch` applies; `firmware/test_ab_upgrade.py`, `test_boot_rollback.py` and the release suite's upgrade from local files pass on the emulated R4S.

## 2. Boot order and readiness (D2, D3, D4)

- [x] 2.1 Add the boot-order test (the image's first boot script is `S00orbyt-trial`) and drop the health check init's claim to run last.

  Verify: the test passes on the image; `spec-coverage` covers "The trial watchdog starts first".

- [x] 2.2 Add `honk_holds` to honk's package, use it in `50-honk`, and make `orbyt-sync` wait for it on `podman0` when honk is enabled; reword `fetch`'s retry as a transport retry.

  Verify: the device-sync scenario "The sync starts before the proxy" passes on the emulator (the sync started with honk stopped sends nothing until honk holds the bridge); the release suite passes.

- [x] 2.3 Pin procd's removal of a replaced service's cgroup on the emulator (the window the honk init's comment describes), have honk's instance set its cgroup up itself (`honk-start`), and drop honk's `service_started` setup.

  Verify: the pin's record in design D4 (seen 2026-11-21: 4 of 30 restarts unpinned without the setup, each where procd freed the service); 20 restarts of a pinned honk keep its cpuset; the transparent proxy suite passes.

## 3. Defaults, helpers and layout facts (D5, D6, D7)

- [x] 3.1 Drop the code's copies of the shipped values (orbyt-sync; einat's init and health check), failing on a missing option; bind the trial deadline's and the health check's safety fallbacks, and `orbyt-slot`'s boot limit, to their sources by a unit test.

  Verify: `just check`; the unit test passes and fails when one value is changed; the health check, device-sync and NAT tests pass on the emulator.

- [x] 3.2 Export the result path and the monotonic clock from `orbyt.ab` and use them; use `orbyt_data_mounted` and `ORBYT_DATA` wherever the test or the path is spelled out; run the health check's checks as argument vectors, after checking how the image's ucode reports a killed child.

  Verify: the base system's ucode compile test passes; the health check suite passes on the emulator.

- [x] 3.3 Share the rockchip boards' U-Boot watchdog block, fix the R4S-only comments, and add the partition-map consistency test.

  Verify: both boards' U-Boot configs are unchanged (`diffconfig` compared before and after); the unit test passes and fails when one copy of the map is changed.

- [x] 3.4 honk's keep.d entry from its package (START and STOP), the seeds' append form for `ubsan.seed`, the kmod exclusion test, `release.seed` renamed `device-sync.seed`.

  Verify: the image's sysupgrade.conf list holds the same paths as before; the ubsan and ci profiles merge to the same `.config` as before; the unit tests pass.

- [x] 3.5 orbyt-data writes its fstab stub alone (`80-orbyt-data`); ksmbd's hardening in its template (packages/0015); the data disk's paths from orbyt-data's library.

  Verify: the file-sharing and data-disk suites pass on the emulator; the image's ksmbd.conf is unchanged.

## 4. Leftovers (D8)

- [x] 4.1 The keyring's build check, `manifest`'s strict mode, orbyt-metrics' description, the partition pair read with `read`, the `shellcheck source=` placements, the VPN zones' comment.

  Verify: `just check`; an orbyt-keyring build without keys fails.

## 5. Verification

- [x] 5.1 `just check`, the unit and quality suites, and the firmware, release, services and network suites on the emulated R4S, the Mac's load gated and sampled.

  Verify: every test passes; the run's load samples are recorded with the results. Seen 2026-11-21: the R4S's whole suite at f8e8668, 21:54 to 02:01Z, 599 passed and 13 failed; the failures were the harness's (try_run's timeout, three assertions, the resolver's IPv6 record, two reviewed theme classes, the stale R6S tree) and pass on their fixes, re-run on the R4S. The Mac's 1-minute load over 246 samples: median 6.7, 90th percentile 9.2, two samples over 20 (34.4 at most).

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification (2026-11-19: CI only for releases); its run is recorded for this change in docs/ci.md.
- Archive after orbyt-brand, orbyt-theme, nixpkgs-2605 and python-style, in that order, then patch-hygiene, test-hygiene and tooling-hygiene follow.
