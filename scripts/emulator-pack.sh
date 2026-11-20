#!/bin/sh
# emulator-pack: build the emulator and put it, with what it runs on, into a directory.
# Usage: scripts/emulator-pack.sh <directory>
# The directory becomes a binary cache (nix copy --to file://), which
# emulator-unpack imports into another store (tooling-hygiene D3).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

directory=${1:-}

[ -n "${directory}" ] || die "usage: emulator-pack <directory>"
require_linux
emulator=$(nix build --no-link --print-out-paths "${REPO_DIR}#emulator")
nix copy --to "file://${directory}" "${emulator}"
info "emulator ${emulator} in ${directory}"
