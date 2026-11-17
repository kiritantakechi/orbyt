# Proposal

## Why

Four places of the release flow decide from the wrong facts whether what they hold is current, found by a review of the project on 2026-11-17:

- **Publishing waits for a run that never comes.** `release-publish.sh --upload` publishes only while the branch's head is the commit that was built (release-integrity D1). A commit that changes only documents, which `build.yml`'s `paths` keep from starting a run, moves the head all the same: the run before it then refuses with "the newer run publishes", and no newer run comes. On main, every release would wait for the next code change after its last documentation commit.
- **An older run's re-run prunes the newer run's caches.** `cache-prune.sh` keeps the toolchain of the run's own key and the newest compiler cache of each stage, and deletes the rest of the ref's. A re-run of an older run waits for the newer one and then runs after it (release-integrity D1): its prune deletes the newer run's toolchain, whose key differs whenever the toolchain's inputs changed in between, and the next run builds the host stage anew, two to four hours.
- **A build with untracked files says it was built from a clean commit.** `build.sh` marks the manifest's commit `-dirty` only when `git diff --quiet HEAD` finds a tracked file changed. A new file that is not committed, as a patch just written is, goes into the build unrecorded: on 2026-11-17 an R4S image was built with patch 0048 before it was committed, and its manifest named ec54e25, which has no such patch, without `-dirty`.
- **The toolchain's key leaves out build files the host stage reads.** `toolchain-key.sh` hashes three of OpenWrt's build files (`include/depends.mk`, `include/host-build.mk`, `rules.mk`), while the host tools and the toolchain include `include/toolchain-build.mk`, `cmake.mk`, `meson.mk`, `rust-host-build.mk`, the kernel's build files and more, and run OpenWrt's `scripts/`. An upstream change to one of them alone keeps the key, and CI restores a toolchain built without it.

## What Changes

- **One definition of the files the build reads.** A library function says whether a path is one the build workflow runs for, from the same patterns as `build.yml`'s `paths`, which a test keeps equal to the workflow's; publishing and pruning both ask it.
- **A run is current while its branch has moved by documents alone.** Publishing goes on when the branch's head descends from the commit built and every file between them is one the build does not read; the Release is still tagged on the commit built. A head moved by a file the build reads still stops it, naming both commits.
- **Only the newest build of a ref prunes the ref's caches.** `cache-prune.sh` prunes nothing, saying so, when its run's commit is no longer current in that sense; the newer run prunes.
- **Any difference from the commit marks the build.** The manifest's commit is `-dirty` whenever the working tree differs from it, an untracked file that is not ignored included, as `git status --porcelain` lists it.
- **The toolchain's key covers OpenWrt's build files and scripts whole.** The `include/` and `scripts/` trees take the three files' place beside `rules.mk`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `release/publishing`: a Release is published from the commit built while its branch has moved past it by files the build does not read; tagged on the commit built.
- `build/ci`: the manifest's commit is marked changed for any difference of the working tree, untracked files included; the host stage's key covers OpenWrt's `include/` and `scripts/`; only the newest build of a ref prunes its caches.

## Impact

- `scripts/lib/`: the build's paths, as a module the scripts load; `scripts/release-publish.sh`, `scripts/cache-prune.sh` (which reads `GITHUB_SHA` now), `scripts/build.sh`, `scripts/toolchain-key.sh`.
- `.github/workflows/build.yml`: nothing changes in its `paths`; its comment names the library as their twin.
- Tests: `tests/release/test_publishing.py` (a branch moved by documents only publishes; one moved by a file the build reads does not, as before), `tests/build/test_ci.py` (a superseded run prunes nothing, one past documents prunes; the library's patterns are the workflow's; the commit stamp with an untracked, an ignored and a staged file), the stand-in `gh` they share (`wrt_tests.model.github`); `tests/verified-elsewhere.toml` for the key's scenarios.
- `docs/ci.md` and `docs/release-flow.md` where they describe publishing's check, the prune and the key.
- No change to the image: the next CI run on main rebuilds the host stage once, for the key's new inputs.
