#!/bin/sh
# download-key: print the download cache's key and the prefix of its keys, as key=<value> and prefix=<value>.
# Usage: scripts/download-key.sh >>"$GITHUB_OUTPUT"
# The download cache holds the sources the build downloads (release-integrity
# D6). Its key covers what names them: upstream.lock, whose trees name their
# packages' sources, and the makefiles of the feed, each by its path and content;
# the host stage and every board's restore and save it by the same key
# (tooling-hygiene D2).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"

cd "${REPO_DIR}"
sources=$(
	{
		sha256sum upstream.lock
		find feed -name Makefile -type f | LC_ALL=C sort | xargs sha256sum
	} | sha256sum
)
printf 'key=dl-%s\nprefix=dl-\n' "${sources%% *}"
