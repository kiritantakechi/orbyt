# Proposal

## Why

The router's WAN addresses change with every PPPoE session (the ISP hands out a new IPv4 address on each dial-in), so the services it offers from outside, WireGuard first, are reachable only by an address that no name follows. The maintainer's domains are at Cloudflare; the router should keep their records on its current addresses itself. The stock way to do that, ddns-scripts' Cloudflare provider, puts the API token on curl's command line, where every local process can read it, and a token or record changed through LuCI or a push takes effect only after a restart.

## What Changes

- **Dynamic DNS in the image**: ddns-scripts with its Cloudflare provider and LuCI's DDNS page (luci-app-ddns), for an A record from the WAN's IPv4 address and an AAAA record from its IPv6 address. The image starts with no DDNS service: the package's two example services go on a fresh configuration.
- **The API token through the config push only**: a new secret, `cloudflare.api_token`, in the private repository, and a DDNS template in its skeleton, off until the operator names the records. On the router the token lives in `/etc/config/ddns`, which root alone reads.
- **The token off every command line** (a patch to ddns-scripts' Cloudflare provider, meant for upstream): curl reads its request headers from a file only root reads, removed after each update, so the token appears in no process's arguments and in none of the commands ddns-scripts logs.
- **A changed configuration takes effect** (a patch to ddns-scripts' init script, meant for upstream): its instances depend on `/etc/config/ddns`, so a reload after a change restarts them, as LuCI's Save & Apply and the push both reload.
- **Records updated on a new address without waiting**: ddns-scripts' interface hotplug restarts a service when its interface comes up or its addresses change; the registered address is read from Cloudflare's API, not from DNS, which shows Cloudflare's proxy for a proxied record.

## Capabilities

### New Capabilities
- `services/dynamic-dns`: the router's WAN addresses kept in DNS at Cloudflare: the records it updates and when, the secrecy of its API token, changes taking effect, and the service in LuCI.

### Modified Capabilities
- `ops/config-push`: "Secrets stored encrypted" adds the Cloudflare API token to the secrets the private repository holds encrypted and the push keeps off command lines.

## Impact

- `config/services.seed`: ddns-scripts, ddns-scripts-cloudflare, luci-app-ddns (its Simplified Chinese strings follow LuCI's language setting).
- `patches/packages/`: two patches to ddns-scripts (the provider's headers from a file; the init script's instances on their configuration file), with their write-ups in `docs/patches.md`.
- `files/etc/uci-defaults/92-wrt-services`: the package's example services removed on a fresh configuration.
- `scripts/config-init.d/`: the secret `cloudflare.api_token` and `uci/ddns.uci.tmpl`.
- Tests: `tests/services/test_dynamic_dns.py` against a stand-in for Cloudflare's API on the emulated internet (`tests/wrt_tests/sandbox/cloudflare.py`, served as `api.cloudflare.com` with the sandbox's test CA); the config push's secrets test extended to the token.
- `docs/services.md` (DDNS) and `docs/ops.md` (the secret and the template).
- CI: the seed's new packages move the host-toolchain key, so the branch's first run and main's first run after the merge each build the host stage anew (about two hours each), as luci-theme-wrt's did.
