#!/bin/sh
# emulator-unpack: import the emulator emulator-pack put into a directory.
# Usage: scripts/emulator-unpack.sh <directory>
# The store then holds the flake's emulator, which the test environment takes
# instead of building it. The directory's binary cache carries no signature:
# the importing user must be trusted, as CI's runner user is (tooling-hygiene
# D3).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

directory=${1:-}

[ -n "${directory}" ] || die "usage: emulator-unpack <directory>"
require_linux
emulator=$(nix eval --raw "${REPO_DIR}#emulator.outPath")
nix copy --no-check-sigs --from "file://${directory}" "${emulator}"
info "emulator ${emulator} imported"
