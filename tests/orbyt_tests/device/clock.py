"""The router's clock, set to the runner's (snapshot-return D2).

The emulated internet has no time server, so the harness sets the
router's clock itself, after each boot and each return to the snapshot.
"""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router

# How far the router's clock may be off the runner's at a return to the
# snapshot (testing/emulation "The router back at its snapshot").
CLOCK_SKEW = 2.0
# A reading of the router's clock counts as precise once its round trip
# is this short, and is taken this often at most. date -s sets whole
# seconds, half of one off at most once rounded, and the emulated clock
# runs over a percent slow, a few tenths more by the time it is checked:
# a second (snapshot-return D2).
CLOCK_ROUND_TRIP = 1.0
CLOCK_READINGS = 5
CLOCK_RESOLUTION = 1.0
# The router's clock to the nanosecond: the image's BusyBox date prints
# whole seconds only (no FEATURE_DATE_NANO), ucode's clock() gives the
# nanoseconds.
READ_CLOCK = "ucode -e 'printf(\"%d.%09d\", ...clock())'"


@dataclass(frozen=True, slots=True)
class ClockReading:
    """The runner's clock minus the router's, plus its round trip.

    The round trip is that of the reading that measured the offset.
    """

    offset: float
    round_trip: float


def _reading(router: Router) -> ClockReading:
    before = time.time()
    shown = float(router.run(READ_CLOCK))
    after = time.time()
    return ClockReading((before + after) / 2 - shown, after - before)


def read_clock(router: Router) -> ClockReading:
    """Read how far the router's clock is behind the runner's.

    The router read its clock somewhere within the reading's round
    trip, so the offset is as precise as half of it. Of a few
    readings the first quick one counts, else the quickest, as NTP
    prefers its quickest exchanges; the first also makes a
    connection that may take a while.
    """
    best = _reading(router)
    for _ in range(CLOCK_READINGS - 1):
        if best.round_trip <= CLOCK_ROUND_TRIP:
            break
        best = min(best, _reading(router), key=lambda reading: reading.round_trip)
    return best


def set_clock(router: Router) -> None:
    """Set the router's clock to the runner's.

    NTP does the same on a router in service.

    The emulated internet has no time server: a router boots with
    the time of its newest file in /etc, and a restored snapshot
    rewinds the clock to when it was taken. What is signed now (a
    release's certificate) is valid from now on. The clock is
    stepped by the offset a reading measured, relative to the
    router's own, so how long the command takes to arrive does not
    count, and a second reading checks it to the precision the two
    readings allow (snapshot-return D2).
    """
    measured = read_clock(router)
    step = (
        "$(ucode -e 'let c = clock(); "
        f"print(int(c[0] + c[1] / 1e9 + {measured.offset:.3f} + 0.5))')"
    )
    router.run(f"date -s @{step} >/dev/null")
    checked = read_clock(router)
    precision = CLOCK_RESOLUTION + (measured.round_trip + checked.round_trip) / 2
    if abs(checked.offset) > precision:
        side = "behind" if checked.offset > 0 else "ahead of"
        msg = (
            f"the router's clock is {abs(checked.offset):.1f} s {side}"
            " the runner's after setting it, where its readings allow"
            f" {precision:.1f} s"
        )
        raise AssertionError(msg)
