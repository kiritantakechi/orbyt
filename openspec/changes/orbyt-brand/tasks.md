# Tasks

## 1. The rename (design D1 to D3)

- [x] 1.1 Apply D1's mapping to every file's contents and to file and directory names outside the archive and the CI runs recorded before the rename; `tests/wrt_tests` becomes `tests/orbyt_tests`.

  Verify: the case-insensitive search for `wrt` outside `OpenWrt` finds only the archive and the past CI rows (1.4 renames those); `just check` passes.

- [x] 1.2 Rename the old names in the patches' added lines and file names, numbers kept; update `docs/patches.md`.

  Verify: `just patch` applies the series on the pinned sources.

- [x] 1.3 Set the image's name (D3): the version options in `config/system.seed`, an Orbyt `/etc/banner`, the hostname `orbyt` as a first-boot default; add the scenario's test to `tests/firmware/test_base_system.py`.

  Verify: `spec-coverage --change orbyt-brand` reports the scenario covered.

- [x] 1.4 Apply the mapping to the archive, `docs/ci.md`'s earlier runs and the release key's comment, with the joined and camel-case forms (D1's last row) everywhere; add `quality/code-standards`' delta for the `ORBYT_` prefix.

  Verify: the case-insensitive search for `wrt` outside `OpenWrt`, `ImmortalWrt` and this change's documents finds nothing; the unit tests pass.

## 2. The local environment (design D4)

- [x] 2.1 With no VM job running, move the work volume to `orbyt-work.ext4` at `/mnt/orbyt` and the test directory to `/home/kiritan/orbyt-test`.

  Verify: `/mnt/orbyt/openwrt` is the tree, `df` shows the volume, and `/mnt/wrt` is gone.

- [x] 2.2 Move the private repository to `~/orbyt-config` and the release keys to `~/.config/orbyt/release-keys`, without printing them.

  Verify: the files' count, modes and checksums match before and after (checksums compared, not shown).

  Result: the four release keys moved, mode 0600 kept. No private repository was on this Mac or the VM to move: the maintainer's lives elsewhere, and `just config-init ~/orbyt-config` makes one where `docs/ops.md` names it.

## 3. Verification (design D5)

- [ ] 3.1 Build the R4S from the moved tree and run the boot chain's, the base system's and the release suite's tests on the emulator, the Mac's load sampled.

  Verify: the build succeeds with `orbyt-` image files; the tests pass, the new scenario among them.

- [ ] 3.2 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub.
- Rebase `dynamic-dns` onto the renamed main and rename its proposal.
- Copy Claude's project notes to the new path, move the checkout to `~/Projects/orbyt` and reopen the session there.
- Then the theme's redesign after the TouhouAsia design system, as its own change, from a mockup the maintainer approves.
