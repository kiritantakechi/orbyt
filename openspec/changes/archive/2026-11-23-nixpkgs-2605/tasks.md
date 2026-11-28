# Tasks

## 1. The move (design D1)

- [x] 1.1 Point `nixpkgs` at `nixos-26.05` and update its lock alone.

  Verify: `nix flake metadata` shows `nixpkgs` at `f68407657ad2` and `nixpkgs-unstable` unchanged.

- [x] 1.2 Build the dev shells on 26.05 and run the checks.

  Verify: `build`, `quality` and the default shell build; `just check` passes.

- [x] 1.3 Take `erofs-utils` from `nixpkgs-unstable` (D3).

  Verify: the shell's `fsck.erofs` is 1.9.4; `unit/test_oci.py` passes, which failed with 26.05's 1.9.1.

## 2. The local host side (design D4)

- [x] 2.0 Record the host environment in the toolchain's record; build the host side anew when it changes, and refuse a toolchain of another environment in `build`.

  Verify: the toolchain tests of `build/test_boards.py`, the new environment's among them, pass; the R4S's local build on 26.05 rebuilds the tools and the toolchains and builds its image. Seen: the toolchain tests of `build/test_boards.py` passed in the R4S's whole suite at 83fd67f (2026-11-22); on 2026-11-21 the R4S's local build on 26.05 rebuilt the host tools (01:03 to 01:10 +0800) and the toolchain (01:27 to 01:49) after e439b2b and built its image, the toolchain's record naming the new environment.

## 3. Verification (design D2)

- [x] 3.1 CI's release verification: the one run on the stack's final head builds and tests both boards with this change (2026-11-19: CI runs only to verify a release; changes are verified locally until then).

  Verify: the host stage builds anew; every job passes; the run is recorded in `docs/ci.md` for this change. Seen: the release verification's run on main at 4740b94 (build 45095056994, check 45095056946, 2026-11-23): the host stage found no toolchain under its new key and built anew, in 205 minutes; every job passed (`docs/ci.md`).

- [x] 3.2 After orbyt-brand's and orbyt-theme's local tests, build the toolchain and the R4S on the VM from this branch.

  Verify: the toolchain builds anew with the new environment, and the R4S's image builds. Seen 2026-11-21: the toolchain built anew with the new environment (01:27 to 01:49 +0800) and the R4S's image built; on 2026-11-22, after the local tests, both boards built at the stack's head, 83fd67f.

## Workflow follow-up

- The stack (orbyt-brand, orbyt-theme, nixpkgs-2605, python-style, then firmware-, patch-, test- and tooling-hygiene) is verified locally on its final head, then archived change by change in that order there; main fast-forwards to it and is pushed, Codeberg first, then GitHub, whose run on main is the release verification.
- When NixOS 26.11 is released, move to it in a change of its own.
