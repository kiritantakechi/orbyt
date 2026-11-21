# Tasks

## 1. Failures with their output (design D1)

- [x] 1.1 Add `model.process.run` and route the six wrappers and the direct checked calls through it; match the expected failures by their output (the five python-style left as "non-zero exit status", the signer's).

  Verify: `just check`; the unit and testing suites pass; a test expecting a refusal fails, showing the probe's output, when the probe times out instead (tried once by hand).

## 2. One form of wait (D2)

- [x] 2.1 `until` with `notes` and a shared deadline; the nine loops and the hand-attached diagnostics moved onto it; `Router.detach` starting its command after its shell has exited, the callers' `sleep 1;` removed.

  Verify: the testing suite (the harness's own tests, the failure reports' among them) and the boot and upgrade suites pass on the emulated R4S.

- [x] 2.2 The tests' fixed sleeps as waits (BBR, the health check's rounds, the tc hook window, the prompt's duration named).

  Verify: the firmware and network suites pass on the emulated R4S.

## 3. Setups undone, daemons ready (D3)

- [x] 3.1 `Network.__enter__` and `Netns` undo on failure; `WireGuard.connect` and `Tailnet.join` as context managers; `proxy_stop`; readiness probes for the sandbox's daemons.

  Verify: the testing suite's setup-failure tests pass, and one more fails a daemon on purpose and finds no namespace or process left; the services and network suites pass.

## 4. Independent tests (D4)

- [ ] 4.1 Module fixtures for the Pod, the data disk and the trigger queue; the order comments gone.

  Verify: each test of the six modules passes alone (`-k`), and each module passes whole, on the emulated R4S.

## 5. Each fact once (D5)

- [x] 5.1 `device/paths.py`, `Router.upgrade`, `wait_logged`; the repository's paths, the addresses, the WAN device and the resolver from one place each.

  Verify: no test defines a router `/tmp` path or `UPGRADE_IMAGE` (a grep); the firmware and network suites pass.

- [x] 5.2 The sandbox's layout object; `model/erofs.py` and one partition table; one name per limit and per boot limit.

  Verify: no `../pki` string or hand-written superblock offset remains; the unit, release and upgrade suites pass.

## 6. Modules with one job (D6)

- [x] 6.1 Split emu-prepare from the runtime, the Releases store from its server, the clock from the router; the ISP's scripts and the stress driver as checked files; the fake `gh` as a module; `send` with a count.

  Verify: `just check` (tach's layers, shellcheck on the new scripts, no dead code); the testing, release, services and network suites pass.

## 7. Asserts that prove their scenario (D7)

- [x] 7.1 The download's lower bound, MSS and DNS learning over IPv6, the trial failure's slot and named check, the native API's constant, the duplicate tests; measure `Listener`'s loss and keep or drop its resend accordingly.

  Verify: the network, firmware and transparent proxy suites pass; the loss measurement is recorded beside `Listener`.

## 8. Build-tree tests and the cache key (D8)

- [x] 8.1 The `build_tree` mark, its selection in CI's system suite and firmware job, the one-board form of "Two boards in one tree"; the unit test of `toolchain-key.sh` and verified-elsewhere's entries trimmed to CI runs.

  Verify: `spec-coverage` passes; `just test r4s dev -m build_tree` passes on the VM; the system suite selects none of them; the key test fails when an input is removed from the script.

## 9. Leftovers (D9)

- [x] 9.1 PyYAML declared and tach pinned (lock updated), `ORBYT_EMU_DIR`, asserts as raises, `ubsan.report`, the renames, `Router.poll`'s exceptions, one `GIT_IDENTITY` and `repo_files`, the module order, `LONG_DEVICE`.

  Verify: `just check`; the unit and testing suites pass.

## 10. Verification

- [ ] 10.1 The whole system suite of both boards on the emulator, the Mac's load gated and sampled.

  Verify: every test passes on the R4S and the R6S.

## Workflow follow-up

- CI runs once, on the stack's final head, as the release verification; its run is recorded for this change in docs/ci.md.
- Archive after patch-hygiene.
