# Design

## Context

- `wrt-healthcheck` decides a trial boot: started by its init script at `START=99`, it checks until everything passes or its total time (300 s) is up, then confirms the slot or reboots. Nothing else reboots a trial boot but the watchdog, after a kernel hang, and a kernel panic.
- procd runs the boot scripts from its own queue, one at a time (`rcS.c`: `max_running_tasks = 1`). It bounds a script's `stop` and `shutdown` runs (15 s, then 10 s to end), never its `boot` run, and keeps feeding the watchdog from its own loop while a script runs. A procd service's instance starts as soon as its init script has run: it does not wait for the queue.
- A shutdown runs the `K` scripts in that same queue, which `rcS()` sets up anew with libubox's `runqueue_init()`: that empties the queue's lists but keeps its count of running tasks. A boot script still running when the shutdown starts keeps counting against the limit of one, and no `K` script starts until it returns. Nothing ends it before the halt, so a boot script that never returns keeps the system in procd's shutdown state, feeding the watchdog, for good (procd 2026.11.03; on the emulator, `- shutdown -` with the hung script still running ten minutes later).
- The U-Boot environment is reached through `/etc/fw_env.config`, which the uci-defaults script `31-wrt-ab` writes from the copies the bootloader names on the kernel command line (`wrt.env=`), during the boot script `S10boot`. A kept configuration carries it (it is a conffile of uboot-envtools, restored by preinit's `80_mount_root`); after an upgrade that kept none, it exists only once `S10boot` has run that script.
- uboot-envtools' own defaults (`30_uboot-envtools`) leave an existing `/etc/config/ubootenv` alone and name no place for these boards. preinit's `82_config_generate` already runs them on a first boot, so that board files can read the environment.
- sysupgrade's image check (`platform_check_image` in `lib/upgrade/wrt-ab.sh`) refuses an image that is not a single-slot upgrade, a system not booted from a slot and an environment that cannot be read; it does not look at the trial state.

## Goals / Non-Goals

**Goals:**
- Every trial boot ends in a confirmation or a counted reboot, whatever its boot scripts do.
- The trial state can be read from the first boot script on, on every boot.
- The slot a rollback returns to is never overwritten while the running slot is on trial, and a confirmation never takes back a switch.

**Non-Goals:**
- Hangs in preinit, before any boot script: preinit's scripts are short and fixed, and a kernel hang is the watchdog's.
- A confirmed slot whose boot hangs: rebooting it would loop on the same slot, uncounted. It stays as the health check leaves a failed confirmed boot.
- Changing U-Boot: routers keep the bootloader their factory image wrote.

## Decisions

### D1. A trial supervisor, started first

A new ucode program `wrt-trial`, run as a procd instance by an init script at `START=00`, the first boot script:

1. It reads the environment once. Unless it names the running slot on trial (`boot_slot` the running slot, `upgrade_available` 1), it ends: on a confirmed boot, after a fallback within a power cycle, and when the environment cannot be read, as the health check never reboots for a trial state it cannot know.
2. On a trial boot it says on the kernel log when the boot's deadline falls, and waits for it: `wrt-ab.trial.deadline` seconds (900 by default) on the monotonic clock, which counts from the kernel's start and which setting the time of day does not move.
3. At the deadline it ends if the health check has recorded a result for this boot (`/var/run/wrt-healthcheck.json`, in RAM, so of this boot alone): that check has decided, by confirming, by rebooting, or by staying on trial as the health-check spec says when the environment or the confirmation fails. Otherwise it reads the environment again and, while it still names the running slot on trial, says so on the kernel log and reboots, which U-Boot counts.

Its messages go to the kernel log (`/dev/kmsg`): logd starts after it (`START=12`), and the console shows the kernel log on a boot whose scripts never got as far as SSH. logread shows them once logd runs.

The default deadline lies well past the longest boot to the health check seen in CI plus the health check's 300 s; an administrator can lengthen it in `/etc/config/wrt-ab` for a slower setup.

Alternatives considered:
- Starting the supervisor in preinit: it would cover preinit too, but a process left by preinit has no supervisor of its own and no configuration yet, for hangs that do not occur there.
- Leaving the watchdog unfed during a trial until the confirmation: procd feeds it; this needs a procd patch, and a slow but healthy boot would reset without a clean shutdown.
- Starting the health check itself first: its checks wait for the services, and its time limits would then include the boot.

### D2. The environment configured in preinit

`/lib/preinit/81_wrt_ab_environment` takes `31-wrt-ab`'s place, run as a hook of `preinit_main` after `80_mount_root` has restored a kept configuration and before `82_config_generate`. On a system booted from a slot whose configuration names no environment, it adds the copies the bootloader names to `/etc/config/ubootenv` and writes `/etc/fw_env.config` from them, with uboot-envtools' own functions, as the uci-defaults script did; a bootloader that names none leaves it unconfigured, with a line on the kernel log. A configuration a kept configuration carries stays as it is. The hook runs in a subshell, so preinit's shell keeps none of its definitions and none of its failures, and on a configured boot it ends after one `uci` lookup. `30_uboot-envtools` then finds the configuration, in `82_config_generate` and in `S10boot`, and leaves it.

`31-wrt-ab` goes: one place configures the access, before anything reads it.

### D3. No upgrade during a trial

`platform_check_image` refuses an image when the environment names the running slot on trial, with "Slot <x> is on trial: the other slot is the one a rollback returns to until the health check confirms <x>", before anything is written. A trial slot that failed to load, booted from the other slot within the power cycle, does not count: the running slot is not the trial slot, and writing the failed one is what an upgrade is for. As with sysupgrade's other checks, `-F` forces past it; `wrt-update` never forces.

### D4. A confirmation reads the environment again

Just before it confirms, `wrt-healthcheck` reads the environment again, and confirms only while it names the same slot on trial as when the checks began. Otherwise it records the pass, leaves the environment as it is and logs that it left the switch in place. The comparison is with the start, not with the running slot: after a fallback within a power cycle the environment names the trial slot that failed to load, and the health check confirms the slot that did boot, as it does today. An environment that cannot be read this time is the failed check `environment`, without a reboot, as at the start. The read and the write stay two commands: what is left between them is a few milliseconds, against an administrator's own command.

### D6. A shutdown cancels the boot scripts still running

D1's reboot needs a shutdown that completes while a boot script hangs, and procd's does not (Context). The fix goes into procd, through an OpenWrt patch that carries a procd patch (`patches/openwrt/0048`), as patches 0039, 0043 and 0047 do: when `rcS()` starts a run, it cancels what is left of the previous one instead of setting the queue up anew. The scripts not yet started are dropped; the running one gets SIGTERM, and SIGKILL 10 s later, as a `shutdown` script past its 15 s does; the shutdown's scripts start once it has ended. Every script procd runs from that queue gets the 10 s from SIGTERM to SIGKILL, the queue is set up once (as procd's queue of single init scripts is), and a script dropped before it started closes no output. A `reboot` during any hung boot script then completes, on every OpenWrt system, not only for `wrt-trial`.

Alternatives considered:
- `reboot -f` in `wrt-trial` once a plain `reboot` has not completed in time: it leaves procd's defect for every other reboot and skips the `K` scripts and the unmount on exactly the boots that need them.
- Letting a hung boot script finish its `boot` run under a time limit: a long boot script is not wrong (a first boot's uci-defaults can take minutes), and a limit for every boot would be a new policy; a shutdown ends what is left of the boot anyway.

### D5. Tests

- A hung boot (boot-rollback): the test commits a short deadline and a uci-defaults script that sleeps forever on the trial slot alone, listed in `/etc/sysupgrade.conf` so that the upgrade carries it, and upgrades. Each trial boot hangs in `S10boot` until `wrt-trial` reboots it, through the shutdown D6 lets complete; after three, U-Boot rolls back. The original slot's next boot runs the script once, which ends at once there and is dropped, as uci-defaults scripts are. The test reads the console: three reboots announced by `wrt-trial`, the bootlimit exceeded, slot A confirmed. Without D6, the first of those reboots never completes.
- The environment at the first boot script (boot-rollback): after an upgrade without kept configuration, the new slot's kernel log holds `wrt-trial`'s line naming its trial.
- A switch during the checks (health-check): with a registered check failing, the test runs the health check, writes the other slot as the trial slot meanwhile, then lets the check pass.
- An upgrade during a trial (ab-upgrade): with the running slot set on trial, sysupgrade refuses and changes neither the other slot nor the environment.

## Risks / Trade-offs

- [A healthy boot slower than the deadline is rebooted, and three of them roll back] → The default is generous and configurable; a boot that slow has no health check result either way.
- [A boot script that a shutdown cancels leaves its work half done] → The system is going down; the `K` scripts and the unmount still run, and the next boot runs the boot scripts again, an unfinished uci-defaults script among them.
- [procd's patch waits upstream] → It stays `Upstream-Status: Pending` until upstream takes it; the hung-boot test fails without it.
- [A failing preinit hook would stop the boot] → It runs in a subshell, and every failure in it ends there with a kernel log line.
- [The read and the write of D4 are not atomic] → Accepted (D4).
