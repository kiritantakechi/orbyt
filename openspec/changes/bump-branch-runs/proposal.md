# Proposal

## Why

A bump pull request cannot pass main's required check `upgrade-drill` once release signing is set up. GitHub counts the checks of a workflow run toward a pull request's required checks only when the run was started by an eligible event, such as `push` or `pull_request`; the checks of a `workflow_dispatch` run do not even appear in the pull request ("Troubleshooting required status checks", GitHub Docs). The release pipeline relies on exactly such a run:

- The bot pushes the bump branch with the workflow's token, which starts no workflow, and dispatches `check` and `build` on it. Those are the runs that sign and drill, and the pull request ignores them: on 2026-11-16 the checks of pull request 5 listed only its own runs, though the branch's dispatched runs had passed `check` first.
- The pull request's own run cannot sign (only main and `bump/*` may deploy to `release-signing`), so release-integrity D4 makes its `upgrade-drill` fail once signing is set up. Nothing could then pass the check; a bump would merge only by an administrator bypassing main's rules, as every bump so far reached main.

The two runs also cost twice for one commit: a maintainer's push to a bump branch starts the pull request's run, which builds the host stage from scratch on a ref without caches (on 2026-11-16, run 43887051682, cancelled by hand), while the run that drills needs a manual dispatch.

## What Changes

- **A push to a bump branch runs its build, and that run decides.** `build.yml` runs on pushes to `bump/**` as on main: the run builds, tests, signs and drills the branch's commit, and its `upgrade-drill` is the pull request's.
- **The bot pushes with a token that starts workflows** (**BREAKING** for the repository's settings): a secret `BUMP_PUSH_TOKEN` that the maintainer creates, a fine-grained token for this repository with read and write access to its contents and pull requests. The bot pushes the branch and opens the pull request with it, so the branch's build and the pull request's `check` start on their own, and it dispatches nothing. Without the secret the bot stops before it pushes, naming it. Workflows no longer need to be allowed to create pull requests.
- **The pull request's run of a bump branch builds nothing.** The host stage is skipped, and every job that needs it with it. Its drill job reports under another name, so the required `upgrade-drill` waits for the branch's run, and no two checks of that name can disagree: a skipped `upgrade-drill` would count as passed.
- **The audit** reads back that the secret exists, in place of the setting that let workflows create pull requests.
- **The documents** (`docs/release-flow.md`, `docs/ci.md`) describe the branch's run, the token and its renewal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `release/upstream-bump`: the bot pushes so that the branch's build runs; a commit pushed to a bump branch starts that run, which decides the drill check; the pull request's run builds nothing and reports no drill check.

## Impact

- `.github/workflows/build.yml`: the push trigger, `host-toolchain`'s condition, `upgrade-drill`'s name and step.
- `.github/workflows/bump.yml`: the token, no dispatch.
- `scripts/github-audit.sh`: the secret in place of the workflow permission.
- `tests/release/test_upstream_bump.py`, `tests/build/test_ci.py`, `tests/unit/test_github_audit.py`.
- `docs/release-flow.md`, `docs/ci.md`.
- The maintainer creates `BUMP_PUSH_TOKEN` before the first bump after the merge, and renews it before it expires.
- Verification on GitHub with a throwaway branch `bump/verify-branch-runs` and its pull request, closed and deleted afterwards.
- Runner time: a maintainer's push to a bump branch costs one build instead of two. No change to the firmware or to other pull requests' runs.
