# runs: which changes run the build workflow (release-freshness D1), and which
# commits a newer run supersedes (D2).
# Usage: use runs   (POSIX sh; sourced)
# shellcheck shell=sh
: "${REPO_DIR:?load scripts/lib/core.sh first}"

# build_paths: build.yml's paths, the same for pushes and pull requests, one a
# line in their order; tests/build/test_ci.py holds them to the workflow's.
build_paths() {
	cat <<-'PATHS'
		**
		!openspec/**
		!docs/**
		!**/*.md
		docs/patches.md
		docs/services.md
	PATHS
}

# build_reads <path>: whether a change to the repository's file <path> runs the
# build workflow: the last of build_paths that matches it decides, one with a
# leading ! keeping the build from running, as GitHub reads the list. Of the
# pattern syntax it reads the forms build_paths uses: ** alone, <dir>/**,
# **/<name>, whose name is matched against the path's end, and a plain path.
# Another form says so and counts as read, so that no file goes unbuilt for it.
build_reads() (
	build_paths | {
		reads=no
		while IFS= read -r pattern; do
			verdict=yes
			case "${pattern}" in
				'!'*)
					verdict=no
					pattern=${pattern#!}
					;;
				*) ;;
			esac
			matched=no
			case "${pattern}" in
				'**') matched=yes ;;
				'**/'*)
					name=${pattern#'**/'}
					# shellcheck disable=SC2254 # the name is a pattern
					case "$1" in
						${name} | */${name}) matched=yes ;;
						*) ;;
					esac
					;;
				*'/**')
					case "$1" in
						"${pattern%'/**'}"/*) matched=yes ;;
						*) ;;
					esac
					;;
				*'*'* | *'?'* | *'['*)
					echo "build_reads: a pattern of a form it does not read: ${pattern}" >&2
					reads=yes
					break
					;;
				*) [ "$1" != "${pattern}" ] || matched=yes ;;
			esac
			[ "${matched}" = no ] || reads=${verdict}
		done
		[ "${reads}" = yes ]
	}
)

# superseding_head <repository> <commit> <branch>: print the head of <branch> of
# the GitHub repository when it supersedes a run of <commit>, nothing when
# <commit> is current: the head itself, or one the head descends from by changes
# to files the build workflow does not run for alone, as the compare API lists
# them, each renamed file's former name too (release-freshness D2). GitHub lists
# 300 files at most, so a comparison of that many may hide more and supersedes.
# Dies when GitHub does not answer.
superseding_head() (
	head=$(gh api "repos/$1/git/ref/heads/$3" --jq .object.sha) ||
		die "cannot read the head of $3"
	[ "${head}" != "$2" ] || exit 0
	compared=$(gh api "repos/$1/compare/$2...${head}" \
		--jq '.status, (.files | length), (.files[] | .filename, (.previous_filename // empty))') ||
		die "cannot compare $2 with the head of $3, ${head}"
	if printf '%s\n' "${compared}" | {
		read -r status && read -r count || exit 1
		[ "${status}" = ahead ] && [ "${count}" -lt 300 ] || exit 1
		while IFS= read -r file; do
			! build_reads "${file}" || exit 1
		done
	}; then
		exit 0
	fi
	echo "${head}"
)
