#!/bin/sh
# ipv6-up of the emulated ISP's sessions (orbyt_tests.sandbox.isp): SLAAC on the
# link (radvd) and a delegated prefix (kea-dhcp6), both run from the session's
# directory, named after its pppd. pppd runs it with the interface, tty, speed,
# local and remote link-local address, and the ipparam: the ISP's directory,
# whose isp.env holds the rest.
set -eu
# shellcheck source=/dev/null # written by isp.configure
. "$6/isp.env"
: "${SESSIONS:?}" "${WAN_GATEWAY:?}" "${WAN_PREFIX:?}" "${DELEGATED_PREFIX:?}" "${DELEGATED_NETWORK:?}" "${DELEGATED_LENGTH:?}" "${RESOLVER6:?}"

session="${SESSIONS}/${PPPD_PID:?}"
mkdir -p "${session}"
# pppd sets the link-local address with the peer's; kea would bind to the
# peer's, so the session's own becomes a plain one.
ip -6 addr flush dev "${IFNAME:?}" scope link
ip -6 addr add "$4/64" dev "${IFNAME}" nodad
# The newest session owns the prefixes: the previous one may still be going
# down (its peer left without a word, as after a snapshot jump).
ip -6 addr add "${WAN_GATEWAY}/64" dev "${IFNAME}" nodad
ip -6 route replace "${WAN_PREFIX}" dev "${IFNAME}"
ip -6 route replace "${DELEGATED_PREFIX}" dev "${IFNAME}"
cat >"${session}/radvd.conf" <<CONF
interface ${IFNAME} {
	AdvSendAdvert on;
	AdvManagedFlag on;
	AdvOtherConfigFlag on;
	MinRtrAdvInterval 3;
	MaxRtrAdvInterval 10;
	prefix ${WAN_PREFIX} { AdvOnLink on; AdvAutonomous on; };
	RDNSS ${RESOLVER6} {};
};
CONF
# ipv6-up runs as IPv6CP comes up, possibly before the link-local address is
# usable: kea keeps trying to bind for a while. Its server DUID is fixed, and
# kept in memory, as its leases are, instead of in /var/lib/kea.
cat >"${session}/kea.json" <<CONF
{
	"Dhcp6": {
		"interfaces-config": {
			"interfaces": ["${IFNAME}"],
			"service-sockets-max-retries": 20,
			"service-sockets-retry-wait-time": 500
		},
		"lease-database": {"type": "memfile", "persist": false},
		"server-id": {
			"type": "LL",
			"htype": 1,
			"identifier": "020000000001",
			"persist": false
		},
		"renew-timer": 900,
		"rebind-timer": 1800,
		"preferred-lifetime": 3600,
		"valid-lifetime": 7200,
		"option-data": [{"name": "dns-servers", "data": "${RESOLVER6}"}],
		"subnet6": [
			{
				"id": 1,
				"subnet": "${WAN_PREFIX}",
				"interface": "${IFNAME}",
				"pd-pools": [
					{
						"prefix": "${DELEGATED_NETWORK}",
						"prefix-len": ${DELEGATED_LENGTH},
						"delegated-len": ${DELEGATED_LENGTH}
					}
				]
			}
		],
		"loggers": [
			{
				"name": "kea-dhcp6",
				"output-options": [{"output": "stdout"}],
				"severity": "INFO"
			}
		]
	}
}
CONF
setsid -f radvd -n -m stderr -C "${session}/radvd.conf" -p "${session}/radvd.pid" \
	>"${session}/radvd.log" 2>&1 </dev/null
KEA_PIDFILE_DIR="${session}" KEA_LOCKFILE_DIR="${session}" \
	setsid -f kea-dhcp6 -c "${session}/kea.json" >"${session}/kea.log" 2>&1 </dev/null
