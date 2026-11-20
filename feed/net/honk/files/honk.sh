# honk: what honk's datapath holds, for the scripts that depend on it
# (firmware-hygiene D3). POSIX sh, so no locals: the variables keep a honk_
# prefix.
# shellcheck shell=sh

# honk_holds <device>: whether honk's LAN programs sit on the device, on ingress
# and egress: lan_<direction>_l2 on a bridge, _l3 on a device without link layer.
honk_holds() {
	honk_programs=$(bpftool net show dev "$1" 2>/dev/null) || return 1
	for honk_direction in ingress egress; do
		echo "${honk_programs}" |
			grep -q -E " tcx/${honk_direction} lan_${honk_direction}_l[23] " || return 1
	done
}
