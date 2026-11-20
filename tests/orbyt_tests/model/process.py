"""Commands of the test environment, run with their output kept.

A command that fails carries what it said, its standard output and its
standard error, as notes of its error, so that a test expecting a
failure names it by that output, and a report shows it
(test-hygiene D1).
"""

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

type Argument = str | Path


def _note_output(
    error: subprocess.CalledProcessError | subprocess.TimeoutExpired,
) -> None:
    """Add what the command said to ``error``, a stream per note.

    A command past its time limit said it as bytes: the text mode of
    subprocess decodes only a whole output.
    """
    for stream, said in (("stdout", error.stdout), ("stderr", error.stderr)):
        if said is None:
            continue
        text = said.decode(errors="replace") if isinstance(said, bytes) else str(said)
        if text.strip():
            error.add_note(f"{stream}:\n{text.strip()}")


def run(
    *argv: Argument,
    timeout: float | None = None,
    stdin: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> str:
    """Run a command; return its standard output.

    A command that fails raises CalledProcessError, with its standard
    output and standard error as notes; one that runs past ``timeout``
    raises TimeoutExpired, with its command line and what it said until
    then as notes.
    """
    command = [str(argument) for argument in argv]
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin,
            env=env,
            cwd=cwd,
        ).stdout
    except subprocess.CalledProcessError as error:
        _note_output(error)
        raise
    except subprocess.TimeoutExpired as error:
        error.add_note(" ".join(command))
        _note_output(error)
        raise
