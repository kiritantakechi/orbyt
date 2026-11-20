#!/bin/sh
# ip-down of the emulated ISP's sessions (orbyt_tests.sandbox.isp): the session
# leaves the registry ip-up recorded it in. Its arguments are ip-up's.
set -eu
# shellcheck source=/dev/null # written by isp.configure
. "$6/isp.env"
: "${REGISTRY:?}"

rm -f "${REGISTRY}/${PPPD_PID:?}"
