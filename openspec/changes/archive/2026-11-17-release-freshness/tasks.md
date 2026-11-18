# Tasks

## 1. The files the build runs for (design D1)

- [x] 1.1 Add to `tests/unit/test_lib.py` the tests that `scripts/lib/runs.sh`'s list is `build.yml`'s `paths`, for pushes and for pull requests, and that `build_reads` answers as GitHub's rules do for a path in and out of each pattern.

  Verify: both fail before 1.2 (no such module).
  Result (2026-11-17): both failed with "no library module 'runs'". They went to `tests/unit/test_lib.py`, beside the library's other modules: a test of `tests/build/` carries one scenario, and these check a definition. GitHub's matching is re-implemented in the test as its oracle (`**` across slashes, `*` within one).

- [x] 1.2 Add `scripts/lib/runs.sh` with the list and `build_reads`; `build.yml`'s comment on its `paths` names the module beside the tests.

  Verify: the tests of 1.1 and the rest of `tests/build/test_ci.py` pass; `just check` passes.
  Result (2026-11-17): both pass, with the rest of `tests/build/test_ci.py` but its emulator test of the manifest (the image was rebuilt for 3.2); `just check` passes. A pattern of a form `build_reads` does not read counts as read and says so, so that a new form in the workflow never lets a run pass as current.

## 2. Publishing and pruning by a current commit (design D2, D3)

- [x] 2.1 Add the tests of "A branch moved by documentation only" (`tests/release/test_publishing.py`, with a comparison of 300 files that does not publish) and "A re-run of a superseded run" (`tests/build/test_ci.py`, beside the other scenarios of the prune, with a head moved by documentation alone that prunes as before); the stand-in `gh` (`orbyt_tests.model.github`), which the publishing tests now share, answers for branch heads, the compare API and the release it records.

  Verify: `spec-coverage --change release-freshness` reports both covered; before 2.2 the test of a branch moved by documentation fails (publishing refuses) and the test of a superseded run fails (it deletes the newer run's caches).
  Result (2026-11-17): both covered. Before 2.2, publishing refused the branch moved by documentation ("main has moved from c… to d…: the newer run publishes"), and the superseded run deleted the newer run's toolchain and caches, and on main a deleted branch's too; the other cases of a moved branch (a script, a script renamed into the documentation, 300 files, a head that does not descend) refused as before. The test of a run past documentation went to `tests/unit/test_ci_caches.py`, unmarked.

- [x] 2.2 Add `superseding_head` to `scripts/lib/runs.sh`; have `release-publish.sh --upload` and `cache-prune.sh` ask it (the prune with `GITHUB_SHA`); describe both in `docs/release-flow.md` (step 5) and `docs/ci.md` (the `caches` job and the paragraph on cancelled runs).

  Verify: the tests of 2.1 and the rest of both modules pass; `just check` passes.
  Result (2026-11-17): the publishing, cache, library and CI tests pass, 72; `just check` passes. The helper prints the newer head, or nothing for a current commit, and dies when GitHub does not answer, so that a failed API call is never read as a moved branch (design D2).

## 3. The commit a build names (design D4)

- [x] 3.1 Add to `tests/build/test_ci.py` the tests of `source_commit` in a scratch repository: clean, an untracked file, an ignored file, a staged change.

  Verify: `spec-coverage --change release-freshness` reports "A file not committed" covered; the tests fail before 3.2 (no such function).
  Result (2026-11-17): covered; all five cases failed before 3.2.

- [x] 3.2 Add `source_commit` to `scripts/lib/manifest.sh` and take `build.sh`'s commit from it; update the field's description in `tests/orbyt_tests/model/outputs.py`.

  Verify: the tests of 3.1 pass; `just check` passes; on the VM, `just build r4s` with an untracked scratch file in the checkout writes a manifest whose `commit` ends in `-dirty`, and without it one that does not.
  Result (2026-11-17): the five cases pass; `just check` passes. On the VM, the R4S built from 768f855 with an untracked scratch file wrote `768f855…-dirty`, where the check of tracked files would have written it clean, and built again without it wrote `768f855…` (a first build, with tracked changes besides, proved nothing and is not counted).

## 4. The host stage's key (design D5)

- [x] 4.1 Have `toolchain-key.sh` hash `HEAD:include`, `HEAD:scripts` and `HEAD:rules.mk`; describe the key's inputs in `docs/ci.md`; update the scenarios of "Cache keyed on actual inputs" in `tests/verified-elsewhere.toml`, "A build file of OpenWrt changes" among them.

  Verify: `just check` passes; on the VM, a scratch commit of the build tree that changes `include/cmake.mk` alone moves the key, one that changes a file of the packages feed outside `lang/golang` and `lang/rust` does not, and the tree is put back on its series afterwards (`just patch`).
  Result (2026-11-17): `just check` passes. On the VM, on the series c77d3f7d: the key was toolchain-f67ea23a; a scratch commit appending a comment to `include/cmake.mk` moved it to toolchain-89b70535, while main's key of three build files stayed at toolchain-5030fa04; one appending a comment to the packages feed's `net/socat/Makefile` kept toolchain-f67ea23a. `just patch` put the tree back on c77d3f7d.

## 5. Verification

- [x] 5.1 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the host stage builds anew once, for the key's new inputs; the run is recorded in `docs/ci.md`.
  Result (2026-11-17): CI run 44035778048, of 85cb1df, passed on both boards in its first attempt; its host stage built anew under the new key, 144 min, and its `caches` job pruned through the new check. Recorded in `docs/ci.md`. The branch was then rebased onto main past push-isolation, which touches none of its files.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub; then start test-controls.
