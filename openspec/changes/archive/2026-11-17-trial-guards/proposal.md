# Proposal

## Why

A trial boot is decided by the health check, which starts after every other boot script has returned (`START=99`). procd runs the boot scripts one at a time and bounds only their `stop` and `shutdown` runs, never `boot`, and it goes on feeding the watchdog meanwhile. A trial slot whose boot hangs before the health check, in a script that waits for a device or a daemon that never forks or in one of its uci-defaults, is therefore neither confirmed nor rebooted: U-Boot never counts another boot, and the slot never rolls back. That is exactly the kind of image the A/B slots exist to survive.

An upgrade started during a trial writes the other slot, the only one known to be good, while the running slot is still unconfirmed; the health check then confirms the running slot with a blind write of `boot_slot`, which takes back the switch the upgrade (or a manual switch) wrote in the meantime. A review of the router's code on 2026-11-17 found both.

## What Changes

- **A trial boot has a deadline the boot order cannot hold off.** The first boot script starts a supervisor that, on a trial boot, waits until a deadline counted on the monotonic clock from the kernel's start (`wrt-ab.trial.deadline`, 900 s by default), and reboots when the slot is then still on trial and the health check has recorded no result for the boot. Every such reboot counts toward rollback, as a failed check does. It reports to the kernel log, which the console shows even when no service has started. procd's shutdown cancels the boot scripts still running, so that a reboot completes while one hangs: until now it waited for them, and a boot script that never returned kept a reboot from ever completing.
- **The U-Boot environment is reachable before the first boot script.** Its access is configured in preinit, right after the configuration is restored, from the copies the bootloader names on the kernel command line, in place of the uci-defaults script `31-wrt-ab`, which runs only in the middle of the boot and, after an upgrade without kept configuration, only once that boot has got that far.
- **No upgrade while the running slot is on trial.** sysupgrade refuses, before it writes anything, an image to be written while the running slot awaits confirmation, naming the trial: until then the other slot is the one rollback returns to.
- **A confirmation takes back nothing.** The health check reads the environment again just before it confirms, and confirms only while it is as the checks found it; a switch written meanwhile stays.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `firmware/boot-rollback`: hangs before the health check become counted reboots (the trial deadline); the environment's access is configured before the first boot script.
- `firmware/health-check`: a confirmation only while the environment still names the running slot on trial.
- `firmware/ab-upgrade`: no upgrade while the running slot is on trial.

## Impact

- `feed/utils/wrt-ab`: a new program `wrt-trial` and its init script (`START=00`); `/lib/preinit/81_wrt_ab_environment` in place of `/etc/uci-defaults/31-wrt-ab`; `wrt-healthcheck`'s confirmation; `lib/upgrade/wrt-ab.sh`'s image check; `/etc/config/wrt-ab`'s `trial` section; the package's description and release.
- Tests: `tests/firmware/test_boot_rollback.py` (a trial boot whose boot script hangs rolls back; the environment reachable at the first boot script after an upgrade without kept configuration), `test_health_check.py` (a switch written during the checks stays), `test_ab_upgrade.py` (an upgrade refused during a trial). The rollback test of a hung boot takes three deadlines, set short in the test.
- `docs/` describing the A/B slots and the health check.
- procd: an OpenWrt patch (`patches/openwrt/0048`) carrying a procd patch, so that a shutdown cancels the boot scripts still running instead of waiting for them, and procd's release; `docs/patches.md`.
- No change to U-Boot or to the image layout.
