# Tasks

## 1. Interpreter and tools (design D1, D2)

- [x] 1.1 Pin ruff, ty and pytest exactly; move the tests to `3.15t` and resolve the lock; add the interpreter's test to `tests/quality/`; turn labgrid's pytest plugin off and give the device layer the session's `target`.

  Verify: `uv sync --locked` installs on 3.15t in the FHS shell; the new test passes, and fails with the GIL forced on (`PYTHON_GIL=1`); the unit and quality suites pass.

  Result (2026-11-19): with labgrid's plugin on, the new test failed: grpc, imported by it, turned the GIL on. With it off: passes, fails under `PYTHON_GIL=1`.

- [ ] 1.2 Cache uv's cache in CI's jobs that sync the tests' environment.

  Verify: the release run saves uv's cache under the lock's key; a run after it on the same lock (the check workflow's on the same push, or the next) restores it and builds no distribution.

- [x] 1.3 Take the standard's `ruff.toml` and `ty.toml`, with the project's documented exceptions.

  Verify: ruff and ty run with them; the findings are the families of 2.x.

## 2. The code (design D3)

- [x] 2.1 `ruff format` at 88 columns.

  Verify: `ruff format --check` passes.

- [x] 2.2 Rewrap comments and docstrings at 72 columns; split the code lines the formatter cannot.

  Verify: no W505 or E501 finding.

  Result (2026-11-19): the script refilled 1,300 lines; about 500 docstring summaries were reworded by hand, detail that no longer fit moved into the description. Every changed file's syntax tree, docstrings aside, is the same as before but where a later task changed code.

- [x] 2.3 Fix the remaining families: `pytest.raises` with `match`, imports, unused `noqa`, the rest.

  Verify: `ruff check` and `ty` pass.

  Result: 13 `pytest.raises` with a `match`, 8 on the failure they expect; the 5 on `CalledProcessError` match only "non-zero exit status", which every such error says, as the harness's commands carry no output on failure (test-hygiene D1 gives them their failure's own text); 4 split strings in collections parenthesized, the unused `noqa`s dropped; ty needed one rule renamed (`unsound-return`) and labgrid's attrs-declared `Environment` one targeted ignore.

## 3. Threads and tasks (design D4)

- [x] 3.1 Review the console reader, the login reader and the HTTP server for shared state; start the network probe's servers in a task group.

  Verify: each finding fixed with its invariant; the network probe's tests pass.

  Result: the console's buffer and end are read and written under its condition; the login's list is read after the reader is joined; the HTTP server's handlers share nothing with the test thread. The probe's servers run in a task group, and each connection is answered within the probe's timeout, then closed. `unit/test_netprobe.py` passes; the network suite exercises the servers.

- [x] 3.2 Keep the tests' environment outside the repository (D5).

  Verify: after `just check` and a test run, no `tests/.venv-*` exists in the checkout; a `path:` copy of it holds no environment; the code standards' tests pass.

  Result (2026-11-19): a `path:` copy of the worktree went from 755 MB to 7.9 MB; the code standards' 11 tests pass with the scratch copy on `ORBYT_TESTS_VENV`.

## 4. Verification

- [x] 4.1 `just check`, the unit suite, and the system suite on the emulator on 3.15t.

  Verify: all pass. Seen 2026-11-22: `just check` passes at 83fd67f; the unit suite (193 tests) and the system suite ran on 3.15t in the R4S's whole suite at 83fd67f, 2026-11-22 12:56 to 17:03Z: 623 passed, and 4 skipped as they are meant to (two traps only a ubsan build makes, the release keys only the ci profile carries, a test of LAN ports for a board with several); the Mac's 1-minute load over 247 samples had a median of 5.7, a 90th percentile of 10.1 and a maximum of 24.6.

- [ ] 4.2 CI's release verification: the one run on the stack's final head builds and tests both boards with this change (2026-11-19: CI runs only to verify a release; changes are verified locally until then).

  Verify: every job passes; the run is recorded in `docs/ci.md` for this change.

## Workflow follow-up

- The stack (orbyt-brand, orbyt-theme, nixpkgs-2605, python-style, then firmware-, patch-, test- and tooling-hygiene) is verified locally on its final head, then archived change by change in that order there; main fast-forwards to it and is pushed, Codeberg first, then GitHub, whose run on main is the release verification.
