# Design

## Context

`series_commit()` in `scripts/lib/upstream.sh` applies each patch of a series to an index with `git apply --cached`, and dies naming the first patch that does not apply. The index then holds the pinned commit with the patches before it applied.

## Goals / Non-Goals

**Goals:** a patch whose whole change upstream has made is reported as such, in the same step and with the same file name.

**Non-Goals:**
- A patch upstream made only part of. Neither direction applies, and the message stays the conflict's: telling which hunks went upstream is the maintainer's reading.
- The patches a series patch adds inside a package (`package/.../patches/`). Those apply when the package is prepared, and OpenWrt's own patch step reports one that is already applied ("Reversed (or previously applied) patch detected").

## Decisions

### D1. Reverse application decides

When `git apply --cached` refuses a patch, `git apply --cached --reverse --check` runs on the same index. If it succeeds, every line the patch adds is there and every line it removes is gone: upstream made the change. The message becomes `patch does not apply: <file>: upstream has its change (it applies in reverse); drop the patch`; otherwise it stays `patch does not apply: <file>`.

`--check` leaves the index as it was, and the step dies either way, so the commit a series makes and the tree's untouched files are unchanged (build/environment, "A patch that does not apply").

Alternative considered: comparing the patch's subject with upstream's log. Upstream rewords subjects (0045's update and OpenWrt's carried the same title, but 0023's fix did not), and a log search needs history the shallow fetch does not have.

### D2. The release flow's job

`docs/release-flow.md` names `host-toolchain`, which runs `just fetch patch` before any other job. `firmware` runs the same step again, so it would fail the same way.

## Risks / Trade-offs

- [Upstream made the same change with other lines around it] → The patch's context no longer matches in either direction, so it is reported as a conflict, the safe reading: refreshing it shows the change is there.
- [A patch whose reverse applies although upstream's change differs] → The reverse can apply only where every line the patch adds stands in its context, which is the patch's result; what upstream added beyond it is upstream's.
