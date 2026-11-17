# Proposal

## Why

config-push applies a service's uci batches in two places, and both reach past the push's own files:

- The dry run of `validate` runs each batch with `uci -c <copy of /etc/config> batch`. `-c` moves only the configuration's directory: uci keeps every change of a package named without a path in its change directory, `/tmp/.uci`, as libuci's `uci_file_load` and `uci_save` do. Every push therefore leaves uncommitted on the router whatever its batches change there, in plain text: each value the router holds otherwise, as after a change made in LuCI since the last push, the PPPoE password and the WireGuard private key among them, whether or not the push's files changed; and every `add_list`, which uci records even when the value is already listed. LuCI then lists them as unsaved, and the next `uci commit`, LuCI's Save & Apply or another push, commits them, over what has been set since; a batch with `add_list` adds its values twice, once from the dry run and once from the push. A batch that fails its dry run after another leaves the other's changes behind, though validation failed.
- `write` commits with a bare `uci commit`, which commits every package with uncommitted changes: changes an administrator made in LuCI and has not saved go with the push. A batch that fails after another has run leaves that one's changes uncommitted, while the push puts the files of `/etc/config` back.

The push's requirement already says that validation changes nothing and that the push's temporary files are gone however it ends; neither holds for `/tmp/.uci`. A review of the project on 2026-11-17 found it.

## What Changes

- **The dry run keeps its changes to itself.** Each batch runs on the copy with a change directory of its own (`uci -t`), inside the push's temporary directory, which the push removes. Its files also name the packages the batches change.
- **A push refuses to mix with uncommitted changes.** When the router holds uncommitted changes to a package the batches change, validation fails before anything changes, naming the package and how to commit or revert it. Uncommitted changes to other packages stay as they are.
- **A push commits its own changes, and only them.** The batches run with the push's own change directory and are committed package by package; a batch that fails leaves nothing behind, and the push's directory goes with its other files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `ops/config-push`: validation leaves no change on the device; a push commits only the packages its batches change, refuses beside uncommitted changes to them, and leaves no change of its own uncommitted.

## Impact

- `scripts/config-push.d/device.uc`: `validate`'s dry run and the uci case of `write`.
- `tests/ops/test_config_push.py`: nothing uncommitted after a push; a push refused beside an uncommitted change to a pushed package; an uncommitted change to another package left as it is.
- `docs/ops.md` where it describes what a push changes.
- No change to the image: config-push sends its device side with every push.
