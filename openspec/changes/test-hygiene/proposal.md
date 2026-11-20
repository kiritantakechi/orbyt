# Proposal

## Why

On 2026-11-20 the maintainer asked for the project's band-aids to be replaced by fixes at their causes, and for its code to be elegant, symmetric and modern. A review of the tests (`tests/`) found the harness waiting in nine hand-made loops beside its own polling helper, fixed sleeps standing for conditions a test can observe, setups that are not undone when they fail halfway, tests that depend on the order they run in, and one fact (a path, an address, a timeout, a layout) written down in up to seventeen places. Five `pytest.raises` added by python-style match only what every failed command says, because the harness's commands carry no output on failure. Two build tests skip in CI, where no build tree exists, while counting as covered.

## What Changes

- **One process wrapper** that carries a failed command's output; every expected failure is matched by that output.
- **One form of wait**: the polling helper gains the diagnostics its callers attach by hand, and the nine loops, the `sleep 1;` before detached commands and the tests' fixed sleeps become waits on their conditions.
- **Setups undone on failure**: the network's setup, the WireGuard and tailnet joins, the proxy's start and stop as a pair; the sandbox's daemons probed ready before use.
- **Tests independent of order**: the modules whose last test leaves a Pod or a disk behind, or whose first test sets something up for the rest, get fixtures that do it.
- **Each fact once**: router paths and the upgrade sequence in the harness (`Router.upgrade`), the repository's paths from `model.repository`, the LAN and ISP addresses, the sandbox's directory layout, EROFS' superblock layout, named timeouts.
- **Modules with one job**: emu-prepare apart from the emulator's runtime, the Releases stand-in's store apart from its server, the router's clock apart from its commands, the ISP's scripts and the containers' stress driver as checked files, the fake `gh` as a real module.
- **Asserts that prove their scenario**: the download's lower bound, MSS and DNS learning over IPv6, a trial failure's reboot into the other slot; duplicate tests merged or given their own check.
- **Build-tree tests** marked and run where the tree is; the cache key's scenarios tested by a unit test of `toolchain-key.sh`.
- **Leftovers**: PyYAML declared, tach pinned, `LG_EMU_DIR` named `ORBYT_EMU_DIR`, library asserts as raises, names that clash.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `testing/harness`: failed commands show their output; every wait has one form; the sandbox's daemons are ready before use; tests are independent of their order; tests that need the build tree are marked and run where it is.

## Impact

- `tests/orbyt_tests/` (every layer), the suites under `tests/`, `tests/pyproject.toml` and `uv.lock`, `tests/verified-elsewhere.toml`, `tests/pytest.toml` (the mark).
- `scripts/test.sh` and the justfile (`ORBYT_EMU_DIR`), `.github/workflows/build.yml` (the build-tree tests in the firmware job, deselected in the system suites).
- No firmware change.
