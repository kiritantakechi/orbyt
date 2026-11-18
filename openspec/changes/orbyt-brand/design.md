# Design

## Context

- About 250 files outside the archive carry names derived from wrt-build: `wrt_tests` (443 uses), `wrt-sync`, `WRT_WORKDIR`, `wrt-ab`, `wrt-data`, `wrt-containers`, `wrt-keyring`, `wrt-healthcheck`, U-Boot's `wrt_boot` and its other variables, the kernel arguments `wrt.slot` and `wrt.env`, the feed `wrtbuild`, `luci-theme-wrt` and its `/luci-static/wrt`, and the sandbox's own user names. Forty-two patches add lines that carry them, and some patch file names do.
- The image names no distribution: its files are `openwrt-<target>-…`, its banner and release files say OpenWrt, its hostname is OpenWrt.
- The work volume `/Volumes/SSD/wrt-work.ext4` is mounted in the VM at `/mnt/wrt` (`scripts/workdir-mount.sh`), the OpenWrt tree at `/mnt/wrt/openwrt`; OpenWrt's build records absolute paths, so a tree at another path builds anew from its caches.
- The repositories were renamed on 2026-11-18 (GitHub `kiritantakechi/orbyt`, Codeberg `kiritan/orbyt`), the local remotes with them; GitHub and Codeberg redirect the old names.

## Goals / Non-Goals

**Goals:**
- One name, Orbyt, with one lowercase form, `orbyt`, in every identifier the project owns.
- No identifier or record left of the old name: on 2026-11-19 the maintainer asked for every leftover to go, the archive and the CI history included.

**Non-Goals:**
- A migration for devices on an older image: none exists in production.
- Renaming upstream: OpenWrt, LuCI, their packages and paths, and the `openwrt/` source tree.

## Decisions

### D1. One mapping

| Old | New | Where |
|---|---|---|
| `wrt-<name>` | `orbyt-<name>` | commands, packages, services, uci configurations, files, Nix outputs |
| `WRT_<NAME>` | `ORBYT_<NAME>` | environment variables |
| `wrt_<name>` | `orbyt_<name>` | shell, ucode and Python names, U-Boot's environment, `tests/orbyt_tests` |
| `wrt.<name>` | `orbyt.<name>` | kernel arguments |
| `wrtbuild` | `orbyt` | the feed |
| `wrt-build` | `orbyt` | the repository, prose naming the project as Orbyt |
| `luci-theme-wrt`, theme `wrt`, `luci.themes.Wrt` | `luci-theme-orbyt`, theme `orbyt`, `luci.themes.Orbyt` | the theme, its media path `/luci-static/orbyt`, its script `menu-orbyt.js`, its strings' context `orbyt`, its browser storage keys |
| `wrt` (a name alone) | `orbyt` | the sandbox's PPPoE and tailnet users, U-Boot's environment source file |
| `wrt<name>`, `Wrt<Name>`, `wrt<Name>` joined | `orbyt<name>`, `Orbyt<Name>`, `orbyt<Name>` | the data disk's label and fstab section `orbytdata`, the work volume's label `orbytwork`, U-Boot's make functions `OrbytAB/…`, the theme's `window.orbytTheme` |

A one-off script applies the mapping to file contents and to file and directory names; a search for the old forms afterwards, case-insensitive with OpenWrt and ImmortalWrt excluded, must find nothing outside this change's own documents, which record the mapping.

The first pass matched a name only between separators, and kept the archive, the CI runs before the rename and the release key's comment as history. A second pass, after the maintainer's word, applies the mapping there too, with the joined and camel-case forms the first had missed (`wrtdata`, `WrtAB`, `wrtTheme`, and `\0wrt_boot` in a unit test's data, which failed the test), and relabels the work volume. The archived luci-theme change is renamed with the rest; orbyt-theme, whose design replaces it, removes it.

### D2. Patches keep their numbers

A patch whose added lines carry an old name gets them renamed in place, and a file name that carries one is renamed with its number kept (patch numbers are identities). The series must still apply on the pinned sources (`just patch`), and `docs/patches.md` follows.

### D3. The image's name

`config/system.seed` sets `CONFIG_VERSIONOPT` with `CONFIG_VERSION_DIST="Orbyt"` (the release files, `/etc/os-release`, LuCI's version line, and the image files' prefix, which OpenWrt derives from it) and the project's home and issue URLs on Codeberg. The image's `/etc/banner` shows Orbyt. A first-boot default of the image sets the hostname `orbyt` on a fresh configuration, as the image's other defaults are set; a kept configuration keeps its hostname. LuCI's footer keeps linking LuCI and OpenWrt.

Alternatives considered:
- A patch to base-files' `config_generate` for the hostname: the image's own defaults are where this project sets first-boot values.

### D4. The local paths move, in an order

With no job running in the VM: the work volume is unmounted, its image file renamed `orbyt-work.ext4` and mounted at `/mnt/orbyt` (the mount script's defaults change); the test directory becomes `/home/kiritan/orbyt-test`; the private repository `~/orbyt-config` and the release keys `~/.config/orbyt/release-keys` are moved, never copied out or printed. Claude's notes for the project are copied to the directory of the new checkout path. The checkout moves last, to `~/Projects/orbyt`, and the session reopens there.

### D5. Evidence

- `just check`, the patch series applied on the pinned sources, and the leftover search of D1.
- A full R4S build from the moved tree, and the system tests of the boot chain, the base system (the new scenario, `tests/firmware/test_base_system.py`) and the release suite on the emulator.
- CI's build of the branch for both boards, from the renamed repository.

## Risks / Trade-offs

- [An old name in a place the search misses, such as a generated file or a cache key] → The search runs over the tree and the image's files list; a cache key that changes builds anew once.
- [The renamed U-Boot variables and kernel arguments break a boot path] → The boot chain's tests (firmware/rootfs, boot-rollback, ab-upgrade) run on the emulator and in CI before the merge.
- [External links to the old repository names] → Both hosts redirect them; the image and docs name the new ones.
- [The local tree builds anew at its new path] → Hours of local build once; the compiler and download caches move with the volume.
