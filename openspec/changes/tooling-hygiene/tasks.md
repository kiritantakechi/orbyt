# Tasks

## 1. fmt and check alike (design D1)

- [x] 1.1 `format_files` and the shared prelude in `scripts/lib/core.sh`, used by `check.sh` and `fmt.sh`; a code-standards test with a misindented preinit hook.

  Verify: the test passes (check fails on the hook, fmt fixes it); `just check` passes.

## 2. Workflows that run recipes (D2, D3)

- [x] 2.1 `bump-open.sh`, `drill-check.sh` with its test over every combination, `release-sign.sh` checking the build's board; every step through `just`.

  Verify: `tests/build/test_ci.py` and the release suite's signing tests pass; actionlint passes.

- [x] 2.2 The `uv-cache` action for check, system-test and drill; the runner's preparation in the Nix action; the path list once (anchors, read by `runs.sh` through yq); `just download-key`; `NIX_CONFIG` dropped if the installer enables its features.

  Verify: `test_ci.py` passes without the copies' equality test; actionlint passes.

- [ ] 2.3 The emulator built in the host stage, cached by its inputs, imported by the test jobs.

  Verify: on the VM, `nix copy --to file://` and a `--no-check-sigs` import into a fresh store give a dev shell that builds nothing; the release run shows no QEMU compile in its test jobs.

## 3. No maintainer's machine (D4)

- [x] 3.1 `github_repository`, `ORBYT_WORKDIR_IMAGE`, `ORBYT_TESTDIR`'s default, docs/dev-setup.md's placeholders.

  Verify: a grep finds no user, home directory, volume or repository name of the maintainer's in scripts/ and docs/ (the CI records' run links aside); a unit test of `github_repository` with an origin remote and without one.

## 4. Helpers and errors (D5, D6)

- [x] 4.1 `scratch_dir`, `build_jobs`, `require_board`, `manifest_write`, `toolchain_record_differs`, used by every script that spelled them out.

  Verify: the unit suite's library tests (dead code included) pass; `just build r4s dev` with nothing changed rebuilds nothing; a build's manifest is unchanged.

- [x] 4.2 The kernel version required; the compiler caches failing when selected and missing.

  Verify: unit tests for both; `just build r4s dev` passes.

## 5. Names and documents (D7)

- [x] 5.1 `ORBYT_CACHE_*`, the check and recipe names, `lan_subnet`, the flake's quality shell once, `fetch.sh`'s index (checked, kept or dropped).

  Verify: `just check` and the unit suite pass; `nix flake check` passes; `just fetch` followed by `just patch` applies.

- [x] 5.2 The design citations named by their change; docs/conventions.md, docs/ci.md, docs/dev-setup.md and docs/validation brought to the present; `.gitignore` and the exemption list.

  Verify: a grep finds no "design D" citation without its change; `just check` passes; every command in docs/ runs as written (each recipe and its arguments exist).

## 6. dae's layout (D8)

- [x] 6.1 config-push's `dae/` refusal, its test and scenario, and docs/ops.md's "Moving from dae" go.

  Verify: `spec-coverage` passes with the scenario removed; the configuration push suite passes on the emulated R4S.

## 7. Verification

- [x] 7.1 `just check`, the unit and quality suites, and a build of both boards on the VM with nothing changed.

  Verify: every check and test passes; the builds rebuild nothing. Seen 2026-11-22: `just check` passes at 83fd67f; the unit and quality suites passed in the R4S's whole suite; both boards built at 83fd67f and then again: no package, tool or toolchain stage ran, only OpenWrt's image step, which every build runs, and each board's manifest was the first build's, byte for byte.

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification, which is also the first run of D2 and D3's workflow changes; its run is recorded in docs/ci.md for every change it covers.
- Archive after test-hygiene.
