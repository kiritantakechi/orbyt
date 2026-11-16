# Design

## Context

- uci's command line keeps the configuration in a directory (`-c`, `/etc/config` by default) and uncommitted changes in change directories: it reads a package's changes from every directory of its list, which always holds `/tmp/.uci`, and saves new ones in its save directory, `/tmp/.uci` unless `-t` (or `-P`) names another, which `-t` adds to the list (`uci_set_savedir`). `-P` does the same and refuses `commit`; `-t` does not. A commit applies the changes of every directory of the list and clears those of the save directory alone (`uci_load_delta`). Every command that changes a package saves its changes at once (`cli.c`).
- `validate` (`scripts/config-push.d/device.uc`) runs each batch alone, on a fresh copy of `/etc/config`, with `-c` alone; `write` runs a service's batches with plain `uci batch`, then `uci commit` without a package, which commits every package with changes.
- `apply` saves `/etc/config` whole before `write`, and `restore` puts it back after a failure; config-push removes the router's `/tmp/wrt-push` once the push ends, however it ends (`docs/ops.md`, step 5).

## Goals / Non-Goals

**Goals:**
- No push leaves a change uncommitted, its dry run included, and none of its secrets outside `/etc/config` and its own temporary directory.
- A push commits nothing it did not change, and never mixes its changes with someone else's uncommitted ones.

**Non-Goals:**
- Merging a push with uncommitted changes to the same package: which should win is the administrator's to say, by committing or reverting first.
- A change made in LuCI between a push's validation and its commit, seconds apart: the push cannot tell it from its own.

## Decisions

### D1. The dry run in a change directory of its own

`validate` runs a service's batches in order, as `write` will, on one fresh copy of `/etc/config` per service, with `uci -c <copy> -t <copy's changes>`: the changes go to that directory, inside `/tmp/wrt-push`, which the push removes. The directory's files then name the packages the service's batches change: uci saves a package's changes in a file of the package's name.

Running a service's batches together rather than each on a copy of its own checks what the push will do: a batch may set what an earlier one added.

### D2. Refusing beside uncommitted changes

For every package the dry run found changed, `validate` asks the device's own change directory (`uci changes <package>`); any change there fails validation, before anything is written, with "the router has uncommitted changes to <package> (uci changes <package>): commit or revert them, then push again". Uncommitted changes to the packages no batch changes are none of the push's business, and stay.

Alternatives considered:
- Reverting them: discards an administrator's work unasked.
- Committing them with the push: what the push does today, and the defect.

### D3. Committing package by package from the push's own changes

`write` runs the service's batches with `uci -t <push's changes>`, a fresh directory in `/tmp/wrt-push`, then commits each package that directory names, `uci -t <push's changes> commit <package>`; `/tmp/.uci` holds no change of those packages (D2), so each commit writes the push's changes alone. Whatever the outcome, `write` removes the directory before it returns: a batch that fails leaves no change behind, and `restore` puts the files back as today.

### D4. Tests

`tests/ops/test_config_push.py`, against the module's pushed router:
- After a push that finds every service unchanged, `uci changes` prints nothing and no file under `/tmp/.uci` holds the WireGuard key.
- With an uncommitted change to `network` (a package the network batch changes), the push fails naming `network`, the router is as before, and the change is still uncommitted.
- With an uncommitted change to `system` and a changed network batch, the push applies the batch, `system`'s change is still uncommitted, `/etc/config/system` is as before, and `uci changes` shows nothing else.

## Risks / Trade-offs

- [An administrator's unsaved LuCI change to a pushed package now stops the push] → The refusal names the package and both ways out; before, the change went in unseen.
- [A LuCI change made within the seconds between validation and commit is committed with the push and stays listed as uncommitted] → Accepted (Non-Goals); a later commit of it changes nothing more.
