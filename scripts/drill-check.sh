#!/bin/sh
# drill-check: decide the check main's rules require, from a run's results.
# Usage: scripts/drill-check.sh [--bump-pull-request] <system-test> <sign> <drill>
# Each of the three is a job's result. It passes when the system tests passed
# and every board's drill passed, or when signing, and with it every drill, did
# not run (pull requests, no release keys yet). A failed or rejected signing
# skips the drills too, and fails here (board-model D9). A bump's pull request
# builds nothing and passes: the push run of its branch, which drills, reports
# the check (bump-branch-runs D3).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

bump=
if [ "${1:-}" = --bump-pull-request ]; then
	bump=1
	shift
fi
[ "$#" -eq 3 ] || die "usage: drill-check [--bump-pull-request] <system-test> <sign> <drill>"
system_test=$1 sign=$2 drill=$3

info "system-test: ${system_test}, sign: ${sign}, drill: ${drill}"
if [ -n "${bump}" ]; then
	info "a bump's pull request builds nothing: its branch's push run reports the drills"
	exit 0
fi
[ "${system_test}" = success ] || die "the system tests did not pass: ${system_test}"
[ "${drill}" = success ] && exit 0
[ "${sign}" = skipped ] && [ "${drill}" = skipped ] && exit 0
die "signing ran, so every board's drill must pass: sign ${sign}, drill ${drill}"
