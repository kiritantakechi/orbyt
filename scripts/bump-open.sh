#!/bin/sh
# bump-open: push an upstream bump's branch and open its pull request.
# Usage: scripts/bump-open.sh <pull request text>   (in CI; PUSH_TOKEN and GH_TOKEN set)
# The text is upstream-bump's: its title, a blank line, its body; empty when
# upstream has not moved, and then nothing is pushed. The branch is
# bump/<date>, with upstream.lock committed by the workflow's bot; a branch that
# exists stays as it is, and so does a pull request it has. PUSH_TOKEN pushes,
# so that the push starts the branch's workflows, which the workflow's own token
# would not (docs/release-flow.md).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

BOT_NAME="github-actions[bot]"
BOT_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"

description=${1:-}

[ -n "${description}" ] || die "usage: bump-open <pull request text>"
if [ ! -s "${description}" ]; then
	info "upstream has not moved"
	exit 0
fi
[ -n "${PUSH_TOKEN:-}" ] ||
	die "no secret BUMP_PUSH_TOKEN: the bump pushes and opens its pull request with a token whose pushes start workflows (docs/release-flow.md); nothing was pushed"

branch="bump/$(date -u +%Y-%m-%d)"
title=$(head -n 1 "${description}")
scratch_dir orbyt-bump-open
body="${scratch}/body"
tail -n +3 "${description}" >"${body}"

if git ls-remote --exit-code --heads origin "${branch}" >/dev/null; then
	info "${branch} exists already: it stays as it is"
else
	git switch -q -c "${branch}"
	git -c user.name="${BOT_NAME}" -c user.email="${BOT_EMAIL}" commit -q -m "${title}" upstream.lock
	git push -q origin "${branch}"
fi
pulls=$(gh pr list --head "${branch}" --state all --json number --jq '.[].number')
if [ -n "${pulls}" ]; then
	info "${branch} has its pull request"
else
	gh pr create --base main --head "${branch}" --title "${title}" --body-file "${body}" ||
		die "cannot open the pull request of ${branch}: BUMP_PUSH_TOKEN needs Pull requests read and write; its build runs, open it by hand"
fi
