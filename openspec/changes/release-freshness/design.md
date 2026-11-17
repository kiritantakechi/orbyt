# Design

## Context

- `build.yml` runs for pushes and pull requests whose files match its `paths`: everything but `openspec/**`, `docs/**` and `**/*.md`, with `docs/patches.md` and `docs/services.md` back in, which system tests read (`tests/build/test_ci.py` holds the list to the tests). A newer run of a ref cancels the older one; a re-run of an older run waits for the newer instead, and then runs (`concurrency`, release-integrity D1).
- The jobs check out the commit at depth one: no history to compare commits with. `gh` and the workflow's token are there; the compare API (`repos/<repo>/compare/<base>...<head>`) answers whether the head descends from the base (`status` `ahead` or `identical`) and lists the files between them, at most 300.
- `release-publish.sh --upload` reads the commit built from the first board's manifest, refuses one marked `-dirty`, and in CI compares it with the head of `GITHUB_REF`'s branch, refusing any difference. `cache-prune.sh` prunes `GITHUB_REF`'s caches against its toolchain key, and on the default branch the caches of merged or deleted branches and closed pull requests. The `caches` job runs on pushes and dispatched runs, never for pull requests.
- `build.sh` writes the manifest's `commit`: `git rev-parse HEAD`, `-dirty` when `git diff --quiet HEAD --` fails, which looks at tracked files alone.
- `toolchain-key.sh` hashes, among its inputs, the blobs of `include/depends.mk`, `include/host-build.mk` and `rules.mk`. The host stage's makefiles (`tools/`, `toolchain/`, the Go and Rust host builds) include, directly, `rules.mk`, `host-build.mk`, `cmake.mk`, `toolchain-build.mk`, `package.mk`, `rust-host-build.mk`, `meson.mk`, `rust-values.mk`, `target.mk`, `kernel-version.mk`, `kernel.mk`, `kernel-defaults.mk` and `kernel-build.mk`, and those include more, some through variables (`kernel-$(KERNEL_PATCHVER)`); they run `scripts/` (Kconfig, the patch and download helpers).
- Upstream's history between the last four pins (2026-09-27 to 2026-11-16): `include/` changed in 24, 13 and 1 commits, `scripts/` in 8, 3 and 0, while `tools/` (13, 12, 2) or `target/linux/generic` (51, 49, 4), which the key covers already, changed in every interval.

## Goals / Non-Goals

**Goals:**
- A run publishes, and prunes, while no newer run of its ref is to come; never while one is.
- The manifest's commit says whether anything at all differed from it.
- The host stage's key moves for every file of OpenWrt's build machinery the stage reads.

**Non-Goals:**
- What a re-run of a superseded run saves: its caches are of an older commit; the newer run's restore keys still find its own, and the next prune of the newest run removes the older ones.
- Publishing a run whose branch moved by a code change: its run is the one to publish, as before.

## Decisions

### D1. One definition of the files the build runs for

A library module, `scripts/lib/runs.sh`, holds `build.yml`'s `paths` as a list in their order, and `build_reads <path>`, which says whether a change to the path starts the build: the last pattern that matches decides, `!` excluding, as GitHub reads the list. It supports the forms the list uses: an exact path, `<dir>/**`, `**/<glob>` and `**`. `tests/build/test_ci.py` checks that the module's list is the workflow's, for pushes and for pull requests, and that `build_reads` answers as GitHub's rules do for paths in and out of each pattern.

Alternatives considered:
- Reading `build.yml` at run time: the scripts would parse YAML, and a local run of `release-publish.sh` reads a workflow file it does not run under.
- Hard-coding the documentation directories in each script: two more copies of a list that already has one twin to keep equal.

### D2. A commit current for its branch

`superseding_head <repository> <commit> <branch>` (same module) prints nothing when the branch's head is the commit, or when the compare API finds the head `ahead` of it and every file between them, each renamed file's former name too, is one `build_reads` refuses; otherwise it prints the head, so that the caller names both commits. A comparison listing 300 files, GitHub's limit, may hide more: it counts as a change the build reads. An error of the API makes it die, which its caller passes on, so that a failure is never read as a move.

`release-publish.sh --upload` asks it about the built commit and `GITHUB_REF`'s branch, and keeps the commit built as the tag's target: a Release names what was built, never a newer head it did not build. Its message for a branch moved by a code change stays "<branch> has moved from <commit> to <head>: the newer run publishes".

Alternatives considered:
- Publishing the head's tree, or tagging the head: its documents were not built, and the tag would claim a build of a commit that had none.
- Making documentation start the build: a five-hour run for a typo, on every documentation commit.

### D3. Only a current run prunes

`cache-prune.sh` asks `superseding_head` about `GITHUB_SHA` and `GITHUB_REF`'s branch before it deletes anything. When the run is not current, it says that the newer run of the ref prunes, and ends with success, deleting nothing, neither the ref's superseded caches nor, on the default branch, those of merged branches and closed pull requests: the newer run does both. A ref that is not a branch prunes as before.

Alternatives considered:
- Comparing with the newest run of the ref through the runs API: one more query, and a head moved by documentation has no run of its own; D2's rule is the one publishing reads, so a run that may publish may prune.
- Keeping every toolchain cache: the quota holds two or three.

### D4. Any difference marks the commit

`build.sh` takes its `commit` from `source_commit` (`scripts/lib/manifest.sh`): `git rev-parse HEAD`, and `-dirty` when `git status --porcelain` lists anything: a tracked file changed, a change staged, or a file neither tracked nor ignored. The build's outputs live outside the repository (`WRT_WORKDIR`), and the repository's own outputs are ignored, so a clean checkout stays clean. `tests/wrt_tests/model/outputs.py` says so where it describes the field.

### D5. OpenWrt's build files and scripts whole in the key

`toolchain-key.sh` hashes the trees `HEAD:include` and `HEAD:scripts` and the blob `HEAD:rules.mk` of the patched tree in place of the three files. The trees hold what the host stage includes and runs, whatever variable an include goes through; a superset, as the generic kernel files already are (build-integrity D4). In the last three intervals between pins it would have changed the key in none in which the key stayed: each changed `tools/` or `target/linux/generic` too.

Alternatives considered:
- Following make's includes from the host stage's makefiles: some go through variables only make resolves, and a missed one is the defect this fixes.

### D6. Tests

- `tests/release/test_publishing.py`: the stand-in `gh` of the cache tests (`wrt_tests.model.github`), which now also answers for a branch's head and the compare API and records a release it is asked to create, takes the place of the module's own. A branch moved by documentation alone publishes, its tag on the commit built; moved by a file the build reads, it fails naming both commits, as today's test does; a comparison of 300 files, documentation all, does not publish.
- `tests/build/test_ci.py`, beside the prune's other scenarios: with the ref's head moved by a file the build reads, a run deletes nothing and says why, on a branch and on main; moved by documentation alone, it prunes as today.
- `tests/build/test_ci.py`: the module's list is the workflow's; `build_reads` for a path in and out of each pattern.
- `tests/build/test_ci.py`: `source_commit` in a scratch repository: clean; an untracked file; an ignored file (clean); a staged change.
- The key, on the VM (`tests/verified-elsewhere.toml`): a scratch commit of the build tree that changes `include/cmake.mk` alone moves the key, and one that changes a file of the packages feed outside `lang/golang` and `lang/rust` does not.

## Risks / Trade-offs

- [Every `include/` or `scripts/` change upstream rebuilds the host stage] → In the last three intervals between pins the key moved anyway; a bump that changes only those is a bump the toolchain may need.
- [The compare API's limit of 300 files] → Treated as a change the build reads: such a run waits for a newer one, as every moved run did before.
- [A rate-limited or failing API ends publishing or the prune] → As reading the head does today; the job fails visibly and a re-run retries.
