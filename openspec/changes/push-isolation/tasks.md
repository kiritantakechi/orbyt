# Tasks

## 1. The tests (design D4)

- [x] 1.1 Add the tests of "A configuration that validates", "Uncommitted change to a pushed package" and "Uncommitted change to another package" to `tests/ops/test_config_push.py`.

  Verify: `spec-coverage --change push-isolation` reports the three covered; on the emulator, before 2.1, all three fail: the dry run leaves the network batch's changes uncommitted, the push takes the uncommitted change to `network` along, and it commits `system`'s.
  Result (2026-11-17): all three covered. On the emulated R4S with the device side before 2.1, the test of another package's change failed (`system`'s change committed by the push). The other two passed in the first red run, for want of a change to make: uci records nothing for a value an option already holds, and after the fixture's push the network batch's values were the router's. With the router's WireGuard key changed and committed first, as a LuCI change since the push would, both failed as the task names: the dry run left `network.wg0.private_key` uncommitted in `/tmp/.uci`, and the push went ahead beside the uncommitted change to `network`. The proposal and design D4 now say which changes the old dry run left behind.

## 2. The device side (design D1, D2, D3)

- [x] 2.1 Change `scripts/config-push.d/device.uc`: `validate` runs each service's batches on its own copy with its own change directory, and refuses beside uncommitted changes to the packages they change; `write` runs them with the push's change directory, commits package by package and removes the directory; describe it in `docs/ops.md`, steps 2 and 3.

  Verify: the tests of 1.1 and the rest of `tests/ops/test_config_push.py` pass on the emulator; `just check` passes.
  Result (2026-11-17): 26 of 26 pass on the emulated R4S; `just check` passes. The first green run failed at once: `validate` called `services()`, and `write` `commit_batches()`, declared below them, which ucode resolves when it compiles a body; both now come before their callers, and the entry points run on the host ucode with stub modules.

## 3. Verification

- [ ] 3.1 Run CI's build on this change's branch for both boards.

  Verify: every test passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub; then start release-freshness.
