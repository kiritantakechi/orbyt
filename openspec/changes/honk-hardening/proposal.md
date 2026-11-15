# Proposal

## Why

A review of honk-datapath after its merge, each finding checked against the code, found defects the tests did not catch:

- **The native API's token mode could be bypassed.** honk takes a native API boolean as `true`, `yes`, `1` or `on`, in any case, while config-push refused `true` alone, so `password_auth: yes` passed the push. A configuration edited on the router (LuCI's editor) is not checked by the push at all.
- **The push's rollback could leave a different router behind.**
  - Putting honk back started it even where it had been off before the push.
  - A file the push could not write ended the push without putting anything back.
  - An SMB user's password went to `ksmbd.adduser` on its command line, against the spec, because its prompt mangles a piped password.
- **honk's patches had three faults and a misleading account.**
  - Patch 005 could panic when every flow of a batch had been failed by its waiter just after its release.
  - Patch 006 let the watchdog retire batch after batch before scanning the holds.
  - Patch 002's test of missing geodata fails wherever geodata lies in honk's fallback directories, as on upstream's own CI.
  - Patch 007 did not say what a token cleanup left to the janitor costs.
- **Packaging and the init script:**
  - `core="unlimited"` let every crash write a core dump into RAM.
  - `check` created honk's directory on the data disk.
  - `flock` and `bpftool` were used without being dependencies.
  - The bindgen include list ran the target compiler whenever the Makefile was read.
  - A doona or bpf-linker bump did not rebuild honk.
- **Tests that pass without proving their point:**
  - waits that the old process satisfies;
  - negatives without a positive control;
  - a table comparison that a recreated table passes;
  - a vacuous `ss` check;
  - a leaked ping;
  - a fractional `sleep` that BusyBox refuses, so the push's watchers spun;
  - a flow count that depends on the host's load.
- **einat 0.2.0 is out**, with GRE support and aya 0.16; our pin and a test still name 0.1.11.

## What Changes

- **The firmware keeps the native API in token mode:**
  - honk's init writes `password_auth`, `allow_anonymous_loopback` and `config_write` as false into the firmware's settings, which honk takes last, whatever the configuration says.
  - config-push refuses each of them in any spelling but a false one, and refuses a blank `secret`.
  - LuCI's switch replaces an empty secret instead of adding a second one.
- **config-push:**
  - It refuses a private repository still in dae's layout, naming `git mv dae honk`.
  - A file it cannot write is put back like a failed reload.
  - Putting honk back stops it again when its start-at-boot switch is off.
  - It fails early on a router without honk.
  - SMB passwords go to `ksmbd.adduser` on standard input, with ksmbd-tools' upstream fix backported (packages 0014).
- **honk's patches are amended:**
  - 005 reads each released flow's hold under the lock that releases it.
  - 006 retires a batch a watchdog tick.
  - 007 and the docs state that the staging lasts 120 s from the flow's first packet, its packets queued and dropped meanwhile.
  - 002's tests pin the geodata lookup to their own data directory.
- **Packaging:**
  - No core dumps; `check` creates nothing and takes an absolute path; a failed pinning is logged.
  - `+flock +bpftool` for honk, `+bpftool` for einat, `+flock` for wrt-sync.
  - The bindgen includes expand at compile time and fail loudly when empty.
  - honk is rebuilt when bpf-linker or doona changes (`PKG_FILE_DEPENDS`).
- **The tests:**
  - Each fixed test proves its point.
  - The netprobe flow count is exact.
  - The pinned versions of honk and einat come from their Makefiles.
  - New tests cover the new refusals, the token mode on the router, the honk-off rollback, and the SMB password's path and stored hash.
- **einat 0.2.0**, its mark patch carried over unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities
- `ops/config-push`:
  - no SMB password on a command line;
  - the dae layout refused;
  - a write failure and a honk that was off put back as they were;
  - the native API's booleans in every spelling honk takes, and a blank token refused.
- `network/transparent-proxy`: the firmware keeps password login, anonymous loopback and configuration writes off whatever the configuration says.

## Impact

- **Router side:** `feed/net/honk` (`init`, `Makefile`, patches 002, 005, 006 and 007), `feed/net/einat`, `feed/utils/wrt-sync`, `config/datapath.seed`, `patches/daeuniverse/0001`, `patches/packages/0014`.
- **Host side:** `scripts/config-push.sh`, `scripts/config-push.d/device.uc`, `scripts/upstream-bump.sh`.
- **Tests:** network (`transparent_proxy`, `tc_hook_order`, `nat`), ops (`config_push`), unit (`netprobe`), and `wrt_tests` (`repository`, `datapath`, `netprobe`).
- **Docs:** `docs/patches.md` (the amended and new patches' write-ups and logs), `docs/ops.md`.
