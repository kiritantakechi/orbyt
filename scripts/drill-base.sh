#!/bin/sh
# drill-base: prepare the image a board's upgrade drill starts from (r4s-release-pipeline D5, board-model D10).
# Usage: scripts/drill-base.sh <board>
# out/<board>/drill-base gets the board's factory image of the latest stable
# release on GitHub, the one the board's manifest in that release names, checked
# against it. While no stable release carries the board, before the first
# release or when the board is new, it gets this build's own (out/<board>/ci).
# Either comes with this build's emulator firmware, and with the manifest of
# the build the image comes from, profile drill-base, its files those two: as
# emu-prepare reads a build, the drill boots it and upgrades to the signed
# candidate. Only GitHub's answer that there is no stable release counts as none:
# any other failure to look it up stops here, rather than let the drill start
# from the candidate itself.
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"
use boards github manifest

board=${1:-}

workdir_tree >/dev/null
[ -n "${board}" ] || die "usage: drill-base <board>"
device=$(board_field "${board}" .device)
ci="${ORBYT_WORKDIR}/out/${board}/ci"
base="${ORBYT_WORKDIR}/out/${board}/drill-base"
repository=$(github_repository)
[ -f "${ci}/manifest.json" ] || die "no build outputs in ${ci}"

scratch_dir orbyt-drill-base
rm -rf "${base}"
mkdir -p "${base}/targets"

if gh api "repos/${repository}/releases/latest" >"${scratch}/release.json" 2>"${scratch}/error"; then
	tag=$(jq -r .tag_name "${scratch}/release.json")
else
	error=$(cat "${scratch}/error")
	case "${error}" in
		*"HTTP 404"*) tag= ;;
		*) die "cannot look up the latest release of ${repository}: ${error}" ;;
	esac
fi
manifest="${device}-manifest.json"
if [ -n "${tag}" ] &&
	jq -e --arg name "${manifest}" 'any(.assets[]; .name == $name)' "${scratch}/release.json" >/dev/null; then
	gh release download "${tag}" --repo "${repository}" --pattern "${manifest}" --dir "${scratch}" ||
		die "cannot download ${manifest} of ${tag}"
	manifest_files_check "${scratch}/${manifest}"
	manifest_checksums "${scratch}/${manifest}" '^targets/[^/]+-factory\.img\.gz$' >"${scratch}/factory.sha256"
	images=$(wc -l <"${scratch}/factory.sha256")
	[ "${images}" -eq 1 ] || die "${manifest} of ${tag} does not name one factory image"
	read -r _ image <"${scratch}/factory.sha256"
	gh release download "${tag}" --repo "${repository}" --pattern "${image#targets/}" \
		--dir "${base}/targets" || die "cannot download ${image#targets/} of ${tag}"
	(cd "${base}" && sha256sum --check --quiet --strict "${scratch}/factory.sha256") ||
		die "${image#targets/} of ${tag} does not match ${manifest}"
	built="${scratch}/${manifest}"
	info "drill base: ${tag}, the latest stable release"
else
	if [ -n "${tag}" ]; then
		reason="${tag}, the latest stable release, carries no ${board}"
	else
		reason="no stable release yet"
	fi
	cp "${ci}"/targets/*-factory.img.gz "${base}/targets/"
	built="${ci}/manifest.json"
	info "drill base: this build (${reason})"
fi
cp "${ci}/u-boot-qemu.bin" "${base}/"
jq '. + {profile: "drill-base"}' "${built}" | manifest_write "${base}"
