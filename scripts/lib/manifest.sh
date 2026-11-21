# manifest: the files a build's manifest lists, written by build.sh, drill-base.sh
# and release-sign.sh and read by the release scripts.
# Usage: use manifest   (POSIX sh; sourced)
# shellcheck shell=sh
: "${REPO_DIR:?load scripts/lib/core.sh first}"

# source_commit <repository>: the commit of the git repository a build ran in,
# -dirty when its working tree differs from it in any way: a tracked file changed,
# a change staged, or a file neither tracked nor ignored, as git status lists it
# (release-integrity D1, release-freshness D4).
source_commit() (
	commit=$(git -C "$1" rev-parse HEAD)
	changes=$(git -C "$1" status --porcelain)
	echo "${commit}${changes:+-dirty}"
)

# manifest_write <dir> [<list>]: write <dir>/manifest.json, the object on the
# standard input with files the sha256 of each file <list> names, one path in
# <dir> on each line, or of every file in <dir> but the manifest itself, and
# check it (manifest_files_check). The object goes to jq as a file: a release's
# manifest, with every package of every board, is past what one argument may
# hold. sha256sum escapes a name with a backslash or a line break, and starts
# its line with a backslash, which the capture below would misread: no such name
# is listed. Names that are no plain paths fail the check.
# shellcheck disable=SC2154 # scratch, which scratch_dir sets
manifest_write() (
	dir=$1 list=${2:-}
	scratch_dir orbyt-manifest
	cat >"${scratch}/fields.json"
	if [ -n "${list}" ]; then
		[ -s "${list}" ] || die "manifest_write: ${list} names no file"
		hashes=$(cd "${dir}" && xargs sha256sum -- <"${list}")
	else
		hashes=$(cd "${dir}" && find . -type f ! -path ./manifest.json -exec sha256sum -- {} + |
			sed 's|  \./|  |')
	fi
	case "${hashes}" in
		*\\*) die "a file's name holds a backslash or a line break: ${hashes}" ;;
		*) ;;
	esac
	printf '%s\n' "${hashes}" | LC_ALL=C sort -k 2 | jq -R -n --slurpfile fields "${scratch}/fields.json" '
		$fields[0] + {files: [inputs | capture("^(?<sha>[0-9a-f]+)  (?<path>.+)$") | {(.path): .sha}] | add}
	' >"${dir}/manifest.json"
	manifest_files_check "${dir}/manifest.json"
)

# manifest_fact <file> <what>: a fact of the build for its manifest, the contents
# of <file>, which the build leaves; a failure naming <what> when the file is
# missing or empty.
manifest_fact() (
	[ -s "$1" ] || die "the build left no $2 in $1"
	cat "$1"
)

# manifest_files_check <manifest.json>: fail unless the manifest lists files, each
# by a plain path inside its build with its sha256 (release-integrity D2). A
# plain path has no leading slash, no empty, . or .. component, and nothing but
# letters, digits and ._+~- between its slashes, so that a script may read,
# copy and sign a file by its name and stays inside the build.
manifest_files_check() (
	jq -e '
		.files | type == "object" and length > 0 and all(
			to_entries[];
			(.key | test("\\A[A-Za-z0-9._+~-]+(/[A-Za-z0-9._+~-]+)*\\z")
				and (split("/") | all(. != "." and . != "..")))
			and (.value | type == "string" and test("\\A[0-9a-f]{64}\\z")))
	' "$1" >/dev/null || die "$1 lists a file that is no plain path inside its build, or no sha256 of one"
)

# manifest_checksums <manifest.json> [<pattern>]: the files the manifest lists,
# all or those whose path matches the jq regex, as sha256sum --check reads them.
manifest_checksums() (
	jq -r --arg pattern "${2:-}" '
		.files | to_entries[] | select(.key | test($pattern)) | "\(.value)  \(.key)"
	' "$1"
)
