# Tasks

## 1. The files the build runs for (design D1)

- [ ] 1.1 Add to `tests/build/test_ci.py` the tests that `scripts/lib/runs.sh`'s list is `build.yml`'s `paths`, for pushes and for pull requests, and that `build_reads` answers as GitHub's rules do for a path in and out of each pattern.

  Verify: both fail before 1.2 (no such module).

- [ ] 1.2 Add `scripts/lib/runs.sh` with the list and `build_reads`; `build.yml`'s comment on its `paths` names the module beside the tests.

  Verify: the tests of 1.1 and the rest of `tests/build/test_ci.py` pass; `just check` passes.

## 2. Publishing and pruning by a current commit (design D2, D3)

- [ ] 2.1 Add the tests of "A branch moved by documentation only" (`tests/release/test_publishing.py`, with a comparison of 300 files that does not publish) and "A re-run of a superseded run" (`tests/unit/test_ci_caches.py`, with a head moved by documentation alone that prunes as before); the fake `gh` answers the compare API.

  Verify: `spec-coverage --change release-freshness` reports both covered; before 2.2 the test of a branch moved by documentation fails (publishing refuses) and the test of a superseded run fails (it deletes the newer run's caches).

- [ ] 2.2 Add `run_current` to `scripts/lib/runs.sh`; have `release-publish.sh --upload` and `cache-prune.sh` ask it (the prune with `GITHUB_SHA`); describe both in `docs/release-flow.md` (step 5) and `docs/ci.md` (the `caches` job and the paragraph on cancelled runs).

  Verify: the tests of 2.1 and the rest of both modules pass; `just check` passes.

## 3. The commit a build names (design D4)

- [ ] 3.1 Add to `tests/unit/test_lib.py` the tests of `source_commit` in a scratch repository: clean, an untracked file, an ignored file, a staged change.

  Verify: `spec-coverage --change release-freshness` reports "A file not committed" covered; the tests fail before 3.2 (no such function).

- [ ] 3.2 Add `source_commit` to `scripts/lib/manifest.sh` and take `build.sh`'s commit from it; update the field's description in `tests/wrt_tests/model/outputs.py`.

  Verify: the tests of 3.1 pass; `just check` passes; on the VM, `just build r4s` with an untracked scratch file in the checkout writes a manifest whose `commit` ends in `-dirty`, and without it one that does not.

## 4. The host stage's key (design D5)

- [ ] 4.1 Have `toolchain-key.sh` hash `HEAD:include`, `HEAD:scripts` and `HEAD:rules.mk`; describe the key's inputs in `docs/ci.md`; update the scenarios of "Cache keyed on actual inputs" in `tests/verified-elsewhere.toml`, "A build file of OpenWrt changes" among them.

  Verify: `just check` passes; on the VM, a scratch commit of the build tree that changes `include/cmake.mk` alone moves the key, one that changes a file of the packages feed outside `lang/golang` and `lang/rust` does not, and the tree is put back on its series afterwards (`just patch`).

## 5. Verification

- [ ] 5.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the host stage builds anew once, for the key's new inputs; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub; then start test-controls.
