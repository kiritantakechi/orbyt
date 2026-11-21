# Patches

Every patch the project carries or prepares is a file in the repository:
- `patches/openwrt`, `patches/packages` and `patches/luci`: the series applied to the sources (`just patch`);
- `patches/qemu`: QEMU's, built into the emulator (`flake.nix`);
- `feed/*/*/patches`: the feed packages' own, applied by OpenWrt as it builds them;
- `docs/upstream`: prepared for upstream, not carried.

Nothing is submitted upstream, as a pull request, an issue or a mail, without the maintainer's consent. The patches meant for upstream are prepared here; whether and when to submit them is the maintainer's decision.

## What a patch fixes

A patch fixes a fault where it lies, in the component whose code is wrong: a package, a tool such as the linker, or the compiler. It does so in a form that component's upstream could take, and it does not trade generality away to suit this project: it does not turn a feature off, narrow a mode, serialize work or stand in for a missing part, and it keeps working every configuration upstream supports (a fallback for older kernels, the old path for upstream's images). A patch to a tool or to the toolchain is a file in OpenWrt's `tools/<tool>/patches` or `toolchain/<component>/patches-*`, added by a patch of the series. When a general fix replaces a workaround, the workaround goes in the same step.

`Inappropriate` is for what only exists in this project, such as its A/B slot layout and its boards' images.

## Upstream status

Every patch file states its upstream status in an `Upstream-Status` trailer, in OpenEmbedded's vocabulary, which Buildroot follows as well:

| Status | Meaning |
|---|---|
| `Pending` | Meant for upstream, not submitted |
| `Submitted [<where>]` | Submitted, under review: the pull request or the mail |
| `Backport [<source>]` | Taken from upstream or another primary source |
| `Inappropriate [<reason>]` | Specific to this project |

In a patch made by `git format-patch`, the trailer ends the message, before the `---` line, where `git interpret-trailers --parse` reads it. A plain diff carries it in its header, before the first `diff`. The status lives in the patch, so a patch that moves or goes takes its status along, and no list elsewhere can drift from the files.

A patch's number is its identity. A dropped patch leaves its number unused, no patch is renumbered, and a new patch takes the next free number, so that a number in a message, a document or a test always means the same patch.

Every `Pending` and `Submitted` patch has a write-up below, which names its file; every write-up names a patch that exists. `tests/build/test_upstream_pinning.py` checks the trailers and holds the two in step.

## Patches meant for upstream

The write-ups follow, by where their patch lives, each in its file's order; every one has the same sections, in this order: Problem, Why it matters here, What the patch does (or the patches do, for a patch that adds several), Verification log.

## The openwrt series

### qosify configured whenever its daemon comes up

Patch: `patches/openwrt/0006-qosify-configure-the-daemon-whenever-it-comes-up.patch`, for openwrt/openwrt.

Problem: qosify's init script configures the daemon from `service_running`, the `running` action, which procd runs after a start and after a respawn, but which every status query runs as well: `/etc/init.d/qosify running` and rpcd's `rc list`, which LuCI's Startup page calls, each send the daemon its whole configuration again, with `reset`. The function also waited only 10 seconds for the daemon's ubus object, which a busy boot can take longer to register. Upstream's umdns and bridger configure their daemons from `service_running` too.

Why it matters here: qosify shapes and classifies the WAN of every image (network/qos), from boot on.

What the patch does: qosify's init reloads the daemon whenever its ubus object appears (`procd_add_reload_object_trigger qosify`, patch 0054): at boot, at a start and after a respawn; a status query sends it nothing. `service_running` is rc.common's again, which tells whether the service runs. `PKG_RELEASE` goes to 2. Until 2026-11-21 the patch waited for the object from `service_running` in the background (patch-hygiene D1).

Verification log: 2026-11-21 on the emulated R4S with that earlier version, qosify's init logging each run and its caller: procd ran `running` right after the boot's start and again after the daemon was killed and respawned, so `test_a_boot_shapes_the_upload` and `test_a_respawned_daemon_shapes_the_upload_again` passed, and `test_a_status_query_leaves_the_daemon_alone` failed, `ubus monitor` showing the running action's `config` call with `"reset":true`.

### rockchip: IRQ affinity for every net device

Patch: `patches/openwrt/0007-rockchip-wait-for-a-NIC-s-IRQ-only-on-that-NIC-s-own.patch`, for openwrt/openwrt.

Problem: `40-net-smp-affinity` runs its whole body on every net `add` event, whatever the device: each bridge, veth or tunnel sets every NIC's IRQ affinity again and waits up to ten seconds per NIC for the IRQ to show in `/proc/interrupts`. procd runs hotplug scripts one after another, so a NIC whose IRQ carries another name (the emulator's virtio NICs) holds up every later net event: dae's own veths and a container bridge were bound minutes late.

Why it matters here: honk's veths and podman's bridge must be bound within the transparent proxy's 60 seconds (network/transparent-proxy), and the emulator's NICs, whose IRQs carry other names, held up every net event after them.

What the patch does: `set_interface_core` waits for a NIC's IRQ only on that NIC's own event. Any other net event still sets the affinity of every NIC whose IRQ is listed already, and skips the others without waiting. A NIC's driver may request its IRQ only when the NIC is brought up, as r8169 and stmmac do, so the IRQ can appear after the NIC's own event stopped waiting: the next net device to appear then sets it, as before the patch.

Verification log: 2026-09-29, a bridge created after dae is bound within the spec's 60 seconds (`tests/network/test_transparent_proxy.py`).

2026-10-05: the script run with stand-ins for `/proc/interrupts` and `/proc/irq` (the emulator's virtio IRQs never match): a bridge's event set eth0, whose IRQ was listed, and skipped eth1, whose IRQ was not, at once; the next event set both. On the devices, the IRQs of the NICs are not checked by a test.

### ubox: a log file on a disk that is not mounted

Patch: `patches/openwrt/0008-ubox-log-to-a-file-only-while-its-mount-point-is-mou.patch`, for openwrt/openwrt.

Problem: the log service leaves its log file out while the file's fstab mount point is not mounted, but only at boot. A start or reload later on, such as the reload that any change to the system configuration brings, creates the directory on the root filesystem and logs there: onto the flash, underneath where the disk mounts.

Why it matters here: the persistent log is `/mnt/data/logs/messages`, on the data disk (r4s-services D2).

What the patch does: the log file is left out whenever a mount point that holds it is not mounted (`procd_mountpoints_ready`, patch 0035: of mount points within one another, every one counts, where the old check took any); its mount trigger starts it once the mount point is mounted, as at boot. `PKG_RELEASE` goes to 2.

Verification log: 2026-09-29, in the emulator the log service restarted while the data disk is absent writes nothing to the SD card, and starts writing to the disk when it is plugged in (`tests/storage/test_data_disk.py`).

2026-10-05, without `boot()`: `tests/storage/test_data_disk.py` passes on both boards' `-O3` builds.

### qosify: an interface on a replaced device

Patch: `patches/openwrt/0010-qosify-start-an-interface-anew-on-a-replaced-device.patch` (adds the package patch `100-interface-start-an-interface-anew-on-a-replaced-device.patch`), for git.openwrt.org/project/qosify.

Problem: qosify sets an interface up on its device once, and takes it as set up for as long as it finds the interface up on a device of that name. pppoe-wan is a new device for every PPP session. When one session ends and the next starts before qosify handles the hotplug events (they run one after another, and a busy router runs them late), qosify finds the interface up on "pppoe-wan" again and leaves it be: the new device has neither the cake qdisc nor the classifiers, and nothing is shaped or classified until the interface goes down again.

Why it matters here: the emulator hit it after a redial, in CI (run 36793323171) and locally with every CPU of the VM kept busy, where `ubus call qosify status` showed `wan` active on pppoe-wan while the device carried only its default qdisc.

What the patch does: a package patch for qosify remembers the index of the device an interface was set up on, and starts the interface anew when its device has another name or another index. Upstream, it belongs to the qosify repository rather than to openwrt.git; the OpenWrt patch carries it until then. `PKG_RELEASE` goes to 3.

Verification log: 2026-10-01, with every CPU of the VM kept busy, the second redial without the patch left pppoe-wan without qosify; with it, eight rounds of restarts and redials left einat and qosify on pppoe-wan every time, 14 to 28 s after the session came up.

### build: stamps that hold across checkouts and follow the flags

Patch: `patches/openwrt/0011-build-name-prepared-stamps-after-content-and-the-tar.patch`, for openwrt/openwrt.

Problem: the prepared stamps of packages and of the kernel are named after a hash of their files, which covers the files' modification times unless `CONFIG_AUTOREMOVE` is set. Another checkout of the same sources gives every file a new time, and with it every stamp a new name: a host package built in one checkout is prepared and built again in the other. And no stamp names the flags the packages are compiled with: changing `CONFIG_TARGET_OPTIMIZATION` or `CONFIG_EXTRA_OPTIMIZATION` rebuilds nothing, and every package keeps its objects of the old flags.

Why it matters here: CI's host job packs Go's and Rust's host builds with their stamps, and each firmware job unpacks them into a fresh checkout (build-acceleration D4); with times in the stamps' names, every firmware job would build Rust again, for hours. And toolchain-o3 changes the target's flags, which the packages of a tree's earlier builds would otherwise keep.

What the patch does: the prepared stamps of packages (`PKG_FILES_MD5`) and of the kernel always hash content, as `CONFIG_AUTOREMOVE` builds already do. A host build's `rdep` looks only for files newer than its stamp, so an edit, or a touch to force a rebuild, still rebuilds, and a checkout of the same content does not. A target package and the kernel still prepare again when a file's time changes, as their `rdep` under `CONFIG_AUTOREBUILD` also compares a list of the files' times (`.dep_files`); the patch leaves that as it is, and a build with nothing changed keeps their times instead (`scripts/patch.sh` moves the tree in one checkout). Each target package's prepared stamp also hashes the symbols of the optimization flags `TARGET_CFLAGS` starts with (`TARGET_FLAGS_DEPENDS` in `rules.mk`: `CONFIG_TARGET_OPTIMIZATION`, `CONFIG_DEBUG`, `CONFIG_EXTRA_OPTIMIZATION`), so a package prepared with other flags is prepared, and so built, anew. A configured stamp would not do: configuring again keeps the build directory, and with it most of a package's objects. The kernel needs no such stamp, as Kbuild compares every object's command line.

Verification log: 2026-10-04, on the VM. With every file of the packages feed's `lang/golang` set to 2020, Go's host build prepared nothing again: its prepared stamp kept the name of its files' content, where the former name, of their paths and times, changed. Dropping `-fno-plt` from `config/toolchain.seed` prepared all 132 target packages of the R4S again, and neither the kernel nor the host builds; restoring it, the same 132. A first try with `-g0` failed in the kernel, which takes `CONFIG_EXTRA_OPTIMIZATION`, all but `-fno-plt`, as its `KCFLAGS`: without debug information, its modules' BTF could not be made.

### kernel: the modules pass ignores what the image pass writes

Patch: `patches/openwrt/0012-kernel-the-modules-pass-ignores-what-the-image-pass-.patch`, for openwrt/openwrt.

Problem: `Kernel/Make` skips kbuild when its command line is the one of its last run and no file of the kernel tree is newer than that run's stamp. The image pass runs after the modules pass and writes `vmlinux.symvers`, which modpost writes whenever it links `vmlinux` alone. The next build's modules pass finds that file newer than its stamp and runs kbuild, which removes `vmlinux` and `System.map` first and so links the kernel again, BTF included; the image pass then runs again in turn. No build ever skips kbuild.

Why it matters here: a build with nothing changed linked the kernel again in 6.5 of its minutes (5:45 for the modules pass, 0:43 for the image pass, on the VM; build-acceleration, task 2.4).

What the patch does: what the image pass writes into the kernel tree, `vmlinux`, `vmlinux.symvers`, `System.map` and the boot images (`KERNEL_MAKE_OUTPUTS_modules`), is left out of the modules pass's scan, as the build system files at the top of the tree are: the outputs of the pass that follows are no inputs of the modules pass. A file that is, such as a module's source, still makes the modules pass build. Until 2026-11-21 the patch refreshed the modules pass's stamp after the image pass instead (patch-hygiene D4).

Verification log: 2026-10-04 and 2026-10-05, on the VM, with the earlier version: every build with nothing changed skipped kbuild in both passes, in 2.5 s; with `net/sched/act_csum.c` touched, `make target/linux/install` linked the kernel again and `make target/linux/compile` then built `act_csum.ko` again. 2026-11-21, on the R4S's tree after a build with nothing changed in the kernel: the image pass had written `vmlinux.symvers` alone outside the top level's dot files. With this version, `make target/linux/compile target/linux/install` with nothing changed left both passes' stamps as they were (9 s); with `net/sched/act_csum.c` touched, the modules pass built `act_csum.ko` again (6 min, the kernel linked again) and the image pass then ran (3 min); the next run with nothing changed left both stamps again (27 s).

### download: a package's source only has to be there

Patch: `patches/openwrt/0013-download-depend-on-a-package-s-source-only-being-the.patch`, for openwrt/openwrt.

Problem: a package's prepared stamp depends on every file the package downloads (`DOWNLOAD_RDEP` in `include/download.mk`), by modification time. A download that lands after the stamp, in a fresh download directory or in a tree whose build directories a cache restored, makes make prepare the package again, although the file is the one the package's hash names.

Why it matters here: CI's firmware jobs restore the toolchain, whose stamps include the host builds of Go and Rust, before `make download` runs. On 2026-10-04 main's first run after its download cache was gone (run 37220393208) downloaded Go's and Rust's sources after the restore, built both host toolchains again in each board's job, and failed the check that a board's build compiles no part of the toolchain.

What the patch does: the download becomes an order-only prerequisite of the stamps. The stamp's name covers the package's files, its Makefile among them, which names each download and its hash, so another source still gets another stamp; and a missing download is still fetched before the package is prepared.

Verification log: 2026-10-05, on the VM. With Go's source made newer than its host build's prepared stamp, Go's host build was prepared and built again without the patch (382 s), and was up to date with it (8 s).

### ppp: a PPPoE service name's length checked before it is truncated

Patch: `patches/openwrt/0014-ppp-pppoe-check-a-service-name-s-length-before-trunc.patch` (adds the package patch `209-pppoe-check-a-service-name-s-length-before-truncating-it.patch`), for github.com/ppp-project/ppp.

Problem: pppd's PPPoE plugin truncates the service name's length to the 16 bits of its tag before `sendPADI` and `sendPADR` check the room the tag takes in the packet. A name of 65532 bytes or more makes the tag's length wrap and passes the check, and the name overflows the 1528-byte packet on the stack: `sendPADI` copies all of it, `sendPADR` up to 65535 bytes. The name comes from the `rp_pppoe_service` option (UCI's `service`), which takes a string of any length. ppp's master and 2.5.4 have the same code.

Why it matters here: `pppoe.so` dials the WAN of every image. Only root sets the name, but an overflow of a stack buffer is undefined behavior that `-O3` is free to exploit, and the review of the build's warnings (docs/undefined-behavior.md) found it next to the lines GCC flagged.

What the patch does: both functions check the room with the untruncated length, so a name that does not fit fails discovery with "Would create too-long packet", as any other tag that does not fit does; `sendPADI` copies as many bytes as the tag states.

Verification log: 2026-10-05, found by the review of the R4S's UB-indicative warnings at `-O3` (toolchain-o3 task 3.3) and patched; the patched pppd builds in both boards' images since. No test reaches the overflow: a service name that long is root's alone to set.

### build: each job's output whole in a package's log

Patch: `patches/openwrt/0016-build-write-each-job-s-output-whole-to-a-package-s-l.patch`, for openwrt/openwrt.

Problem: a package built in parallel runs its jobs beside each other, and each compiler writes its diagnostics to the package's log as it goes. A diagnostic is written in pieces, its "In function" context and its chain of inlined calls apart from the message, so the pieces of jobs running at once interleave: a warning follows another job's context, and a reader of the log places it in the wrong function or in none.

Why it matters here: the build reports the UB-indicative warnings of each package from its log, by function (`docs/undefined-behavior.md`). bash's warnings were placed in different functions on the two boards.

What the patch does: a parallel package's make runs with `--output-sync=target`, which writes each job's output once the job ends. The jobs still run in parallel under the build's jobserver; only their output is held back. Make passes the option on to the makes it starts, among them the one GCC runs for a link's LTO jobs under the jobserver.

Verification log: 2026-10-05, on the VM: the make that GCC ran for bash's LTRANS jobs had `-Otarget` and the build's output-sync mutex in its `MAKEFLAGS`, and no log of either board's build held a diagnostic cut by another job's output.

### build: sanitizers at the link

Patch: `patches/openwrt/0017-build-link-with-the-sanitizers-the-packages-are-comp.patch`, for openwrt/openwrt.

Problem: a sanitizer is a link option too: the link adds the sanitizer's runtime, or with `-fsanitize-trap` leaves it out, and under LTO GCC expands the checks only at the link, as traps or as calls into the runtime, by the options on the link line (lto-wrapper passes no sanitizer option on from the objects). Packages compile with `TARGET_CFLAGS`, but many link with `TARGET_LDFLAGS` alone, as make's built-in rule and meson do.

Why it matters here: the `ubsan` profile (`docs/undefined-behavior.md`) compiles every package with `-fsanitize=undefined -fsanitize-trap=undefined`. mtd and glib2, which use LTO, linked their checks as calls into libubsan, which OpenWrt's musl toolchain does not have.

What the patch does: `include/package.mk` adds the sanitizer options of `TARGET_CFLAGS` to `TARGET_LDFLAGS`. A build without sanitizers is unchanged.

Verification log: 2026-10-06, on the VM, in the R4S's `ubsan` tree: without the patch, mtd's link failed on undefined `__ubsan_handle_add_overflow` and `__ubsan_handle_sub_overflow`, and glib2's on four; with it, mtd linked with no call into the runtime and 264 trap instructions.

### libtool: every sanitizer option passed to the link

Patch: `patches/openwrt/0019-tools-libtool-pass-every-sanitizer-option-through-to.patch` (adds the libtool patch `tools/libtool/patches/150-pass-every-sanitizer-option-through-to-the-link.patch`), for GNU libtool, carried by openwrt/openwrt until then.

Problem: libtool passes `-fsanitize=*` to the compiler driver that links, but drops the sanitizers' other options, `-fsanitize-trap=*` and `-fsanitize-recover=*` among them. Those decide what the link does: with `-fsanitize=undefined` alone GCC links libubsan, while with `-fsanitize-trap=undefined` too it needs no runtime; and under LTO GCC expands the checks at the link by the options on its line.

Why it matters here: in the `ubsan` profile, libmd, libmnl and musl-fts failed to link for want of a libubsan the toolchain does not have, and `libnftnl.so`, which uses LTO, linked five calls into it.

What the patch does: libtool passes every option that starts with `-fsanitize` through, as it already does those that start with `-fno-sanitize`. Upstream, the patch belongs to libtool's `build-aux/ltmain.in`.

Verification log: 2026-10-06, on the VM: libmd, libmnl and musl-fts linked under LTO with `-fsanitize-trap` and no call into a runtime once their libtool passed every sanitizer option (patch 0021 gives their own copies this patch's change).

### gcc: each LTRANS job's output whole

Patch: `patches/openwrt/0020-toolchain-gcc-write-each-LTRANS-job-s-output-whole.patch` (adds the GCC patch `toolchain/gcc/patches-15.x/990-lto-wrapper-write-each-LTRANS-job-s-output-whole.patch`), for GCC, carried by openwrt/openwrt until then.

Problem: when lto-wrapper runs a link's LTRANS jobs in parallel through make, the jobs write their diagnostics to the same stream as they go, in pieces, and those of jobs running at once interleave. Under a jobserver the make inherits the build's flags, but a package built without one has lto-wrapper start make with a number of jobs of its own (`-flto=auto`) and no flags from above.

Why it matters here: the warnings of such a package's link would be placed in the wrong function, as bash's were before patch 0016. Running those jobs one after another (`-flto=1`) would have avoided it by giving up their parallelism.

What the patch does: lto-wrapper runs its make with `--output-sync=target`, so each job's output is written whole once the job ends, and the jobs keep running in parallel. GNU make has had the option since 4.0, and lto-wrapper already needs GNU make to run LTRANS in parallel.

Verification log: see the builds of both boards in `docs/undefined-behavior.md` and `docs/ci.md`.

### build: the sanitizer options through the packages' libtool

Patch: `patches/openwrt/0021-build-pass-the-sanitizer-options-through-the-package.patch`, for openwrt/openwrt.

Problem: most packages built with autotools carry their own copy of libtool, which passes `-fsanitize=` to the link but drops the sanitizers' other options, `-fsanitize-trap` among them. Patch 0019 fixes libtool itself, but reaches only the packages that OpenWrt regenerates with its own libtool, those that ask for the libtool fixup.

Why it matters here: in the `ubsan` profile, libmd, libmnl and musl-fts, among others, failed to link for want of libubsan.

What the patch does: in a build whose `TARGET_CFLAGS` sanitize, every `ltmain.sh` a package carries gets `-fsanitize*` among the options it passes through, before the package is configured, as the build's own libtool has it. The line it extends is the same in every libtool from 2.2 to 2.5, and a copy without it stops the build. Regenerating the packages' build systems with the build's libtool, tried first, broke libffi's build directories. A build without sanitizers is unchanged.

Verification log: 2026-10-06, on the VM, in the R4S's `ubsan` tree: the 27 copies of libtool in the R4S's packages, 2.2.7a to 2.5.4, all have the line. libffi (libtool 2.4.7), libmd, libmnl and musl-fts linked under LTO with no call into a runtime and 4,909, 1,290, 92 and 222 trap instructions.

### busybox: printf without arithmetic on a null pointer

Patch: `patches/openwrt/0022-busybox-printf-no-arithmetic-on-a-null-pointer.patch` (adds the busybox patch `package/utils/busybox/patches/800-printf-do-not-subtract-from-a-null-pointer.patch`), for busybox, carried by openwrt/openwrt until then.

Problem: `print_direc()` tells a `*` for the width from the one of `.*` by comparing the place of the first `*` less one with that of `.*`. In a conversion without a `*`, `strchr()` returns NULL, and the comparison subtracts one from a null pointer, which is undefined behavior.

Why it matters here: the `ubsan` profile's first run (`docs/undefined-behavior.md`) trapped here: 384 traps during one boot, in every init script and tool that runs printf, the log service's and the health check's among them.

What the patch does: it compares only when the conversion has a `*`.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### ubox: logd's log copied into the new buffer

Patch: `patches/openwrt/0024-ubox-logd-copy-the-log-into-the-new-buffer-when-it-g.patch` (adds the ubox patch `package/system/ubox/patches/101-logd-advance-in-the-new-buffer-when-it-copies-the-log.patch`), for git.openwrt.org/project/ubox, carried by openwrt/openwrt until then.

Problem: when the log buffer grows, `log_buffer_init()` copies the entries into the new buffer, but moves the destination past each copy by the old entry's size from the old entry's address. From the second entry on it copies into the old buffer, frees that buffer, and leaves `newest` pointing into it.

Why it matters here: found while reading `log_buffer_init()` for patch 0023, which aligned logd's entries until ubox took the same fix (9555709f00d5, in OpenWrt's ubox of 2026-11-15). A change of the system's log size grows the buffer at run time; ubox of 2026-11-15 still copies this way.

What the patch does: it moves past each copy in the new buffer.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### libubox: 64-bit integers read without assuming alignment

Patch: `patches/openwrt/0025-libubox-blobmsg_json-read-64-bit-integers-without-as.patch` (adds the libubox patch `package/libs/libubox/patches/100-blobmsg_json-read-64-bit-integers-without-assuming-alignment.patch`), for git.openwrt.org/project/libubox, carried by openwrt/openwrt until then.

Problem: blob attributes are padded to four bytes, so the data of an `INT64` attribute is only four-byte aligned, and `blobmsg_format_element()` read it with a 64-bit load, which is undefined behavior.

Why it matters here: the `ubsan` profile's first run (`docs/undefined-behavior.md`) trapped here: `ubus call` trapped printing a reply with a 64-bit value.

What the patch does: the value is read with `blobmsg_get_u64()`, two aligned 32-bit words, as the `DOUBLE` case already does through `blobmsg_get_double()`.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### netifd: container_of_safe for nodes that may be null

Patch: `patches/openwrt/0026-netifd-take-container_of_safe-of-nodes-that-may-be-n.patch` (adds the netifd patch `package/network/config/netifd/patches/100-netifd-take-container_of_safe-of-nodes-that-may-be-null.patch`), for git.openwrt.org/project/netifd, carried by openwrt/openwrt until then.

Problem: netifd's vlist update callbacks get the old or the new node as NULL when an entry is added or removed, and `interface_update_prefix()` is called with a NULL tree too. Four of them compute `container_of()` of those pointers before they look at them, which is pointer arithmetic on a null pointer.

Why it matters here: the `ubsan` profile's first run (`docs/undefined-behavior.md`) trapped here: netifd trapped adding a delegated prefix, and the network never came up, so no system test could reach the router.

What the patch does: `interface_update()`, `interface_update_proto_neighbor()`, `__interface_update_route()` and `interface_update_prefix()` use `container_of_safe()`, which keeps NULL, as the other callbacks check before they convert.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### ppp: the host name hashed without signed overflow

Patch: `patches/openwrt/0027-ppp-pppd-hash-the-host-name-without-signed-overflow.patch` (adds the ppp patch `package/network/services/ppp/patches/210-pppd-hash-the-host-name-without-signed-overflow.patch`), for ppp-project/ppp, carried by openwrt/openwrt until then.

Problem: pppd seeds its random numbers with `get_host_seed()`, which hashes the host name into an `int`, `h = h * 37 + c`, from 407. Any name longer than six characters overflows it, which is undefined behavior.

Why it matters here: with every earlier trap fixed, the `ubsan` profile's second run trapped in pppd's `magic_init()` at every start, so the WAN never came up.

What the patch does: the hash is computed in `unsigned int`, which wraps, and takes each character as an unsigned byte.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### gcc: no flexible array size without its object's initializer

Patch: `patches/openwrt/0028-toolchain-gcc-no-flexible-array-size-without-its-obj.patch` (adds the GCC patch `toolchain/gcc/patches-15.x/991-tree-no-flexible-array-size-without-its-object-s-initializer.patch`), for GCC, carried by openwrt/openwrt until then.

Problem: `component_ref_size()` takes the size of an initialized flexible array member from its object's initializer, and gives up for an extern object, whose initializer it cannot see. Under LTO, a partition other than the one that defines the object cannot see the initializer either, as `DECL_INITIAL` is `error_mark_node` there. It then took the size of the struct alone, so the member looked empty, and `-fsanitize=object-size` turned every function there that reads it into a trap.

Why it matters here: the `ubsan` profile's third run trapped in nftables' `ct_print()`, which walks a statically initialized flexible array of symbols and had become a single trap: `nft` trapped printing any rule with a ct expression. Without the object-size check, the same function compiles to its code.

What the patch does: the size is unknown when the initializer is not available, as it already is for an extern object.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### odhcp6c: no variable length array of zero IA_NA addresses

Patch: `patches/openwrt/0029-odhcp6c-no-variable-length-array-of-zero-IA_NA-addre.patch` (adds the odhcp6c patch `package/network/ipv6/odhcp6c/patches/100-dhcpv6-no-variable-length-array-of-zero-IA_NA-addresses.patch`), for git.openwrt.org/project/odhcp6c, carried by openwrt/openwrt until then.

Problem: `dhcpv6_send()` puts the IA_NA addresses in a variable length array as long as their count. That is zero until the client holds an address, and always when it asks for prefixes only, and a variable length array of length zero is undefined behavior.

Why it matters here: the `ubsan` profile's third run trapped here when odhcp6c sent its first Solicit on the WAN.

What the patch does: the addresses are allocated with `alloca()`, as the IA_PD options already are, and their length is taken from their count.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### fstools: a UUID formatted without assuming its alignment

Patch: `patches/openwrt/0030-fstools-format-a-UUID-without-assuming-its-alignment.patch` (adds the fstools patch `package/system/fstools/patches/100-libblkid-tiny-format-a-UUID-without-assuming-its-alignment.patch`), for git.openwrt.org/project/fstools, carried by openwrt/openwrt until then.

Problem: libblkid-tiny's `blkid_probe_set_uuid_as()` reads the UUID it is given through an `unsigned short` pointer, but the probes pass pointers into on-disk structures of any alignment: btrfs passes its device item's UUID, at the odd offset 0x10b of the superblock. A misaligned load is undefined behavior, and the function made it even for a name it ignores.

Why it matters here: the `ubsan` profile's fourth run trapped here: `block info` died on the data disk that `orbyt-data init` had just formatted, so the data disk was never set up, and every module that uses it failed.

What the patch does: the UUID is formatted a byte at a time, which gives the same text.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### ucode: ubus values read without assuming their alignment

Patch: `patches/openwrt/0031-ucode-ubus-read-blob-values-without-assuming-their-a.patch` (adds the ucode patch `package/utils/ucode/patches/120-ubus-read-blob-values-without-assuming-their-alignment.patch`), for github.com/ucode-lang/ucode, carried by openwrt/openwrt until then.

Problem: the ubus module's `blob_to_ucv()` reads 64-bit integers and doubles through a `uint64_t` pointer, but blob attributes are padded to four bytes, so their data is only four-byte aligned: a misaligned load, which is undefined behavior. It is the fault of patch 0025, in ucode's copy of the conversion.

Why it matters here: the `ubsan` profile's first R6S run trapped here: uhttpd's ucode handler died converting a ubus reply with such a value, and the metrics stopped after the first collector.

What the patch does: every scalar is read with libubox's `blobmsg_get_*()` accessors, whose `blobmsg_get_u64()` reads two aligned 32-bit words.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### qosify: DNS packets received with the IP header aligned

Patch: `patches/openwrt/0032-qosify-dns-receive-packets-with-the-IP-header-aligne.patch` (adds the qosify patch `package/network/config/qosify/patches/101-dns-receive-packets-with-the-IP-header-aligned.patch`), for git.openwrt.org/project/qosify, carried by openwrt/openwrt until then.

Problem: `qosify_dns_socket_cb()` receives each packet at the start of its buffer, so the IP header, after the 14-byte Ethernet header, is two bytes off a four-byte boundary, and qosify reads it through a `struct ip` or `struct ip6_hdr` pointer, whose alignment is four: a misaligned access, which is undefined behavior.

Why it matters here: the `ubsan` profile's second R6S run trapped here once, when a DNS reply reached qosify's DNS socket during a trial boot.

What the patch does: the packets are received two bytes into a four-byte aligned buffer, as the kernel's `NET_IP_ALIGN` does, so the IP header is aligned, with a VLAN tag or without. It is the least change that fixes today's qosify; patch 0034's DNS sockets, which receive each packet from its IP header on, start the aligned buffer with it instead.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### base-files: the firmware keys in /etc/usign/keys

Patch: `patches/openwrt/0033-base-files-fwtool-read-the-firmware-keys-from-etc-us.patch`, for openwrt/openwrt.

Problem: sysupgrade checks an image's signature with ucert against the keys in `/etc/opkg/keys` (`fwtool_check_signature()`). They are usign keys, kept in opkg's directory, which an image built with apk no longer needs for anything else.

Why it matters here: the image has no opkg left, and no `/etc/opkg` (`device-modernization` D5): orbyt-keyring puts the release keys in `/etc/usign/keys`, and sysupgrade has to find them there.

What the patch does: `fwtool_check_signature()` reads `/etc/usign/keys`, named after the tool whose keys they are as `/etc/apk/keys` is, and `/etc/opkg/keys` on an image without that directory, so upstream's images check their signatures as before.

Verification log: the firmware/ab-upgrade tests take a signed upgrade and refuse an unsigned one on both boards.

### qosify: tcx links, and DNS names learnt on each device

Patch: `patches/openwrt/0034-qosify-attach-as-tcx-links-and-learn-DNS-names-on-ea.patch` (adds the qosify patches `package/network/config/qosify/patches/102-dns-learn-from-a-packet-socket-on-each-device.patch` and `103-interface-attach-the-classifiers-as-tcx-links.patch`, and passes the `defaults` option `tcx` on in the init script), for git.openwrt.org/project/qosify, carried by openwrt/openwrt until then.

Problem: qosify attaches its classifiers as `cls_bpf` filters under `clsact`, and redirects with tc filters: two flower filters, one for IPv4 and one for IPv6, redirect DNS replies to `ifb-dns`, and a mirred filter sends the ingress to the interface's ifb when it is shaped. All of them stay on the device when qosify is killed. A program attached as a tcx link runs before them whatever either asks for. DNS learning reads the mirrored packets from a raw socket on `ifb-dns` as Ethernet frames, but the packets of a device without a link-layer header, such as pppoe-wan, come without one, so qosify learns no name there.

Why it matters here: einat runs as tcx links on pppoe-wan, so qosify's filters were the only legacy filters on the WAN port, and their order after einat held by the kernel's rule that tcx runs first rather than by anything either asked for (`device-modernization` D4). A rule by DNS name never matched on the PPPoE WAN.

What the patches do:
- 102: DNS learning opens a packet socket on each device qosify sets up, with `PACKET_IGNORE_OUTGOING` and a classic BPF filter for UDP from port 53 over IPv4 (not a later fragment) or IPv6. The filter reads from the network header on, so one filter serves every link layer, and it looks past a VLAN tag that the kernel left in the packet, the inner tag of a double-tagged one, as qosify's parser did. On an Ethernet device the socket is `SOCK_RAW`, whose frames keep their Ethernet header: the header says whether such a tag comes first. A `SOCK_DGRAM` socket reports the protocol behind the tag and keeps the tag in the packet (`vlan_get_protocol_dgram()`, kernel 6.10 on), so its reader cannot tell where the IP header starts. On any other device, which has no VLAN tags, the socket is `SOCK_DGRAM`, whose packets start with their IP header whatever the link layer. It gets a copy of each reply, which goes on untouched. The socket is registered for errors too, which it reads like packets: without that, uloop drops it on the first, `ENETDOWN` as its device goes down, so that nothing reads it once the device is up again, and closing it skipped a socket uloop no longer held, one per redial. `ifb-dns` and its filters go, and the socket goes with the device's setup and with the process. DNS over TCP was never learnt (the parser takes UDP alone), and still is not.
- 103: the classifiers attach as tcx links with `BPF_F_AFTER` (`bpf_link_create()` on the loaded program); einat asks to run first (`BPF_F_BEFORE`), so the order holds whichever starts first. The program is named `qosify_classify`, as a tcx link has no name of its own to tell it from einat's. The links go with the process, however it ends, and with the device; patch 0010's start anew on a replaced device attaches anew. The ingress classifier redirects to the interface's ifb itself (`bpf_redirect()`), when the ifb's index is in the `ingress_ifb` map, which qosify writes once the ifb exists: without one, the packets go on unshaped, where an index of 0 would have dropped them all. On a device without a link-layer header, the packet first gets an Ethernet header, which the ifb strips as it returns the packet (an ifb takes link-layer frames, and at ingress `bpf_skb_change_head()` has no MTU limit); that ifb's cake gets `overhead 0`, so that it counts from the network header, as with the mirred filter, and not that header too (the configured options may set another overhead). A kernel that refuses a tcx link (`EINVAL` or `EOPNOTSUPP`) gets `cls_bpf` under `clsact`, which runs after every tcx program, as does the `defaults` option `tcx` set to 0 on any kernel; qosify adds `clsact` only then.

Verification log: the network/tc-hook-order and network/qos tests on both boards: einat's tcx programs first and qosify's after them, with no legacy filter and no ifb; a `dns:` rule classifying a flow on pppoe-wan; ingress shaping through the ifb; and the `clsact` fallback with `tcx` set to 0. 2026-10-11, with every CPU of the VM kept busy, eight rounds of restarts of qosify and einat and redials on the R6S left einat's programs and then qosify's on pppoe-wan's tcx hooks every time, 26 to 36 s after the restarts and 27 to 42 s after the hang-ups. 2026-10-26, the socket filter on a veth pair and a tun device in a network namespace, with the parse of `qosify_dns_recv()`: of 26 crafted packets (untagged, 802.1Q, 802.1ad and double-tagged; IPv4 with and without options, fragments; IPv6; wrong ports and TCP), the 14 UDP replies from port 53 arrived with their IP header found and four-byte aligned, and none of the others.

### procd: init scripts triggered on unmounts too

Patch: `patches/openwrt/0035-procd-trigger-init-scripts-on-unmounts-too.patch`, for openwrt/openwrt. Until 2026-11-21 it carried the three fixes that are now 0051 to 0053 (patch-hygiene D2).

Problem: `procd.sh` gives init scripts mount triggers for `mount.add` only, so a service whose disk is unmounted keeps serving from the mount point until someone restarts it.

Why it matters here: ksmbd's shares are on the data disk, and services/file-sharing requires that no share be offered once the disk is gone (`device-robustness` D1, D3).

What the patch does: one helper registers a trigger for an event and an action on the mount points that hold the given paths. `_procd_add_action_mount_trigger` is it with `mount.add`, as before, and the new `_procd_add_action_unmount_trigger`, with `procd_add_restart_unmount_trigger` and `procd_add_reload_unmount_trigger`, with `mount.remove`. A single mount point's trigger is the same as before, and `_procd_add_mount_trigger` keeps its arguments. With patch 0036 `mount.remove` follows the unmount, as `mount.add` follows the mount: an action that reads `/proc/mounts` finds the mount point gone.

Verification log: 2026-10-12, the triggers `procd.sh` builds, compared before and after with the build tree's host `jshn`: the same for one mount point with restart, reload and start (as ubox's log, ksmbd-tools, transmission, nfs-kernel-server and postgresql call them), and `mount.remove` from the unmount helpers. 2026-11-08: with `mount.remove` after the unmount (patch 0036) an unmount trigger is a mount trigger on that event, its action without arguments. 2026-11-21: 0035 and 0051 to 0053 give the `procd.sh` the one patch did.

### fstools: mount.remove once the device is unmounted, with its mount point

Patch: `patches/openwrt/0036-fstools-send-mount.remove-once-the-device-is-unmount.patch` (adds the fstools patch `package/system/fstools/patches/101-blockd-send-mount.remove-once-the-device-is-unmounted.patch`), for fstools, carried by openwrt/openwrt until then. Two patches until 2026-11-21, 0036 and 0044, the second rewriting the first's lines; one fault of one function, so one patch (patch-hygiene D2).

Problem: when a hotplugged device is removed, `block` has blockd forget the device (`hotplug` with `remove`) before it unmounts it, and blockd sends `mount.remove` from `block`'s `umount` call, before the unmount, while `mount.add` follows the mount. blockd's `umount` handler then no longer finds the device, and sends the mount point it kept in a static buffer from an earlier unmount, or none; and a service that a `mount.remove` trigger reloads could find the mount point still mounted, with nothing telling it to look again.

Why it matters here: the data disk is a hotplug mount at `/mnt/data`, and ksmbd's unmount trigger (patch 0035) waits for a `mount.remove` that names it (`device-robustness` D2). procd.sh's unmount triggers had to tell their action which mount point was going, with a trigger per mount point and an argument every init script had to take; and a reload for another reason, between that action and the unmount, would have started ksmbd on a disk about to go (device-integrity D7).

What the patch does: `block` unmounts a removed device first and has blockd forget it after; it reports a finished unmount with blockd's new `umounted` call, and blockd sends `mount.remove` from that, with the mount point of the device just unmounted, or none for a device it does not know. The hotplug scripts still run before the unmount, and a failed unmount sends no event. Nothing else in the tree listens for `mount.remove`. `PKG_RELEASE` goes to 3.

Verification log: on both boards, `echo remove` to the data disk's `uevent` gives a `mount.remove` that names `/mnt/data` (the file-sharing test "Data disk removed while sharing"). The window is at most blockd's 3 s; the file-sharing test "Data disk removed while an unmount script runs" holds the unmount script that long, has a reload asked for meanwhile, and fails on a build without the patch: the SMB service stays running. 2026-11-21: the merged patch gives the fstools source tree the two did (`84478ca9`).

### qosify: an interface's ifb shown as the daemon names it

Patch: `patches/openwrt/0037-qosify-show-each-interface-s-ifb-as-the-daemon-repor.patch` (adds the qosify patch `package/network/config/qosify/patches/104-interface-report-each-interface-s-ifb-in-its-status.patch`, and changes `qosify-status`), for git.openwrt.org/project/qosify, carried by openwrt/openwrt until then.

Problem: `qosify-status` derives the name of an interface's ifb in a way of its own, `printf %.16s "ifb-$ifname"`. For a device name of 12 to 15 characters, that is no interface name at all, and not the one the daemon gives the ifb: the name's first two characters and its last nine. The daemon itself took that tail from before the name until qosify 21cc618 (2026-10-14), which the pin of 2026-10-25 brought; the patch had carried the same fix until then.

Why it matters here: ingress shaping redirects to the interface's ifb (patch 0034), and a VLAN or a tunnel can have a long name (`device-robustness` D5).

What the patch does: `ubus call qosify status` reports each active interface's ifb as `ifb`, and `qosify-status` shows that device. `PKG_RELEASE` goes to 6.

Verification log: the network/qos test "Ingress shaping on a device with a long name" on both boards.

### toolchain: rebuilt with its targets when its inputs change

Patch: `patches/openwrt/0038-toolchain-rebuild-it-and-its-targets-when-its-inputs.patch`, for openwrt/openwrt (patch 0009, folded into it on 2026-11-21, fixed its check's race: patch-hygiene D2).

Problem: the toolchain components name their prepared stamps without their content, so a component is built again only once its build directory is gone. Only buildbot mode cleans up: it removes the toolchain when `toolchain_hash`, the hash of the files under `toolchain/`, changes, and `check-toolchain-clean.sh` runs `make targetclean` when the GCC version or `toolchain/build_version` does. Outside buildbot mode, a changed toolchain patch leaves the old toolchain in place. No mode covers the generic kernel patches, from which the toolchain's kernel headers come. The cleanup also reaches only the configuration at hand: other target directories built with the same toolchain keep objects of the old one. And buildbot mode's check races: every make that reads the top-level Makefile runs it while `tmp/.build` is newer than the stamp, which each make touches, and under `-j` world starts several at once (those for `package/cleanup` and `target/compile`); each wrote the hash to the same file, `tmp/.ver_check`, before comparing that file with the stamp, so one that read the file another had just truncated saw a different hash, deleted the toolchain with the build and staging directories, and the build failed for want of a compiler ("Could not find compiler").

Why it matters here: patch 0020 added a GCC patch, and `just toolchain-build dev` in an existing tree did not rebuild GCC. Every board builds in directories of its own on the one board-neutral toolchain (board-model D2), so cleaning the configuration at hand would leave the other board's packages compiled by the old toolchain (`build-integrity` D1, D2). The release profile builds in buildbot mode on a toolchain unpacked from the cache, whose stamp is older than `tmp/.build` from the first make on: the race lost a CI run's R4S firmware job (run 36736937629), while the R6S's, on the same toolchain, got through.

What the patch does:
- `.ver_check` holds upstream's `toolchain_hash`, the one GCC's version string carries, and a hash of the generic kernel files of the configured kernel version, taken by the same function (`toolchain_files_hash`, upstream's hash made one of paths): the kernel version file, the backport, pending and hack directories, and the files directories, as `include/target.mk` picks them. GCC's version string keeps upstream's hash of `toolchain/` alone. A toolchain built from other files is removed with its build directory, to be built anew as a whole: its three GCC passes share one source tree, so rebuilding a component alone would leave the toolchain partly old. A hash of `toolchain/` that cannot be taken, as without `mkhash`, stops the build, instead of comparing unequal and removing the toolchain.
- Each target build directory records the toolchain it was built with, by directory name and content (`$(BUILD_DIR)/.toolchain`). When that is not the toolchain at hand, the build and staging directories are removed, so a change of the GCC version or the C library, which builds a toolchain in another directory, cleans the target too.
- Each make compares the hash it holds with the stamp itself, writing no file first, so concurrent checks share none.
- Both checks run where buildbot mode's ran: every make that reads the top-level Makefile remakes the `info.mk` it includes before building anything, so the first make of a build decides, before world starts any other. They run in every mode.
- `toolchain/build_version` is a file of `toolchain/`, so bumping it still rebuilds. `check-toolchain-clean.sh`, `toolchain_rebuild_check` and `.toolchain_build_ver` go.

The first make after the patch rebuilds the toolchain and each target once, as none has the new records yet; so did the first after upstream's hash replaced the content hash the patch had taken itself (`find_md5_reproducible`), on 2026-10-26.

Verification log: 2026-10-01, for the race: eight makes started a millisecond apart deleted the toolchain in 38 of 40 rounds with the upstream check and in none with the fixed one. `tests/build/test_boards.py` runs the patched check on a stand-in tree: "Keep each board's build with its toolchain" for the target records, "Keep the toolchain in buildbot mode" and "Check the version from parallel makes" for the toolchain's.

2026-10-12, on the VM with the dev profile: the first `just build r4s dev` after the patch found a toolchain whose record named a git commit, built it anew as a whole, Rust's host toolchain with it, and built the R4S anew. A second `just build r4s dev` compiled nothing: its time report held only the kernel's two forced passes (41 s), and ccache saw no cacheable call. `just build r6s dev` then kept the toolchain and built the R6S anew, as its build directory had no record yet.

2026-10-13, on the VM: with a scratch GCC patch that changes nothing built (a new file in GCC's source), `just build r4s dev` built the toolchain anew and compiled all 475 stages of the R4S, at 14.8 % ccache hits, as the new compiler differs; `just build r6s dev` kept that toolchain and compiled all 481 stages of the R6S. With the patch removed, the R4S's build built the toolchain anew again, and both boards compiled every stage anew, at 99.99 % hits: the toolchain built without the patch is the one built before it, whose entries ccache kept. CI's run 38305783785 built the toolchain in the ci profile, which is buildbot mode, and neither board's build compiled any part of it.

### procd: firmware images validated without blocking

Patch: `patches/openwrt/0039-procd-validate-firmware-images-without-blocking.patch` (adds the procd patch `package/system/procd/patches/100-system-validate-images-without-blocking-the-main-loop.patch`), for procd, carried by openwrt/openwrt until then.

Problem: procd's `system` object validates an upgrade image, for `validate_firmware_image` and in `sysupgrade` before the upgrade starts, by running `/usr/libexec/validate_firmware_image` and reading its output with a blocking `read()` in its main loop until the script ends. Meanwhile procd answers no ubus call, supervises no service and feeds no watchdog. A validation longer than procd's 30 s watchdog timeout resets the device before the upgrade begins. The validation script opens the image several times (fwtool's signature and metadata checks, then `platform_check_image`), so a large image on a slow device can take that long. The result went into a global `blob_buf`, and the error message into a static buffer.

Why it matters here: in the emulator on a slow host, the A/B tests' upgrades reset the router now and then before they began, and the trial came back on the wrong slot (CI runs 37293958173, 38252151081 and 38696888543). On the VM, with the session on four host cores that `stress-ng` slows, the A/B upgrade module reset seven times a run, and a monitor in the guest found procd in `anon_pipe_read` for the last 22 to 28 s before each reset (`procd-async-validation`).

What the patch does: a validation keeps its pipe's read end, non-blocking, in procd's event loop, with its own JSON tokenizer, result and error message, and the request deferred. When the output holds a whole JSON object, fails or ends, it answers the request: `validate_firmware_image` with the result, and `sysupgrade` by checking the result and starting the upgrade, with the same replies and statuses as before. Both ends of the pipe are close-on-exec, so the services procd starts meanwhile do not inherit them. `PKG_RELEASE` goes to 3.

Alternatives considered: pinging the watchdog while reading would leave ubus and service supervision waiting; a thread would be the first in procd, whose event loop already serves the job; a time limit on the validation would be a new policy, which the old code did not have.

Verification log: the firmware/ab-upgrade test "A validation slower than the watchdog" validates a FIFO that nobody writes for 45 s. Without the patch, its first `ubus call system board` meanwhile times out; with it, procd answers throughout, the router keeps its boot, and the validation answers once its checks end (2026-10-17, both boards). The A/B upgrade module on four host cores that `stress-ng` slows reset the router seven to nine times a run without the patch, and not once in two runs with it (2026-10-18, R4S). CI run 39060253957 passed on both boards.

### U-Boot: configured without asking

Patch: `patches/openwrt/0040-uboot-rockchip-configure-without-asking.patch` (adds the U-Boot patches `package/boot/uboot-rockchip/patches/120-kconfig-run-olddefconfig-after-merging-fragments.patch` and `121-kconfig-default-to-zero-if-int-hex-symbol-lacks-default.patch`, which the emulator's U-Boot takes too), for U-Boot, carried by openwrt/openwrt until then. Both are backports of Linux commits by Masahiro Yamada.

Problem: U-Boot's `scripts/kconfig/Makefile` merges a configuration fragment (`make <defconfig> <fragment>.config`) and then pipes `yes ""` into `make oldconfig`, so that every symbol the fragment brings up takes its default. U-Boot's Kconfig gives an int or hex symbol without a default an empty value, which is no valid one: `oldconfig` asks it again on every empty answer, and the merge never ends. Were the merge to end, the next `oldconfig` or `syncconfig` would ask it again at the end of its input, for ever. Linux merges with `olddefconfig` since 3266c806dc86 (2019) and gives such a symbol zero since 6262afa10ef7 (6.8); upstream U-Boot has neither.

Why it matters here: every board's U-Boot and the emulator's merge `orbyt-ab.config` and a board fragment onto their defconfig, and then, as both set `UBOOT_CUSTOMIZE_CONFIG`, OpenWrt's `include/u-boot.mk` changes `.config` with `scripts/config` and runs `make oldconfig`. On 2026-10-15 the emulator's build asked for `ENV_ADDR_REDUND` for two hours and filled the work volume, once `orbyt-ab.config` turned on the second environment copy while the emulator's defconfig still kept the environment in flash (`trial-boot-resilience`, `uboot-config-merge`).

What the patches do:
- 120, Linux's 3266c806dc86 as it is: the rule runs `olddefconfig` after the merge, which asks nothing and gives the configuration `yes ""` gives wherever it ends.
- 121, Linux's 6262afa10ef7: an int symbol without a default is `0`, a hex one `0x0`. U-Boot's `sym_calc_value()` starts a number from `symbol_empty`, so its two cases set the tristate too.
- `PKG_RELEASE` goes to 2. uboot-orbyt-qemu takes uboot-rockchip's patch directory, as it takes its version and hash, so the emulator's U-Boot is built with the boards' patches.

Alternatives considered: 120 alone ends the merge, but on the VM the `oldconfig` after it, with stdin from /dev/null, wrote 1.1 GB of prompts for the empty `ENV_ADDR_REDUND` in 20 s. Stopping `oldconfig` at the end of its input was a 2023 Linux series, dropped for breaking builds that run make with stdin from /dev/null. OpenWrt's `FAIL_ON_UNCONFIGURED` hack for its kernel's Kconfig is meant for OpenWrt only.

Verification log: the `build/boards` test "A fragment leaves a question for the next" configures a copy of the emulator's prepared U-Boot source as the build does. Without the patches, its merge was still asking after a minute; with 120 alone, the merge ended and the `oldconfig` after it was still asking (2026-10-18, both boards' build trees). With both, it passes on both boards' build trees, and both boards built anew with every U-Boot's `.config`, the boards' and the emulator's, the same as before (2026-10-18).

### build: a host build's stages named after its logs in the time log

Patch: `patches/openwrt/0042-build-name-a-host-build-s-stages-after-its-logs-in-t.patch`, for openwrt/openwrt.

Problem: the build time log (b95b0928ac, "build: add per stage build time profiling") names each stage by its package's directory, the host build's stages as the target build's: "compile" of `package/feeds/packages/rust` is either. A host build logs to `host-compile.txt`, a target build to `compile.txt`, and nothing in the time log says which of them ran. When both run at once, `build-time-report.pl` pairs the begin and end events by stage and name, so each takes the other's.

Why it matters here: the build records a package's UB-indicative warnings from its compile log when its time log has a compile stage for it (release-integrity D8). A host build named alike would have the target log read: one that only packed the package again holds no compiler output, and its warnings would be forgotten.

What the patch does: `include/host-build.mk` names its stages host-prepare, host-configure, host-compile and host-install, as its make targets and logs are named.

Verification log: the unit tests of `toolchain_stages` and `warnings_harvest` on stand-in time logs; on the VM, a board build's time log names the host builds it runs host-* (2026-10-26).

### procd: the trigger commands yet to run

Patch: `patches/openwrt/0043-procd-report-the-trigger-commands-yet-to-run.patch` (adds the procd patch `package/system/procd/patches/101-service-report-the-trigger-commands-yet-to-run.patch`), for procd, carried by openwrt/openwrt until then.

Problem: procd runs its triggers' commands one at a time, each after its trigger's delay, and `ubus call service event` and `reload_config` return once they are queued. One change can queue many, and `reload_config` queues those of every configuration changed since its last run, so a command can start long after its delay; nothing tells when procd has acted on a change.

Why it matters here: config-push judges a service after its reload. Under CI's load uhttpd's reload began 41 s after `reload_config` had returned, behind dae's, ksmbd's, dnsmasq's and others', and the push had accepted a configuration that stopped uhttpd by then (device-integrity D8).

What the patch does: the service object's new method `trigger_commands` lists the commands yet to end, each `delayed` (with the milliseconds left), `queued` behind others, or `running` (with its process). The list is empty once procd has run them all. `PKG_RELEASE` goes to 4.

Verification log: the ops/config-push test "A service that stops with its new configuration" holds a 30 s command ahead of uhttpd's reload.

### build: services disabled in the image

Patch: `patches/openwrt/0046-build-disable-the-services-TARGET_DISABLED_SERVICES-.patch`, for openwrt/openwrt.

Problem: `prepare_rootfs` enables every init script of the image except those its third argument names. The image builder passes `DISABLED_SERVICES` there; a build from source passes nothing. A package cannot ship its service disabled itself either: its `postinst` runs before `default_postinst` enables its init scripts.

Why it matters here: honk must not run before a configuration is pushed (its built-in DNS upstream would answer the LAN), and its start-at-boot switch is its rc.d link, as daeuniverse's LuCI page sets it. With honk disabled in the image and its rc.d links kept through upgrades (`files/lib/upgrade/keep.d/orbyt-config`), a new router starts without it and an upgraded one as it was. daeuniverse's own package disables honk from a uci-defaults script, which a firmware upgrade runs again.

What the patch does: `TARGET_DISABLED_SERVICES` in "Target Images", passed to `prepare_rootfs` wherever a build from source prepares a root filesystem (`package/Makefile`, `include/image.mk`). The rootfs cache key reads `.config`, so a changed list builds the root filesystem anew.

Verification log: 2026-11-13, the R4S image has no rc.d link of honk's (`/rom/etc/rc.d`, the transparent-proxy test of the image's template).

### procd: the cgroup of an instance that runs again

Patch: `patches/openwrt/0047-procd-keep-the-cgroup-of-an-instance-that-runs-again.patch`, for openwrt/procd.

Problem: once an instance's process has exited, `instance_exit_done` removes the instance's cgroup and its service's, before it decides whether the instance runs again. A restart (an init script's stop, then a start that comes while the old process is still exiting, which procd turns into a restart of the same instance) and a respawn start the instance again in a cgroup procd creates anew, without what the init script had set on the service's cgroup.

Why it matters here: honk's init pins honk to the big cores through the cpuset of honk's service cgroup and enables the memory controller there for honk's telemetry (honk-datapath D5). On the emulator, after `/etc/init.d/honk restart` with pinning on, `services/honk/cpuset.cpus` read 4-5 while the old honk exited and was empty once the new one ran, on every core (`taskset` 3f).

What the patch does: the cgroups go with the instance only, as `instance_free` already removes them when an instance is deleted. An instance that stopped and stays registered keeps its empty cgroup until it starts again or is deleted, as it already keeps a program attached to it (`instance_set_vrf`).

Verification log: 2026-11-13, procd 6 in the R4S image: the transparent-proxy test of CPU pinning, which turns pinning on and restarts honk, finds honk on the big cores in two runs of the network suite; without the patch it ran on every core.

### procd: a shutdown cancels the boot scripts still running

Patch: `patches/openwrt/0048-procd-cancel-the-boot-scripts-still-running-when-the.patch` (adds the procd patch `package/system/procd/patches/103-rcS-cancel-the-boot-scripts-still-running-when-the-shutdown-starts.patch`), for openwrt/procd.

Problem: procd runs the boot's `S` scripts and the shutdown's `K` scripts in one runqueue, one script at a time, and `rcS()` set that queue up anew for each run with libubox's `runqueue_init()`, which empties the task lists but keeps the count of running tasks. A shutdown that starts while a boot script still runs therefore starts none of its `K` scripts until that script returns, and nothing ends it before the halt: a boot script that never returns (one waiting for a device that never comes, a loop) keeps the system in procd's shutdown state for good, procd feeding the watchdog meanwhile. A reboot then never completes, whoever asked for it.

Why it matters here: orbyt-ab's trial supervisor turns a hung trial boot into a counted reboot (trial-guards D1), which is exactly a reboot while a boot script hangs. On the emulator, a uci-defaults script looping forever on a trial slot kept the system at `- shutdown -` for the ten minutes the probe watched, the script still running, and the rollback test of a hung boot timed out after 30 minutes on its first trial boot.

What the patch does: `rcS()` cancels what is left of the previous run instead of setting the queue up anew. The scripts not yet started are dropped; the running one gets SIGTERM and, 10 s later, SIGKILL, as a `shutdown` script past its 15 s already does; the shutdown's scripts start once it has ended. Every script of that queue gets the 10 s from SIGTERM to SIGKILL (none is cancelled otherwise), the queue is set up once, as procd's queue of single init scripts (`rc()`) is, and a script dropped before it started closes no output: its pipe was never opened, where the completion closed descriptor 0 for it. `PKG_RELEASE` goes to 7.

Alternatives considered: a forced reboot (`reboot -f`) in orbyt-ab's supervisor once a plain one has not completed in time would leave every other reboot during a hung boot script hanging, and skip the `K` scripts and the unmount; a time limit on `boot` runs would be a new policy, and a first boot's uci-defaults may take minutes.

Verification log: 2026-11-17, the firmware/boot-rollback test of a boot script that hangs during a trial boot. With procd 6, on the emulated R4S and in CI run 43976186041 on both boards, it timed out waiting for the rollback; a probe in the hung script (never committed) found the system at `- shutdown -` from 61 s until 659 s, the script running throughout. With procd 7, each of its three hung trial boots reboots 7 s after the trial's deadline (`- SIGTERM processes -`, `- SIGKILL processes -`, `- reboot -`), the bootlimit is exceeded and slot A confirmed; the R4S's `upgrade` and `boot` suites pass, 44 tests. CI run 44002274413 passed on both boards.

### procd: the script a mount trigger runs named from $initscript

Patch: `patches/openwrt/0051-procd-name-the-script-a-mount-trigger-runs-from-initscript.patch`, for openwrt/openwrt.

Problem: `_procd_add_mount_trigger` ran `/etc/init.d/$name`, a variable of whoever called it: a trigger an init script registered with it directly, or from a function with a `$name` of its own, ran another script or none.

Why it matters here: the unmount triggers (patch 0035) call it through the same helper as the mount triggers, from init scripts that set `$name` for their own instances.

What the patch does: `_procd_add_mount_trigger` names the script itself, from `$initscript` as `readlink` resolves it, as the mount helpers named it for their call.

Verification log: 2026-10-12, the triggers `procd.sh` builds, with the build tree's host `jshn`: each names its own init script.

### procd: one condition for the mount points of a mount trigger

Patch: `patches/openwrt/0052-procd-one-condition-for-the-mount-points-of-a-mount-trigger.patch`, for openwrt/openwrt.

Problem: the mount helpers passed the mount points of their paths as one argument, joined by newlines, so paths on several mount points gave a single `eq` against the whole list, which no event matched.

Why it matters here: ksmbd's shares and the log can lie on different mount points of the data disk (`/mnt/data` and a mount point inside it), and a service must follow each.

What the patch does: the mount points are separate arguments, split on lines as `procd_get_mountpoints` lists them, which `_procd_add_mount_trigger` turns into one `or` that any of them meets.

Verification log: 2026-10-12, one `or` for two mount points; 2026-10-26, with an fstab of `/mnt/data` and `/mnt/data/media`: one `mount.add` trigger with an `or` of both, and a `mount.remove` trigger for each.

### procd: a mount point with a space in it counted as mounted

Patch: `patches/openwrt/0053-procd-a-mount-point-with-a-space-in-it-counts-as-mounted.patch`, for openwrt/openwrt.

Problem: `procd_mountpoints_ready <path>...`, upstream's check since a530a202, tells whether every fstab mount point that holds the paths is mounted. It took a mount point with a space in it for one never mounted: it split the list of mount points on any white space, and compared each with the second field of `/proc/mounts` as the kernel escapes it (`\040` for a space).

Why it matters here: ksmbd leaves a share out unless the mount points its path lies on are mounted (patch packages/0001), and a share path an administrator names may hold a space.

What the patch does: the list is split on lines, once `procd_get_mountpoints` has run, since `config_foreach` splits its list of sections on `IFS`; the field is unescaped, and the mount point reaches awk through the environment, which leaves it as it is.

Verification log: 2026-10-26, `procd_mountpoints_ready` false for a path under a mount point that is not mounted inside one that is (device-integrity D7). The R4S's suites then found the services on the data disk started without it: that version split the list with a newline `IFS`, under which `config_foreach` took the whole list of sections for one and `procd_get_mountpoints` found no mount point, so every path counted as mounted. In a chroot of the R4S's root filesystem with its BusyBox and the VM's `/proc`, the current version: `/mnt/data/shares` not mounted, `/proc/self` mounted, a path no fstab mount point holds mounted, and `/proc/self` with `/mnt/data/logs` not mounted; the awk alone found mount points with a space, a tab and a backslash in `/proc/mounts`' escapes.

### procd: a service acting when a ubus object appears

Patch: `patches/openwrt/0054-procd-let-a-service-act-when-a-ubus-object-appears.patch` (adds the procd patch `package/system/procd/patches/104-service-pass-object-registrations-to-the-triggers.patch`), for procd and openwrt/openwrt.

Problem: procd listens to `ubus.object.add` only to subscribe to the objects services watch; its service triggers never see it, so an init script cannot act when its daemon's object appears. It configures the daemon from the `running` action instead, which procd runs after a start and a respawn but every status query runs too, as qosify's, umdns's and bridger's do, or waits for the object (`ubus wait_for`).

Why it matters here: qosify takes its configuration over ubus once its daemon is up (patch 0006).

What the patch does: procd passes every `ubus.object.add` to the triggers too, and `procd.sh` gains `procd_add_object_trigger <object> <command>...` and `procd_add_reload_object_trigger <object>`, which run a command, or reload the init script, whenever the object of that path appears, after procd's usual reload delay. `PKG_RELEASE` goes to 11.

Verification log: 2026-11-21, the series applies.

### procd: an instance procd stops is not running

Patch: `patches/openwrt/0055-procd-an-instance-procd-stops-is-not-running.patch` (adds the procd patch `package/system/procd/patches/105-instance-report-an-instance-stopped-for-good.patch`), for procd and openwrt/openwrt.

Problem: procd's service list says `running` for an instance as long as its process lives, and an instance procd stops for good, its service deleted, lives on until it exits, up to its term timeout. `procd_running` reads it as running, so an init script that acts on a running service only, as one that restarts it, acts on a service that has just been stopped, and starts it again.

Why it matters here: honk's init restarts a running honk when the data disk is mounted or unmounted, and leaves a stopped one stopped (firmware-hygiene D9); honk can take seconds to shut down, and the R6S's suite found it started again after its stop.

What the patch does: procd reports an instance it stops for good, its process still running, as `stopping`, and `procd_running` counts only an instance that runs and is not stopping. `PKG_RELEASE` goes to 12.

Verification log: 2026-11-21, on the emulated R4S: honk held still (SIGSTOP), the data disk unmounted and honk stopped before procd ran the unmount's command; before the patch honk ran again after its stop, two runs of two.

## The packages series

### ksmbd-tools: shares on a disk that is not mounted

Patch: `patches/packages/0001-ksmbd-tools-share-only-what-is-mounted-and-start-onc.patch`, for openwrt/packages.

Problem: ksmbd's init script shares every configured path whether or not the disk it belongs on is mounted. A share on a USB disk that is late or absent then shares the empty directory underneath, on the router's flash: what clients write there fills the flash, and disappears from view once the disk is mounted over it. Nothing starts the service again when the disk arrives, and nothing withdraws a share whose disk is unmounted while the service runs.

Why it matters here: the shares are on the data disk, a USB disk that may be late or absent, and services/file-sharing requires that no share be offered from underneath it (device-robustness D1).

What the patch does: `smb_add_share` leaves a share out unless every fstab mount point its path lies on is mounted (`procd_mountpoints_ready`, patch 0035). `service_triggers` adds a reload trigger per share path for the mount, and one for the unmount (procd's unmount helpers, patch 0035), so the mount brings the share and the unmount takes it away: `mount.remove` follows the unmount (patch 0036), and `/proc/mounts` tells the reload what went. A reload starts the service anew, as every start resets the server hard; a restart would drop the service, and its triggers with it, until it had started again, so a disk back within that time went unnoticed. A start with every share waiting stops a running server, after that hard reset, and starts nothing. Shares on no fstab mount point are unaffected. `PKG_RELEASE` goes to 4.

How this project uses it: the share `shares` lies on the data disk, whose fstab entry exists from the first boot (r4s-services D2).

Verification log: 2026-09-29, in the emulator ksmbd stays down without the data disk and starts when it is plugged in (`tests/storage/test_data_disk.py`, `tests/services/test_file_sharing.py`). With patches 0035 and 0036, the data disk removed while the service runs stops it, port 445 included, and its return brings the shares back (the file-sharing test "Data disk removed while sharing", both boards). The file-sharing tests "Data disk removed while an unmount script runs" and "Share within a disk within another" check a reload asked for while the unmount waits and the nested mount points (device-integrity D7).

### crun: an update's JSON checked before it is used

Patch: `patches/packages/0003-crun-check-the-generated-JSON-before-using-it.patch` (adds the package patch `100-update-check-the-generated-JSON-before-using-it.patch`), for github.com/containers/crun.

Problem: `libcrun_container_update_from_values`, which `crun update` runs, ignores the status of `json_gen_get_buf`. When json-c cannot allocate the document or its text, the buffer stays unset, and the indeterminate pointer is parsed as the update's JSON. crun's other callers of `json_gen_get_buf` check the status; crun's main has the same code (2026-10-05).

Why it matters here: `podman update` runs `crun update` for the containers of orbyt-containers, and a router runs out of memory more readily than a server. The review of the build's warnings found it (`'buf' may be used uninitialized`).

What the patch does: the update fails with an error, after freeing the generator, as the other callers do.

Verification log: 2026-10-05, found by the review of the R4S's UB-indicative warnings at `-O3` (toolchain-o3 task 3.3) and patched; the patched crun builds in both boards' images since. No test runs json-c out of memory.

### bash: six places of undefined behavior

Patch: `patches/packages/0004-bash-fix-the-undefined-behavior-of-six-places.patch` (adds the package patches `100` to `105`), for bash (bug-bash@gnu.org, git.savannah.gnu.org/git/bash.git).

Problem: the review of bash 5.3's warnings at `-O3` (docs/undefined-behavior.md) found five faults behind them and one next to them, none fixed in bash's devel branch (1c20880e, 2026-09-23):
- `make_command` clears every command's flags through a `SIMPLE_COM` pointer, larger than the group or subshell structure it points to (`-Warray-bounds`).
- `parse_comsub` restores `extglob` from a local it never set, when parsing a command substitution changes the compatibility level, as a `PS2` that assigns `BASH_COMPAT` does.
- `array_value_internal` goes on with an array that expanding its subscript (`${ unset A; ...; }`) unset, freed or gave another type: it reads freed memory, and at `-O3` the shell crashed, or an index it never computed.
- `split_at_delims` leaves the word counts unset for a string of whitespace delimiters, and programmable completion sets `COMP_CWORD` from an indeterminate value.
- `do_redirection_internal` restores a word's flags from a variable never set, when expanding the word turns posix mode on (`${POSIXLY_CORRECT:=...}`).
- `pushd --9223372036854775808` overflows a subtraction.

Why it matters here: bash is in every image, and `-O3` is free to exploit any of them.

What the patches do: one patch per fault, each the smallest change that removes it. `array_value_internal` looks the array up again after each expansion of its subscript and expands to nothing when its type changed; `pushd` checks the offset before it subtracts. The others store what they left unset, or keep what they read twice.

Verification log: 2026-10-05, on the VM, with the R6S's `-O3` build run through the image's musl loader. The array whose subscript unsets it and makes it indexed expands to nothing, in a function and at global scope, where the unpatched shell printed another element or crashed; arrays, groups, subshells, functions, posix mode through a redirection word, and `pushd` with `--9223372036854775808` and `--1` behave as before or fail with bash's own errors. The interactive cases (`PS2`, completion) were not run.

### wsdd2: the random seed without overflow

Patch: `patches/packages/0005-wsdd2-seed-without-overflow.patch` (adds the package patch `020-wsd-seed-without-overflow.patch`), for openwrt/packages: wsdd2's own repository, github.com/Netgear/wsdd2, is gone, and openwrt/packages builds it from its mirror.

Problem: `set_seed()` folds the endpoint's UUID into its seed by shifting the first 16 bits of each pair left by 16 as an `int`. For a value of 0x8000 or more, as half of all UUIDs have, the result does not fit in an `int`, which is undefined behavior. It also has `time()` write a `time_t` into an `unsigned long`, which is too small for it on a 32-bit target with a 64-bit `time_t`, as musl's are.

Why it matters here: the `ubsan` profile's fifth run trapped here: wsdd2 trapped on almost every start, and procd started it again, through every suite.

What the patch does: the shift is done as `unsigned long`, and the seed takes `time()`'s result. `srand48()` takes the low 32 bits of its seed, which stay the same.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

### podman: equal database paths matched without resolving them

Patch: `patches/packages/0006-podman-match-equal-database-paths-without-resolving-.patch` (adds the podman patch `utils/podman/patches/020-libpod-match-equal-database-paths-without-resolving-them.patch`), for podman, carried by openwrt/packages until then.

Problem: `ValidateDBConfig` compares the paths the database recorded with the runtime's own, resolving the symlinks of each in turn; a path is resolved only if it exists. Without `--runroot`, the runtime's run root is the database's, the same string. The storage creates the run root after the validation, so a second podman process that creates it between the first one's two resolutions makes the same path compare unequal: `database run root "/run/containers/storage" does not match our run root "/tmp/run/containers/storage": database configuration mismatch`. Since podman 6, only the SQLite state validates its configuration: the BoltDB state is left for the migration to SQLite. Upstream fixed the same race for the volume path by creating it first (containers/podman#23515).

Why it matters here: the image's run root goes through `/run` → `/var/run` → `/tmp/run`, and orbyt-containers and orbyt-sync run podman at the same time after a boot or a mount of the data disk. CI run 37324813891 lost a device sync to it (`device-robustness` D4).

What the patch does: the SQLite state resolves the paths only when they differ as strings; equal paths match. `PKG_RELEASE` goes to 2.

Verification log: the services/containers test "Runtime commands at the same time" runs ten rounds of eight `podman info` at once, each on a scratch storage whose run root does not exist yet. Concurrency alone reproduced nothing in ten rounds without the patch, even with the run root behind 32 symlinks: the window is two path resolutions wide. A symlink on the run root's path that keeps changing its target between two names of one directory (a bind mount), as a concurrent creation changes how the path resolves, made all ten rounds fail without the patch (2026-10-12, R6S).

### podman: the storage's feature probes leave no mounts behind

Patch: `patches/packages/0007-podman-lock-the-storage-s-home-mount-for-its-lazy-fe.patch` (adds the podman patch `utils/podman/patches/021-overlay-lock-home-s-mount-for-the-lazy-feature-probes.patch`, to its vendored copy of go.podman.io/storage), for go.podman.io/storage, carried by openwrt/packages until then.

Problem: the storage's overlay driver probes three kernel features when it is first asked about them, after its initialization: idmapped lower layers, in `Status()`, which `podman info` calls, and in the creation of a layer or a container; volatile mounts, in `Status()` and when it mounts a layer; and data-only lower layers. Each probe mounts in a new directory under the driver's home, then unmounts by path. The store holds its graph lock while the driver initializes, which binds the home onto itself unless it is a mount point already (`mount.MakePrivate`), and while `Cleanup()` unmounts the home at a command's end. It does not hold it for `Status()` or the creations. When another process binds the home while a probe has its mounts under the home's previous mount, the bind hides them. podman warns `Unmount ".../overlay/compat1721885628/lower-mapped": invalid argument`, the probe's directory cannot be removed, and the mounts stay until a reboot.

Why it matters here: the storage is on the data disk, and orbyt-containers and orbyt-sync run podman at the same time after a boot or a mount of the data disk, on a run root in RAM that has no record of the probes yet. Mounts left under the storage keep the data disk's mount busy until a reboot. CI run 38556156281 lost the services/containers test "Runtime commands at the same time" to it in both attempts: its cleanup could not remove the scratch storage (`Resource busy`).

What the patch does: the driver gets a lock of its own, `home.lock` in the `overlay` directory of the run root. It is held while the driver binds the home, while `Cleanup()` unmounts it, and while a probe that runs after the initialization mounts under the home. It keeps two operations on one mount apart, as the graph lock does for the probes of the initialization, and a probe runs once per run root, so once per boot. Taking the graph lock in `Status()` instead would leave the creations' probes unlocked: they run under the layer store's lock, after which the graph lock cannot be taken. The lock file's name stands in a group of its own, the paths within the run home, beside the storage's group of the paths within the home. `PKG_RELEASE` goes to 3.

Verification log: the services/containers test "Runtime commands at the same time" runs ten rounds of eight podman commands at once, three in a row each, with the probes' records removed as they appear, so that every command probes. Without the patch, 7 and 8 of the 10 rounds left the probes' mounts behind in two runs; with it, none of 30 rounds in three runs did, and every command succeeded (2026-10-15, R4S).

### netavark: aardvark-dns in a cgroup of its own without systemd

Patch: `patches/packages/0009-netavark-run-aardvark-dns-in-a-cgroup-of-its-own-wit.patch` (adds the netavark patch `010-aardvark-run-aardvark-dns-in-a-cgroup-of-its-own-without-systemd.patch`), for netavark, carried by openwrt/packages until then.

Problem: netavark starts aardvark-dns, the DNS server of a network with DNS enabled, when a container on it needs one, and aardvark-dns then outlives that run of netavark and serves every container of its networks until the last one goes. With systemd it runs in a scope of its own (`systemd-run --scope`); without systemd it stays in the cgroup of whatever ran netavark. procd's 39b5aac8c1 (2026-10-18, in OpenWrt's procd of the pins of 2026-10-25) kills what a service leaves in its cgroup once the service's main process exits, as OpenRC's `rc_cgroup_cleanup` does when a service stops. aardvark-dns then died with the first service that ran a container and ended, its pid file staying behind. The next run of netavark that removed the network's last container found no process behind the pid file, started aardvark-dns on a configuration without a container, which exits at once, and failed: `aardvark-dns failed to start: Error from child process`.

Why it matters here: podman's default network, which orbyt-containers' Pods and orbyt-sync's fetch container join, has DNS enabled. orbyt-sync and `orbyt-containers apply` run as procd instances that end once their work is done. On the R4S, aardvark-dns ran in `/services/orbyt-sync/instance1` and was gone once orbyt-sync had ended; stopping the app Pod then failed (2026-10-26).

What the patch does: on the cgroup v2 hierarchy, a rootful netavark without systemd has aardvark-dns join a cgroup of its own, `/sys/fs/cgroup/aardvark-dns`, made when it is missing, between fork and exec, so that the daemon it forks runs there too. podman moves conmon and the containers into `libpod_parent` the same way. A rootless netavark has no say over the hierarchy and leaves aardvark-dns where it is. `PKG_RELEASE` goes to 2.

Verification log: without the patch, on the R4S, aardvark-dns ran in `/services/orbyt-sync/instance1`, was gone with orbyt-sync, and stopping the app Pod failed as above. With it, the services/containers tests passed on the R4S, "A service's container ended" among them (device-integrity): after orbyt-sync ended, the app Pod stopped and started again, and aardvark-dns answered its name (2026-10-26).

### libpfring: ring_bind with the kernel's address type

Patch: `patches/packages/0010-libpfring-build-against-Linux-6.18.57-and-later.patch` (adds the package patch `902-pf_ring-bind-with-the-address-type-of-the-kernel.patch`), for ntop/PF_RING, carried by openwrt/packages until then.

Problem: `proto_ops.bind` takes a `struct sockaddr_unsized *` in mainline since 6.19 (0e50474fa514), and 6.18.57 took that change as a dependency of a Bluetooth fix (946dc5835c8f). PF_RING 9.2.0's `ring_bind` still takes a `struct sockaddr *`, and GCC rejects the initializer of `ring_ops.bind` as an incompatible pointer type. PF_RING's development branch has the new type from 6.19.0 on, which leaves out the stable releases that took it.

Why it matters here: the `ci` profile sets `CONFIG_ALL_KMODS`, so this one module stopped the firmware build on kernel 6.18.60.

What the patch does: `ring_bind` is declared with the new type from 6.18.57 on, in the version check `pf_ring.c` uses throughout; it already has one on a stable release, 6.5.3 for `sendpage`. The body reads the same in both types. `PKG_RELEASE` goes to 2.

Verification log: the module is built by both boards' `ci` builds on 6.18.60.

### rust: 1.99.1

Patch: `patches/packages/0011-rust-update-to-1.99.1.patch`, for openwrt/packages.

Problem: openwrt/packages, at its pin of 2026-11-05, builds Rust 1.96.1; the stable release is 1.99.1, released on 2026-10-16.

Why it matters here: honk (honk-datapath) depends on Aya 0.16, whose crates require rustc 1.98.0; with 1.96.1, cargo refuses to build them.

What the patch does: `PKG_VERSION` and `PKG_HASH` of rustc 1.99.1's source, which bundles LLVM 23.1.1. Rust's bootstrap manifest moved, so the xz2 patch (`0001-Update-xz2-and-use-it-static.patch`) is refreshed on it; the AtomicExpand patch applies as it is.

Verification log: 2026-11-13, the R4S tree builds rust/host 1.99.1 and with it honk-core (Aya 0.16) and its eBPF object, and the network and services suites pass on the image (58 and 42 tests).

### rust: the LLVM rustc links, installed for host tools

Patch: `patches/packages/0012-rust-install-the-LLVM-rustc-links-for-host-tools-tha.patch`, for openwrt/packages.

Problem: rust/host builds LLVM for rustc and keeps it to itself. A host tool that works on rustc's LLVM bitcode needs an LLVM that reads it: the same version, or a newer one.

Why it matters here: bpf-linker links honk's eBPF programs, which rustc emits as bitcode. The host's other LLVM (`flake.nix`, for C BPF objects) is 21, older than Rust 1.99's 23, and a second LLVM of the right version would be a second toolchain to build and trust.

What the patch does: rust/host's dist adds Rust's `rust-dev` component, its LLVM with `llvm-config`, libraries and headers, and installs it under a prefix of its own, `RUST_LLVM_PREFIX` (`rust-values.mk`, `$(STAGING_DIR_HOSTPKG)/lib/llvm-rust`), so that `llvm-config` stays off other packages' PATH, where configure scripts would find it and link LLVM.

Verification log: 2026-11-13, in the R4S tree bpf-linker/host builds against `lib/llvm-rust` and links honk's eBPF object, whose programs the image's honk attaches (the transparent-proxy tests).

### rust: host artifacts linked with the host compiler

Patch: `patches/packages/0013-rust-link-host-artifacts-with-the-host-compiler.patch`, for openwrt/packages.

Problem: `rust-values.mk` names the linker of the target triple (`CARGO_TARGET_<TRIPLE>_LINKER`) but none for the host's, so host artifacts (host packages, build scripts and procedural macros) link with rustc's default `cc`, or with whatever a crate's own `.cargo/config.toml` names for its development.

Why it matters here: bpf-linker's `.cargo/config.toml` asks for `clang` on Linux; the build environment's clang does not know the host GCC, finds neither `crtbeginS.o` nor `libgcc`, and bpf-linker/host fails to link its first build script.

What the patch does: `CARGO_HOST_LINKER`, the host triple's linker set to `HOSTCC_NOCACHE`, in the variables of host builds (`CARGO_HOST_CONFIG_VARS`) and of target builds (`CARGO_PKG_CONFIG_VARS`), before the target's own. A setting named for the triple takes precedence over one a crate sets for a `cfg()`.

Verification log: 2026-11-13, bpf-linker/host's build scripts link with the host compiler in the R4S tree, and the image builds.

### rust: LLVM built through ccache

Patch: `patches/packages/0016-rust-build-LLVM-through-ccache-when-the-build-uses-it.patch`, for openwrt/packages.

Problem: with `CONFIG_CCACHE`, the build's C and C++ go through ccache, but rust/host's LLVM, most of the host toolchain's build time, did not: a host toolchain built again, as after a change of its flags, compiled all of LLVM again.

Why it matters here: CI's host stage builds the Rust host toolchain whenever its key changes, and a local tree builds it anew after a new host environment (nixpkgs-2605 D4).

What the patch does: with `CONFIG_CCACHE`, rustbuild gets the build's ccache (`build.ccache`) for LLVM's C++.

Verification log: 2026-10-03, in the patch it was part of (packages/0002 until 2026-11-21, patch-hygiene D2): the host stage's compiler cache report counts LLVM's objects. 2026-11-21: the split series gives the tree the one patch did.

## The luci series

### luci-base: the host tools built in the host build directory

Patch: `patches/luci/0001-luci-base-build-po2lmo-and-jsmin-in-the-host-build-d.patch`, for openwrt/luci.

Problem: luci-base's host build compiles `po2lmo` and `jsmin` with `make -C src/`, in the package's own source directory, after it has written its prepared stamp. Their objects and binaries are then newer than that stamp, so every build prepares luci-base again, for the host and for the target, and packages it anew.

Why it matters here: with the rest of build-acceleration, luci-base was the only package a build with nothing changed still prepared and compiled.

What the patch does: `Host/Prepare` already copies `src/` into the host build directory, so `Host/Compile` builds there, and `Host/Install` takes the tools from there.

Verification log: 2026-10-04, both tools build from a copy of `src/`, as in the host build directory, and with the patch a build with nothing changed no longer prepares luci-base.

### luci-base: the string hash without shifting a negative value

Patch: `patches/luci/0002-luci-base-hash-without-shifting-a-negative-value.patch`, for openwrt/luci.

Problem: `sfh_hash()`, which keys LuCI's translation catalogs, shifts the third of the trailing bytes, as a `signed char`, left by 18 bits. For a byte of 0x80 or more, as UTF-8 text has, that shifts a negative value, which is undefined behavior.

Why it matters here: the `ubsan` profile's third run trapped here translating a page into Simplified Chinese, and the page did not render.

What the patch does: the value is shifted as `uint32_t`. That keeps every hash as GCC computed it, so the catalogs that `po2lmo` made still match.

Verification log: see the `ubsan` run in `docs/undefined-behavior.md`.

## The daeuniverse series

### luci-lib-daeuniverse: BusyBox's timeout

Patch: `patches/daeuniverse/0003-luci-lib-daeuniverse-BusyBox-s-timeout-is-enough.patch`, for daeuniverse/openwrt-packages.

Problem: the library's package check bounds `apk update` with `timeout --signal=TERM --kill-after=5 20`, and the library depends on `coreutils-timeout` for those long options. That builds coreutils and puts it in every image with the LuCI pages, for one call.

Why it matters here: coreutils came into the image with luci-app-honk, and with it 22 warnings of the reviewed-warnings register's kinds (quality/undefined-behavior) across coreutils, of which the image installs only timeout.

What the patch does: the short options `-s TERM -k 5`, which coreutils' timeout and BusyBox's (on by default in OpenWrt's BusyBox, 1.38 here) both take, and a dependency on BusyBox's applet (`+@BUSYBOX_CONFIG_TIMEOUT`, since 2026-11-21) instead of coreutils-timeout, so that no configuration without the applet selects the library.

Verification log: 2026-11-13, the R4S image has no coreutils, and the reviewed-warnings register check passes with 40 warnings of its kinds (22 fewer). On the emulated R4S, `/usr/bin/timeout` is BusyBox's and ends a command on time with these options (`-s TERM -k 5 2 sleep 10` exits 143 after two seconds), and the page's check, `daeuniverse-pkg check honk`, answers `{ "packages": [ ], "warning": "" }`.

## QEMU's

### sdhci-pci loses its card on loadvm (QEMU)

Patch: `patches/qemu/0001-hw-sd-sdhci-pci-migrate-the-PCI-device-state.patch`, for qemu/qemu.

Problem: `sdhci-pci` takes the migration description of the sysbus SDHCI variants, `sdhci_vmstate`, which holds only the controller registers. Its PCI configuration space is never saved, so after `loadvm` (or a migration) the BAR is unmapped, every register reads as all ones, and the guest loses its card ("Controller never released inhibit bit(s)").

Why it matters here: since r4s-ab-rollback, the emulator boots the factory image from its boot disk, an SD card or an eMMC on `sdhci-pci`, and the tests return the machine to a `savevm` snapshot between every two tests.

What the patch does: it gives `sdhci-pci` a description of its own: the PCI device state first, then the shared controller state. Its migration section is then named `sdhci-pci` rather than `sdhci`, so a stream from an earlier QEMU no longer loads into `sdhci-pci`; such a stream holds no PCI state, and its guest lost the card anyway. `flake.nix` builds the emulator's QEMU (aarch64 guests only) with it, and with every other patch in `patches/qemu/`.

Verification log: 2026-09-29, QEMU 11.1.1 builds with the patch, and the emulation tests, which restore a snapshot between every two tests, pass with the SD card. 2026-10-26, QEMU 11.1.2 builds with it; its `sdhci-pci.c` still migrates no PCI state.

## The feed packages' own

### einat marks the inbound packets it translates back

Patch: `feed/net/einat/patches/100-mark-inbound-packets-translated-back.patch`, for EHfive/einat-ebpf.

Problem: einat reverse-translates inbound packets in its tc ingress program, before netfilter sees them, and leaves no trace of having done so. A firewall behind it cannot tell a packet einat let in (a reply, or a new flow to a mapped port under full-cone filtering) from one that arrived for an internal address by other means (a spoofed destination). The usual answer, accepting every forwarded packet from the external zone towards the internal ones, accepts both.

Why it matters here: einat runs with `--inbound-mark 0x20000000` (the bit `config/marks.tsv` gives it), and its init script adds one fw4 rule that accepts forwarded packets from wan to lan carrying the bit (r4s-ebpf-datapath D2, D3).

What the patch does: an `inbound_mark` option (`--inbound-mark` on the command line), ORed into `skb->mark` by `ingress_rev_snat` after a successful reverse translation. It is a read-only global of the BPF object, 0 by default, which marks nothing, so without the option einat behaves as before. Hairpinned packets never pass `ingress_rev_snat` (egress redirects them), so they stay unmarked. The Rust side adds the option to the configuration and the command line (hexadecimal accepted) and passes it with the other globals; the rodata struct gains explicit padding, as the loader requires a layout without implicit padding.

Verification log: 2026-09-29, the patch applies to einat-ebpf 0.1.11 (`ba647ce`) and builds with the aya loader. 2026-11-15, einat 0.2.0 (aya 0.16): the patch's range-diff against its 0.1.11 form is empty, its index lines and one hunk's offset the only change; it builds, and the NAT tests pass on the emulated R4S, the inbound connection the mark lets in among them.

### honk: a prebuilt eBPF object

Patch: `feed/net/honk/patches/001-build-take-a-prebuilt-eBPF-object.patch`, for daeuniverse/honk.

Problem: honk-core's build script embeds an eBPF object it finds only when a `.toolchain` file beside it names the nightly that `crates/honk-ebpf/rust-toolchain.toml` pins; otherwise it builds the object with `cargo +<nightly>`, which only rustup provides.

Why it matters here: the firmware builds honk with OpenWrt's own Rust, and its eBPF object in a step of its own (honk-datapath D2), with no rustup and no nightly.

What the patch does: `HONK_PREBUILT_EBPF_OBJECT`, the absolute path of an object, makes the build script check that the object carries BTF and embed it as it is. Without it, nothing changes. The copy into `OUT_DIR` both paths share moves into `embed_object`.

Verification log: 2026-11-13, honk-core's build embeds the package's object (`eBPF object embedded (3292696 bytes)`), in the package build and in honk-core's tests on the VM with `HONK_PREBUILT_EBPF_OBJECT`; on the R4S, honk attaches its programs from it (the transparent-proxy tests).

### honk: check, offline admission of a configuration

Patch: `feed/net/honk/patches/002-cli-add-check-offline-admission-of-a-configuration.patch`, for daeuniverse/honk.

Problem: honk-core cannot say whether it would take a configuration without starting, which binds its listeners and attaches its programs. A reload is no answer: SIGHUP keeps the old configuration on refusal and says so only in the log.

Why it matters here: the firmware wraps the operator's configuration in an entry of its own (honk-datapath D4), and config-push must refuse a configuration honk would refuse before the router changes (ops/config-push), as the init script must before it starts or reloads honk (D5).

What the patch does: `honk-core check` admits the `-c` entry offline as a start would: the entry and its includes parsed, validated and assembled, with the configuration as its own active one, then routing and DNS compiled over the geodata it finds, its data directory's first. It shares the native API's offline admission, which refuses a candidate whose geodata file is missing; a start and a reload run without it instead (its rules match nothing until the file is fetched), so the patch splits that admission's compile from the refusal (`CapturedConfig::compile` under `validate`), lets geodata load from a given data directory (`GeoSourceSet::load_from`, which `load` now calls with the process-wide one), and admits for a start through `offline::validate_for_start`, which reports a missing file as a `geo-asset-missing` warning. Nothing is bound, attached, created or written. Each finding goes to standard error as `<file>[:line[:column]]: <severity>[<code>]: <setting>: <message>`, without values, which may be secrets, and the command exits nonzero when a start would refuse the configuration. It needs the `native-api` feature, as that admission does, and a `.dae` entry. Unit tests beside it: a configuration a start takes, admitted without creating its data directory; one whose geodata is not there yet, admitted with the warning (it fails without the split: `missing-offline-dependency`); a routing target no group declares, a syntax error and an include outside the entry's directory, refused. The tests load geodata from their own data directory alone (`GeoSourceSet::load_pinned`, as `load_captured` pins the lifecycle tests' inputs, through `check_with`): honk also looks in fallback directories, `/etc/dae` among them, where upstream's weekly CI installs `geosite.dat`, and the test of geodata not there yet would find it (review, 2026-11-15). The CLI reference, in both languages, has the command.

Verification log: 2026-11-13, honk-core's unit tests on the VM (aarch64 Linux, the tree's host Rust, `--no-default-features --features native-api`): `check::`, `routing::geo::`, `native_api::offline` and `native_api::config`, 185 passed; the test of geodata not there yet failed before the split, refused with `missing-offline-dependency`. On the emulated R4S: the init script checks the entry before every start and reload, and the ops suite's config-push tests pass, among them the refusal of a routing target no group declares and of a syntax error, with the router's configuration unchanged; the storage tests of honk's state find it starting on a router whose geodata is not there yet. 2026-11-15, the review: with a `geosite.dat` where honk looks first (`DAE_LOCATION_ASSET`), the check's five tests pass, where the test of geodata not there yet failed before (no `geo-asset-missing` warning); honk-core's tests as 006's.

### honk: the namespace registry, shared

Patch: `feed/net/honk/patches/003-daens-keep-the-namespace-registry-as-other-tools-share-it.patch`, for daeuniverse/honk.

Problem: honk binds its `daens` namespace into `/run/netns`, the registry of named network namespaces that `ip netns` keeps and podman shares for its containers' namespaces. Where the registry was no mountpoint, honk mounted a tmpfs over it, and it unmounted that tmpfs on stop, taking along every namespace registered there while it ran. It judged whether the registry was a mountpoint by comparing the unresolved path with `/proc/mounts`, which lists resolved paths: where `/run` or `/var/run` is a symlink the comparison never matches, so every start mounted another tmpfs over the registry, hiding the namespaces registered before it, and a stale `daens` mount of a run that did not clean up was never detached.

Why it matters here: on OpenWrt `/run` and `/var/run` lead to `/tmp/run`, and honk runs beside the containers on the data disk (honk-datapath D5). On the emulator, honk started after the app Pod stacked a tmpfs on podman's registry (`/proc/self/mountinfo`: podman's `/tmp/run/netns` with the Pod's two nsfs mounts, honk's tmpfs on it), `ls /run/netns` showed `daens` alone, and `podman pod restart` warned `container netns not found: open /run/netns/netns-…: No such file or directory`. Started the other way round, as the data disk's late mount does (honk at boot, then the Pods and honk's restart onto the disk at once), the Pods' namespaces went with honk's tmpfs and the Pod failed to start (`netavark: invalid namespace path`).

What the patch does: the registry is made a mountpoint as iproute2 and podman make it: shared, and where that fails with `EINVAL` because it is none, bound onto itself first, recursively, so that every namespace registered there stays in view. Nothing undoes it. The kernel resolves both the registry's path and the stale `daens` mount's, which is now detached by its path at start whatever it resolves to, so `is_mountpoint()` and its `/proc/mounts` comparison go. A root-only unit test in a private mount and network namespace registers a namespace before the setup, while the registry is no mountpoint, and one during it, and checks that both still name a namespace after the cleanup.

Verification log: 2026-11-13, honk-core's unit tests on the VM (aarch64 Linux, the tree's host Rust, `--no-default-features --features ebpf,native-api`, the build's eBPF object), as root: the registry test failed on the unpatched `daens.rs` (`ENOENT`: the namespace registered before the setup was hidden by the tmpfs) and passes with the patch, as do `daens::`'s other tests. On the emulated R4S, unpatched: honk started beside the app Pod covered podman's registry with its tmpfs, and the storage test of the data disk's late mount failed (`netavark: invalid namespace path`). Patched: the services suite passes, 42 tests, among them the containers test of honk's restart beside the Pods (a namespace registered before honk started and one registered while it ran) and the late mount.

### honk: a verdict for a packet no longer queued

Patch: `feed/net/honk/patches/004-nfqueue-a-verdict-for-a-packet-no-longer-queued-ends-nothing.patch`, for daeuniverse/honk.

Problem: honk sends its NFQUEUE verdicts on the queue's socket, where its listener reads, without asking for acknowledgements, and the kernel answers a verdict there only when it fails. The listener took every message but a queued packet for a protocol failure, so the kernel's answer to a verdict whose packet it had already dropped ended the listener and honk with it: `NFQUEUE listener failed: unexpected netfilter netlink message type 2` (honk #476). The kernel drops queued packets on its own: every packet of every queue whenever any netfilter hook of the namespace is unregistered (`nfqnl_nf_hook_drop` flushes them all, Linux 6.18), as a firewall replacing its table does, and those of a device that goes down; a verdict that comes after finds no packet (`ENOENT`).

Why it matters here: fw4 reloads its table on every firewall change and interface event, and honk queues the first packet of every new direct UDP flow whose route a domain rule could still change, as with any configuration that routes by domain. On the emulator, with 200 new UDP flows a second to a direct target and a domain rule, fifteen `fw4 reload`s ended honk four times; procd respawned it until its respawn limit, then left it down. A reload of honk itself (SIGHUP) did not end it there.

What the patch does: the listener reads an answer to a verdict as what it is. `ENOENT` says the packet is gone and nothing is left to decide; any other refusal of a verdict, or an answer to anything else, stays fatal and now names the error (`VerdictRefused`). The verdict message type gets its name, `NFQNL_MSG_VERDICT`, where verdicts are built. A unit test dispatches the kernel's answers (an `ENOENT` for a verdict, then a queued packet; `EPERM`, an acknowledgement and an answer to a configuration message); a root-only kernel test in a network namespace of its own holds a queued packet's verdict, brings the loopback device down, sends the verdict and checks that the listener goes on serving. Both fail without the change.

Verification log: 2026-11-13, honk-nfqueue's tests on the VM (aarch64 Linux, the tree's host Rust): 29 unit tests pass, the new one failing without the change (the answer ended the dispatch); as root, both kernel tests pass, the new one failing on the unpatched listener with `UnexpectedMessage { message_type: 2 }`. On the emulated R4S, with 200 new UDP flows a second waiting for honk's decision (a domain rule): unpatched, fifteen `fw4 reload`s ended honk four times (`NFQUEUE listener failed: unexpected netfilter netlink message type 2`) and procd's respawn limit then left it down through fifteen honk reloads; patched, the same honk process ran through fifteen `fw4 reload`s and fifteen honk reloads, its queue bound after each, and the network suite passes, 58 tests, among them the transparent-proxy test of firewall reloads while flows wait for honk.

### honk: direct flows activated together, armed only in time

Patch: `feed/net/honk/patches/005-nfqueue-activate-a-batch-s-direct-flows-together-and-arm-only-in-time.patch`, for daeuniverse/honk.

Problem: honk's commit pump arms a batch of direct UDP flows under one backend acquisition, then activated them one at a time, each flow accepting its held originals, acquiring the backend write lock again and updating its conn state in a blocking section of its own. A batch of N flows waited N times behind whatever held the backend meanwhile, and the pump took no new commits until its last activation. Under a sustained arrival of new direct flows, requests aged in its queue, the next batch was armed close to its three-second hold, and an armed flow that misses the hold ends the process by honk's design (`DirectArmed flow lost its initializer before activation`): every queued packet has one three-second receipt-to-verdict deadline, and once a direct flow has armed, userspace can no longer tell safely which of its originals the kernel accepted.

Why it matters here: with any domain rule, every new direct UDP flow waits for honk's decision. On the emulated R4S, 200 new UDP flows a second ended honk within minutes, every time. Instrumented (never shipped): every flow that missed its hold had waited microseconds to tens of milliseconds for the backend itself but arrived at its activation about 3 s after its first packet, and the pump reported a batch of 256 armed flows whose one-by-one activation took 2.6 s, its oldest request already 3 s old.

What the patch does: the batch's armed flows accept their held originals off the backend lock, oldest first, and one backend acquisition and one blocking section activate every flow whose originals are out; a flow whose originals arrived meanwhile accepts them and goes round again, as before, so Arm, originals and Activate keep their FIFO order and a failure after arming stays fatal. And a flow is armed only with the time left for its activation, which comes after the rest of its batch's commit and the release of the originals of every flow the batch arms: its deadline less a 300 ms margin, the commit work of the batch's requests still to visit, itself included, at the slower of a moving average per request (from the batch's first visit until its armed flows can be activated) and the batch's own rate so far, and the activation work of the flows armed before it and of those still to visit, at a moving average per flow (without the waits for the backend, which a stall must not inflate); at least half the hold, since under load the work and waits between arming and activation outgrow what the measured work foretells (to a second on the emulator, where every flow that missed its hold had been armed with less than that left), and at most all of the hold but the margin, so that a flow fresh from the queue is always armed and the averages stay current. A later flow expires unarmed, without conn mutation, as a late request already does, and its originals are dropped. Each released flow's hold end is read with its originals, under the lock it releases them under, and the batch waits for the backend until the earliest: a flow its waiter fails at its hold meanwhile then meets the timeout or the blocking section, whose outcomes upstream's single-flow path has. Until the review of 2026-11-15, every version read the holds after the releases, of the flows still armed: a round whose flows had all been failed meanwhile broke out with their results unset, and the final `expect` panicked. A first version measured arming to activation, waits included: on the emulator a few stalled batches raised the reserve beyond the hold, every direct flow was then shed and no activation could bring the average down (honk ran on, direct UDP failed for good); the bound and the measure of work alone keep that from happening. A second version reserved the activation work of the flows armed before a flow alone: on CI's slower R4S runner (run 43619835257) and on the emulator under CI-like load (four cores and stress-ng), a flow visited early in a batch of 44 was armed with 365 ms left and missed its hold while the 43 requests after it committed, 8 ms each, and during a firewall reload one of a batch of 81, armed by the recorded 2.6 ms a request, missed it while the rest committed at 6.4 ms each and the batch's 81 flows had their originals released (instrumented, never shipped). honk's design document (English and Chinese) describes both. Tests beside the pump's: direct flows decided together while a scanner holds the backend for reading 150 ms at a time are all activated (unpatched, the later ones fail with `ArmedInProgress`); a flow without time for its activation expires unarmed, nothing armed and nothing fatal (unpatched, it is armed); a flow fresh from the queue is armed however long commits and activations took (the first version shed it); a flow past half its hold expires unarmed however little its batch's work; a flow visited early in a batch reserves the commit work of the requests after it, a batch slowed down reserves at its own rate, and a flow reserves the activation work of the flows its batch may still arm (the second version armed each); a batch's first armed flow reserves its own activation only, a later one those before it too; the reserve follows the recorded work, up to its bound.

Verification log: 2026-11-14, honk-core's tests on the VM (aarch64 Linux, the tree's host Rust, `--features ebpf,native-api`): the 43 NFQUEUE tests pass, the two new behavioural ones failing on the unpatched pump and the test of a fresh flow on the first version; 2,197 of honk-core's tests pass, the four geosite tests failing without the `geosite.dat` they read from the repository's root, as without the patch. On the emulated R4S: the transparent-proxy tests pass, among them the stream of 200 new UDP flows a second for three minutes and the fifteen firewall reloads while flows wait, the same honk process running through each and new UDP flows going direct again after; unpatched, honk had exited within minutes of such a stream, every time. 2026-11-15, the amendment: the tests of a flow reserving the rest of its batch, of a batch slowed down and of a flow reserving its batch's activations fail on the second version, and the test of a flow past half its hold fails without the floor; honk-core's tests pass with 006 and 007 (their logs). On the emulated R4S under CI-like load (four cores and stress-ng), with 006 and 007: the transparent-proxy tests of a stream of new flows and of firewall reloads while flows wait pass in three runs, the same honk process running through each. 2026-11-15, the review's amendment (each flow's hold end read with its originals): honk-core's tests as 006's.

### honk: scheduled token cleanups, retired together in the pump's turn

Patch: `feed/net/honk/patches/006-nfqueue-retire-scheduled-token-cleanups-together-in-the-pump-s-turn.patch`, for daeuniverse/honk.

Problem: a packet honk sheds before its flow reaches the correlator (its ingest queue full, the backend not readable within the hold) schedules a token cleanup that retires the flow's kernel staging, which otherwise lasts until 120 s after the flow's first packet, every packet of the flow queued and dropped meanwhile. The watchdog drained the scheduled cleanups each tick one at a time, each in a fenced retirement batch of one that waits for a grace period of its own, and gave up until its next tick whenever another writer held the backend. The set is bounded by the queue's length (4096), and reaching the bound is fatal: `scheduled cleanup set reached NFQUEUE maxlen`.

Why it matters here: with any domain rule, every new direct UDP flow waits for honk's decision, and an overloaded router sheds some of them. On CI's slower R4S runner (run 43619835257) the transparent-proxy test of a stream of new flows found honk's queue unbound after it; on the emulator under CI-like load (four cores and stress-ng), instrumented (never shipped): of 200 new flows a second some 100 were shed, a retirement took 80 ms, and the drain found the backend free for six of them in the 33 s the set took to fill; honk then exited, its shutdown spending five more minutes retiring the 4096 one by one, and procd restarted it.

What the patch does: a scheduled token cleanup is retired together with the other token cleanups scheduled, up to a retirement batch (1024), under one fence and one grace period. That alone was not enough on the emulator: the drain found no turn in nearly every tick, the ingest actor taking the backend for reading again as soon as it let it go, and the set filled all the same. A drain that waits its turn beside the watchdog kept the set small, but held the backend for a whole batch (seconds there) while an armed flow waited for its activation, which then missed its hold. So while the commit pump has work, it retires the token cleanups itself, a batch after each of its own batches, when none of its flows is armed, waiting its turn for the backend as it does for its commits; the watchdog retires them while the pump is idle, still without waiting, and waits for no other drainer either (honk's tests of a contended cleanup and of the hold watchdog under a held backend stand), a batch a tick, so its pause before it scans the holds is one grace period at most; a first form retired batch after batch there (review, 2026-11-15). A flow cleanup still settles its cell, a refusal is still recorded per request and a failure is still fatal. `retire_pending` takes a slice of requests, and `ebpf::retire_pending`, its single-request wrapper, goes. honk's design document (English and Chinese) describes the drain. Tests beside the drain's: a retirement batch and one more of scheduled token cleanups are retired in two backend batches, every staged entry gone and the set empty (one at a time: a batch each), and by the watchdog in two ticks, a batch each (batch after batch: both in the first); the pump retires a cleanup after its batch within a second while a reader takes the backend in turn (without the pump's retirement: none in that time); a late request of a batch is never applied, its staging left to its token cleanup.

Verification log: 2026-11-15, honk-core's unit tests on the VM (aarch64 Linux, the tree's host Rust, `--features ebpf,native-api`), with 005 and 007: 2,205 pass, the four geosite tests failing without the `geosite.dat` they read from the repository's root, as without the patches; the test of the batched drain fails retiring a cleanup a batch, and the test of the pump's turn without the pump's retirement. On the emulated R4S: the network suite passes, 62 tests; under CI-like load (four cores and stress-ng) its 25 transparent-proxy tests pass, and in three runs of the test of a stream of new flows with 005 and 006 alone, instrumented (never shipped), the same honk process ran through each, the set holding up to 2,865 of its 4,096 (007). 2026-11-15, the review: with 002, 005 and 007 as amended, 2,206 of honk-core's unit tests pass, the four geosite tests failing as before; the test of the watchdog's batch a tick fails retiring batch after batch (both batches in the first tick), and every file of the seven patches is rustfmt-clean at its commit. On the emulated R4S, with the four amended: the network suite's transparent-proxy tests pass, 26 of 26, the stream of new flows and the firewall reloads while flows wait among them.

### honk: token cleanups past the bound, left to the janitor

Patch: `feed/net/honk/patches/007-nfqueue-leave-token-cleanups-past-the-bound-to-the-janitor.patch`, for daeuniverse/honk.

Problem: the scheduled cleanups are bounded by the queue's length (4096), and reaching the bound is fatal (`scheduled cleanup set reached NFQUEUE maxlen`), as if a cleanup could not outnumber the queue's packets. It can: a cleanup outlives the packet it came from, which is shed at once while its token cleanup waits for the drain. When flows are shed faster than their staging can be retired, the set fills however fast the drain is, and honk exits.

Why it matters here: on the emulator under CI-like load, instrumented (never shipped), with 006's drain in three runs of the transparent-proxy test of a stream of new flows, all passing: a retirement took some 4 ms, a batch of 1024 some 4 s, and the drain retired about 206 a second while the stream of 200 new flows a second was shed at about 200 a second for ninety seconds; the set held up to 2,865, 2,511 and 1,270 of its 4,096. That margin of a few per cent is one CI's slower runners need not leave. honk's other bounds shed and count on overload: a full ingest queue (`actorQueueFull`), a full correlator (`correlatorFull`), and the kernel's full queue (`kernelDropped`), whose packets' staging the janitor reclaims once it expires.

What the patch does: a token cleanup the full set has no room for is left to the staging's expiry and the janitor, and counted (`cleanupFull` among the API's NFQUEUE metrics), instead of ending the process. A token cleanup only hastens the retirement of staging the kernel keeps fenced by its token: without it, the staging expires 120 s after the flow's first packet, whose time the eBPF side keeps for a pending flow, and the flow's packets are queued and dropped until then, as for the staging of a packet the kernel's queue dropped and userspace never saw. That costs the flows shed past the bound up to two minutes; ending the process takes every flow down instead, and procd's respawn limit may keep honk down (the patch's message and comment say so since the review of 2026-11-15). A flow cleanup always has room: it settles one of the correlator's cells, so flow cleanups never outnumber them. honk's design document and API reference (English and Chinese) describe it. Tests: a full set leaves one more token cleanup to the janitor, counted and without a fatal, and still takes a flow cleanup (with the fatal bound: the set refuses both); the API's metrics test reads the counter.

Verification log: 2026-11-15, honk-core's unit tests as 006's; the test of a full set fails with the fatal bound, and the API's metrics test passes (`--features ebpf,native-api,clash-api`). On the emulated R4S under CI-like load, instrumented (never shipped), with 005 and 006 below it: in three runs of the test of a stream of new flows the set held up to 1,461, 2,365 and 2,290 of its 4,096, no token cleanup was left to the janitor, and the same honk process ran through each. The emulator did not fill the set; the patch is for a runner slower than it, where the drain's margin is gone. 2026-11-15, the review: the staging's lifetime checked in honk's eBPF code (`lookup_udp_seen_at` keeps a pending flow's `last_seen_ns`, `UDP_CONN_STATE_TIMEOUT_NS` is 120 s); honk-core's tests as 006's, and the API's metrics test passes (39 tests, `--features ebpf,native-api,clash-api`).

## Prepared for upstream, not carried

### EROFS compression algorithm

Patch: `docs/upstream/0001-build-make-the-EROFS-compression-selectable.patch`, for openwrt/openwrt.

Problem: `include/image.mk:110` tests `CONFIG_EROFS_FS_ZIP_LZMA`, but that symbol does not exist; the Kconfig option is named `KERNEL_EROFS_FS_ZIP_LZMA`. So the LZMA branch never runs, and every EROFS image is in fact compressed with lz4hc.

Why it matters here: this project's images are EROFS (firmware/rootfs), with the compression it chose, lz4hc; it does not depend on the patch.

Why a rename alone is not enough: `KERNEL_EROFS_FS_ZIP_LZMA` has no prompt and defaults to y when EROFS is enabled. With only the rename, every EROFS build would **silently switch to LZMA**, and this project's images would change with it, whereas we chose lz4hc.

What the patch does: it adds a `compression` choice that defaults to lz4hc, matching the current actual behavior; choosing LZMA also selects the kernel's LZMA support. `image.mk` now tests this choice instead.

Verification log: 2026-09-28, it applies cleanly with `git am` onto openwrt `1019293`, as pinned then, with the F2FS one below.

### Kernel options for F2FS compression

Patch: `docs/upstream/0002-config-kernel-add-F2FS-compression-options.patch`, for openwrt/openwrt.

Problem: fstools can format the overlay as compressed f2fs via `fstools_overlay_compression_type=`, but `config/Config-kernel.in` has no matching `KERNEL_F2FS_*` options, so the build configuration cannot select them.

Why it matters here: it does not depend on this patch; instead, the upstream-native kernel config overlay (`config/kernel.config` → `env/kernel-config`) provides the same options. Once upstream accepts the patch, we can switch back to `CONFIG_KERNEL_F2FS_*` in the seed.

What the patch does: it adds `KERNEL_F2FS_FS_COMPRESSION` and each algorithm option beneath it (LZO, LZO-RLE, LZ4, LZ4HC, ZSTD). The kernel defaults all of these options to y, and if any of them has no value the build stops, so each one needs a matching `KERNEL_*`. F2FS selects the libraries of the algorithms it compresses with, which are modules when f2fs is one, so `kmod-fs-f2fs` depends on the kmods that hold them (`kmod-lib-lzo`, `kmod-lib-lz4`, `kmod-lib-lz4hc`, `kmod-lib-zstd`), each under its option.

Verification log: 2026-09-28, this patch and the EROFS one above apply cleanly with `git am` onto openwrt `1019293`, as pinned by the lock.

2026-10-05: on `1019293`, `make defconfig` for the NanoPi R4S with `kmod-fs-f2fs` as a module and `KERNEL_F2FS_FS_COMPRESSION` selects `kmod-lib-lz4` and `kmod-lib-zstd`, the algorithms on by default, and neither LZO's nor LZ4HC's kmod. Before submitting: build f2fs as a module with every algorithm on and check that `f2fs.ko` loads with the selected kmods (this project builds F2FS into the kernel).
