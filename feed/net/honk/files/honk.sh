# honk: what honk's datapath holds, for the scripts that depend on it
# (firmware-hygiene D3), and honk's service cgroup, which its instance sets up
# and its init pins anew (firmware-hygiene D4). POSIX sh, so no locals: the
# variables keep a honk_ prefix.
# shellcheck shell=sh

# procd runs honk's instance in services/honk/honk, below this service cgroup.
HONK_CGROUP=/sys/fs/cgroup/services/honk

# honk_holds <device>: whether honk's LAN programs sit on the device, on ingress
# and egress: lan_<direction>_l2 on a bridge, _l3 on a device without link layer.
honk_holds() {
	honk_programs=$(bpftool net show dev "$1" 2>/dev/null) || return 1
	for honk_direction in ingress egress; do
		echo "${honk_programs}" |
			grep -q -E " tcx/${honk_direction} lan_${honk_direction}_l[23] " || return 1
	done
}

# honk_big_cores: the CPUs of the highest capacity, which are the big cores of a
# big.LITTLE SoC, as a CPU list; empty where the kernel reports no capacities
# (board-model D6).
honk_big_cores() {
	honk_highest=0
	honk_cores=
	for honk_file in /sys/devices/system/cpu/cpu[0-9]*/cpu_capacity; do
		[ -r "${honk_file}" ] || continue
		honk_capacity=$(cat "${honk_file}")
		honk_cpu=${honk_file%/cpu_capacity}
		honk_cpu=${honk_cpu##*/cpu}
		if [ "${honk_capacity}" -gt "${honk_highest}" ]; then
			honk_highest=${honk_capacity}
			honk_cores=${honk_cpu}
		elif [ "${honk_capacity}" -eq "${honk_highest}" ]; then
			honk_cores="${honk_cores},${honk_cpu}"
		fi
	done
	echo "${honk_cores}"
}

# honk_enable_controller <controller> <cgroup>...: the controller enabled for
# the children of each cgroup, where the kernel has it.
honk_enable_controller() {
	honk_controller=$1
	shift
	grep -qsw "${honk_controller}" /sys/fs/cgroup/cgroup.controllers || return 0
	for honk_parent in "$@"; do
		echo "+${honk_controller}" >"${honk_parent}/cgroup.subtree_control" ||
			logger -t honk "cannot enable the ${honk_controller} controller in ${honk_parent}"
	done
}

# honk_pin <cpu_pinning>: honk's cgroup on the big cores while cpu_pinning is 1,
# on every CPU otherwise. The cpuset holds every task of the cgroup at once, so a
# running honk moves without a restart.
honk_pin() {
	honk_cores=
	[ "$1" = 0 ] || honk_cores=$(honk_big_cores)
	if [ ! -e "${HONK_CGROUP}/cpuset.cpus" ]; then
		[ -z "${honk_cores}" ] || logger -t honk "no cpuset controller: honk is not pinned"
		return 0
	fi
	# Unpinned, honk has every CPU its parent has: the kernel keeps a cgroup
	# with tasks from going back to an empty cpuset (ENOSPC).
	[ -n "${honk_cores}" ] || honk_cores=$(cat "${HONK_CGROUP%/*}/cpuset.cpus.effective")
	echo "${honk_cores}" >"${HONK_CGROUP}/cpuset.cpus" ||
		logger -t honk "cannot give honk the CPUs ${honk_cores}"
}

# honk_setup_cgroup <cpu_pinning>: honk's service cgroup set up: the
# controllers honk needs, memory down to its instance, whose files honk's
# telemetry reads once, at startup, and cpuset for its own cgroup, which pins
# it (honk_pin).
honk_setup_cgroup() {
	honk_enable_controller memory /sys/fs/cgroup /sys/fs/cgroup/services "${HONK_CGROUP}"
	honk_enable_controller cpuset /sys/fs/cgroup /sys/fs/cgroup/services
	honk_pin "$1"
}
