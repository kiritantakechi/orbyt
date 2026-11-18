# Tasks

## 1. Interpreter and tools (design D1, D2)

- [x] 1.1 Pin ruff, ty and pytest exactly; move the tests to `3.15t` and resolve the lock; add the interpreter's test to `tests/quality/`; turn labgrid's pytest plugin off and give the device layer the session's `target`.

  Verify: `uv sync --locked` installs on 3.15t in the FHS shell; the new test passes, and fails with the GIL forced on (`PYTHON_GIL=1`); the unit and quality suites pass.

  Result (2026-11-19): with labgrid's plugin on, the new test failed: grpc, imported by it, turned the GIL on. With it off: passes, fails under `PYTHON_GIL=1`.

- [ ] 1.2 Cache uv's cache in CI's jobs that sync the tests' environment.

  Verify: the second run on the same lock builds no distribution.

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

  Result: 13 `pytest.raises` with a `match` on the failure they expect, 4 split strings in collections parenthesized, the unused `noqa`s dropped; ty needed one rule renamed (`unsound-return`) and labgrid's attrs-declared `Environment` one targeted ignore.

## 3. Threads and tasks (design D4)

- [x] 3.1 Review the console reader, the login reader and the HTTP server for shared state; start the network probe's servers in a task group.

  Verify: each finding fixed with its invariant; the network probe's tests pass.

  Result: the console's buffer and end are read and written under its condition; the login's list is read after the reader is joined; the HTTP server's handlers share nothing with the test thread. The probe's servers run in a task group, and each connection is answered within the probe's timeout, then closed. `unit/test_netprobe.py` passes; the network suite exercises the servers.

## 4. Verification

- [ ] 4.1 `just check`, the unit suite, and the system suite on the emulator on 3.15t.

  Verify: all pass.

- [ ] 4.2 Run CI's build on this change's branch for both boards.

  Verify: every job passes; the run is recorded in `docs/ci.md`.

## Workflow follow-up

- After nixpkgs-2605 is merged: merge main into this branch, sync the delta, archive, merge and push Codeberg first, then GitHub.
