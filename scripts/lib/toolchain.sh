# toolchain: what a toolchain was built with: the host environment, its C library
# and Rust's standard libraries, whether its record still names them, and the
# stages of a build that built any of it.
# Usage: use toolchain   (POSIX sh; sourced)
# shellcheck shell=sh
: "${REPO_DIR:?load scripts/lib/core.sh first}"

# toolchain_environment: the host environment the host side is built in, by its
# fingerprint (flake.nix: buildInputsId), which CI's key and the toolchain's
# record name (nixpkgs-2605 D4).
toolchain_environment() (
	[ -n "${ORBYT_BUILD_INPUTS:-}" ] || die "ORBYT_BUILD_INPUTS is not set; the build environment is too old"
	echo "${ORBYT_BUILD_INPUTS##*/}"
)

# toolchain_libc <toolchain dir>: the hash of the toolchain's C library, or
# nothing when it has none (board-model D2: the record in orbyt-toolchain.json
# names it).
toolchain_libc() (
	[ -f "$1/lib/libc.so" ] || return 0
	sum=$(sha256sum "$1/lib/libc.so")
	echo "${sum%% *}"
)

# toolchain_rust_std <tree>: the hash of the Rust standard libraries in the
# tree's staging_dir/hostpkg, the target's among them, or nothing when Rust is
# not built (build-acceleration D7): a rebuild changes it, as it does libc.so.
# Rust's uninstaller leaves its directories, so it is the libraries that count.
toolchain_rust_std() (
	[ -d "$1" ] || die "toolchain_rust_std: no build tree at $1"
	rustlib="$1/staging_dir/hostpkg/lib/rustlib"
	[ -d "${rustlib}" ] || return 0
	cd "${rustlib}" || return
	rlibs=$(find . -path './*/lib/*.rlib' -type f | LC_ALL=C sort)
	[ -n "${rlibs}" ] || return 0
	sum=$(printf '%s\n' "${rlibs}" | xargs sha256sum | sha256sum)
	echo "${sum%% *}"
)

# toolchain_record_differs <tree> <toolchain dir> [cflags]: the first part of the
# toolchain that its record (orbyt-toolchain.json) no longer names, as one word:
# record (there is none), environment (the host side is another environment's),
# toolchain (another C library, or flags other than <cflags> when given) or rust
# (another standard library of Rust); nothing while the record names the
# toolchain as it is. build.sh refuses a toolchain this names a part of, and
# toolchain-build.sh builds that part anew (tooling-hygiene D5).
toolchain_record_differs() (
	tree=$1 toolchain=$2 cflags=${3:-}
	record="${toolchain}/orbyt-toolchain.json"
	if [ ! -f "${record}" ]; then
		echo record
		exit 0
	fi
	environment=$(toolchain_environment)
	recorded=$(jq -r '.environment // ""' "${record}")
	if [ "${recorded}" != "${environment}" ]; then
		echo environment
		exit 0
	fi
	libc=$(toolchain_libc "${toolchain}")
	recorded=$(jq -r '.libc // ""' "${record}")
	recorded_cflags=$(jq -r '.cflags // ""' "${record}")
	if [ -z "${libc}" ] || [ "${recorded}" != "${libc}" ] ||
		{ [ -n "${cflags}" ] && [ "${recorded_cflags}" != "${cflags}" ]; }; then
		echo toolchain
		exit 0
	fi
	rust_std=$(toolchain_rust_std "${tree}")
	recorded=$(jq -r '.rust_std // ""' "${record}")
	[ "${recorded}" = "${rust_std}" ] || echo rust
)

# toolchain_stages <time log>: the stages of a build's time log that built part of
# the toolchain (tools, the cross toolchain, Go or Rust), which only toolchain-build
# builds (build-acceleration D7), one per line.
toolchain_stages() (
	awk -F '\t' '$2 == "begin" && ($4 ~ /^(tools|toolchain)\// ||
		$4 ~ /^package\/feeds\/packages\/(golang|golang-bootstrap|golang1\.[0-9]+|rust)$/) {
		print $4 " [" $3 "]"
	}' "$1" | LC_ALL=C sort -u
)
