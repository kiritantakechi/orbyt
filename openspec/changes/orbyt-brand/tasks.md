# Tasks

## 1. The rename (design D1 to D3)

- [ ] 1.1 Apply D1's mapping to every file's contents and to file and directory names outside the archive and the CI runs recorded before the rename; `tests/wrt_tests` becomes `tests/orbyt_tests`.

  Verify: the case-insensitive search for `wrt` outside `OpenWrt`, the archive and the past CI rows finds nothing; `just check` passes.

- [ ] 1.2 Rename the old names in the patches' added lines and file names, numbers kept; update `docs/patches.md`.

  Verify: `just patch` applies the series on the pinned sources.

- [ ] 1.3 Set the image's name (D3): the version options in `config/system.seed`, an Orbyt `/etc/banner`, the hostname `orbyt` as a first-boot default; add the scenario's test to `tests/firmware/test_base_system.py`.

  Verify: `spec-coverage --change orbyt-brand` reports the scenario covered.

## 2. The local environment (design D4)

- [ ] 2.1 With no VM job running, move the work volume to `orbyt-work.ext4` at `/mnt/orbyt` and the test directory to `/home/kiritan/orbyt-test`.

  Verify: `/mnt/orbyt/openwrt` is the tree, `df` shows the volume, and `/mnt/wrt` is gone.

- [ ] 2.2 Move the private repository to `~/orbyt-config` and the release keys to `~/.config/orbyt/release-keys`, without printing them.

  Verify: the files' count, modes and checksums match before and after (checksums compared, not shown).

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
