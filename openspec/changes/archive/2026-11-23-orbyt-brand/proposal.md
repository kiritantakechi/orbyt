# Proposal

## Why

The project grew from "a build of OpenWrt" (wrt-build) into a router system of its own: its own A/B upgrades, release channel, services, datapath and web theme. On 2026-11-18 the maintainer named it Orbyt. The name has to be one name everywhere, in the repositories, the commands, the identifiers and what the router says about itself, rather than a new brand over `wrt-` remnants.

## What Changes

- **The repositories** are `codeberg.org/kiritan/orbyt` (primary) and `github.com/kiritantakechi/orbyt` (CI and Releases), renamed in place, with their history, releases, caches and settings.
- **Every identifier derived from the old name**, one mapping throughout: `wrt-<name>` commands, packages, services, uci configurations and files become `orbyt-<name>` (`orbyt-ab`, `orbyt-sync`, `orbyt-data`, `orbyt-snap`, …); `WRT_<NAME>` environment variables `ORBYT_<NAME>`; `wrt_<name>` in shell, ucode, U-Boot's environment and Python `orbyt_<name>` (the test package `orbyt_tests`); the kernel arguments `wrt.<name>` `orbyt.<name>`; the feed `wrtbuild` `orbyt`; the theme `luci-theme-orbyt`. **BREAKING** for devices running an image from before: none exists in production, so no migration path is kept.
- **The image presents itself as Orbyt**: Orbyt as OpenWrt's distribution name (release files, `/etc/os-release`, LuCI's title, image files `orbyt-<target>-…`), an Orbyt login banner, and the hostname `orbyt` on a fresh configuration. LuCI's footer keeps crediting LuCI and OpenWrt as the system's base.
- **The development environment's paths**: the checkout `~/Projects/orbyt`, the VM's work volume `orbyt-work.ext4` at `/mnt/orbyt`, the test directory `~/orbyt-test`, the private configuration repository `~/orbyt-config` and the release keys in `~/.config/orbyt/release-keys`, moved, not recreated.
- What keeps its name: OpenWrt, LuCI and every upstream name; OpenWrt's source tree, `openwrt/` in the work volume; and the records of the past, the archived changes and the CI runs before the rename in `docs/ci.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `firmware/base-system`: a new requirement, the image's name: Orbyt as distribution, banner and hostname.
- `firmware/rootfs`: "Complete boot chain" names U-Boot's boot command `orbyt_boot`.
- `testing/emulation`: "Boot the shipped artifacts" names the emulator's firmware `uboot-orbyt-qemu` and the kernel argument `orbyt.slot`.

## Impact

- Nearly every file outside the archive: scripts, the flake, the justfile, workflows, the feed's packages, the image's files, U-Boot's fragments, patches (their added lines and file names; their numbers stay), tests (the package directory `tests/wrt_tests` becomes `tests/orbyt_tests`), docs and specs.
- `config/`: `CONFIG_VERSIONOPT` with `CONFIG_VERSION_DIST="Orbyt"` and the project's URLs.
- The private configuration repository's skeleton and its path; an existing private repository is moved and keeps working.
- The local build tree moves to `/mnt/orbyt`, whose absolute path its build depends on: the next local build starts from its caches, not from the old tree's state. CI's host stage builds anew once, as its work directory changes.
- The project's notes for Claude (its memory) move with the checkout's path.
- The change `dynamic-dns`, proposed on its branch, is rebased onto the renamed main and renamed with it.
