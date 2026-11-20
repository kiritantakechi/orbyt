#!/bin/sh
# toolchain-key: print the host-toolchain cache key as key=<value>.
# Usage: scripts/toolchain-key.sh [profile] >>"$GITHUB_OUTPUT"   (default dev)
# The key covers exactly the inputs that change the cached host tools and cross
# toolchain of the profile (design D11): among them the configuration
# toolchain-build.sh builds it from.
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"
use seeds toolchain

profile=${1:-dev}

require_linux
tree=$(workdir_tree)
ensure_fhs build "$@"

[ -f "${tree}/feeds.conf" ] || die "no source tree; run 'just fetch' and 'just patch' first"

arch=$(uname -m)
# The generic kernel files go with toolchain/: the toolchain's kernel headers come
# from them. Every kernel version's count, a superset of what the toolchain's own
# record covers, so that the key moves whenever that record would (build-integrity D4).
trees=$(git -C "${tree}" rev-parse HEAD:tools HEAD:toolchain HEAD:target/linux/generic)
langs=$(git -C "${tree}/feeds/packages" rev-parse HEAD:lang/golang HEAD:lang/rust)
# OpenWrt's build files and build scripts, whole: the host tools' and the
# toolchain's makefiles include them, some through variables only make resolves,
# and run the scripts; and they name the stamps of the Go and Rust host builds,
# which the archive carries (build-acceleration D2, release-freshness D5).
build_files=$(git -C "${tree}" rev-parse HEAD:rules.mk HEAD:include HEAD:scripts)
# The board-neutral configuration of the profile, as toolchain-build.sh composes
# it: every seed of the profile and every board's device (board-model D2). Its
# options alone, set or not set, as merge-seeds.awk reads them: a comment of a
# seed changes no tool.
scratch_dir orbyt-toolchain-key
configuration="${scratch}/configuration"
compose_seeds "${tree}" "${profile}" "" "${configuration}"
seed=$(grep -E '^(CONFIG_[^= ]+=|# CONFIG_[^ ]+ is not set$)' "${configuration}" | sha256sum)
# The target and subtarget the configuration selects, by their makefiles, which
# name what the toolchain is built for: the architecture, the CPU type, the
# features and the kernel version, whose headers the toolchain carries
# (release-integrity D6). The devices are defined elsewhere (image/).
target=$(sed -n 's/^CONFIG_TARGET_\([a-z0-9]*\)=y$/\1/p' "${configuration}")
subtarget=$(sed -n "s/^CONFIG_TARGET_${target}_\\([a-z0-9]*\\)=y\$/\\1/p" "${configuration}")
definition=$(git -C "${tree}" rev-parse \
	"HEAD:target/linux/${target}/Makefile" "HEAD:target/linux/${target}/${subtarget}/target.mk") ||
	die "the configuration selects no target and subtarget of ${tree}: '${target}' '${subtarget}'"
# Build environment fingerprint (flake.nix: buildInputsId): the store paths of the
# host packages plus the build profile. Test and quality tooling are not part of
# it, so adding them keeps the cached toolchain.
environment=$(toolchain_environment)
# The scripts that build and pack the archive decide what it holds, and so do the
# library modules they load (module-boundaries D8).
set -- "${REPO_DIR}/scripts/toolchain-build.sh" "${REPO_DIR}/scripts/toolchain-pack.sh"
modules=$(loaded_modules "$@")
# shellcheck disable=SC2086 # modules is a newline-separated list of plain paths
recipe=$(cat "$@" ${modules} | sha256sum)

digest=$(printf '%s\n' "${arch}" "${trees}" "${langs}" "${build_files}" "${seed}" "${definition}" "${environment}" "${recipe}" | sha256sum)
printf 'key=toolchain-%s\n' "${digest%% *}"
