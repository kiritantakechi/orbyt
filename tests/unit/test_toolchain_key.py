"""Unit tests of scripts/toolchain-key.sh on a stand-in tree.

The key covers exactly what the cached host tools and cross toolchain
are built from (build-integrity D4, release-freshness D5): each input
moves it, and a change anywhere else keeps it (test-hygiene D8). The
stand-in tree holds the directories and files the script reads, each a
commit of its own, in a work directory outside the repository.
"""

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from orbyt_tests.model import git
from orbyt_tests.model.repository import REPO_DIR

if TYPE_CHECKING:
    from pathlib import Path

SCRIPT = REPO_DIR / "scripts" / "toolchain-key.sh"
# The target and subtarget the profiles' configuration selects
# (config/target.seed).
TARGET = "target/linux/rockchip"
# What the key covers, of the tree and of the packages feed.
TREE_INPUTS = (
    "tools/Makefile",
    "toolchain/Makefile",
    "target/linux/generic/config-6.12",
    "rules.mk",
    "include/toolchain-build.mk",
    "scripts/config.guess",
    f"{TARGET}/Makefile",
    f"{TARGET}/armv8/target.mk",
)
FEED_INPUTS = ("lang/golang/golang/Makefile", "lang/rust/Makefile")
# What it does not: the packages, another target's files, a subtarget's
# devices, and the rest of the packages feed.
TREE_ELSEWHERE = (
    "package/network/config/qosify/Makefile",
    "target/linux/mediatek/Makefile",
    f"{TARGET}/image/armv8.mk",
)
FEED_ELSEWHERE = ("net/socat/Makefile",)
OTHER_ENVIRONMENT = "/nix/store/0000000000000000000000000000000c-orbyt-build-inputs"


def _repository(root: Path, files: tuple[str, ...]) -> Path:
    for name in files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(f"# {name}\n")
    git.run(root, "init", "-q")
    git.commit(root, "the stand-in")
    return root


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Return a work directory: a stand-in tree and packages feed."""
    tree = tmp_path / "openwrt"
    tree.mkdir(parents=True)
    _repository(tree, (*TREE_INPUTS, *TREE_ELSEWHERE, "feeds.conf"))
    feed = tree / "feeds" / "packages"
    feed.mkdir(parents=True)
    _repository(feed, (*FEED_INPUTS, *FEED_ELSEWHERE))
    return tmp_path


def _key(workdir: Path, **env: str) -> str:
    result = subprocess.run(
        [SCRIPT],
        env={**os.environ, "ORBYT_WORKDIR": str(workdir), **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _change(repository: Path, name: str) -> None:
    with (repository / name).open("a") as file:
        file.write("# changed\n")
    git.commit(repository, f"change {name}")


@pytest.mark.parametrize("name", TREE_INPUTS)
def test_an_input_of_the_tree_moves_the_key(workdir: Path, name: str) -> None:
    before = _key(workdir)
    _change(workdir / "openwrt", name)
    assert _key(workdir) != before


@pytest.mark.parametrize("name", FEED_INPUTS)
def test_a_language_of_the_feed_moves_the_key(workdir: Path, name: str) -> None:
    before = _key(workdir)
    _change(workdir / "openwrt" / "feeds" / "packages", name)
    assert _key(workdir) != before


@pytest.mark.parametrize("name", TREE_ELSEWHERE)
def test_the_rest_of_the_tree_keeps_the_key(workdir: Path, name: str) -> None:
    before = _key(workdir)
    _change(workdir / "openwrt", name)
    assert _key(workdir) == before


@pytest.mark.parametrize("name", FEED_ELSEWHERE)
def test_the_rest_of_the_feed_keeps_the_key(workdir: Path, name: str) -> None:
    before = _key(workdir)
    _change(workdir / "openwrt" / "feeds" / "packages", name)
    assert _key(workdir) == before


def test_another_host_environment_moves_the_key(workdir: Path) -> None:
    assert _key(workdir) != _key(workdir, ORBYT_BUILD_INPUTS=OTHER_ENVIRONMENT)


def test_the_key_names_the_toolchain(workdir: Path) -> None:
    key = _key(workdir)
    assert key.startswith("key=toolchain-"), key
    assert len(key.removeprefix("key=toolchain-")) == 64
