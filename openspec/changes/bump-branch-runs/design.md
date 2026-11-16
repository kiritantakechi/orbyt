# Design

## Context

See proposal.md, Why. Today:

- `bump.yml` pushes `bump/<date>` with the workflow's token and dispatches `check.yml` and `build.yml` on it (release-integrity D5), then opens the pull request with the same token. Neither the push nor the pull request starts a workflow. The pull request's own runs wait for approval ("action_required"), and the dispatched runs do not count for it.
- `build.yml` runs on pushes to main, on pull requests and by dispatch. Its `upgrade-drill` job fails in a bump pull request's run once `RELEASE_SIGNING` is enabled (release-integrity D4).
- main's ruleset requires the checks `check` and `upgrade-drill` of GitHub Actions; administrators may bypass it.

GitHub's rules this design rests on ("Troubleshooting required status checks"):

- only the checks of runs started by `push`, `pull_request`, `pull_request_review`, `pull_request_target`, `deployment` or `deployment_status` count, and only on the pull request's latest commit;
- a job skipped by its condition reports success;
- a check and a commit status of the same name must both pass.

## Goals / Non-Goals

**Goals:**
- One run per commit decides a bump pull request's `upgrade-drill`: the branch's push run, the only kind that can sign.
- Fail closed: until that run reports, the check is pending, never passed by a skipped or renamed job.

**Non-Goals:**
- How changes reach main. Merging stays the maintainer's, by the pull request or by fast-forward.
- Other pull requests' runs, which keep building and passing on their system tests.

## Decisions

### D1. The branch's push run decides

`build.yml` runs on `push` to `branches: [main, "bump/**"]`, with the paths it has. A bump branch's run is then a push run: its checks are the pull request's, it may deploy to `release-signing` (whose branches are main and `bump/*`), and its `upgrade-drill` already requires the drill once signing is set up. Its concurrency group is its ref, so a newer push cancels the run of the commit it replaced, the bot's included (build/ci, "Workflows cancel only their own superseded runs").

Alternatives considered:
- The pull request's run decides: it cannot deploy to `release-signing` by its ref, and builds the merge commit rather than the commit the branch holds, which `publish` tags.
- The dispatched run posts a commit status `upgrade-drill`: the pull request's run reports a check of that name, and both would have to pass; a second mechanism for one check.

### D2. The bot's token

The bot pushes and opens the pull request with `BUMP_PUSH_TOKEN`, a fine-grained personal access token of the maintainer:

- repository access: this repository only;
- permissions: Contents read and write (the push), Pull requests read and write (`gh pr list` and `gh pr create`); Metadata read comes with them;
- no Workflows permission: the bot's commit changes only `upstream.lock`, and the branch's other commits are main's.

`actions/checkout` takes it as its token, so the push uses it, and `gh` takes it as `GH_TOKEN`. Pushes and pull requests made with it start workflows like the maintainer's own. Its expiry is the maintainer's choice, at most a year; `docs/release-flow.md` names the renewal.

The bot stops when there is something to push and no token: before it creates the branch, it fails naming the secret. With nothing to push, the run passes without it. The bot dispatches nothing: a dispatched run counts for no pull request.

Alternative considered: a GitHub App's installation token, which does not expire. It needs an app, its private key as a secret and a step to mint the token, for one push a week. The token can be replaced by one later without changing the workflow's shape.

Since the pull request is no longer opened with the workflow's token, workflows need not be allowed to create pull requests. The audit stops requiring it (D4); turning it off is the maintainer's choice.

### D3. The pull request's run of a bump builds nothing and reports no drill check

- `host-toolchain` gets `if: ${{ !(github.event_name == 'pull_request' && startsWith(github.head_ref, 'bump/')) }}`. `firmware` and `system-test` need it and are skipped with it; `caches` requires its success; `sign` excludes pull requests, and `drill` and `publish` follow `sign`.
- `upgrade-drill` keeps running in every run (`if: always()`), but in a bump pull request's run its name is `upgrade-drill of the branch` (the job's `name` is an expression), and its step only says which run reports the check, and passes. The required context `upgrade-drill` then comes from the branch's run alone; until it reports, the check is pending.
- Skipping the job instead would report a success under the required name. Failing it, as D4 did, gives the pull request two checks of the name with opposite outcomes, of which GitHub documents no order.

The step's `BUMP_PULL_REQUEST`, which tested `RELEASE_SIGNING`, goes; the signing setting no longer changes a pull request's run.

### D4. The audit

`github-audit.sh` reads `repos/<repository>/actions/secrets/BUMP_PUSH_TOKEN` (its name and dates, never its value) in place of `actions/permissions/workflow`. Only a token with administration access may read it; a workflow's cannot, and the audit then notes it could not read it, as before.

### D5. Verification on GitHub

A throwaway branch `bump/verify-branch-runs`, pushed by the maintainer's credentials from this change's branch, and its pull request show what no local test can:

1. the push starts the branch's build, and its `upgrade-drill` appears among the pull request's checks while it runs;
2. the pull request's run skips `host-toolchain`, and its drill job runs as `upgrade-drill of the branch` and passes;
3. cancelling the push run makes its `upgrade-drill` fail, and the pull request's required check fails with it.

The pull request is then closed, the branch deleted, and any cache of the branch's ref with it. The bot's own token is seen at the first weekly bump after the merge.

## Risks / Trade-offs

- [A commit that changes only documents no test reads, pushed to a bump branch, starts no build: the pull request's required checks stay pending on it] → Such commits (a CI run's record in `docs/ci.md`) go on main after the merge; `docs/release-flow.md` says so. A pending check blocks rather than passes.
- [The token expires, or is revoked] → The bot's push fails, naming the remote's refusal, before anything is opened; the audit cannot see the expiry, so `docs/release-flow.md` asks for a renewal date in the maintainer's calendar.
- [The token is a long-lived credential] → Only this repository, no Workflows or administration permission, used by `bump.yml` alone, which runs only on main's schedule and dispatch; forks' runs get no secrets.
- [The job name's expression is not evaluated as documented] → D5's second point checks it before the merge.

## Migration Plan

1. Merge; the next bump fails, naming the secret, until it exists.
2. The maintainer creates the token and the secret (`docs/release-flow.md`, one-time setup), then runs `just github-audit`.
3. Bump PR 5 (2026-11-16) is landed as before, by fast-forward, as its branch's run is a dispatched one.
