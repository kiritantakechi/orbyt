# A/B sysupgrade (r4s-ab-rollback D6): the upgrade steps that the
# target's platform.sh hands to the slots by name (firmware-hygiene D1), as
# upstream's legacy_sdcard_* and emmc_* are handed theirs. Every name here is
# orbyt_ab_'s own, so the order sysupgrade reads /lib/upgrade/*.sh in does not
# matter. An upgrade writes only the slot that is not running, then makes it the
# trial slot.

# shellcheck source=../functions/orbyt-ab.sh
. /lib/functions/orbyt-ab.sh

# The second stage runs from a RAM root; take the U-Boot environment tools along.
RAMFS_COPY_BIN="${RAMFS_COPY_BIN:-} /usr/sbin/fw_printenv /usr/sbin/fw_setenv"

# orbyt_ab_members <image>: print the files of an upgrade image's tar, sorted, as
# the archive names them: <dir>/<member>.
orbyt_ab_members() {
	get_image "$1" | tar -tf - 2>/dev/null | grep -v '/$' | sort
}

# orbyt_ab_dir <image>: print the directory an upgrade image's members sit in
# (sysupgrade-<board>), when they are exactly CONTROL, kernel and root of one
# directory; the check and the write read the same names.
orbyt_ab_dir() {
	orbyt_listed=$(orbyt_ab_members "$1")
	orbyt_dir=${orbyt_listed%%/*}
	[ -n "${orbyt_dir}" ] &&
		[ "${orbyt_listed}" = "$(printf '%s/CONTROL\n%s/kernel\n%s/root' "${orbyt_dir}" "${orbyt_dir}" "${orbyt_dir}")" ] &&
		echo "${orbyt_dir}"
}

# orbyt_ab_member <image> <dir> <name>: write one member of an upgrade image to
# stdout; fails when the image cannot be read to the member's end.
orbyt_ab_member() {
	get_image "$1" | tar -xOf - "$2/$3"
}

# orbyt_ab_write <image> <dir> <name> <device>: write one member of an upgrade
# image to a device. pipefail: a member that cannot be read fails the write as a
# device that cannot be written does.
orbyt_ab_write() {
	(
		# shellcheck disable=SC3040 # POSIX.1-2024; busybox ash has it
		set -o pipefail
		orbyt_ab_member "$1" "$2" "$3" | dd of="$4" bs=1M conv=fsync
	)
}

# orbyt_ab_put_config <boot device>: put the configuration backup on the new
# slot's boot partition, where its preinit (79_move_config) picks it up.
orbyt_ab_put_config() {
	mount -o rw,noatime "/dev/$1" /mnt || return 1
	# shellcheck disable=SC2154 # set by sysupgrade
	cp -af "${UPGRADE_BACKUP}" "/mnt/${BACKUP_FILE}" && sync
	orbyt_copied=$?
	umount /mnt || return 1
	return "${orbyt_copied}"
}

# orbyt_ab_erofs_size <device>: print the size of the EROFS image the device starts
# with: blocks (superblock offset 36) shifted by blkszbits (offset 12).
orbyt_ab_erofs_size() {
	orbyt_bits=$(dd if="$1" bs=1 skip=1036 count=1 2>/dev/null | hexdump -e '1/1 "%u"')
	orbyt_blocks=$(dd if="$1" bs=4 skip=265 count=1 2>/dev/null | hexdump -e '1/4 "%u"')
	echo "$((orbyt_blocks << orbyt_bits))"
}

# orbyt_ab_check_image <image>: accept only a single-slot upgrade image, a tar of
# CONTROL, kernel (the boot partition) and root (EROFS), on a system running A/B
# that can write the U-Boot environment where its bootloader reads it: one
# whose bootloader named no environment has none configured (its preinit), and
# refuses before anything is written (trial-boot-resilience D3); and not while
# the running slot is on trial (trial-guards D3).
orbyt_ab_check_image() {
	if ! orbyt_ab_dir "$1" >/dev/null; then
		orbyt_listed=$(orbyt_ab_members "$1" | tr '\n' ' ') || orbyt_listed=
		echo "Not a single-slot upgrade image (members: ${orbyt_listed:-none})"
		return 1
	fi
	if ! orbyt_ab_slot >/dev/null; then
		echo "Not running from an A/B slot; flash the factory image instead"
		return 1
	fi
	if ! fw_printenv >/dev/null 2>&1; then
		echo "The bootloader names no U-Boot environment; flash the factory image instead"
		return 1
	fi
	# While the running slot is on trial, the other slot is the one a rollback
	# returns to (trial-guards D3). A trial slot that did not load, which U-Boot
	# fell back from within the power cycle, is not the running slot.
	orbyt_running=$(orbyt_ab_slot)
	# A variable that is not set is no trial.
	orbyt_trial=$(fw_printenv -n upgrade_available 2>/dev/null) || orbyt_trial=0
	orbyt_boot_slot=$(fw_printenv -n boot_slot 2>/dev/null) || orbyt_boot_slot=
	if [ "${orbyt_trial}" = 1 ] && [ "${orbyt_boot_slot}" = "${orbyt_running}" ]; then
		echo "Slot ${orbyt_running} is on trial: the other slot is the one a rollback returns to until the health check confirms ${orbyt_running}"
		return 1
	fi
}

# orbyt_ab_do_upgrade <image>: write the inactive slot, give it a fresh overlay
# and the configuration backup (sysupgrade's UPGRADE_BACKUP), and only once all
# of it is written, make it the slot U-Boot tries next, as a trial. Stage 2
# reboots whatever this returns: after a failure, into the running slot
# (device-integrity D2).
orbyt_ab_do_upgrade() {
	orbyt_dir=$(orbyt_ab_dir "$1") || {
		echo "Not a single-slot upgrade image"
		return 1
	}
	orbyt_running=$(orbyt_ab_slot) || {
		echo "Not running from an A/B slot"
		return 1
	}
	orbyt_target=$(orbyt_ab_other "${orbyt_running}")
	orbyt_partitions=$(orbyt_ab_partitions "${orbyt_target}")
	read -r orbyt_boot_part orbyt_root_part <<EOF
${orbyt_partitions}
EOF
	orbyt_boot_dev='' orbyt_root_dev=''
	if ! export_bootdevice ||
		! export_partdevice orbyt_boot_dev "${orbyt_boot_part}" ||
		! export_partdevice orbyt_root_dev "${orbyt_root_part}"; then
		echo "Unable to find the partitions of slot ${orbyt_target}"
		return 1
	fi

	v "Writing slot ${orbyt_target} to /dev/${orbyt_boot_dev} and /dev/${orbyt_root_dev}..."
	if ! orbyt_ab_write "$1" "${orbyt_dir}" kernel "/dev/${orbyt_boot_dev}" ||
		! orbyt_ab_write "$1" "${orbyt_dir}" root "/dev/${orbyt_root_dev}"; then
		echo "Writing slot ${orbyt_target} failed; slot ${orbyt_running} stays"
		return 1
	fi

	# fstools keeps the overlay after EROFS, rounded up to 64 KiB. Clearing the
	# start of the old one makes the new system format a fresh overlay.
	orbyt_overlay=$((($(orbyt_ab_erofs_size "/dev/${orbyt_root_dev}") + 65535) / 65536))
	if ! dd if=/dev/zero of="/dev/${orbyt_root_dev}" bs=64k seek="${orbyt_overlay}" count=16 conv=fsync; then
		echo "Clearing the overlay of slot ${orbyt_target} failed; slot ${orbyt_running} stays"
		return 1
	fi

	# The configuration before the switch: a power cut in between must not boot
	# the new slot without it.
	if [ -n "${UPGRADE_BACKUP:-}" ] && ! orbyt_ab_put_config "${orbyt_boot_dev}"; then
		echo "Copying the configuration to slot ${orbyt_target} failed; slot ${orbyt_running} stays"
		return 1
	fi

	orbyt_ab_setenv boot_slot "${orbyt_target}" upgrade_available 1 bootcount 0
}

# orbyt_ab_copy_config: nothing left to do. orbyt_ab_do_upgrade has put the
# configuration on the new slot already, before the switch.
orbyt_ab_copy_config() {
	:
}
