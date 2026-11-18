# Tasks

## 1. The move (design D1)

- [x] 1.1 Point `nixpkgs` at `nixos-26.05` and update its lock alone.

  Verify: `nix flake metadata` shows `nixpkgs` at `f68407657ad2` and `nixpkgs-unstable` unchanged.

- [x] 1.2 Build the dev shells on 26.05 and run the checks.

  Verify: `build`, `quality` and the default shell build; `just check` passes.

- [x] 1.3 Take `erofs-utils` from `nixpkgs-unstable` (D3).

  Verify: the shell's `fsck.erofs` is 1.9.4; `unit/test_oci.py` passes, which failed with 26.05's 1.9.1.

## 2. Verification (design D2)

- [ ] 2.1 Run CI's build on this change's branch for both boards.

  Verify: the host stage builds anew; every job passes; the run is recorded in `docs/ci.md`.

- [ ] 2.2 After orbyt-brand's and orbyt-theme's local tests, build the toolchain and the R4S on the VM from this branch.

  Verify: the toolchain builds anew with the new environment, and the R4S's image builds.

## Workflow follow-up

- After orbyt-theme is merged: merge main into this branch, sync, archive, merge and push Codeberg first, then GitHub.
- When NixOS 26.11 is released, move to it in a change of its own.
