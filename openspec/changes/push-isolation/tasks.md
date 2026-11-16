# Tasks

## 1. The tests (design D4)

- [ ] 1.1 Add the tests of "A configuration that validates", "Uncommitted change to a pushed package" and "Uncommitted change to another package" to `tests/ops/test_config_push.py`.

  Verify: `spec-coverage --change push-isolation` reports the three covered; on the emulator, before 2.1, all three fail: the dry run leaves the network batch's changes uncommitted, the push takes the uncommitted change to `network` along, and it commits `system`'s.

## 2. The device side (design D1, D2, D3)

- [ ] 2.1 Change `scripts/config-push.d/device.uc`: `validate` runs each service's batches on its own copy with its own change directory, and refuses beside uncommitted changes to the packages they change; `write` runs them with the push's change directory, commits package by package and removes the directory; describe it in `docs/ops.md`, steps 2 and 3.

  Verify: the tests of 1.1 and the rest of `tests/ops/test_config_push.py` pass on the emulator; `just check` passes.

## 3. Verification

- [ ] 3.1 Run CI's build on this change's branch for both boards.

  Verify: every test passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub; then start release-freshness.
