# Proposal

## Why

The flake's `nixpkgs` follows `nixos-25.11`, which reached its end of life on 2026-06-30 and has had no commit since: its host tools get no security or bug fixes. On 2026-11-16 the maintainer chose to wait for NixOS 26.11 and move once; on 2026-11-19, with 26.11 not yet branched, they asked to move to the current release, `nixos-26.05`, now.

## What Changes

- `flake.nix`'s `nixpkgs` follows `nixos-26.05`, and `flake.lock` pins its head of 2026-11-16 (`f68407657ad2`). `nixpkgs-unstable`, which supplies uv and the emulator's tools, stays as locked; `erofs-utils` joins those tools from it, as 26.05's cannot extract the images' EROFS.
- The build environment's host tools move with it: the compilers and libraries the host stage builds OpenWrt's tools and toolchains with, and the quality tools (shellcheck, shfmt, nixfmt, actionlint, editorconfig-checker, gitleaks). The toolchain key covers the environment, so the host stage and every toolchain build anew once, in CI and on the VM.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: build/environment's "Pinned common host environment" asks for exactly this, a version change made in `flake.lock` alone.

## Impact

- `flake.nix`, `flake.lock`.
- CI: the branch's first run and main's first run after the merge each build the host stage anew (about 2 hours each), as a seed change does.
- The VM's work tree: its toolchain builds anew on the first build after the move; it runs after orbyt-brand's and orbyt-theme's local tests, which use the tree's current toolchain.
- The VM's own NixOS (`docs/dev-setup.md`: 25.11) is the host of the flake's environment, not part of it, and stays.
