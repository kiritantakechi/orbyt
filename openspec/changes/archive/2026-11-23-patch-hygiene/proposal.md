# Proposal

## Why

On 2026-11-20 the maintainer asked for the project's band-aids to be replaced by fixes at their causes. A review of the patch series found patches that fix a symptom or the wrong hook, patches that rewrite each other's lines, and patches that bundle several faults. The worst: qosify's init configures the daemon from `service_running`, the `running` action, which procd runs after a start and a respawn but every status query runs as well, so that rpcd's list of the services (LuCI's Startup page) sends qosify its whole configuration again, with reset; and patch 0021 edits every package's `ltmain.sh` with `sed`, which build/upstream-pinning forbids.

## What Changes

- **qosify configured on its object's registration**: procd passes `ubus.object.add` to its service triggers, and qosify's init reloads on its daemon's registration, at boot, start and respawn alike; a status query no longer configures it. The background wait in `service_running` goes.
- **One fault per patch**: 0035's three `procd.sh` fixes become patches of their own; fstools' 0036 and 0044 become one blockd change; 0009 folds into 0038; packages/0002 splits into its three changes. The patched trees stay byte for byte the same.
- **0021's `sed` goes**: the sanitizers' options reach the links without editing any package's files.
- **0012 as an exclusion**, if it holds: the modules pass's freshness ignores what the image pass writes, instead of refreshing a stamp.
- **The write-ups alike**: every entry in docs/patches.md has the same four sections, in order, grouped by where its patch lives and in its files' order, checked by a test.
- **daeuniverse/0003** depends on BusyBox's `timeout` applet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network/qos`: qosify is configured whenever its daemon comes up, with no configuration change and no wait at boot.
- `build/upstream-pinning`: one fault or feature per patch, no patch rewriting another's lines, every write-up with the same sections.

## Impact

- `patches/openwrt/` (0006, 0009, 0021, 0035, 0036, 0038, 0040, 0044, a procd patch, the `ubsan` profile's flags), `patches/packages/0002`, `patches/daeuniverse/0003`, `docs/patches.md`.
- Tests: `network/test_qos.py` (boot and respawn), `build/test_upstream_pinning.py` (the write-ups' sections).
- Rebuilt packages: procd and qosify; the `ubsan` profile's tree for D3.
