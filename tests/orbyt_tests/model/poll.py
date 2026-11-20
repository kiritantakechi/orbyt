"""Waiting for a condition, the one way every test waits."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def _report(error: TimeoutError, notes: Callable[[], Iterable[str]]) -> None:
    """Add the report of ``notes`` to ``error``, whatever it does."""
    try:
        for note in notes():
            error.add_note(note)
    except Exception as failure:  # noqa: BLE001 # a report must not hide the timeout
        error.add_note(f"(the report failed: {failure!r})")


def until[T](
    probe: Callable[[], T | None],
    *,
    what: str,
    timeout: float,
    every: float = 1,
    notes: Callable[[], Iterable[str]] | None = None,
) -> T:
    """Call ``probe`` until it answers with content; return that answer.

    An empty answer is no answer yet, as Python's truth testing reads
    it: None, False, zero, an empty string or collection alike, so that
    a probe means what it would mean in a condition. A probe that
    reports an empty value as its result returns something with content
    instead, such as a comparison.

    Waits that share a budget pass what is left of it as ``timeout``.
    Past it, a TimeoutError says what was awaited, with what ``notes``
    reports then (test-hygiene D2). A probe that raises stops the wait:
    probes catch what they expect themselves.
    """
    limit = max(timeout, 0.0)
    deadline = time.monotonic() + limit
    while not (result := probe()):
        if time.monotonic() > deadline:
            error = TimeoutError(f"no {what} within {round(limit, 1):g} s")
            if notes is not None:
                _report(error, notes)
            raise error
        time.sleep(every)
    return result
