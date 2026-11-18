# Design

## Context

- ddns-scripts 2.8.5 (the packages feed) runs one updater per enabled `service` section of `/etc/config/ddns` under procd (`dynamic_dns_updater.sh -S <section>`, with a reload trigger on `ddns`). Its Cloudflare provider, `update_cloudflare_com_v4.sh`, is sourced by the updater and builds curl's command line as a string: with an API token (`username` set to `Bearer`), the header `Authorization: Bearer <token>` is an argument of curl, readable in `/proc/<pid>/cmdline` by every local process while the request runs. At log level 7 the provider writes each command line to the service's log; `write_log` masks the password in the log file and sends level 7 to no syslog.
- The provider only updates records that exist: it looks up the zone by name and the record by name and type, then patches its `content`. With `use_api_check` set it reads the address a record holds from the API, which shows the record's own address where DNS shows Cloudflare's proxy.
- The package's hotplug script starts a service again on `ifup` of its interface and on `ifupdate` with new addresses; its check interval is at least five minutes.
- `/etc/config/ddns` is installed with mode 0600, and the package ships two example services, disabled, with placeholder credentials.
- A procd reload restarts an instance only when its definition changed; the updater's definition is its command line, which names the section alone, so a changed token or record leaves running updaters on their old configuration (to be shown on the emulator first, task 2.1).
- The config push writes a uci configuration from `uci/<config>.uci.tmpl` in the private repository, `@path@` filled from the encrypted secrets, and reloads with `reload_config` unless the service needs more (`scripts/config-push.d/device.uc`). Its secrets test samples every command line on the router during a push (`tests/ops/test_config_push.py`).
- The emulated internet serves its services over HTTPS with the sandbox's test CA, named in a hosts file the ISP's resolver answers from; the Releases stand-in (`wrt_tests.sandbox.releases`) is the pattern. A redial hands the router the ISP pool's next IPv4 address; its IPv6 address comes from SLAAC on a fixed prefix and stays.

## Goals / Non-Goals

**Goals:**
- An A and an AAAA record at Cloudflare that follow the WAN's addresses, updated as the address changes.
- The API token readable by root alone and absent from every command line and log.
- Changes from LuCI or the push effective on reload.

**Non-Goals:**
- Providers other than Cloudflare, and records of hosts on the LAN.
- Creating records or zones: the operator creates the records once, at any address.
- The token outside uci (a file of its own, as Tailscale's key): LuCI's page edits the uci option, and the file is root's already.

## Decisions

### D1. The packages

`config/services.seed` selects `ddns-scripts`, `ddns-scripts-cloudflare` (which brings curl) and `luci-app-ddns`; LuCI's language setting brings the page's Simplified Chinese strings. The image keeps the package's defaults otherwise.

### D2. Two services, off until the operator names them

The private repository's skeleton (`scripts/config-init.d`) gains the secret `cloudflare.api_token` and `uci/ddns.uci.tmpl`: a service `wan4` (A, `interface` and `ip_network` `wan`) and a service `wan6` (AAAA, `use_ipv6` 1, `interface` and `ip_network` `wan6`), each `service_name` `cloudflare.com-v4`, `username` `Bearer`, `password` `@cloudflare.api_token@`, `use_api_check` 1, `domain` a placeholder `host@example.com` and `enabled` 0: the operator sets the domain and enables them. On a fresh configuration, `92-wrt-services` deletes the package's two example services, so that LuCI's page lists only what was pushed or entered.

Alternatives considered:
- One service per record type found by the address: ddns-scripts takes one record type per service.
- Example services kept: their placeholder credentials and a provider the image does not ship confuse the page.

### D3. The token in `/etc/config/ddns`, root's alone

The token stays a uci option, where LuCI's page and the push both write it. The package installs the file 0600, and uci's commit writes a new file the same way, so it stays root's alone; a test holds that after a push-like batch and a commit.

### D4. curl's headers from a file (ddns-scripts patch)

The provider writes its request headers (the token's `Authorization` or the global key's `X-Auth-Email` and `X-Auth-Key`, and `Content-Type`) to `<ddns_rundir>/<section>.hdr` with umask 077 just before each request, passes `--header @<file>` (curl reads headers from a file since 7.55), and removes it after: the file exists while curl runs, root's alone, on the run directory's tmpfs. The command line the provider logs names the file. The patch is in `patches/packages/`, `Upstream-Status: Pending`, written up in `docs/patches.md`.

Alternatives considered:
- `--config` with a curl configuration file: the same effect with a second file format; `--header @file` is the one curl documents for headers.
- The token in the environment: readable in `/proc/<pid>/environ` by root only, but curl takes no header from its environment.

### D5. The updaters depend on their configuration (ddns-scripts patch)

The init script sets `procd_set_param file /etc/config/ddns` on each instance, so procd compares the file's checksum at a reload and restarts the instances when it changed: a token or a record saved in LuCI or pushed takes effect, and the push's default reload needs no case of its own. Every updater restarts on any change; a restart reads the record and writes nothing when it is current (D2's `use_api_check`).

Alternatives considered:
- A restart for ddns in `device.uc`: the push alone would be fixed, not LuCI's Save & Apply.
- A checksum of the section's own options per instance (`procd_set_param data`): restarts only the changed section, at the cost of serializing the section in shell; the whole file is the idiom of the packages feed.

### D6. A stand-in for Cloudflare's API

`wrt_tests.sandbox.cloudflare` serves `https://api.cloudflare.com/client/v4` on the emulated internet (a new server among `wrt_tests.sandbox.internet.SERVERS`, its certificate from the sandbox's CA): zones by name, records by name and type, a record by id, and `PATCH` of a record's `content`, as the provider calls them. A JSON state file holds the token it accepts, the zones and the records; a request with another token gets Cloudflare's error with `"success": false`. Every request is appended to a log (method, path, whether the token matched, body). A hold file, while it exists, keeps each response waiting, so that a test sees a request under way.

The router resolves the name through the ISP's resolver; dnsmasq's rebind protection holds back its documentation-range address as private, so the tests' fixture lets `cloudflare.com` through, as `internet_zone` lets `example.net` through, and trusts the test CA (`trusted_ca`).

### D7. Tests and their evidence

`tests/services/test_dynamic_dns.py`, the services suite, configures the two services with a uci batch as the push writes them (the push itself is ops/config-push's test):
- Records after dialing in: both records hold the WAN's addresses (`ubus` network status).
- A new address after a redial: the A record holds the new address within a minute.
- A record already current: a restart reads the record and sends no `PATCH`.
- Readable by root alone: `/etc/config/ddns` is root's, mode 0600, after the batch's commit.
- No process's arguments: with the stand-in holding its response, no `/proc/*/cmdline` holds the token, and the held request carried it.
- Not in the logs: with the service's log at its most detailed (`use_logfile` 1, updates logged at level 7), neither `logread` nor the log file holds the token.
- A new token: the token is changed, `reload_config` run, and the next requests carry the new one.
- The services' state: `ubus call luci.ddns get_services_status` lists both services, the enabled one with its record's address.

`tests/ops/test_config_push.py`'s "Secrets on the device" pushes a DDNS service too: the token is in no sampled command line, and `/etc/config/ddns` is root's alone.

## Risks / Trade-offs

- [The record does not exist at Cloudflare] → The provider logs that it found no record and the service retries; `docs/services.md` says to create the records first.
- [Cloudflare changes its API] → The stand-in follows today's v4 API; the provider is upstream's, and a bump brings its changes.
- [A patch that upstream changes under it] → Both patches are small and stated in `docs/patches.md`; the series stops at a patch that does not apply, named.
- [Every updater restarts on any change of the file] → Each restart costs one API read per service.
- [The seed's packages move the toolchain key] → The branch's first run and main's first run after the merge build the host stage anew, about two hours each.
