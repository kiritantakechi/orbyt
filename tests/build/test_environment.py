"""build/environment: entry points refuse macOS, stop at failures.

They patch what changed, pass their arguments on as given, and talk to
the clone's own repository.
"""

import hashlib
import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from orbyt_tests import spec
from orbyt_tests.model import git
from orbyt_tests.model.boards import load_all
from orbyt_tests.model.repository import REPO_DIR
from orbyt_tests.model.series import Series

if TYPE_CHECKING:
    from pathlib import Path

CAPABILITY = "build/environment"
SOURCE_ENTRY_POINTS = (
    "fetch",
    "patch",
    "config",
    "download",
    "build",
    "toolchain-build",
)


@pytest.fixture
def macos(tmp_path: Path) -> dict[str, str]:
    """Return an environment whose uname reports Darwin, like macOS."""
    uname = shutil.which("uname")
    assert uname is not None
    shim = tmp_path / "bin" / "uname"
    shim.parent.mkdir()
    shim.write_text(f'#!/bin/sh\n[ "$1" = -s ] && echo Darwin || exec {uname} "$@"\n')
    shim.chmod(0o755)
    return {**os.environ, "PATH": f"{shim.parent}:{os.environ['PATH']}"}


@spec(CAPABILITY, "Build only on Linux hosts", "Run directly on macOS")
@pytest.mark.parametrize("entry_point", SOURCE_ENTRY_POINTS)
def test_macos_is_refused(
    entry_point: str, macos: dict[str, str], tmp_path: Path
) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    result = subprocess.run(
        [str(REPO_DIR / "scripts" / f"{entry_point}.sh")],
        env={**macos, "ORBYT_WORKDIR": str(workdir)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "only on Linux" in result.stderr
    assert list(workdir.iterdir()) == []


@spec(CAPABILITY, "Common build entry points", "Substep fails")
def test_failed_step_stops_the_build(tmp_path: Path) -> None:
    not_a_directory = tmp_path / "work"
    not_a_directory.write_text("")
    result = subprocess.run(
        [
            "just",
            "--justfile",
            str(REPO_DIR / "justfile"),
            "build",
            load_all()[0].id,
            "dev",
        ],
        env={**os.environ, "ORBYT_WORKDIR": str(not_a_directory)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "scripts/fetch.sh" in result.stderr
    assert "scripts/patch.sh" not in result.stderr
    assert "scripts/build.sh" not in result.stderr


@spec(CAPABILITY, "Common build entry points", "An argument with a blank or a quote")
@pytest.mark.parametrize("shape", ["a command after a blank", "a quote"])
def test_an_argument_reaches_its_script_whole(tmp_path: Path, shape: str) -> None:
    justfile = REPO_DIR / "justfile"
    # No recipe pastes an argument into its command line: just passes
    # them on.
    dump = subprocess.run(
        ["just", "--justfile", justfile, "--dump", "--dump-format", "json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    recipes = json.loads(dump)["recipes"]
    pasted = [
        name
        for name, recipe in recipes.items()
        for line in recipe["body"]
        if any(not isinstance(fragment, str) for fragment in line)
    ]
    assert pasted == []
    # A board's name with more after it reaches boards.sh as one
    # argument.
    ran = tmp_path / "ran"
    board = load_all()[0].id
    argument = (
        f"{board}; touch {ran}" if shape == "a command after a blank" else f"{board}'s"
    )
    result = subprocess.run(
        ["just", "--justfile", justfile, "boards", argument],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert f"no board '{argument}'" in result.stderr
    assert not ran.exists()


@pytest.fixture
def series(tmp_path: Path) -> Series:
    """Return a scratch repository with its series applied once."""
    created = Series(tmp_path)
    applied = created.apply()
    assert applied.returncode == 0, applied.stderr
    return created


@spec(CAPABILITY, "Rebuild only what changed", "Re-apply an unchanged series")
def test_reapplied_series_writes_nothing(series: Series) -> None:
    head = series.head
    # Ignored build output stays, time included; an untracked file of no
    # commit goes.
    (series.repo / "po2lmo.o").write_bytes(b"built")
    (series.repo / "stray.patch").write_text("a patch a package would apply\n")
    before = series.age()
    applied = series.apply()
    assert applied.returncode == 0, applied.stderr
    assert series.head == head
    assert series.times() == {
        name: time for name, time in before.items() if name != "stray.patch"
    }


@spec(CAPABILITY, "Rebuild only what changed", "Change one patch")
def test_changed_patch_rewrites_its_files_only(series: Series) -> None:
    before = series.age()
    patch = series.patch(2)
    # The second patch changes b.txt another way and no longer adds
    # d.txt.
    head, *diffs = (
        patch.read_text()
        .replace("+two, patched", "+two, patched again")
        .split("\ndiff --git ")
    )
    kept = [diff for diff in diffs if not diff.startswith("a/d.txt ")]
    patch.write_text("\ndiff --git ".join([head, *kept]).rstrip("\n") + "\n")
    applied = series.apply()
    assert applied.returncode == 0, applied.stderr
    after = series.times()
    assert {name for name in before if after.get(name) != before[name]} == {
        "b.txt",
        "d.txt",
    }
    assert "d.txt" not in after
    assert (series.repo / "b.txt").read_text().endswith("two, patched again\n")


@spec(CAPABILITY, "Rebuild only what changed", "A patch that does not apply")
def test_failing_patch_leaves_the_tree(series: Series) -> None:
    head = series.head
    before = series.age()
    patch = series.patch(2)
    patch.write_text(patch.read_text().replace(" one\n", " uno\n"))
    applied = series.apply()
    assert applied.returncode != 0
    assert patch.name in applied.stderr
    assert series.head == head
    assert series.times() == before


# GitHub, standing in: the fork alone has a release, its assets the
# files in assets/; any other repository has none.
FORK = "someone/fork"
FORK_GH = f"""#!/bin/sh
here=$(dirname "$0")
case "$1" in
    api)
        [ "$2" = "repos/{FORK}/releases/latest" ] && exec cat "$here/latest.json"
        echo "gh: Not Found (HTTP 404)" >&2
        exit 1
        ;;
    release)
        shift 3
        while [ "$#" -gt 0 ]; do
            case "$1" in
                --repo) repository=$2 ;;
                --pattern) pattern=$2 ;;
                --dir) dir=$2 ;;
            esac
            shift 2
        done
        [ "$repository" = "{FORK}" ] || {{ echo "release not found" >&2; exit 1; }}
        cp "$here"/assets/$pattern "$dir/"
        ;;
esac
"""


@spec(CAPABILITY, "No machine of one maintainer's", "A fork's clone")
def test_a_fork_s_clone_fetches_the_fork_s_releases(tmp_path: Path) -> None:
    # The fork's clone: its scripts and boards, and a remote on GitHub
    # after one elsewhere.
    clone = tmp_path / "clone"
    for part in ("scripts", "boards"):
        shutil.copytree(REPO_DIR / part, clone / part)
    git.run(clone, "init", "-q")
    git.run(
        clone, "remote", "add", "codeberg", "https://codeberg.org/someone/orbyt.git"
    )
    git.run(clone, "remote", "add", "origin", f"https://github.com/{FORK}.git")
    board = load_all()[0]
    factory = f"{board.device}-factory.img.gz"
    ci = tmp_path / "work" / "out" / board.id / "ci"
    (ci / "targets").mkdir(parents=True)
    (ci / "manifest.json").write_text("{}")
    (ci / "targets" / factory).write_bytes(b"this build's factory image")
    (ci / "u-boot-qemu.bin").write_bytes(b"this build's emulator firmware")
    # The fork's latest release carries the board.
    gh = tmp_path / "gh"
    (gh / "assets").mkdir(parents=True)
    (gh / "gh").write_text(FORK_GH)
    (gh / "gh").chmod(0o755)
    image = b"the fork's factory image"
    (gh / "assets" / factory).write_bytes(image)
    digest = hashlib.sha256(image).hexdigest()
    (gh / "assets" / f"{board.device}-manifest.json").write_text(
        json.dumps({"files": {f"targets/{factory}": digest}})
    )
    assets = [{"name": path.name} for path in sorted((gh / "assets").iterdir())]
    (gh / "latest.json").write_text(json.dumps({"tag_name": "r1", "assets": assets}))
    environment = {
        name: value for name, value in os.environ.items() if name != "GITHUB_REPOSITORY"
    }
    result = subprocess.run(
        [clone / "scripts" / "drill-base.sh", board.id],
        capture_output=True,
        text=True,
        check=False,
        env={
            **environment,
            "PATH": f"{gh}{os.pathsep}{os.environ['PATH']}",
            "ORBYT_WORKDIR": str(tmp_path / "work"),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "drill base: r1, the latest stable release" in result.stderr
    base = tmp_path / "work" / "out" / board.id / "drill-base" / "targets"
    assert (base / factory).read_bytes() == image
