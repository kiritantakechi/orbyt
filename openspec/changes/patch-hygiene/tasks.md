# Tasks

## 1. qosify configured on its object's registration (design D1)

- [ ] 1.1 Pin what configures qosify today: on the emulated R4S, boot with no configuration change and read pppoe-wan's qdisc; kill the daemon and read it again after procd respawns it.

  Verify: the record in docs/patches.md's 0006 entry states what was seen (expected: unconfigured in both cases until a reload).

- [ ] 1.2 Add the two QoS scenarios to `tests/network/test_qos.py` (a boot with no change; the daemon killed and respawned).

  Verify: `spec-coverage --change patch-hygiene` covers them; they fail on the current image.

- [ ] 1.3 The procd patch passing `ubus.object.add` to the service triggers; 0006 rewritten as the raw trigger on qosify's registration, `service_running` gone; the write-ups.

  Verify: 1.2's tests and the QoS suite pass on the emulated R4S.

## 2. One fault per patch (D2)

- [ ] 2.1 Split 0035, merge 0036 and 0044, fold 0009 into 0038, split packages/0002, with their write-ups.

  Verify: applying the old and the new series to the pinned trees gives identical files (a `diff -r` of the two trees, `.git` aside); `just patch` applies.

## 3. 0021 and 0012 (D3, D4)

- [ ] 3.1 Find which of D3's three ways holds, implement it, and drop 0021.

  Verify: in the R4S's `ubsan` tree, libffi, libmd, libmnl and musl-fts link with no runtime call and 0021's trap counts; the dev profile's packages are unchanged.

- [ ] 3.2 Try 0012 as an exclusion from `Kernel/Newer`.

  Verify: the two experiments of 0012's log hold; otherwise 0012 stays and its write-up says why.

## 4. Write-ups and small fixes (D5, D6)

- [ ] 4.1 Bring every write-up to the four sections in series order, fix 0040's trailer and the titles, and add the write-up check to `tests/build/test_upstream_pinning.py`.

  Verify: the check passes, and fails on a write-up with a section removed.

- [ ] 4.2 daeuniverse/0003's dependency on BusyBox's `timeout`.

  Verify: `just patch`; the honk LuCI app builds and its tests pass.

## 5. Verification

- [ ] 5.1 `just check`; the unit and quality suites; the network and services suites on the emulated R4S, the Mac's load gated and sampled.

  Verify: every test passes.

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification; its run is recorded for this change in docs/ci.md.
- Archive after firmware-hygiene.
