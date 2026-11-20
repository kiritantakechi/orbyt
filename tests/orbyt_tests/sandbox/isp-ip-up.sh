#!/bin/sh
# ip-up of the emulated ISP's sessions (orbyt_tests.sandbox.isp): record the
# session for the tests, its PPP interface and the address the peer got, in a
# file named after its pppd. pppd runs it with the interface, tty, speed, local
# and remote address, and the ipparam: the ISP's directory, whose isp.env holds
# the rest.
set -eu
# shellcheck source=/dev/null # written by isp.configure
. "$6/isp.env"
: "${REGISTRY:?}"

printf '%s %s\n' "${IFNAME:?}" "${IPREMOTE:?}" >"${REGISTRY}/${PPPD_PID:?}.new"
mv "${REGISTRY}/${PPPD_PID}.new" "${REGISTRY}/${PPPD_PID}"
