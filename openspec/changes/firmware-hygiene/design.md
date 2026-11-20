# Design

## Context

- sysupgrade and its second stage read every `/lib/upgrade/*.sh` in name order (`include` in `lib/functions.sh`: `for file in $(ls $1/*.sh)`). Rockchip's `platform.sh` sets `REQUIRE_IMAGE_METADATA=1` and defines `platform_check_image`, `platform_do_upgrade` and `platform_copy_config` as calls into upstream's `legacy-sdcard.sh`. orbyt-ab's `z-orbyt-ab.sh` defines the same three functions again and wins by being read last; its metadata check is `platform.sh`'s variable, inherited unnamed. Upstream's own layouts are libraries with names of their own (`legacy_sdcard_*`, `emmc_*`, `nand_*`) that a target's `platform.sh` calls. Patch 0004 already changes this target for the A/B images.
- rc.d runs the boot scripts by their links' names: `S00orbyt-trial` is first because no other `S00` script sorts before it (upstream's are `S00sysfixtime`, `S00urngd`); `S99orbyt-healthcheck` sorts before `S99orbyt-sync`, although its init says it checks after every other service has started.
- orbyt-sync's `fetch` tries each request five times, three seconds apart, "the first may leave before honk holds the bridge"; honk's health check (`/etc/healthcheck.d/50-honk`) already tells when honk's programs are on `podman0`.
- honk's init sets its cgroup up in `start_service` and again in `service_started`: on a restart, the old instance may exit after `start_service` set the cgroup up and before procd took the new instance, and procd then deletes the old service's cgroup, the one the new instance is to run in. Patch 0047 already keeps an instance's cgroup across its own restart and respawn.
- Defaults stated twice: `orbyt-sync`'s `api`, `orbyt-ab`'s `deadline` (and `orbyt-trial`'s `DEADLINE = 900`), einat's `ifname`, `ports` and `inbound_mark` (its config, init and health check), `orbyt-slot`'s `bootlimit ?? '3'` (U-Boot's `CONFIG_BOOTCOUNT_BOOTLIMIT`).
- The health check's result path is declared in three scripts, the monotonic clock in two; four scripts spell out `orbyt_data_mounted`; the health check runs each check as `sh -c` under `timeout`, with a quoting function of its own.
- `uboot/board-r4s.config` and `board-r6s.config` hold the same watchdog block; the slots' partitions are written in `uboot/orbyt-ab.env`, `lib/functions/orbyt-ab.sh`, `orbyt/ab.uc` and patch 0004's image generator.
- `config/ubsan.seed` repeats `toolchain.seed`'s `TARGET_OPTIMIZATION` to append two options; `config/ci.seed` excludes four `kmod-usb-*` packages because `config/kernel.config` leaves their symbols out.
- `files/lib/upgrade/keep.d/orbyt-config` keeps `/etc/rc.d/S99honk` and `K01honk`, numbers that honk's init states.

## Goals / Non-Goals

**Goals:**
- No behavior that depends on a file's name or a start order the code does not state.
- No retry or repeated step standing in for a missing readiness point or a race in another component.
- One home for each default, constant and layout fact, or a check that binds the copies that must exist.

**Non-Goals:**
- The theme's stylesheet and templates: orbyt-theme, not merged yet, takes their findings.
- Unifying the first-boot defaults' guards. Two kinds exist, each right for what it guards: value-guarded defaults that set one option only while it holds base-files' value or none (hostname, zram), and batches applied once per configuration, recorded by a kept marker (`/etc/orbyt-datapath`, `/etc/orbyt-services`). A single marker would re-apply the batches over every configuration a current image carries, on its first upgrade. docs/conventions.md states the two kinds.
- orbyt-trial's deadline loop (it wakes at least once a minute to re-read the monotonic clock: trial-guards D1, whose reason holds), orbyt-snap's wait for a new second (snapshot names are seconds; the wait is at most one), orbyt-data's 30-second wait for blockd's mount (an administrator's command, bounded, documented).

## Decisions

### D1. The A/B upgrade handed off by name

orbyt-ab's upgrade file is `orbyt-ab.sh` again and defines `orbyt_ab_check_image`, `orbyt_ab_do_upgrade` and `orbyt_ab_copy_config` with the helpers they use, all under the `orbyt_ab_` prefix. Patch 0004 makes rockchip's `platform.sh` the hand-off: its three functions call those, and it keeps `REQUIRE_IMAGE_METADATA=1`, now the only definition of the platform's metadata policy. The whole-disk calls into `legacy-sdcard.sh` leave it; upstream's file stays in base-files, read and unused. Every upgrade file then defines names of its own, so the order they are read in cannot matter.

The archived r4s-ab-rollback D6 chose to override `platform.sh` from the package, "without patching it". Its reason, a target file left as upstream ships it, no longer outweighs a definition that holds only by its file's name; patch 0004 already makes this target an A/B one.

Alternatives: keep `z-` and a test that the file sorts last (the order still decides, a test only reports it); ship `platform.sh` from orbyt-ab (two packages owning one path).

### D2. Boot order stated

A test reads the image's rc.d links and asserts `S00orbyt-trial` is the first boot script. The health check's init no longer claims to run last; each check already waits for its condition within its limit, and the spec now says so. START values stay as they are: procd has no ordering stronger than the links' names, and the one order that matters is now asserted.

### D3. orbyt-sync waits for its datapath

honk's package gains a readiness test of its own, `honk_holds <device>` in `/lib/functions/honk.sh`: whether honk's programs are attached to the device, as `50-honk` checks for `podman0` (which then calls it). Before starting the sync's container, `orbyt-sync` waits for it on `podman0`, bounded, when honk is enabled; with honk disabled nothing waits. `fetch` keeps a retry for requests that fail in transit, with a comment saying that is what it is for, and no longer explains it with honk's start.

### D4. honk's cgroup, once

The race is procd's: freeing the old instance of a replaced service removes the cgroup directory the new service's instance is about to use. procd's patch (folded into 0047's procd patch file as a second commit, or a patch of its own if it is independent) removes a freed instance's cgroup only when no service of that name holds it. honk's init then sets the cgroup up in `start_service` only, before the instance starts, so honk starts pinned; `service_started` goes. Verified by the transparent proxy's restart test (the cpuset kept across `/etc/init.d/honk restart`) run in a loop on the emulator.

### D5. Defaults in the code that reads them

For the project's own packages, each option's default is the one the code applies when the option is unset; the shipped `/etc/config` file carries only sections and values that differ from it. einat's three defaults come from one function its init and health check share. `orbyt-trial` reads `deadline` through `orbyt.ab`, whose default is the one value. The U-Boot environment names `bootlimit` itself (`uboot/orbyt-ab.env`), so `orbyt-slot` reads it rather than assume U-Boot's constant.

### D6. Shared helpers

`orbyt.ab` exports the health check's result path and the monotonic clock, which the health check, `orbyt-slot`, `orbyt-trial` and orbyt-sync's `fetch` use. Every script that tests for the data disk calls `orbyt_data_mounted`, and every path below it comes from `ORBYT_DATA`. The health check runs a check as an argument vector: through ucode's `system()` with its timeout when ucode reports a killed child distinctly from a failed one (checked with the image's ucode first), otherwise through `timeout` with an argument vector; the quoting function goes either way.

### D7. One home for each layout fact

- U-Boot: the watchdog block both rockchip boards share moves to one fragment the board variants include; the per-board fragments keep the board constants the boot-rollback spec names. Comments that describe only the R4S or only the SD card say what holds for each board.
- The slots' partitions: a unit test reads the map from `uboot/orbyt-ab.env`, `lib/functions/orbyt-ab.sh`, `orbyt/ab.uc` and the image generator and asserts they agree. Each is in a language of its own and read at a different time (U-Boot built in, preinit's shell, ucode, the build), so one generated source would cost more than the check.
- honk's kept rc.d links: the honk package installs its own keep.d entry, written from its init's START and STOP at build time; `files/`' list loses the two lines.
- Seeds: `scripts/lib/seeds.sh` gains an append form, which `ubsan.seed` uses for its two options. A unit test asserts that every kernel symbol `config/kernel.config` leaves out has its kmod packages excluded in `ci.seed`. `release.seed` is renamed `device-sync.seed`, after the capability it selects.
- orbyt-data's fstab stub is written by orbyt-data alone; `92-orbyt-services` keeps the image's policy for upstream packages. ksmbd's two hardening settings move to the UCI options ksmbd's init reads, or, where it reads none, to a template the image owns; the in-place `sed` on the package's conffile goes.

### D8. Leftovers

orbyt-keyring's build fails when it has no keys; `manifest`'s interpreter line and the other scripts' strict mode agree; orbyt-metrics' description is rewritten; the A/B upgrade splits its partition pair with `read`, not the positional parameters; each `shellcheck source=` comment sits above the `.` it describes; `92-orbyt-services` says why the LAN reaches the tailnet (subnet routes) and a WireGuard peer only answers (remote access).

## Risks / Trade-offs

- [The hand-off patches a target file] → patch 0004 is the image's A/B patch already; `just patch` fails loudly when upstream changes the three lines' context.
- [A procd race fix is harder to verify than a repeated setup] → the restart test runs in a loop on the emulator with every CPU kept busy (as CI's slow runners), and the patch's write-up records the window and the evidence.
- [Defaults removed from config files] → a config-preserving upgrade keeps an administrator's values; an option left at its old shipped value reads the same as the code's default.

## Migration Plan

A config-preserving upgrade from a current image keeps its configuration: the markers and kept paths keep their names, and honk's kept links are the same two paths, now listed by its package. Nothing on the router changes name but `/lib/upgrade/z-orbyt-ab.sh`, which the upgrade's own image replaces.
