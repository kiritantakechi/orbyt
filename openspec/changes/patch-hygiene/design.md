# Design

## Context

- qosify's init configures the daemon in `service_running` (patch 0006: a background `ubus wait_for` loop, then `reload_service`), as upstream's qosify, umdns and bridger inits do. rc.common's procd `start()` calls `service_started`, never `service_running`, which is the `running` action's status hook: nothing configures qosify when it starts, only a configuration change (its reload trigger) or a status query does. The image ships qosify alone of the three. A daemon procd respawns passes through no init hook at all.
- procd listens for `ubus.object.add` only to subscribe to the objects services watch (`service/watch.c`); its service triggers, which `procd_add_raw_trigger` registers, see the events `ubus call service event` sends.
- Patches that change the same lines in turn: fstools' inner 101 (0036) and 102 (0044) in `blockd_umount`; 0009 and 0038 in the toolchain's `.ver_check` rule, 0038 removing the `ifdef CONFIG_BUILDBOT` that 0009's fix sits in. Patches that do several things: 0035 (procd's mount trigger on unmounts, plus three fixes to `procd.sh`: a mount point with a space, the init script's name, the condition over several mount points), packages/0002 (rust/host in hostpkg, LLVM's targets, ccache).
- 0021 extends every `ltmain.sh` a package carries with a `sed` before it is configured, in the `ubsan` profile; build/upstream-pinning forbids in-place text substitution of upstream files. Regenerating the packages with the build's libtool (patch 0019) broke libffi's build directories when tried.
- 0012 refreshes the kernel modules pass's stamp after the image pass, so that the image pass's `vmlinux.symvers` does not make the next build relink the kernel.
- docs/patches.md: 12 of 59 write-ups lack a section or name it otherwise; 0040 is a backport from Linux but says `Pending`; two titles differ from their patches' subjects; 0021's entry sits before 0020's.
- daeuniverse/0003 replaces coreutils' `timeout` with BusyBox's without depending on the applet.

## Goals / Non-Goals

**Goals:**
- Each patch one fault or one feature, at the component whose code is wrong, in a form upstream could take; no patch rewriting another's lines.
- qosify configured whenever its daemon comes up, by an event, not a wait.

**Non-Goals:**
- Submitting patches upstream (each submission is the maintainer's to authorize), and honk's carried patches: honk is daeuniverse's, and its patches 005 to 007 stay as reviewed in honk-hardening.
- The series' `PKG_RELEASE` steps: each package patch raises its package's release as an upstream commit would, so consecutive patches to one package apply in order, as commits do.
- 0005 (its sysfs scan is the idiom of upstream's `export_bootdevice`), 0007 (both boards' NIC drivers request their IRQ only when the NIC is opened, and no hotplug event marks a bridge member's coming up; the wait is bounded per NIC and documented), packages/0013 (it sets the host triple's linker as OpenWrt sets the target's, a general fix).

## Decisions

### D1. qosify configured on its object's registration

qosify's init configures the daemon from `service_running`: procd runs the `running` action after a `service set` that brings instances and after an instance starts again (procd's service.c and instance.c), so the daemon is configured at boot, at a start and after a respawn, but so does every status query, `/etc/init.d/qosify running` and rpcd's `rc list` (rpcd's rc.c), which LuCI's Startup page calls: each sends the daemon its whole configuration again, with `reset`.

A procd patch passes every `ubus.object.add` event to the service triggers as well as to the watches, so a service can act when an object appears. qosify's init (0006, rewritten) adds a raw trigger on `ubus.object.add` with `path` `qosify` that reloads qosify, and drops its `service_running`, leaving rc.common's status hook as it was. The trigger fires when the daemon registers, at boot, at a start and after a respawn alike; a status query sends nothing, no boot script waits, and nothing polls. umdns and bridger, which upstream configures the same way, are named in the write-up as upstream's to change likewise.

The plan first had it that nothing ran `service_running` at a start (a reading of rc.common alone). Task 1.1's pin on the emulated R4S, on the old 0006 (qosify's init logging each run and its caller), found procd running it right after the boot's start and again 98 s after a respawn, and both of 1.2's first scenarios passing there, while a status query sent the daemon its configuration with `reset`. The maintainer kept the object trigger for that (2026-11-21), and the requirement gained its status query scenario.

Alternatives: the old 0006, configuring from `service_running` (a status query reconfigures the daemon); `service_started` with the wait (misses a respawn, and still waits); the daemon reading its configuration itself (qosify takes it over ubus only, built by the init from UCI).

### D2. One fault per patch

- 0035 keeps the mount trigger on unmounts; the three `procd.sh` fixes become 0051 to 0053, after it, as a number is an identity and a gap stays one; each raises procd's `PKG_RELEASE`.
- fstools: 0036 becomes the one blockd change (send `mount.remove` once the device is unmounted, with its mount point, `block.c`'s order included); 0044 goes.
- 0009 folds into 0038: one patch recording the toolchain's content in every mode, its check free of the race; 0009 goes.
- packages/0002 splits into rust/host in hostpkg (Inappropriate), the ccache option (Pending), and LLVM's targets, whose write-up states the build time it saves and that rustc needs no other backend here.

A patch that goes leaves its number unused, as docs/patches.md requires. Each change to the series is checked by applying the old and the new series to the pinned trees and comparing the results: the same files byte for byte, but for what a package patch states of itself (procd's and fstools' `PKG_RELEASE`, fstools' one patch for two), where the package's patched source is compared instead.

### D3. 0021's cause

0021's `sed` goes; the sanitizers' options reach every link without an edit of a package's files. The faulty components are the old libtool copies that drop `-fsanitize-trap` from a link, which matters because LTO's link-time code generation expands the sanitizer checks with the link's options. In this order, the first that holds is taken:

1. GCC's LTO link takes the sanitizer options the objects were compiled with (as it does for other options it records per object), so a link needs none: then 0017's link flags go too, and with them every libtool's part in it.
2. The profile's packages that carry a libtool are fixed up with the build's libtool (patch 0019), OpenWrt's own mechanism; libffi's build directories, which that broke, are fixed at their cause.
3. Neither: each package whose libtool drops the option carries a patch to its `ltmain.sh`, as upstream regenerating it would.

Verified on the R4S's `ubsan` tree: libffi, libmd, libmnl and musl-fts link with no call into a runtime and with the trap counts of 0021's log. The first way does not hold: GCC's LTO link does not take `-fsanitize-trap` from the objects (seen 2026-11-21). The second holds (seen 2026-11-22): with autoreconf for every package that carries an `ltmain.sh`, the four link with no call into a runtime and the trap counts of the `sed` (libffi's 4,870 against October's 4,909 under either), and libffi builds, its earlier breakage not recurring; without either, libmd fails. 0021 is that hook, in a build that sanitizes only. A whole `ubsan` build then stopped at binutils, whose build system autoreconf cannot regenerate (OpenWrt patches its libtool instead, `patch-libtool`), so that its own copy linked libsframe without the options: for binutils the third way holds, a patch to its `ltmain.sh` (0056), and 0021's hook regenerates only a package whose build system uses libtool and whose copy drops the options, and stops the build when one still does (e2fsprogs, which uses no libtool, carries a copy nothing reads). The whole build then found a link that no libtool runs and 0017 does not reach: a Rust package's, which takes only `RUSTFLAGS`, so that honk-core linked the checks of the C its crates build (SQLite, aws-lc) as calls into the runtime; packages 0018 gives that link the options too. The profile had not been built since honk joined the image.

### D4. 0012 as an exclusion

`Kernel/Newer` leaves out the files the image pass writes into the kernel tree (`vmlinux.symvers`, `System.map` and `vmlinux`), so the modules pass's freshness does not see its own successor's outputs, and the stamp is no longer refreshed. Kept only if the two experiments of 0012's log hold (a build with nothing changed skips kbuild in both passes; a touched module's source builds that module again); otherwise 0012 stays as it is and its write-up says why.

### D5. The write-ups

Every write-up has the sections `Problem`, `Why it matters here`, `What the patch does` (or, for a patch that adds several, `What the patches do`) and `Verification log`, in that order. The write-ups are grouped by where their patch lives (each series, QEMU's, the feed packages' own, the ones prepared for upstream), each group in its files' order. A check in `tests/build/test_upstream_pinning.py` reads docs/patches.md and fails on a missing or misplaced section, naming the patch, and on a write-up out of order. A title says what its patch fixes, in the documentation's form, so 0025's says it reads, not formats. 0040 stays `Pending`: it ports Linux's two fixes into U-Boot, which lacks them, and is meant for U-Boot; its write-up says they are Linux's. The Rust entry's dates say what each is (the packages' pin, Rust's release).

### D6. Small dependency

daeuniverse/0003 adds `+@BUSYBOX_CONFIG_TIMEOUT` to the package's dependencies, so a configuration without BusyBox's `timeout` cannot select it.

## Risks / Trade-offs

- [A procd feature patch for one init] → it is general (any service can act on an object's registration), small, and the same fix serves upstream's umdns and bridger.
- [The `ubsan` profile's compiler command] → only that profile changes; the dev and ci profiles' commands, and so their builds and caches, stay as they are.
- [Folding and splitting patches by hand] → the byte-for-byte comparison of the patched trees.

## Migration Plan

None on the router beyond the rebuilt procd and qosify packages; no build cache is invalidated by D2.
