#!/bin/sh
# config-push: push the private configuration to a router (r4s-release-pipeline D6).
# Usage: scripts/config-push.sh <host> [--identity <key>]
# Reads $ORBYT_CONFIG_DIR, config-init's repository. Its secrets are decrypted
# with sops into a temporary directory, which goes when the push ends; the uci
# templates are filled in from them. Each service's new files:
#   network, ... (one per uci/<config>.uci.tmpl)   uci batches
#   honk       honk/*.dae.enc, without lan_interface, wan_interface or data_dir
#              (the firmware's), its native API in token mode alone and never
#              writing the configuration (honk-datapath D8)
#   tailscale  the auth key and the login's options (secrets: tailscale.auth_key,
#              tailscale.login_server)
#   smb        the share users (secrets: smb.users)
#   pods       pods/*.yaml and their .options
# Everything is validated before the router changes: honk's configuration by
# honk's own check of the entry its service would run, on the router, and every
# uci batch on a copy of its configuration. Then each service whose files
# changed since its last push (a hash on the router) is written, reloaded and
# checked, and put back as it was if it does not come back, which fails the
# push. SSH authenticates with a key only (--identity, or the agent's); a
# password is never tried. The files are root's alone here and on the router,
# and the router's copy goes however the push ends (device-integrity D8).
set -eu
# shellcheck source=scripts/lib/core.sh
. "$(dirname -- "$0")/lib/core.sh"
umask 077

usage() {
	die "usage: config-push <host> [--identity <key>]"
}

[ "$#" -ge 1 ] || usage
host=$1
shift
identity=
case "$#:${1:-}" in
	0:) ;;
	2:--identity) identity=$2 ;;
	*) usage ;;
esac
config=${ORBYT_CONFIG_DIR:-}
[ -n "${config}" ] && [ -d "${config}" ] || die "ORBYT_CONFIG_DIR does not name the configuration repository"
device="$(dirname -- "$0")/config-push.d/device.uc"

# router <command>...: run a command on the router, over ssh authenticated by a
# key alone. A function rather than "$@": the exit trap runs where exit was
# called, as in die, whose "$@" is its message.
router() {
	set -- -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
		-o PreferredAuthentications=publickey -o ConnectTimeout=10 "root@${host}" "$@"
	[ -z "${identity}" ] || set -- -o IdentitiesOnly=yes -i "${identity}" "$@"
	ssh "$@"
}

work=$(mktemp -d "${TMPDIR:-/tmp}/orbyt-push.XXXXXX")
# The router's copy once uploaded, then the local one, however the push ends.
uploaded=0
trap '[ "${uploaded}" = 0 ] || router "rm -rf /tmp/orbyt-push" || true; rm -rf "${work}"' EXIT
trap 'exit 1' INT TERM
new="${work}/new"
mkdir -p "${new}"

sops decrypt --output-type json "${config}/secrets/secrets.enc.yaml" >"${work}/secrets.json" ||
	die "cannot decrypt the secrets (is the age key in \$SOPS_AGE_KEY_FILE?)"

# honk replaced dae, and its files moved with it (honk-datapath D5): a
# repository still in dae's layout would push no proxy configuration at all.
[ ! -e "${config}/dae" ] ||
	die "the proxy's files are honk's now: run 'git mv dae honk' in ${config} and commit"
for encrypted in "${config}"/honk/*.dae.enc; do
	[ -e "${encrypted}" ] || continue
	mkdir -p "${new}/honk"
	name=${encrypted##*/}
	sops decrypt --input-type binary --output-type binary "${encrypted}" >"${new}/honk/${name%.enc}" ||
		die "cannot decrypt ${name}"
done
if [ -d "${new}/honk" ]; then
	if grep -n -E '^[[:space:]]*(lan_interface|wan_interface|data_dir)[[:space:]]*:' "${new}"/honk/*.dae >&2; then
		die "honk's lan_interface, wan_interface and data_dir are the firmware's (honk-datapath D4): remove them"
	fi
	# The native API's settings, key=value, across the files: its blocks are the
	# ones named native_api, comments go and quotes come off the values, and its
	# booleans, which honk takes as true, yes, 1 or on and false, no, 0 or off in
	# any case, are lowercased. Whichever file honk would take a setting from, a
	# forbidden value anywhere is refused. The router's honk turns password
	# login, anonymous loopback and configuration writes off whatever the files
	# say (the firmware's settings, included last); refusing them here says so.
	awk '
		{ sub(/(^|[[:space:]])#.*/, "") }
		/^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\{[[:space:]]*$/ {
			name = $0; gsub(/[[:space:]{]/, "", name); stack[++depth] = name; next
		}
		/^[[:space:]]*}[[:space:]]*$/ { if (depth) depth--; next }
		depth && stack[depth] == "native_api" && match($0, /^[[:space:]]*[A-Za-z_]+[[:space:]]*:/) {
			key = $0; sub(/:.*/, "", key); gsub(/[[:space:]]/, "", key)
			value = $0; sub(/^[^:]*:[[:space:]]*/, "", value); sub(/[[:space:]]+$/, "", value)
			gsub(/^["\047]|["\047]$/, "", value)
			if (key ~ /^(enabled|password_auth|allow_anonymous_loopback|config_write)$/)
				value = tolower(value)
			print key "=" value
		}
	' "${new}"/honk/*.dae >"${work}/native-api"
	# The booleans some file sets in a spelling other than false's, by name.
	on=$(grep -E '^(enabled|password_auth|allow_anonymous_loopback|config_write)=' "${work}/native-api" |
		grep -Evx '[a-z_]+=(false|no|0|off)' | cut -d= -f1 | sort -u | tr '\n' ' ')
	for key in password_auth allow_anonymous_loopback; do
		case " ${on}" in
			*" ${key} "*) die "honk's native API needs a token (secret), not ${key}: password login lets its first visitor create the administrator" ;;
			*) ;;
		esac
	done
	case " ${on}" in
		*" config_write "*) die "honk's native API: configuration writes stay off, as the configuration's canonical copy is this repository (honk-datapath D8)" ;;
		*) ;;
	esac
	! grep -Eq '^secret=[[:space:]]*$' "${work}/native-api" ||
		die "honk's native API: its secret is blank; set a token or remove the setting"
	case " ${on}" in
		*" enabled "*) grep -q '^secret=' "${work}/native-api" || die "honk's native API needs a token: set its secret" ;;
		*) ;;
	esac
fi

# The uci templates: comments and blank lines go, and @path@ is the secret at
# that path, quoted for uci.
for template in "${config}"/uci/*.uci.tmpl; do
	[ -e "${template}" ] || continue
	name=${template##*/}
	name=${name%.uci.tmpl}
	mkdir -p "${new}/${name}"
	jq -r -n --rawfile template "${template}" --slurpfile secrets "${work}/secrets.json" \
		--arg quote "'" --arg quoted "'\\''" '
		$template | split("\n") | map(select(test("^\\s*(#|$)") | not)) | join("\n")
		| gsub("@(?<path>[a-z0-9_.]+)@";
			.path as $path | $secrets[0] | getpath($path | split("."))
			| if . == null then error("no secret \($path)") else tostring end
			| gsub($quote; $quoted))' >"${new}/${name}/${name}.uci" ||
		die "cannot fill in ${template##*/}"
done

# The auth key in a file of its own, which tailscale reads (--auth-key=file:):
# never on a command line.
auth_key=$(jq -r '.tailscale.auth_key // ""' "${work}/secrets.json")
if [ -n "${auth_key}" ]; then
	mkdir -p "${new}/tailscale"
	printf '%s\n' "${auth_key}" >"${new}/tailscale/auth_key"
	jq -r '(if (.tailscale.login_server // "") != "" then "--login-server=\(.tailscale.login_server) " else "" end)
		+ "--advertise-routes=10.0.0.0/24 --accept-dns=false"' "${work}/secrets.json" \
		>"${new}/tailscale/options"
fi
users=$(jq -r '.smb.users // [] | .[] | "\(.name) \(.password)"' "${work}/secrets.json")
if [ -n "${users}" ]; then
	mkdir -p "${new}/smb"
	printf '%s\n' "${users}" >"${new}/smb/users"
fi
for pod in "${config}"/pods/*.yaml "${config}"/pods/*.options; do
	[ -e "${pod}" ] || continue
	mkdir -p "${new}/pods"
	cp "${pod}" "${new}/pods/"
done

# A hash of each service's files: what the router compares with its last push.
# The names in one order wherever the push runs, whatever they hold.
for service in "${new}"/*/; do
	service=${service%/}
	sums=$(cd "${service}" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum) ||
		die "cannot hash the files of ${service##*/}"
	sum=$(printf '%s\n' "${sums}" | sha256sum)
	printf '%s\n' "${sum%% *}" >"${service}.sha256"
done

uploaded=1
# shellcheck disable=SC2310 # router's status is ssh's alone
tar -C "${new}" -cf - . | router 'umask 077 && rm -rf /tmp/orbyt-push && mkdir -p /tmp/orbyt-push/new &&
	tar -xf - -C /tmp/orbyt-push/new' ||
	die "cannot log in to ${host} with a key"
# shellcheck disable=SC2310 # router's status is ssh's alone
router ucode - validate <"${device}" ||
	die "the configuration does not validate; ${host} is unchanged"
info "the configuration validates"

router ucode - hashes <"${device}" >"${work}/pushed"
status=0
for service in "${new}"/*/; do
	service=${service%/}
	name=${service##*/}
	sum=$(cat "${service}.sha256")
	if grep -qx "${name} ${sum}" "${work}/pushed"; then
		info "${name}: unchanged"
		continue
	fi
	# shellcheck disable=SC2310 # router's status is ssh's alone
	if router ucode - apply "${name}" <"${device}"; then
		info "${name}: pushed"
	else
		status=1
	fi
done
[ "${status}" -eq 0 ] || die "a service did not come back with its new configuration and was put back"
info "pushed to ${host}"
