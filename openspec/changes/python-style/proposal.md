# Proposal

## Why

The maintainer asked on 2026-11-19 for the Python code to be checked and refactored to a modern standard, their Python style standard (CPython 3.15, free-threaded; ruff and ty as the house checkers; PEP 8's prose limits). The tests (`tests/`, 100 files, about 18,500 lines) already pass every ruff rule and ty, but on CPython 3.14, at 100 columns, with comments and docstrings to 100 too, tools pinned by lower bounds, and an `asyncio.gather` where the standard asks for a task group.

## What Changes

- **Free-threaded CPython 3.15** for the tests, from uv; the GIL is asserted off once the dependencies are imported. grpcio, tach and PyYAML have no 3.15t wheels yet and build from source; CI keeps uv's cache so that each job builds them once per lock.
- **ruff, ty and pytest pinned exactly**, at their current releases (0.17.5, 0.0.106, 9.2.0).
- **The standard's configuration**: ruff at 88 columns for code and 72 for comments and docstrings (W505), the Google docstring convention, `pytest.raises` with a `match` everywhere, no relative imports, the formatter's settings fixed; ty with its off-by-default rules named one by one and the strict analysis options. The project's documented exceptions stay (subprocesses on PATH, the command-line tools' output).
- **The code brought to it**: formatted at 88; every comment and docstring rewrapped at 72; the remaining findings fixed by rule family.
- **Shared state and tasks reviewed** where the tests use threads (the console reader, the login reader, the sandbox's HTTP server) and asyncio (the network probe's servers, started in a task group).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality/code-standards`: a requirement for the tests' interpreter: free-threaded CPython 3.15, tools pinned exactly, the GIL still off after the dependencies' import.

## Impact

- `tests/`: `pyproject.toml`, `uv.lock`, `.python-version`, `ruff.toml`, `ty.toml`, every Python file (formatting and prose), `orbyt_tests/sandbox/netprobe.py` (task group), a test for the interpreter in `tests/quality/`.
- `.github/workflows/build.yml` and `check.yml`: uv's cache, keyed by the lock and the interpreter.
- No firmware change: the image's packages are not touched.
