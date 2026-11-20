# github: the GitHub repository the scripts talk to (tooling-hygiene D4).
# Usage: use github   (POSIX sh; sourced)
# shellcheck shell=sh
: "${REPO_DIR:?load scripts/lib/core.sh first}"

# github_repository [clone]: the owner/name of the GitHub repository: CI's
# GITHUB_REPOSITORY, else the repository of the first remote of <clone> (this
# one by default) on github.com. A clone without one fails, naming the variable
# that would say it.
github_repository() (
	if [ -n "${GITHUB_REPOSITORY:-}" ]; then
		printf '%s\n' "${GITHUB_REPOSITORY}"
		exit 0
	fi
	clone=${1:-${REPO_DIR}}
	for remote in $(git -C "${clone}" remote); do
		url=$(git -C "${clone}" remote get-url "${remote}")
		case "${url}" in
			https://github.com/* | git@github.com:* | ssh://git@github.com/*)
				repository=${url#*github.com[:/]}
				printf '%s\n' "${repository%.git}"
				exit 0
				;;
			*) ;;
		esac
	done
	die "no remote of ${clone} is on github.com: set GITHUB_REPOSITORY to owner/name"
)
