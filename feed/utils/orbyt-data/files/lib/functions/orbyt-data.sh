# The USB data disk (r4s-services D1): btrfs, its top level mounted by UUID at
# /mnt/data, and the subvolumes at fixed paths in it. Services that keep their
# data there start only while it is mounted. Without the disk, the mount point is
# a directory of a small filesystem in RAM (/lib/preinit/86_orbyt_data_mountpoint).
# shellcheck shell=sh disable=SC2034 # for the scripts that source this

ORBYT_DATA=/mnt/data
ORBYT_DATA_LABEL=orbytdata
ORBYT_DATA_SUBVOLUMES="containers downloads shares logs"
ORBYT_DATA_OPTIONS=compress=zstd:3,noatime,space_cache=v2
# The data disk's line in /proc/mounts.
ORBYT_DATA_MOUNT=" ${ORBYT_DATA} btrfs "

# orbyt_data_mounted: whether the data disk is mounted at /mnt/data.
orbyt_data_mounted() {
	grep -q "${ORBYT_DATA_MOUNT}" /proc/mounts
}
