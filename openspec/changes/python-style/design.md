# Design

## Context

- The tests run under uv inside the FHS shell `orbyt-test-fhs` (uv's Pythons need a standard dynamic loader, which NixOS has only there), on the VM (aarch64) and on CI's runners (x86_64).
- On 2026-11-19, inside that shell: uv 0.13.4 runs `cpython-3.15.0+freethreaded`; the locked dependencies install on it, grpcio 1.84.1, tach 0.35.3 and PyYAML 6.0.3 built from source as they ship no 3.15t wheels; after `import labgrid, pydantic, pytest, yaml` the GIL is still disabled.
- ruff with the standard's configuration finds 2,579 things in the tests: 1,505 comment or docstring lines past 72 columns, 914 code lines past 88, 124 subprocess calls (S603, S607), 13 `pytest.raises` without `match`, and a dozen small ones. ty with the standard's rules finds nothing; ruff's upgrade rules for 3.15 find nothing to upgrade.
- Threads in the tests: the emulator's console reader (`device/emu.py`, a `Condition` and an `Event`), the login's stdout reader (`device/router.py`), the sandbox's HTTP server (`sandbox/fixtures.py`, `serve_forever` in a daemon thread). asyncio: the network probe's servers (`sandbox/netprobe.py`, `asyncio.gather`).

## Goals / Non-Goals

**Goals:**
- The tests on free-threaded 3.15, pinned tools, the standard's checker configuration, and every finding fixed rather than ignored, but for the project's documented exceptions.

**Non-Goals:**
- Publishing the tests' package: it ships no `py.typed`, as nothing outside this repository imports it; ty and tach check it here.
- Changing what any test checks: formatting, prose and the reviewed concurrency leave each test's assertions as they are.

## Decisions

### D1. The interpreter

`tests/.python-version` names `3.15t`, `requires-python` is `>=3.15`, and uv resolves the lock for it. A test in `tests/quality/` imports every module of the harness, and through them every dependency the tests use, and asserts the interpreter is a free-threaded 3.15 build with the GIL still off (`sys._is_gil_enabled()`), so that a dependency upgrade that turns it back on fails. `PYTHON_GIL=0` is never set: it would silence that check rather than make anything safe.

labgrid's pytest plugin imports its coordinator's client at load, and with it grpc, whose extension (built from source, as grpcio has no 3.15t wheel) turns the GIL back on for the whole process. The tests use no coordinator: they take labgrid's drivers alone. So the plugin is off (`-p no:labgrid`), and the device layer provides the one thing the tests took from it, the session's `target`, from the description emu-prepare writes (`target.yaml` in `LG_EMU_DIR`), closing labgrid's SSH connections at the session's end as the plugin did; `scripts/test.sh` no longer passes `--lg-env`. CI restores and saves uv's cache (`~/.cache/uv`) keyed by `uv.lock`, `.python-version` and the runner's architecture, so the source builds happen once per lock.

### D2. Pinned tools and the standard's configuration

`pyproject.toml` pins ruff, ty and pytest with `==`. `ruff.toml` takes the standard's: `py315`, 88 columns, `max-doc-length = 72`, the formatter-conflict ignores, the Google convention, `raises-require-match-for = ["*"]`, no implicit multi-line concatenation, no relative imports, the formatter's settings fixed (LF, double quotes, docstring code formatted). It keeps the project's reasons for its exceptions: S603 and S607 (the harness runs the FHS shell's pinned tools from PATH with arguments of its own), T201 for the command-line tools, and pydantic as a runtime-evaluated base. Tests take the standard's per-file ignores. `ty.toml` takes the standard's rule list and analysis options, with `python-platform = "linux"`.

### D3. Formatting and prose

`ruff format` at 88 settles the code. Comments and docstrings past 72 columns are rewrapped: a one-off script refills each prose paragraph of a comment block or docstring at 72, leaving list items (with their hanging indent), indented code, tables and URLs as they are; what it leaves past the limit is wrapped by hand. Code lines the formatter cannot shorten (long strings, comments after code) are split by hand.

### D4. Threads and tasks

- The console reader shares its buffer under its `Condition`; the review checks that every read and write of the buffer holds it.
- The login reader appends once and is joined before its list is read.
- The HTTP server's handler threads share only what the server hands them; the review checks what the test thread reads of it.
- The network probe starts its servers in an `asyncio.TaskGroup` instead of `gather`, so that one server's failure cancels the others.

Each finding is fixed with the invariant it breaks stated; none is fixed by a `time.sleep`.

## Risks / Trade-offs

- [Source builds lengthen a cold CI job] → uv's cache keyed by the lock; the builds recur only when the lock or the interpreter changes.
- [A dependency's free-threaded build is less tested] → The GIL assertion tells when one turns the GIL back on; a crash would show in the suites, which all run on it.
- [A rewrapped comment changes its meaning] → The script refills only prose paragraphs; the diff is reviewed in full.
