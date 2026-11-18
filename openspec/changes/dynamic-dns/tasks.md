# Tasks

## 1. The stand-in and the tests (design D6, D7)

- [ ] 1.1 Add the stand-in for Cloudflare's API, `tests/wrt_tests/sandbox/cloudflare.py`: zones, records, `PATCH` of a record's content, the token check, the request log and the hold file; serve it as `api.cloudflare.com` among `wrt_tests.sandbox.internet.SERVERS` and start it with the sandbox's other servers (`wrt_tests.sandbox.net`); unit tests in `tests/unit/` against a local instance.

  Verify: the unit tests pass, the provider's four calls answered as Cloudflare answers them and a wrong token refused; `just check` passes.

- [ ] 1.2 Add `tests/services/test_dynamic_dns.py` with the scenarios of `services/dynamic-dns` (design D7), and the fixture that trusts the test CA, lets `cloudflare.com` through dnsmasq's rebind protection and configures the two services.

  Verify: `spec-coverage --change dynamic-dns` reports every scenario covered; run on the emulator before 2.x, the tests fail where the packages are missing.

- [ ] 1.3 Extend "Secrets on the device" in `tests/ops/test_config_push.py`: the private repository the test pushes holds the Cloudflare token and a DDNS service; the token is in no sampled command line and `/etc/config/ddns` is root's alone.

  Verify: the ops suite's test passes once 3.x is in; `just check` passes.

## 2. The premise (design D5)

- [ ] 2.1 On the emulator, with the packages installed and the patches not yet applied: change a running service's token, run `reload_config`, and show whether the updater keeps running on the old token (its process start time unchanged, the stand-in's log with the old token).

  Verify: the outcome recorded here; if the updater does restart, D5's patch goes and design.md says so.

## 3. The image (design D1 to D5)

- [ ] 3.1 Select `ddns-scripts`, `ddns-scripts-cloudflare` and `luci-app-ddns` in `config/services.seed`, and have `files/etc/uci-defaults/92-wrt-services` delete the package's example services on a fresh configuration.

  Verify: the R4S builds; the image holds the three packages, LuCI's Simplified Chinese strings for the page, and an `/etc/config/ddns` with no service on first boot.

- [ ] 3.2 Patch ddns-scripts' Cloudflare provider to pass curl its headers from a root-only file made just before each request and removed after it (`patches/packages/`, `Upstream-Status: Pending`, written up in `docs/patches.md`).

  Verify: the tests of the token's secrecy pass on the emulator; without the patch, "No process's arguments" fails.

- [ ] 3.3 Patch ddns-scripts' init script to declare `/etc/config/ddns` as its instances' file, if 2.1 showed the premise (`patches/packages/`, `Upstream-Status: Pending`, `docs/patches.md`).

  Verify: "A new token" passes on the emulator; without the patch it fails.

- [ ] 3.4 Add the secret `cloudflare.api_token` and `uci/ddns.uci.tmpl` (the two services, off) to `scripts/config-init.d`; describe DDNS in `docs/services.md` (records to create first, enabling the services) and the secret and template in `docs/ops.md`.

  Verify: `just config-init` on a scratch directory writes both, and a push of that repository passes its checks; `just check` passes.

## 4. Verification

- [ ] 4.1 Run the services and ops suites on the emulator with the image of 3.x, the Mac's load sampled.

  Verify: every test of 1.2 and 1.3 passes, and the suites' other tests with them.

- [ ] 4.2 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta specs, archive the change, merge it to main and push Codeberg first, then GitHub; then start acme-certificates.
