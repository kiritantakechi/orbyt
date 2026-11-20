#!/bin/sh
# The containers module's podman commands at the same time, run on the router
# (test_containers.py; device-robustness D4, container-storage-probes D3).
# Usage: podman-at-once.sh round|clean <scratch> <root> <run root> <at once> <in a row>
#
# "round" starts <at once> commands at once, each running <in a row> of them in
# a row, on a scratch storage <root> whose run root does not exist yet, as the
# configured one after a boot. A concurrent command that creates the run root
# changes how its path resolves between podman's two resolutions of it, a
# window too short to hit by chance. So a symlink on the run root's path,
# <scratch>/link, keeps changing its target, swapped atomically (rename),
# between two names of one directory (a bind mount): the path resolves now to
# one name, now to the other, while every file under it stays the same.
# Commands in a row keep the starts and ends of some, which bind and unmount
# the storage's home, overlapping with the others' work through a round. The
# storage also probes some kernel features with mounts under its home when it
# is first asked about them, unless the run root records the answers, as it
# does not for the first commands after a boot: removing the records as they
# appear keeps every command probing. A round prints what the failed commands
# said, what stayed mounted ("left mounted: "), and failed=<count>.
#
# "clean" removes whatever a round left, as a round does before it starts.
set -u

mode=$1 scratch=$2 root=$3 runroot=$4 at_once=$5 in_a_row=$6

# What is mounted under the scratch storage: nothing, once every command has
# cleaned up after itself.
mounted() {
	grep -F " ${root}/" /proc/self/mountinfo
}

clean() {
	mounted | cut -d' ' -f5 | sort -r | xargs -rn1 umount -l
	# A round that ended early may have left the bind mount, or not.
	umount "${scratch}/b" 2>/dev/null || :
	rm -rf "${root}" "${scratch}" "${scratch}".*
}

round() {
	clean
	mkdir -p "${scratch}/a" "${scratch}/b" &&
		mount -o bind "${scratch}/a" "${scratch}/b" &&
		ln -s a "${scratch}/link" &&
		touch "${scratch}/busy" || exit
	ucode -e "import * as fs from 'fs';
		while (fs.access('${scratch}/busy'))
			for (let target in ['a', 'b']) {
				fs.symlink(target, '${scratch}/next');
				fs.rename('${scratch}/next', '${scratch}/link');
			}" &
	toggle=$!
	ucode -e "import * as fs from 'fs';
		while (fs.access('${scratch}/busy'))
			for (let feature in ['idmapped-lower-dir', 'volatile'])
				for (let found in ['true', 'false'])
					fs.unlink('${scratch}/a/runroot/overlay/' + feature + '-' + found);" &
	forget=$!
	pids=
	for i in $(seq "${at_once}"); do
		(
			for _ in $(seq "${in_a_row}"); do
				podman --root "${root}" --runroot "${runroot}" info >/dev/null || exit
			done
		) 2>"${scratch}.${i}" &
		pids="${pids} $!"
	done
	failed=0
	# shellcheck disable=SC2086 # pids is a space-separated list of numbers
	for pid in ${pids}; do
		wait "${pid}" || failed=$((failed + 1))
	done
	rm "${scratch}/busy"
	wait "${toggle}" "${forget}"
	umount "${scratch}/b"
	cat "${scratch}".*
	mounted | sed 's/^/left mounted: /'
	echo "failed=${failed}"
}

case "${mode}" in
	round) round ;;
	clean) clean ;;
	*)
		echo "usage: podman-at-once.sh round|clean <scratch> <root> <run root> <at once> <in a row>" >&2
		exit 2
		;;
esac
