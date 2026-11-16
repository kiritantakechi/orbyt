# Tasks

## 1. The patch step (design D1)

- [x] 1.1 Add the `release/upstream-bump` test "Upstream made a patch's change" to `tests/release/test_upstream_bump.py`: the pinned openwrt commit carries the result of the series' first patch, and the patch step fails naming that patch and saying upstream has its change.

  Verify: `just check` passes; `spec-coverage --change upstreamed-patches` reports the scenario covered; the test fails before 1.2.
  Result (2026-11-16): the test failed without 1.2, the message being the conflict's; covered. The conflict's test now shares its setup and also requires that a conflict is not reported as upstream's.

- [x] 1.2 Have `series_commit()` check a refused patch in reverse and say, when it applies so, that upstream has its change (D1).

  Verify: the new test and "BBRv3 patch conflict" pass; `just patch` on the pins of 2026-11-16 with patch 0045 put back reports it as upstream's.
  Result (2026-11-16): both pass, with the rest of `release/test_upstream_bump.py` (drill tests aside), `build/test_upstream_pinning.py` and `build/test_environment.py`: 23 passed. `series_commit()` on the openwrt pin of 2026-11-16 with 0045 put back: "patch does not apply: patches/openwrt/0045-firewall4-update-to-Git-HEAD-2026-11-08.patch: upstream has its change (it applies in reverse); drop the patch".

## 2. Documents (design D2)

- [x] 2.1 Name `host-toolchain` in `docs/release-flow.md`, and the reverse check in `docs/upstream-lock.md`.

  Verify: `just check` passes.
  Result (2026-11-16): passes.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub.
