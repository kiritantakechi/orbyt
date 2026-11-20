#!/bin/sh
# emulator-key: print the emulator's cache key as key=<value>.
# Usage: scripts/emulator-key.sh >>"$GITHUB_OUTPUT"
# The key is the patched QEMU's store path (the flake's emulator package),
# which names every input of its build: a run whose emulator is the same takes
# the one an earlier run built (tooling-hygiene D3).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

require_linux
emulator=$(nix eval --raw "${REPO_DIR}#emulator.outPath")
hash=${emulator#/nix/store/}
printf 'key=emulator-%s\n' "${hash%%-*}"
