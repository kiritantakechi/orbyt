# Design

## Context

- `scripts/check.sh` adds the preinit hooks to shfmt's files (shfmt cannot tell them by name); `scripts/fmt.sh` does not. The two scripts open with the same lines (the NixOS guard, the FHS shell, the tests' environment, the file lists).
- The uv cache's restore, prune and save steps are copied in `check.yml` and in `build.yml`'s system-test job; the drill job, which syncs the same environment, has none. `build.yml`'s path list is written for push and for pull requests, and again in `scripts/lib/runs.sh`, a test keeping the copies equal. The download cache's key is an inline expression three times. `Prepare runner` precedes the Nix action four times.
- Decisions in workflow shell: `bump.yml`'s branch, commit and pull request (about 30 lines), the sign job's loop over the boards' manifests, the drill check's condition.
- The patched QEMU (`emulatorQemu` in `flake.nix`) is built by each of a run's twelve system-test jobs and two drill jobs.
- Names of one machine: `workdir-mount.sh`'s default image (`/mnt/mac/Volumes/SSD/orbyt-work.ext4`), the repository `kiritantakechi/orbyt` as the default of `drill-base.sh` and `github-audit.sh`, user names and paths in docs/dev-setup.md, `ORBYT_TESTDIR`'s documented default.
- Repeated idioms: a temporary directory with its trap in ten scripts (`image-audit.sh` decompresses a factory image into the VM's `/tmp`, which is memory), `${ORBYT_JOBS:-$(nproc)}` in three, a board validated by `board_field "$b" .device >/dev/null` in five.
- `build.sh` writes the manifest inline while `lib/manifest.sh` reads it; the toolchain record's checks are written in `build.sh` (as refusals) and in `toolchain-build.sh` (as rebuild triggers).
- Swallowed errors: `kernel_version=$(cat ... || true)` flows into the manifest and the release notes; `ccache_run` and `sccache_run` return 0 when the configuration selects a cache whose binary is missing.
- Documents: docs/conventions.md's module table lacks `manifest` and `runs` and its recipe groups `release` and `ops`; `CACHE_QUOTA` and `CACHE_SAVERS` lack the `ORBYT_` prefix; the check named `boards` runs `board-check`, the recipe `marks-check` is the check `marks`; the LAN subnet is in `config/system.seed`, `image-audit.sh` and `config-push.sh`; `flake.nix` defines the quality shell twice; about 140 comments cite a design as "design D12" without its change; docs/validation's commands omit the board (`just test dev`); docs/ci.md mixes the present with history in its prose and packs rationales into its record tables; `.gitignore` lists patterns nothing produces (`/work/`, `/out/`, the tests' former environments).

## Goals / Non-Goals

**Goals:**
- Every workflow step a recipe or an action; every decision testable outside CI; every list, key and constant written once.
- A fresh clone, or a fork, that runs without the maintainer's machine.

**Non-Goals:**
- The cache quota's management (`cache-room.sh`, `cache-prune.sh`): its reason, other branches pushing main's caches out of the 10 GB quota, holds.
- The check job's 30-minute limit and the uv cache: their reason (no free-threaded 3.15 wheels for grpcio, tach and PyYAML; python-style D1) holds until those wheels exist.
- The private configuration repository's `dae/` guard in `config-push.sh`: it stays until the maintainer says their repository is migrated (`git mv dae honk`), and then goes with docs/ops.md's section.
- `image-audit.sh`'s denylist of dae's packages: daeuniverse's feed still ships them, and the audit keeps them out of the image.

## Decisions

### D1. One file list

`scripts/lib/core.sh` gains `format_files` (the shell, Nix and Python files the formatters own, preinit hooks included), and one prelude function for `check.sh` and `fmt.sh`; both call them.

### D2. Workflows that run recipes

- `scripts/bump-open.sh` (recipe `bump-open`) does what `bump.yml`'s inline shell did; the bot's identity is its constant.
- `release-sign.sh` takes the directory of builds and checks each build's board and manifest itself; the sign job's loop goes.
- `scripts/drill-check.sh` decides the drill check from the three results; `tests/build/test_ci.py` runs it over every combination.
- The firmware, caches and publish jobs call recipes, not scripts.
- `.github/actions/uv-cache` (restore and prune; the save is the action's `post`-free second half, a step that calls the action again with `save: true`) serves check, system-test and drill; `.github/actions/nix` takes the runner's preparation as an input.
- The path list: YAML anchors give `build.yml` one list for push and pull requests, and `scripts/lib/runs.sh` reads it from `build.yml` (yq, added to the quality tools), so the test that kept the copies equal goes. The download cache's key comes from `just download-key`, as the toolchain's and compiler cache's keys come from recipes.
- `NIX_CONFIG`'s experimental features in the workflows go if the pinned installer enables them already (checked in the action's log).

### D3. The emulator once per run

The host stage builds the flake's emulator package (the patched QEMU) and saves its closure with `nix copy --to file://` into an actions cache keyed by `flake.lock` and the QEMU patch, the inputs of its derivation. The test jobs restore that directory and import it with `nix copy --no-check-sigs --from file://...` (the runner's Nix user is trusted) before their dev shell starts, which then finds the QEMU in the store. No binary cache account or key is needed; a job whose restore fails builds the QEMU, as every job does now.

### D4. No maintainer's machine

`lib/github.sh`'s `github_repository`: `GITHUB_REPOSITORY`, else the `origin` remote's owner and name, else a failure. `workdir-mount.sh` takes the image from `ORBYT_WORKDIR_IMAGE` (an argument still wins); `ORBYT_TESTDIR`'s default is `${XDG_CACHE_HOME:-$HOME/.cache}/orbyt/test`. docs/dev-setup.md uses `<repo>`, `<user>` and `<volume>`.

### D5. Helpers

`core.sh`: `scratch_dir` (made under `ORBYT_WORKDIR`'s `tmp/` when set, else `$TMPDIR`; removed on exit), `build_jobs`; `boards.sh`: `require_board`. `lib/manifest.sh`: `manifest_write`, the writer beside the readers. `lib/toolchain.sh`: `toolchain_record_state`, returning which part of the record differs, used by `build.sh` to refuse and by `toolchain-build.sh` to rebuild.

### D6. Errors that matter

`build.sh` fails when the kernel version is absent or empty, as it does for the vermagic. `ccache_run` and `sccache_run` return 0 only when the configuration does not select their cache, and fail when it does and the binary is missing.

### D7. Names and documents

- `CACHE_QUOTA` and `CACHE_SAVERS` become `ORBYT_CACHE_QUOTA` and `ORBYT_CACHE_SAVERS`; the check `boards` becomes `board-schema` and the recipe `marks-check` becomes `marks`, so a check's name is its recipe's.
- The LAN subnet is read from `config/system.seed` by `image-audit.sh` and `config-push.sh` (`lib/boards.sh`'s `lan_subnet`).
- `flake.nix`: the quality shell once, outside the per-system set; packages in two sets once; the `ssh-keygen` wrapper and the process comments go.
- Comments citing "design Dn" name the change ("r4s-ebpf-datapath D11"); a script that `fetch.sh`'s feeds index is redundant with `patch.sh`'s is checked by running `just fetch` alone and then `just patch`, and the first index goes if nothing reads it in between.
- docs/conventions.md's table and groups from the code; docs/ci.md's prose states the present, its tables keep each run's record in one line, rationales moving to the specs they explain; docs/dev-setup.md's VM version from the VM; docs/validation's commands corrected, and folded into docs/ci.md if nothing else remains in them; `.gitignore` keeps only what is produced in the tree (`.claude/worktrees/` added) and one exemption list serves `repo_files` and editorconfig-checker.

## Risks / Trade-offs

- [Workflow changes cannot run before the release run] → actionlint and the workflow tests (`tests/build/test_ci.py`) check them, and every script they call runs in the tests; the release run is their verification.
- [Importing store paths without signatures] → the directory comes only from this repository's own actions cache, written by its host stage; its key is the QEMU's inputs, so a run whose inputs did not change restores the last one, and a failure to restore falls back to building.
