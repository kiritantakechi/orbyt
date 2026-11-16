# Design

## Context

honk-datapath merged on 2026-11-15 after CI passed on both boards. Its diff was then reviewed in four parts, independently of the author: the router-side packaging, the host tools, the tests and honk's patches. Each finding below was checked against the code (honk's and OpenWrt's included) before it was taken. Findings that did not hold, or whose cost outweighs them, are listed with their reason.

## Goals / Non-Goals

**Goals:**
- The native API is in token mode on the router, whatever edits its configuration.
- A failed push leaves the router as it was.
- No secret is on a command line.
- honk's patches are correct under the races they handle, their tests pass wherever upstream runs them, and their write-ups state what they cost.
- Every test fails when what it names breaks.

**Non-Goals:**
- Changing procd's respawn policy (see D7).
- Submitting any patch upstream: they stay `Pending`.

## Decisions

### D1. Token mode on the router, refusal in the push

honk takes a scalar from the last file that sets it, and the init includes the firmware's settings last (honk-datapath D4). A `native_api` block there with `password_auth`, `allow_anonymous_loopback` and `config_write` false holds every edit to them off: the push's, LuCI's editor's, a shell's. Per key, not per block: honk's `experimental` parser sets only the keys a block names.

honk then refuses an enabled API without a credential, and the only credential left is a non-empty `secret`.

config-push still refuses these settings, so a push says why rather than having its setting ignored. It reads booleans as honk's `strict_bool` does: `true`, `yes`, `1` and `on` in any case. It refuses anything but a false spelling, which also fails closed on a value honk would reject. It also refuses a blank `secret` anywhere: a later file's blank token would be the one honk takes.

Alternative: parse the effective configuration with honk itself. honk's `check` prints no values, by design (secrets), and a second command would be a new upstream interface for a policy that is ours.

### D2. The rollback puts back the switch's state

honk's reload step in config-push follows the start-at-boot switch:
- When the switch is on, which a push always makes it, honk restarts.
- When it is off, which only a rollback to such a router can make it, honk stops.

Before this, the rollback restarted honk, which then ran with the template, unenabled, where it had been stopped.

`write` returns whether every file went in, and `apply` puts the service back on false as on a failed reload. A failed honk copy also removes `/etc/honk.new`.

### D3. SMB passwords on standard input

`ksmbd.adduser` prompts on standard input, reading the password twice. On a pipe its `tcgetattr` fails, and the erase character it then compares each byte with is uninitialised stack memory, so a piped password could be stored altered.

Upstream fixed this on 2026-10-17 (317406794f32), after 3.5.7, which OpenWrt packages. packages 0014 backports it, and config-push writes the password twice to `ksmbd.adduser`'s standard input.

The test compares the stored entry with the one `-p` stores in a database of its own (`-P`). The hash has no salt, so the entries are equal exactly when the passwords are.

### D4. honk's patches

- **005:** `release_armed_originals` returns the flow's hold end, read under the lock it takes the originals under.
  - The batch's deadline is the earliest of them, so "released but no deadline" cannot happen.
  - Before, the deadline was read afterwards, and `None` for every flow (each failed by its waiter at its hold meanwhile) broke out with results unset, which the final `expect` panicked on.
  - Upstream's single-flow path answers that case with `StaleIdentity`; the batch now reaches the same outcomes through its timeout branch and the blocking section.
- **006:** the watchdog retires one batch a tick (`drain_cleanups(…, 1)`), so its pause before the hold scan is one grace period. Shutdown still drains them all.
- **007:** a token cleanup the full set has no room for leaves its staging to expire.
  - The eBPF side freezes a pending staging's `last_seen_ns` at the flow's first packet, and treats it as expired 120 s later. Until then, the flow's packets are queued and dropped, as for a packet the kernel's full queue dropped.
  - The message, the comment and the docs now say so. The trade stands: exiting instead takes every flow down, and procd's respawn limit can keep honk down.
- **002:** the check's tests load geodata from their own data directory alone (`GeoSourceSet::load_pinned`, beside upstream's `load_captured`).
  - `check` takes the loader, as `offline::validate_for_start` does.
  - Upstream's weekly CI installs `geosite.dat` in `/etc/dae`, one of honk's fallback directories, where the missing-geodata test would find it.

### D5. Packaging

- **No core dumps.** OpenWrt's `core_pattern` writes to `/tmp`, which is memory, and procd respawns honk after a crash.
- **`check` makes nothing.** `state_dir make` creates the data disk's directory for the service alone, and `check` wants an absolute path.
- **The init's and health checks' commands are dependencies.** `bpftool` is a virtual package whose default variant is minimal.
- **The bindgen includes expand at compile time.** `HONK_CXX_INCLUDES` is a recursive variable, as `CARGO_PKG_VARS` is, and an empty list stops the build.
- **`PKG_FILE_DEPENDS` names the bpf-linker and doona package directories.** The prepare stamp is hashed over them, so honk is rebuilt when either changes; `PKG_BUILD_DEPENDS` only orders the builds.

### D6. Tests that prove their point

- **Restarts:** the hook-order test waits for each restarted daemon's new process (honk's datapath via `wait_proxy`) before reading the order, which the old process satisfies.
- **The NFQUEUE table:** compared with its handles, which a recreated table changes.
- **The native API's negatives:** each has a positive control on the same path. The internet pings the WAN address; the container reaches the probe server.
- **Removed and fixed:**
  - the `ss` check, which a closed socket satisfies, goes;
  - the LuCI save test's ping ends whatever fails.
- **The push's watchers** pause with ucode's `sleep(200)`: BusyBox's `sleep` refuses fractions.
- **Recording arguments:** `_recorded` records the arguments of any multi-call binary's link, tailscale's and `ksmbd.adduser`'s.
- **Flow counts:** netprobe's `flows` starts exactly `rate × seconds` flows on their schedule. Its unit test checks the count, and that the last did not start before its time.
- **Pinned versions:** the versions the tests expect come from the feed's Makefiles (`feed_variable`).

### D7. Not changed

- **Respawn:**
  - Unlimited respawn could let a crash-looping upgrade pass the trial boot's health check between crashes.
  - procd's default (five quick failures, then off) leaves the LAN going direct, which the spec requires of a stopped honk.
- **Swapping the entry's directory:** two renames, a window of microseconds. A respawn that falls in it fails once, and procd starts honk again.
- **The pump's retirement after each batch:** patch 006 chose it, after the drain found no turn otherwise. It is bounded by one grace period a batch.
- **`check`'s rendering of messages:** a diagnostic's message is `&'static str`, so no value is in it.
- **Splitting patch 005, its constants:** for an upstream review that has not been asked for.

### D8. einat 0.2.0

It carries no breaking change: GRE devices count as bare IP, aya goes to 0.16 (tc attachment by interface index, `TcAttach`), and its MSRV is 1.98, below the tree's 1.99.1.

The mark patch's range-diff against 0.1.11 is empty: only its index lines and one hunk's offset differ. TCX `first` and netlink priority 1 are unchanged, so the WAN hook order is as before.

### D9. The host stage's key ignores a seed's comments

The key hashed the board-neutral configuration as `compose_seeds` writes it. `merge-seeds.awk` keeps the seeds' comments and blank lines there, for the configuration's reader. So a comment of `config/datapath.seed`, edited in this change, moved the key: CI run 43734941561 rebuilt the host stage for it, in 3 h 44 min.

The key now hashes the option lines alone: `CONFIG_X=...` and `# CONFIG_X is not set`, as `merge-seeds.awk` tells them apart. The other inputs and the configuration toolchain-build.sh builds from stay as they were, as does the compiler cache key, which already drops `ccache.conf`'s comments.

The new hash moves every key once: the next host stage of each ref is a rebuild.
