# Tasks

## 1. The build's runs (design D1, D3)

- [x] 1.1 Add the `release/upstream-bump` tests of "Merge only after the upgrade drill passes" to `tests/release/test_upstream_bump.py`: "A commit pushed to a bump branch" (`build.yml`'s push trigger takes `bump/**` besides main, with the same paths), and "The PR's own run of a bump" rewritten: in a bump pull request's run `host-toolchain` is skipped, every job but `upgrade-drill` needs it directly or through `sign`, none runs without it, and `upgrade-drill`'s name evaluates to something other than `upgrade-drill` while its step passes, naming the branch's run.

  Verify: `spec-coverage --change bump-branch-runs` reports both scenarios covered; both tests fail on the current `build.yml`.
  Result (2026-11-16): both covered; both failed on the current `build.yml`, which has no push trigger for `bump/**` and no condition on `host-toolchain`. The rewritten test also requires the three places that tell a bump pull request's run to use one condition, and that another pull request's run with nothing built still fails the check.

- [x] 1.2 Change `build.yml`: the push trigger, `host-toolchain`'s condition, `upgrade-drill`'s name and step; drop `BUMP_PULL_REQUEST`'s test of `RELEASE_SIGNING` (D1, D3).

  Verify: the tests of 1.1 and the rest of `tests/build/test_ci.py` pass; `just check` passes (actionlint).
  Result (2026-11-16): `release/test_upstream_bump.py` (the two emulator drill tests aside) and `build/test_ci.py`: 26 passed, 1 skipped; `just check` passes. In a bump pull request's run the step now passes with a notice naming the push run of its branch.

## 2. The bot (design D2)

- [x] 2.1 Rewrite the bot's tests in `tests/release/test_upstream_bump.py`: a new branch is pushed with the token and nothing is dispatched ("The PR cannot be opened", "Bump run again"), and "No token that starts workflows": with updates and no token, nothing is pushed or opened and the run fails naming `BUMP_PUSH_TOKEN`; with no updates and no token, the run passes.

  Verify: `spec-coverage --change bump-branch-runs` reports the scenario covered; the new test fails on the current `bump.yml`.
  Result (2026-11-16): covered; on the current `bump.yml` the new test failed (its checkout takes no token) and "The PR cannot be opened" failed on the two dispatches; "Bump run again" passed as it was. The new test also reads that checkout and `gh` take the secret, checkout falling back on the workflow's token.

- [x] 2.2 Change `bump.yml`: checkout and `gh` take `BUMP_PUSH_TOKEN`, the step stops without it when there is something to push, and the dispatches go (D2).

  Verify: the tests of 2.1 and the rest of `tests/release/test_upstream_bump.py` (drill tests aside) pass; `just check` passes.
  Result (2026-11-16): with `build/test_ci.py`, 27 passed, 1 skipped; `just check` passes. The workflow's own token now only reads (`contents: read`), and the refused pull request's message names the token's permission.

## 3. The audit (design D4)

- [x] 3.1 Have `github-audit.sh` read the secret `BUMP_PUSH_TOKEN` in place of the workflow permission, noting when it cannot read it; update `tests/unit/test_github_audit.py`.

  Verify: `tests/unit/test_github_audit.py` passes; `just github-audit` with the maintainer's token reports the secret missing until it is created.
  Result (2026-11-16): 7 passed. The maintainer had created the secret already (15:24 UTC), so `just github-audit` with their token reported it present, with every other setting held; the missing case is the unit test's.

## 4. Documents

- [x] 4.1 Describe the branch's push run, the token (permissions, renewal, the setting it replaces) and where CI records go in `docs/release-flow.md`, and the jobs of `build.yml` and `bump.yml` in `docs/ci.md`.

  Verify: `just check` passes; no document still says the bot dispatches the branch's runs or that a bump pull request's run fails its drill check.
  Result (2026-11-16): `just check` passes; no such wording left in `docs/`, `.github/` or `scripts/` but the records of past runs in `docs/ci.md`. `docs/ci.md` also says now that `check.yml` runs on pushes to main and on pull requests (it said every push), and that `bump.yml` is the one workflow besides `sign` with a secret.

## 5. Verification on GitHub (design D5)

- [ ] 5.1 Push `bump/verify-branch-runs` from this change's branch and open its pull request; see the push run start and its `upgrade-drill` among the pull request's checks, the pull request's run skip `host-toolchain` and pass `upgrade-drill of the branch`; cancel the push run and see the required check fail; then close the pull request, delete the branch and any cache of its ref.

  Verify: the three observations of D5, with the runs' IDs, recorded in `docs/ci.md`; no branch, pull request or cache of the verification left.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub.
- The maintainer creates `BUMP_PUSH_TOKEN` before the first bump after the merge; that bump shows the bot's push starting the branch's build.
