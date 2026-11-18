# Design

## Context

- `flake.nix` has two inputs: `nixpkgs` (`nixos-25.11`), which supplies the build environment and the quality tools, and `nixpkgs-unstable`, for the newest uv and the emulator's qemu, dtc and U-Boot tools, never part of the build.
- The toolchain key hashes the board-neutral build configuration and the build environment; a different `nixpkgs` gives a new key, so the host stage of CI and the VM's toolchain build anew.
- uv-managed Pythons run only inside the FHS shell (`orbyt-test-fhs`): outside it, NixOS has no `/lib/ld-linux`, which uv reports as "Python interpreter not found". The tests already run there.

## Goals / Non-Goals

**Goals:**
- A supported nixpkgs release for every host tool, with both boards and every check passing on it.

**Non-Goals:**
- `nixpkgs-unstable`: its uv and emulator tools stay as locked; moving them is a change of their own when needed.
- The VM's own NixOS release.
- NixOS 26.11: the next move, once it is released.

## Decisions

### D1. One input, one lock update

`nixpkgs.url` follows `nixos-26.05`; `nix flake update nixpkgs` moves that input's lock alone, to the channel's head of 2026-11-16 (`f68407657ad2`).

### D2. Verified where the tools run

- The dev shells (`build`, `quality`, the default FHS environment) build on 26.05, and `just check` passes with the new quality tools: on 2026-11-19 it did, with no new finding.
- CI on the branch builds the host stage anew and then both boards, and runs every suite.
- The VM's work tree builds its toolchain anew and the R4S on it, after orbyt-brand's and orbyt-theme's local tests, whose images need the current toolchain.

## Risks / Trade-offs

- [A newer host compiler breaks a host tool's build] → The host stage in CI shows it before the merge; a fix goes into the tool's patch, upstream-acceptable, as the series' other tool patches.
- [Two host-stage rebuilds, the branch's and main's] → As for any change of the environment; main cannot restore a branch's cache.
