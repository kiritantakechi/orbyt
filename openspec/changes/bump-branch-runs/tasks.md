# Tasks

## 1. The build's runs (design D1, D3)

- [ ] 1.1 Add the `release/upstream-bump` tests of "Merge only after the upgrade drill passes" to `tests/release/test_upstream_bump.py`: "A commit pushed to a bump branch" (`build.yml`'s push trigger takes `bump/**` besides main, with the same paths), and "The PR's own run of a bump" rewritten: in a bump pull request's run `host-toolchain` is skipped, every job but `upgrade-drill` needs it directly or through `sign`, none runs without it, and `upgrade-drill`'s name evaluates to something other than `upgrade-drill` while its step passes, naming the branch's run.

  Verify: `spec-coverage --change bump-branch-runs` reports both scenarios covered; both tests fail on the current `build.yml`.

- [ ] 1.2 Change `build.yml`: the push trigger, `host-toolchain`'s condition, `upgrade-drill`'s name and step; drop `BUMP_PULL_REQUEST`'s test of `RELEASE_SIGNING` (D1, D3).

  Verify: the tests of 1.1 and the rest of `tests/build/test_ci.py` pass; `just check` passes (actionlint).

## 2. The bot (design D2)

- [ ] 2.1 Rewrite the bot's tests in `tests/release/test_upstream_bump.py`: a new branch is pushed with the token and nothing is dispatched ("The PR cannot be opened", "Bump run again"), and "No token that starts workflows": with updates and no token, nothing is pushed or opened and the run fails naming `BUMP_PUSH_TOKEN`; with no updates and no token, the run passes.

  Verify: `spec-coverage --change bump-branch-runs` reports the scenario covered; the new test fails on the current `bump.yml`.

- [ ] 2.2 Change `bump.yml`: checkout and `gh` take `BUMP_PUSH_TOKEN`, the step stops without it when there is something to push, and the dispatches go (D2).

  Verify: the tests of 2.1 and the rest of `tests/release/test_upstream_bump.py` (drill tests aside) pass; `just check` passes.

## 3. The audit (design D4)

- [ ] 3.1 Have `github-audit.sh` read the secret `BUMP_PUSH_TOKEN` in place of the workflow permission, noting when it cannot read it; update `tests/unit/test_github_audit.py`.

  Verify: `tests/unit/test_github_audit.py` passes; `just github-audit` with the maintainer's token reports the secret missing until it is created.

## 4. Documents

- [ ] 4.1 Describe the branch's push run, the token (permissions, renewal, the setting it replaces) and where CI records go in `docs/release-flow.md`, and the jobs of `build.yml` and `bump.yml` in `docs/ci.md`.

  Verify: `just check` passes; no document still says the bot dispatches the branch's runs or that a bump pull request's run fails its drill check.

## 5. Verification on GitHub (design D5)

- [ ] 5.1 Push `bump/verify-branch-runs` from this change's branch and open its pull request; see the push run start and its `upgrade-drill` among the pull request's checks, the pull request's run skip `host-toolchain` and pass `upgrade-drill of the branch`; cancel the push run and see the required check fail; then close the pull request, delete the branch and any cache of its ref.

  Verify: the three observations of D5, with the runs' IDs, recorded in `docs/ci.md`; no branch, pull request or cache of the verification left.

## Workflow follow-up

- Sync the delta spec, archive the change, merge it to main and push Codeberg first, then GitHub.
- The maintainer creates `BUMP_PUSH_TOKEN` before the first bump after the merge; that bump shows the bot's push starting the branch's build.
