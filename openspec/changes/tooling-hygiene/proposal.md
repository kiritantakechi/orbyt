# Proposal

## Why

On 2026-11-20 the maintainer asked for the project's band-aids to be replaced by fixes at their causes, and for CI's quota to go to the release's verification alone. A review of the scripts, the justfile, the flake, the workflows and the documents found work done twice (the uv cache's steps, the build's path list, the patched QEMU built by every test job), decisions written as inline workflow shell no test can run, `just fmt` formatting less than `just check` checks, the maintainer's machine named in scripts and documents, errors swallowed where they matter (an empty kernel version in a release's notes), and documents that describe what the code no longer does.

## What Changes

- **fmt and check from one file list**, and one prelude for the two scripts.
- **Workflows that run recipes**: the bump's pull request, the sign job's board check and the drill check's decision become scripts with tests; every step goes through `just`; the uv cache and the runner's preparation become shared actions used by every job that needs them, the drill job included; the build's path list and the download cache's key are written once.
- **The emulator built once per run** and shared with the test jobs.
- **No maintainer's machine**: the repository from the clone's remote or `GITHUB_REPOSITORY`, the work volume's image and the tests' directory from configuration, documents with placeholders.
- **Helpers for repeated idioms**: a scratch directory with its cleanup (on the work volume, not the VM's memory-backed `/tmp`), the build's job count, a board's validation; the manifest's writer beside its readers; the toolchain record's check shared by the build and the toolchain build.
- **Errors that matter fail**: an absent kernel version, a compiler cache selected but missing.
- **Names and documents that say what is**: the conventions' module table and recipe groups, `ORBYT_` for every environment variable, check and recipe names aligned, the LAN subnet read from one place, the flake's quality shell defined once, comments citing designs by their change, docs/ci.md and dev-setup.md stating the present with the records kept as records, the validation notes' commands corrected, `.gitignore` without dead patterns.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality/code-standards`: the formatters format exactly what the checks check.
- `build/ci`: the workflows run recipes, their decisions in tested scripts, each list and key written once; the emulator is built once per run.
- `build/environment`: no script or document names one maintainer's machine or repository.

## Impact

- `scripts/` and `scripts/lib/`, the justfile, `flake.nix`, `.github/workflows/` and `.github/actions/`, `.gitignore`, `.editorconfig-checker.json`, `docs/`.
- Tests: `tests/build/test_ci.py` (the drill check, the path list), `tests/unit/test_lib.py` (the new helpers), `tests/quality/test_code_standards.py` (fmt and check alike).
- CI's behavior is unchanged but for where things are computed and the emulator's single build.
