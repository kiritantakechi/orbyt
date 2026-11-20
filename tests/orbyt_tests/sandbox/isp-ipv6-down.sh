#!/bin/sh
# ipv6-down of the emulated ISP's sessions (orbyt_tests.sandbox.isp): stop what
# ipv6-up started from the session's directory. Its arguments are ipv6-up's.
set -eu
# shellcheck source=/dev/null # written by isp.configure
. "$6/isp.env"
: "${SESSIONS:?}"

# pkill finds nothing (1) once both have gone on their own.
pkill -f -- "${SESSIONS}/${PPPD_PID:?}/" || [ "$?" -eq 1 ]
