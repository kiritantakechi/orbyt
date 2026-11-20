"""Unit tests of scripts/marks.sh on the paths it reads."""

import subprocess
from typing import TYPE_CHECKING

from orbyt_tests.model.repository import REPO_DIR

if TYPE_CHECKING:
    from pathlib import Path

MARKS_CHECK = REPO_DIR / "scripts" / "marks.sh"


def test_a_path_that_cannot_be_read_fails_the_check(tmp_path: Path) -> None:
    missing = tmp_path / "feed"
    result = subprocess.run(
        [MARKS_CHECK, missing], capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert f"cannot read every template under {missing}" in result.stderr
