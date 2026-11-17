# manifest: the files a build's manifest lists, as build.sh writes them and the release scripts read them.
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
