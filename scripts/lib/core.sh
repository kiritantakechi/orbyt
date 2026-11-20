# core: what every script needs: the repository's place, messages, the guards of
# the host and the environment, the build tree, and use, which loads the other
# library modules.
# Usage: . "$(dirname -- "$0")/lib/core.sh", then use <module>...   (POSIX sh; sourced)
# POSIX sh has no local variables. So the functions that compute, print or write
# run in a subshell, ( ... ), and their variables never reach the caller's; only
# use, ensure_fhs, scratch_dir, use_tests_venv and quality_prelude change the
# caller, as their names say.
# shellcheck shell=sh

REPO_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

info() {
	printf '==> %s\n' "$*" >&2
}

# use <module>...: load each library module (scripts/lib/<module>.sh) once; a
# module loads what it depends on itself.
use() {
	for lib_module in "$@"; do
		case " ${LIB_MODULES:-} " in
			*" ${lib_module} "*) ;;
			*)
				[ -f "${REPO_DIR}/scripts/lib/${lib_module}.sh" ] || die "no library module '${lib_module}'"
				LIB_MODULES="${LIB_MODULES:+${LIB_MODULES} }${lib_module}"
				# shellcheck source=/dev/null # the module that use names
				. "${REPO_DIR}/scripts/lib/${lib_module}.sh"
				;;
		esac
	done
}

# loaded_modules <script>...: the library modules the scripts load, with the
# modules those load in turn, core first; one file per line.
loaded_modules() (
	names=core
	todo=$(sed -n 's/^use //p' "$@")
	while [ -n "${todo}" ]; do
		next=
		for name in ${todo}; do
			case " ${names} " in
				*" ${name} "*) continue ;;
				*) ;;
			esac
			names="${names} ${name}"
			uses=$(sed -n 's/^use //p' "${REPO_DIR}/scripts/lib/${name}.sh")
			next="${next} ${uses}"
		done
		todo=${next}
	done
	for name in ${names}; do
		printf '%s\n' "${REPO_DIR}/scripts/lib/${name}.sh"
	done
)

# Fail before anything touches the filesystem when the host cannot build:
# BTF (pahole) and mold are unavailable on macOS hosts.
require_linux() (
	os=$(uname -s)
	[ "${os}" = Linux ] ||
		die "builds run only on Linux; use the OrbStack NixOS VM or CI (see docs/dev-setup.md)"
)

# workdir_tree: the build tree, in the work directory, which lives outside the
# repository (ORBYT_WORKDIR).
workdir_tree() (
	[ -n "${ORBYT_WORKDIR:-}" ] || die "ORBYT_WORKDIR is not set (see docs/dev-setup.md)"
	[ -d "${ORBYT_WORKDIR}" ] || die "ORBYT_WORKDIR does not exist: ${ORBYT_WORKDIR}"
	case "${ORBYT_WORKDIR}" in
		"${REPO_DIR}" | "${REPO_DIR}"/*) die "ORBYT_WORKDIR must be outside the repository" ;;
		*) ;;
	esac
	printf '%s\n' "${ORBYT_WORKDIR}/openwrt"
)

# scratch_dir <name> [command]: make a directory for this shell's temporary
# files, <name>.XXXXXX, and set scratch to it; when the shell exits, however it
# ends, <command> runs, if given, and the directory is removed. It is made on the
# work volume when ORBYT_WORKDIR is set, as the VM's /tmp is memory, else in
# $TMPDIR. One for each shell: the exit trap is the shell's own, and a subshell,
# a function in ( ... ) as well, starts without its parent's.
scratch_dir() {
	if [ -n "${ORBYT_WORKDIR:-}" ]; then
		[ -d "${ORBYT_WORKDIR}" ] || die "ORBYT_WORKDIR does not exist: ${ORBYT_WORKDIR}"
		scratch_root="${ORBYT_WORKDIR}/tmp"
		mkdir -p "${scratch_root}"
	else
		scratch_root=${TMPDIR:-/tmp}
	fi
	# shellcheck disable=SC2034 # the caller's
	scratch=$(mktemp -d "${scratch_root%/}/$1.XXXXXX") ||
		die "cannot make a scratch directory in ${scratch_root}"
	# shellcheck disable=SC2064 # the directory as it is now
	trap "${2:+$2; }rm -rf '${scratch}'" EXIT
	trap 'exit 130' INT
	trap 'exit 143' TERM
}

# build_jobs: how many jobs a build runs at once: ORBYT_JOBS, else one for each
# CPU.
build_jobs() (
	if [ -n "${ORBYT_JOBS:-}" ]; then
		printf '%s\n' "${ORBYT_JOBS}"
	else
		nproc
	fi
)

# ensure_fhs <build|test> [args]: re-execute the calling script inside the Nix FHS
# environment of that kind unless already there. The test environment is a
# superset of the build environment, so it satisfies both.
ensure_fhs() {
	kind=$1
	shift
	case "${ORBYT_FHS:-}:${kind}" in
		build:build | test:build | test:test) return 0 ;;
		build:test) die "inside orbyt-build-fhs; run this from the 'nix develop' shell instead" ;;
		:build | :test) ;;
		*) die "ensure_fhs: unknown environment '${kind}'" ;;
	esac
	fhs="orbyt-${kind}-fhs"
	command -v "${fhs}" >/dev/null 2>&1 ||
		die "${fhs} not found; run through 'nix develop' (see docs/dev-setup.md)"
	# shellcheck disable=SC2016 # expanded by the inner shell, not here
	exec "${fhs}" -c 'exec "$0" "$@"' "$0" "$@"
}

# repo_files: files of the repository (tracked and new, not ignored) that follow
# its code standards; upstream-format patches and generated tool files do not.
# The one list of what is exempt: every check takes its files from here, and
# editorconfig-checker's own configuration exempts only the generated lock
# files, which the other checks read as they are.
repo_files() (
	git -C "${REPO_DIR}" ls-files --cached --others --exclude-standard |
		grep -vE '^(patches|docs/upstream|\.claude)/' |
		while IFS= read -r file; do
			[ ! -e "${REPO_DIR}/${file}" ] || printf '%s\n' "${file}"
		done
)

# format_files <shell|nix>: the repository's files of that kind (repo_files), one
# per line, as the formatters and their checks take them. shfmt finds the shell
# files by their extension or interpreter line; preinit's hooks, which preinit
# sources, have neither, so they are added by their place.
format_files() (
	files=$(repo_files)
	case "$1" in
		shell)
			{
				printf '%s\n' "${files}" | xargs shfmt -f
				printf '%s\n' "${files}" | grep '/lib/preinit/'
			} | sort -u
			;;
		nix) printf '%s\n' "${files}" | grep -E '\.nix$' ;;
		*) die "format_files: unknown kind '$1' (shell, nix)" ;;
	esac
)

# use_tests_venv: point uv at the tests' virtual environment for this OS and
# architecture: macOS and the Linux VM share the repository, and a virtual
# environment only works on the host that created it. It lives outside the
# repository, one per checkout: a copy of the tree (a flake's path: source,
# which takes ignored files too, a test's scratch repository) must not carry
# it (python-style D5). ORBYT_TESTS_VENV, when set, names it, as a scratch
# copy shares its original's.
use_tests_venv() {
	if [ -z "${ORBYT_TESTS_VENV:-}" ]; then
		host=$(uname -sm | tr 'A-Z ' 'a-z-')
		checkout=$(printf '%s' "${REPO_DIR}" | cksum | cut -d ' ' -f 1)
		ORBYT_TESTS_VENV="${XDG_CACHE_HOME:-${HOME}/.cache}/orbyt/tests-${checkout}-${host}"
	fi
	UV_PROJECT_ENVIRONMENT=${ORBYT_TESTS_VENV}
	export ORBYT_TESTS_VENV UV_PROJECT_ENVIRONMENT
}

# quality_prelude [args]: what check.sh and fmt.sh do before their tools run. On
# NixOS they re-execute inside orbyt-test-fhs: NixOS cannot run the generic Linux
# binaries that uv installs (Python, ruff, ty). Then the tests' environment, and
# the repository as the working directory. It changes the caller, as its name
# says.
quality_prelude() {
	if [ -e /etc/NIXOS ]; then
		ensure_fhs test "$@"
	fi
	use_tests_venv
	cd "${REPO_DIR}" || exit
}
