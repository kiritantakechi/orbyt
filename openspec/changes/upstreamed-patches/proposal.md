# Proposal

## Why

The bump of 2026-11-16 failed at the patch step: `patches/openwrt/0045-firewall4-update-to-Git-HEAD-2026-11-08.patch` did not apply, because OpenWrt had made the same update (dab12e766366). The failure said only "patch does not apply", the message of a patch that conflicts with upstream's work, so telling the two apart took reading upstream's history. They call for opposite actions: a conflict needs the patch refreshed, while a change upstream has made means dropping the patch. Upstream catches up with this project's patches in most bumps (three on 2026-11-09, two on 2026-11-16).

`docs/release-flow.md` also says a patch that no longer applies fails the `firmware` job. The `host-toolchain` job runs the patch step first, and fails first.

## What Changes

- **The patch step tells a patch whose change upstream has made.** When a patch does not apply, the step checks whether it applies in reverse: if it does, upstream's tree holds the patch's result already, and the message says so and that the patch can go. Otherwise the message stays as it is.
- **The release flow names the job a patch fails in:** `host-toolchain`, the first.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `release/upstream-bump`: a patch that fails because upstream made its change is named as such.

## Impact

- `scripts/lib/upstream.sh`: `series_commit()`.
- `tests/release/test_upstream_bump.py`: the new scenario's test.
- `docs/release-flow.md`, `docs/upstream-lock.md`.
- No change to the firmware or to the commit a series makes.
