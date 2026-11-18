# orbyt-ab: the two slots on the boot disk (r4s-ab-rollback design D1, D4), for the
# A/B sysupgrade alone (/lib/upgrade/z-orbyt-ab.sh), whose second stage runs from a
# RAM root without ucode. Everything else reads these facts through the ucode
# module orbyt.ab (/usr/share/ucode/orbyt/ab.uc). POSIX sh, so no locals: every
# function keeps its variables under an orbyt_ prefix of its own.

# orbyt_ab_slot: print the running slot, a or b, as U-Boot passed it to the kernel.
orbyt_ab_slot() {
	read -r orbyt_cmdline </proc/cmdline
	for orbyt_arg in ${orbyt_cmdline}; do
		case "${orbyt_arg}" in
			orbyt.slot=a | orbyt.slot=b)
				echo "${orbyt_arg#orbyt.slot=}"
				return 0
				;;
			*) ;;
		esac
	done
	return 1
}

# orbyt_ab_other <slot>: print the other slot.
orbyt_ab_other() {
	case "$1" in
		a) echo b ;;
		*) echo a ;;
	esac
}

# orbyt_ab_partitions <slot>: print the slot's boot and root partition numbers.
orbyt_ab_partitions() {
	case "$1" in
		a) echo 1 2 ;;
		*) echo 3 4 ;;
	esac
}

# orbyt_ab_setenv <name> <value> [<name> <value> ...]: write U-Boot variables at once,
# and flush them to the card: a panic or watchdog reset does not wait for writeback.
orbyt_ab_setenv() {
	printf '%s %s\n' "$@" | fw_setenv -s - && sync
}
