# Tasks

## 1. qosify configured on its object's registration (design D1)

- [x] 1.1 Pin what configures qosify today: on the emulated R4S, boot with no configuration change and read pppoe-wan's qdisc; kill the daemon and read it again after procd respawns it.

  Verify: the record in docs/patches.md's 0006 entry states what was seen (expected: unconfigured in both cases until a reload).

  Seen 2026-11-21: configured in both cases, by procd's own `running` call, and a status query sent the daemon its configuration with `reset` (design D1); the maintainer kept the object trigger, and the status query became a scenario.

- [x] 1.2 Add the three QoS scenarios to `tests/network/test_qos.py` (a boot with no change; the daemon killed and respawned; a status query).

  Verify: `spec-coverage --change patch-hygiene` covers them; on the image with the old 0006 the first two pass and the status query fails (seen 2026-11-21).

- [ ] 1.3 The procd patch passing `ubus.object.add` to the service triggers; 0006 rewritten as the raw trigger on qosify's registration, `service_running` gone; the write-ups.

  Verify: 1.2's tests and the QoS suite pass on the emulated R4S.

## 2. One fault per patch (D2)

- [x] 2.1 Split 0035, merge 0036 and 0044, fold 0009 into 0038, split packages/0002, with their write-ups.

  Verify: applying the old and the new series to the pinned trees gives identical trees, but for procd's and fstools' `PKG_RELEASE` and fstools' patch file, whose patched fstools source is identical; `just patch` applies.

  Result (2026-11-21): the openwrt series ends on tree `d59d4242` without the procd and fstools patches' release lines and fstools' patch file; the packages series on `d3082588`, the same as before; fstools' patched source is `84478ca9` both ways; procd's release goes from 7 to 10, fstools' from 4 to 3.

## 3. 0021 and 0012 (D3, D4)

- [ ] 3.1 Find which of D3's three ways holds, implement it, and drop 0021.

  Verify: in the R4S's `ubsan` tree, libffi, libmd, libmnl and musl-fts link with no runtime call and 0021's trap counts; the dev profile's packages are unchanged.

- [ ] 3.2 Try 0012 as an exclusion from `Kernel/Newer`.

  Verify: the two experiments of 0012's log hold; otherwise 0012 stays and its write-up says why.

## 4. Write-ups and small fixes (D5, D6)

- [x] 4.1 Bring every write-up to the four sections, grouped and in order, fix 0025's title and the Rust entry's dates, and add the write-up check to `tests/build/test_upstream_pinning.py`.

  Verify: the check passes, and fails on a write-up with a section removed.

- [ ] 4.2 daeuniverse/0003's dependency on BusyBox's `timeout`.

  Verify: `just patch`; the honk LuCI app builds and its tests pass.

## 5. Verification

- [ ] 5.1 `just check`; the unit and quality suites; the network and services suites on the emulated R4S, the Mac's load gated and sampled.

  Verify: every test passes.

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification; its run is recorded for this change in docs/ci.md.
- Archive after firmware-hygiene.
