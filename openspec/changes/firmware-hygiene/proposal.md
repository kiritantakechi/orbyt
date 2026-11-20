# Proposal

## Why

On 2026-11-20 the maintainer asked for the project to be checked as a whole and its band-aids replaced by fixes at their causes: elegant, symmetric, modern, no debt left. A review of the firmware side (`feed/`, `files/`, `config/`, `uboot/`) found code that works by accident or around a race instead of at its cause. The A/B upgrade's functions win over the target's only because their file sorts last, a rule that broke on 2026-11-19 when the rename sorted it first. orbyt-sync retries its downloads because honk may not hold the container bridge yet. honk sets its cgroup up twice because procd may delete it between the two. Some facts are also kept in two or three places: defaults in a config file and in code, U-Boot's watchdog block per board, the slots' partition numbers in four languages.

## What Changes

- **The A/B upgrade is handed off by name.** orbyt-ab's upgrade file defines `orbyt_ab_check_image`, `orbyt_ab_do_upgrade` and `orbyt_ab_copy_config`, as upstream's `legacy_sdcard_*` and `emmc_*` do, and rockchip's `platform.sh` calls them (patch 0004). No definition shadows another, and the file's name no longer matters: `z-orbyt-ab.sh` becomes `orbyt-ab.sh`. The whole-disk upgrade leaves rockchip's `platform.sh`.
- **Boot order stated, not relied on.** That the trial watchdog is the first boot script becomes a test on the image. The health check's claim to run after every other service goes; its checks wait on their own conditions.
- **Readiness instead of retries.** orbyt-sync starts once honk's datapath holds the container bridge, through the readiness test honk's health check uses. Its downloads keep a bounded retry for transport errors only, justified as such.
- **honk's cgroup set up once.** procd keeps a service's cgroup when a service of the same name replaces it (with patch 0047's), so honk's init no longer sets it up again in `service_started`.
- **Each fact in one place.** Option defaults live in the code that reads them, and the shipped config files carry only what differs. U-Boot's watchdog block is shared by the rockchip boards. The slots' partition map is checked to agree everywhere it is written. honk's kept rc.d links come from its own package, derived from its START and STOP. The sanitizer seed appends to the toolchain's flags instead of repeating them. The emulator's kmod exclusions are checked against the kernel overlay. The data disk's mount point comes from orbyt-data's library. Each package owns its first-boot defaults.
- **Shared helpers used.** The health check's result path and the monotonic clock come from `orbyt.ab`; `orbyt_data_mounted` is used wherever the test is spelled out; the health check runs its checks without a shell.
- **Leftovers.** An empty keyring fails the build; stale comments (R4S-only, the VPN zones) say what the code does; `release.seed` is named after what it selects.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `firmware/ab-upgrade`: the upgrade's functions are the platform's own, handed off by name: no file order decides which definition runs.
- `firmware/health-check`: the trial watchdog is the image's first boot script, asserted on the image; the checks wait on their own conditions, not on running last.
- `release/device-sync`: the sync starts once the datapath it goes through holds the container bridge.

## Impact

- `feed/utils/orbyt-ab` (upgrade file renamed and its functions, the health check, `orbyt.ab`), `patches/openwrt/0004` (rockchip `platform.sh`), a procd patch (cgroup of a replaced service), `feed/net/honk` (init, keep.d), `feed/utils/orbyt-sync`, `feed/utils/orbyt-data`, `feed/utils/orbyt-keyring`, `files/` (uci-defaults, keep.d, config files), `uboot/` (a shared rockchip fragment), `config/` (seeds).
- Tests: `firmware/test_ab_upgrade.py` (the hand-off), a boot-order test, `unit/` consistency tests (partition map, kmod exclusions, keep.d).
- A config-preserving upgrade from a current image keeps its configuration: no marker or kept file changes name.
