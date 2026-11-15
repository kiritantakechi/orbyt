# Tasks

## 1. Token mode on the router (design D1)

- [x] 1.1 honk's init writes `password_auth`, `allow_anonymous_loopback` and `config_write` as false into the firmware's settings.
- [x] 1.2 config-push reads the native API's booleans in honk's spellings, refuses anything but a false one for the three, refuses a blank `secret`, and says the router keeps them off anyway.
- [x] 1.3 LuCI's switch replaces an empty secret with a new token (daeuniverse 0001).

  Verify:
  - the transparent-proxy test of password login in the configuration passes, where without 1.1 honk refuses that configuration;
  - the push tests refuse password login and configuration writes in four spellings, and a blank token after a real one;
  - withSecret leaves a block with a token as it is, and gives a block without one or with `''`/`""` exactly one token.

## 2. The push puts back what it changed (design D2, D3)

- [x] 2.1 Putting honk back stops it when its start-at-boot switch is off; `write` returns whether its files went in, and `apply` puts the service back when they did not.
- [x] 2.2 SMB passwords go to `ksmbd.adduser` on standard input; ksmbd-tools' fix for a piped password is backported (packages 0014).
- [x] 2.3 config-push refuses the dae layout, naming `git mv dae honk`; on a router without honk, it fails before changing anything.

  Verify:
  - the push tests of a honk that was off, of the dae layout and of the secrets on the device pass: no recorded or sampled command line holds the added user's password, and its stored entry equals the one `-p` stores;
  - device.uc compiles.

## 3. honk's patches (design D4)

- [x] 3.1 005: a released flow's hold end is read with its originals; no batch leaves a result unset.
- [x] 3.2 006: the watchdog retires a batch a tick; shutdown drains them all.
- [x] 3.3 007: the message, the comment and the docs state the staging's 120 s and its dropped packets.
- [x] 3.4 002: the check's tests load geodata from their own data directory alone.

  Verify:
  - honk-core's unit tests pass with the series (`ebpf,native-api`, and `clash-api` for the metrics test);
  - the watchdog's test of a batch a tick fails without 3.2;
  - the check's tests pass with a `geosite.dat` where honk looks first (`DAE_LOCATION_ASSET`), where the test of geodata not there yet failed before;
  - the feed's patches equal the series' commits.

## 4. Packaging (design D5)

- [x] 4.1 No core dumps for honk; `check` creates no directory and takes an absolute path; a failed pinning is logged.
- [x] 4.2 Dependencies: `+flock +bpftool` for honk, `+bpftool` for einat, `+flock` for wrt-sync.
- [x] 4.3 The bindgen includes expand at compile time and stop the build when empty; `PKG_FILE_DEPENDS` rebuilds honk with bpf-linker or doona.

  Verify:
  - both boards build; the image keeps bpftool-minimal and flock;
  - honk's prepared stamp moves with a change to doona's or bpf-linker's package, and back with its undoing.

## 5. Tests that prove their point (design D6)

- [x] 5.1 The hook-order test waits for each restarted daemon; the NFQUEUE table is compared with its handles; the native API's negatives have positive controls; the `ss` check goes; the LuCI save test's ping always ends.
- [x] 5.2 The push's watchers pause with ucode's `sleep`; argument recording covers `ksmbd.adduser`.
- [x] 5.3 netprobe's flow count is exact and its unit test checks the count and the pacing; the pinned versions come from the feed's Makefiles.

  Verify: `just check` passes; the unit tests pass on the VM.

## 6. einat 0.2.0 (design D8)

- [x] 6.1 einat goes to 0.2.0 with its mark patch carried over, and the NAT tests expect the pinned version.

  Verify: the R4S builds; the NAT tests pass; the register of reviewed warnings has no stale or unreviewed entry.

## 7. The host stage's key (design D9)

- [x] 7.1 scripts/toolchain-key.sh hashes the board-neutral configuration's option lines alone.

  Verify: on the VM, a comment appended to a seed keeps the key, an option appended moves it; the register of scenarios verified elsewhere names it.

## 8. Integration

- [ ] 8.1 The six suites on the R4S locally, then CI's build and check for both boards.

  Verify: every suite passes on both boards; the runs are recorded in `docs/ci.md`.
