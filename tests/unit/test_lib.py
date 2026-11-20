"""The shell library's modules (scripts/lib/).

They are tree, caches, toolchain, seeds and runs.
"""

import hashlib
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
import yaml

from orbyt_tests.model import git
from orbyt_tests.model.boards import load_all
from orbyt_tests.model.repository import REPO_DIR
from orbyt_tests.model.shell import awk_program, library

if TYPE_CHECKING:
    import subprocess

WORKFLOW = REPO_DIR / ".github" / "workflows" / "build.yml"
PROFILES = [
    line.split(":")[0]
    for line in (REPO_DIR / "config" / "profiles").read_text().splitlines()
    if line and not line.startswith("#")
]


def _missing_lines(tmp_path: Path, wanted: str, actual: str) -> list[str]:
    """Return what missing_config_lines finds missing from ``actual``.

    It looks for the lines of ``wanted``.
    """
    (tmp_path / "wanted").write_text(wanted)
    (tmp_path / "actual").write_text(actual)
    result = library(
        "tree", 'missing_config_lines "$1" "$2"', "wanted", "actual", cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    return [line.strip() for line in result.stdout.splitlines()]


def test_every_seed_line_is_checked(tmp_path: Path) -> None:
    # Packages' symbols hold "-", "." and "+": each such line the
    # configuration lacks, or holds with another value, is named like
    # any other.
    wanted = """\
# The seed's comments are no options.
CONFIG_TARGET_rockchip=y
# CONFIG_PACKAGE_openwrt-keyring is not set
CONFIG_PACKAGE_kmod-nf-conntrack6=m
CONFIG_PACKAGE_libstdcpp6.x+=y
CONFIG_PACKAGE_orbyt-keyring=y
"""
    actual = """\
CONFIG_TARGET_rockchip=y
CONFIG_PACKAGE_openwrt-keyring=y
CONFIG_PACKAGE_orbyt-keyring=y
"""
    assert _missing_lines(tmp_path, wanted, actual) == [
        "# CONFIG_PACKAGE_openwrt-keyring is not set",
        "CONFIG_PACKAGE_kmod-nf-conntrack6=m",
        "CONFIG_PACKAGE_libstdcpp6.x+=y",
    ]


# An output directory's apks, and whether each is stale: of packages the
# configuration builds, with and without an ABI version and a release,
# the kernel's, which is in neither file; and two left by earlier
# builds, a kmod no longer selected and a library under its earlier ABI
# version.
APKS = {
    "targets/packages/kernel-6.18.55~6fcccb57-r1.apk": False,
    "targets/packages/kmod-dummy-6.18.55-r1.apk": False,
    "targets/packages/kmod-gone-6.18.52-r1.apk": True,
    "packages/base/libjson-c5-0.19-r3.apk": False,
    "packages/base/libjson-c4-0.18-r1.apk": True,
    "packages/base/resolveip-2.apk": False,
    "packages/luci/luci-i18n-base-zh-cn-26.297.60563~4bfd110.apk": False,
}
SELECTED = """\
CONFIG_PACKAGE_kmod-dummy=m
# CONFIG_PACKAGE_kmod-gone is not set
CONFIG_PACKAGE_libjson-c=y
CONFIG_PACKAGE_luci-i18n-base-zh-cn=y
CONFIG_PACKAGE_resolveip=y
"""
PACKAGEINFO = """\
Source-Makefile: package/kernel/linux/Makefile

Package: kmod-dummy
Version: <LINUX_VERSION>-r
@@

Package: kmod-gone
Version: <LINUX_VERSION>-r
@@

Source-Makefile: package/libs/libjson-c/Makefile

Package: libjson-c
Version: 0.19-r3
ABI-Version: 5
@@

Source-Makefile: package/network/utils/resolveip/Makefile

Package: resolveip
Version: 2
@@

Source-Makefile: feeds/luci/modules/luci-base/Makefile

Package: luci-i18n-base-zh-cn
Version: 26.297.60563~4bfd110
@@
"""


def _stale(tmp_path: Path, apks: list[str]) -> subprocess.CompletedProcess[str]:
    """Return what stale_packages finds among ``apks``.

    The output directory is under ``tmp_path``.
    """
    (tmp_path / "config").write_text(SELECTED)
    (tmp_path / "packageinfo").write_text(PACKAGEINFO)
    for apk in apks:
        (tmp_path / "bin" / apk).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "bin" / apk).touch()
    return library(
        "tree", 'stale_packages "$@"', "bin", "config", "packageinfo", cwd=tmp_path
    )


def test_the_packages_the_configuration_no_longer_builds_are_stale(
    tmp_path: Path,
) -> None:
    result = _stale(tmp_path, list(APKS))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == sorted(
        f"bin/{apk}" for apk, stale in APKS.items() if stale
    )


def test_an_apk_without_a_version_fails(tmp_path: Path) -> None:
    result = _stale(tmp_path, ["packages/base/odd.apk"])
    assert result.returncode != 0
    assert "cannot tell the package of bin/packages/base/odd.apk" in result.stderr


def test_an_output_directory_not_made_yet_holds_no_stale_package(
    tmp_path: Path,
) -> None:
    result = library(
        "tree", 'stale_packages "$@"', "bin", "config", "packageinfo", cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_trim_keeps_what_the_build_used(tmp_path: Path) -> None:
    # The caches refresh an entry's time when they use it: sccache on
    # every hit, Go only an entry more than an hour old. What a build
    # begun at `start` used is newer than `start` in sccache's cache,
    # and than the hour before it in Go's.
    start = 1_700_000_000
    tree = tmp_path / "openwrt"
    entries = {
        "tmp/go-build/aa/used": start - 1800,
        "tmp/go-build/aa/unused": start - 3600,
        "tmp/go-build/bb/new": start + 60,
        ".sccache/a/used": start + 60,
        ".sccache/a/unused": start,
    }
    for name, mtime in entries.items():
        entry = tree / name
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(name)
        os.utime(entry, (mtime, mtime))
    (tree / ".config").touch()
    result = library("cache", 'compiler_cache_trim "$1" "$2"', str(tree), str(start))
    assert result.returncode == 0, result.stderr
    kept = {str(path.relative_to(tree)) for path in tree.rglob("*") if path.is_file()}
    assert kept == {
        ".config",
        "tmp/go-build/aa/used",
        "tmp/go-build/bb/new",
        ".sccache/a/used",
    }


def _rust_std(tree: Path) -> str:
    """Return what toolchain_rust_std makes of the Rust libraries.

    The libraries are those in ``tree``.
    """
    result = library("toolchain", 'toolchain_rust_std "$1"', str(tree))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_an_uninstalled_rust_has_no_standard_library(tmp_path: Path) -> None:
    # Rust's uninstaller removes the libraries and leaves their
    # directories.
    target = "aarch64-unknown-linux-musl"
    lib = tmp_path / "staging_dir" / "hostpkg" / "lib" / "rustlib" / target / "lib"
    lib.mkdir(parents=True)
    assert _rust_std(tmp_path) == ""
    (lib / "libstd.rlib").write_bytes(b"std")
    listing = f"{hashlib.sha256(b'std').hexdigest()}  ./{target}/lib/libstd.rlib\n"
    assert _rust_std(tmp_path) == hashlib.sha256(listing.encode()).hexdigest()


def test_toolchain_stages_name_what_only_toolchain_build_builds(tmp_path: Path) -> None:
    # A board's time log: what tools/, toolchain/ or the Go and Rust
    # host toolchains ran is named once per stage; the board's own
    # packages are not. Host builds name their stages host-* (patch
    # 0042).
    log = tmp_path / "build-time-r4s.tsv"
    log.write_text(
        "".join(
            f"{time}\t{event}\t{stage}\t{name}\n"
            for time, event, stage, name in (
                (1, "begin", "host-prepare", "tools/flock"),
                (2, "end", "host-prepare", "tools/flock"),
                (3, "begin", "host-compile", "toolchain/gcc/final"),
                (4, "begin", "host-compile", "package/feeds/packages/golang1.27"),
                (5, "begin", "host-compile", "package/feeds/packages/rust"),
                (6, "begin", "host-compile", "package/feeds/packages/rust"),
                (7, "begin", "compile", "package/feeds/orbyt/honk"),
                (8, "begin", "compile", "package/feeds/packages/golang-protobuf"),
                (9, "begin", "compile", "package/feeds/orbyt/einat"),
                (10, "begin", "compile", "target/linux"),
            )
        )
    )
    result = library("toolchain", 'toolchain_stages "$1"', str(log))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "package/feeds/packages/golang1.27 [host-compile]",
        "package/feeds/packages/rust [host-compile]",
        "toolchain/gcc/final [host-compile]",
        "tools/flock [host-prepare]",
    ]


def _tree(command: str, *args: str) -> None:
    """Run ``command`` with the tree module loaded.

    Its arguments are ``args``.
    """
    result = library("tree", command, *args)
    assert result.returncode == 0, result.stderr


OLD = 1_700_000_000


def test_an_unchanged_link_keeps_its_time(tmp_path: Path) -> None:
    link = tmp_path / "link"
    _tree('symlink "$1" "$2"', "target", str(link))
    os.utime(link, (OLD, OLD), follow_symlinks=False)
    _tree('symlink "$1" "$2"', "target", str(link))
    assert link.lstat().st_mtime == OLD
    _tree('symlink "$1" "$2"', "other", str(link))
    assert link.readlink() == Path("other")


def test_an_unchanged_file_keeps_its_time(tmp_path: Path) -> None:
    file = tmp_path / "file"
    file.write_text("same\n")
    os.utime(file, (OLD, OLD))
    _tree('printf "same\\n" | update_file "$1"', str(file))
    assert file.stat().st_mtime == OLD
    _tree('printf "other\\n" | update_file "$1"', str(file))
    assert file.read_text() == "other\n"
    assert file.stat().st_mtime > OLD
    assert sorted(path.name for path in tmp_path.iterdir()) == ["file"]


def test_an_unchanged_configuration_keeps_its_time(tmp_path: Path) -> None:
    # A stand-in tree whose defconfig keeps the seed as the
    # configuration.
    tree = tmp_path / "openwrt"
    (tree / "tmp").mkdir(parents=True)
    (tree / "Makefile").write_text("defconfig:\n\t@:\n")
    config = tree / ".config"
    seed = tmp_path / "seed"

    def configure(text: str) -> float:
        seed.write_text(text)
        _tree('configure_tree "$1" "$2"', str(tree), str(seed))
        return config.stat().st_mtime

    board = 'CONFIG_BUILD_SUFFIX="r4s"\nCONFIG_X=y\n'
    configure(board)
    # The build directories were configured with it long ago.
    for path in (config, tree / "tmp" / "orbyt-config-r4s"):
        os.utime(path, (OLD, OLD))
    assert configure("CONFIG_X=y\n") > OLD
    assert configure(board) == OLD
    assert configure(board.replace("=y", "=n")) > OLD
    assert configure(board) > OLD


def test_go_cache_counts_what_go_compiled(tmp_path: Path) -> None:
    # Go writes an action entry, its creation time inside, only for an
    # action it ran; a hit refreshes an old entry's file time alone.
    start = 1_700_000_000
    tree = tmp_path / "openwrt"
    cache = tree / "tmp" / "go-build"
    entries = (
        ("aa", "11", 10, start - 86_400, b"compiled"),  # a hit
        ("bb", "22", 10, start + 60, b"compiled"),  # compiled anew
        ("cc", "e3", 0, start + 60, None),  # an action with no output
        ("dd", "44", 514, start + 60, b"go index v2 ..."),  # sources unpacked anew
    )
    for action, output, size, created, data in entries:
        action_id, output_id = action * 32, output * 32
        entry = cache / action / f"{action_id}-a"
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(
            f"v1 {action_id} {output_id} {size:20d} {created * 10**9:20d}\n"
        )
        if data is not None:
            (cache / output).mkdir(exist_ok=True)
            (cache / output / f"{output_id}-d").write_bytes(data)
    for path in cache.rglob("*-[ad]"):
        os.utime(path, (start + 120, start + 120))
    result = library("cache", 'go_cache_compiled "$1" "$2"', str(tree), str(start))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def _compose(profile: str, board: str, tmp_path: Path) -> str:
    """Return compose_seeds' seed for ``profile`` and ``board``.

    The result is "" when there is none.
    The tree is ``tmp_path``'s openwrt.
    """
    tree = tmp_path / "openwrt"
    tree.mkdir(exist_ok=True)
    output = tmp_path / f"{profile}-{board or 'neutral'}.config"
    result = library(
        "seeds", 'compose_seeds "$@"', str(tree), profile, board, str(output)
    )
    assert result.returncode == 0, result.stderr
    return output.read_text()


def _options(seed: str) -> list[str]:
    """Return the option each line of ``seed`` sets, in order."""
    return [
        match.group(1) or match.group(2)
        for line in seed.splitlines()
        if (
            match := re.fullmatch(
                r"(CONFIG_[^= ]+)=.*|# (CONFIG_[^ ]+) is not set", line
            )
        )
    ]


def test_a_later_seed_replaces_an_earlier_line(tmp_path: Path) -> None:
    # The later seed's line stands where it stands; comments stay.
    (tmp_path / "a.seed").write_text(
        '# a\nCONFIG_A=y\n# CONFIG_B is not set\nCONFIG_C="-O2"\nCONFIG_D=m\n'
    )
    (tmp_path / "b.seed").write_text('# b\nCONFIG_B=y\nCONFIG_C="-O3"\n')
    result = awk_program("merge-seeds.awk", "a.seed", "b.seed", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (
        result.stdout
        == '# a\nCONFIG_A=y\nCONFIG_D=m\n# b\nCONFIG_B=y\nCONFIG_C="-O3"\n'
    )


def test_a_seed_appends_to_a_string_option(tmp_path: Path) -> None:
    # The appended text joins the value so far, where the append stands.
    (tmp_path / "a.seed").write_text('CONFIG_C="-O2 -pipe"\nCONFIG_D=m\n')
    (tmp_path / "b.seed").write_text('# b\nCONFIG_C+=" -fsanitize=undefined"\n')
    result = awk_program("merge-seeds.awk", "a.seed", "b.seed", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (
        result.stdout == 'CONFIG_D=m\n# b\nCONFIG_C="-O2 -pipe -fsanitize=undefined"\n'
    )


def test_a_name_with_a_plus_is_no_append(tmp_path: Path) -> None:
    (tmp_path / "a.seed").write_text("# CONFIG_PACKAGE_g++ is not set\n")
    (tmp_path / "b.seed").write_text("CONFIG_PACKAGE_g++=y\n")
    result = awk_program("merge-seeds.awk", "a.seed", "b.seed", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "CONFIG_PACKAGE_g++=y\n"


@pytest.mark.parametrize("earlier", ["", "CONFIG_C=y\n", "# CONFIG_C is not set\n"])
def test_an_append_to_no_string_value_fails(earlier: str, tmp_path: Path) -> None:
    (tmp_path / "a.seed").write_text(earlier)
    (tmp_path / "b.seed").write_text('CONFIG_C+=" -O3"\n')
    result = awk_program("merge-seeds.awk", "a.seed", "b.seed", cwd=tmp_path)
    assert result.returncode != 0
    assert "CONFIG_C appends to no string value" in result.stderr


def test_the_ubsan_profile_sanitizes_the_toolchain_s_flags(tmp_path: Path) -> None:
    def optimization(profile: str) -> str:
        composed = _compose(profile, "r4s", tmp_path)
        found = re.search(
            r'^CONFIG_TARGET_OPTIMIZATION="(.*)"$', composed, re.MULTILINE
        )
        assert found is not None, profile
        return str(found[1])

    sanitizers = " -fsanitize=undefined -fsanitize-trap=undefined"
    assert optimization("ubsan") == optimization("dev") + sanitizers


@pytest.mark.parametrize("profile", PROFILES)
def test_a_composed_seed_holds_one_line_per_option(
    profile: str, tmp_path: Path
) -> None:
    # configure_tree checks every line of it against the configuration,
    # which can hold only one value per option.
    for board in ("", *(board.id for board in load_all())):
        options = _options(_compose(profile, board, tmp_path))
        assert len(options) == len(set(options)), (profile, board)


def test_board_only_seeds_leave_the_toolchain_alone(tmp_path: Path) -> None:
    # The toolchain is built from the board-neutral composition, which
    # its key hashes: the ubsan profile's is the dev profile's, so is
    # its toolchain.
    assert _compose("ubsan", "", tmp_path) == _compose("dev", "", tmp_path)


def test_board_only_seeds_build_apart(tmp_path: Path) -> None:
    # The board's -mcpu still comes last, after the ubsan seed's flags,
    # and the build has directories of its own.
    seed = _compose("ubsan", "r4s", tmp_path).splitlines()
    assert (
        'CONFIG_EXTRA_OPTIMIZATION="-fno-caller-saves -fno-plt -O3 -mcpu='
        in "\n".join(seed)
    )
    assert 'CONFIG_BUILD_SUFFIX="r4s_ubsan"' in seed
    assert f'CONFIG_BINARY_FOLDER="{tmp_path / "openwrt"}/bin/r4s_ubsan"' in seed
    assert 'CONFIG_BUILD_SUFFIX="r4s"' in _compose("dev", "r4s", tmp_path).splitlines()


def _paths(event: str) -> list[str]:
    """Return build.yml's paths for an event.

    Its key ``on`` is read by YAML 1.1 as true.
    """
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return cast("list[str]", workflow[True][event]["paths"])


def _github_glob(pattern: str) -> re.Pattern[str]:
    """Return a GitHub filter pattern's regular expression.

    ``**`` crosses slashes, ``*`` does not.
    """
    parts = re.split(r"(\*\*/|\*\*|\*)", pattern)
    wildcards = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*"}
    return re.compile("".join(wildcards.get(part, re.escape(part)) for part in parts))


def _github_reads(patterns: list[str], path: str) -> bool:
    """Say whether a change to ``path`` runs a workflow, as GitHub does.

    The workflow is filtered by ``patterns``.
    """
    runs = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        if _github_glob(pattern.removeprefix("!")).fullmatch(path):
            runs = not negated
    return runs


def test_the_library_reads_the_workflow_s_paths() -> None:
    result = library("runs", "build_paths")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == _paths("push") == _paths("pull_request")


# Paths in and out of each pattern of the workflow's list.
SAMPLE_PATHS = (
    "scripts/build.sh",
    "tests/build/test_ci.py",
    "upstream.lock",
    "openspec/specs/build/ci/spec.md",
    "openspec/config.yaml",
    "docs/ci.md",
    "docs/patches.md",
    "docs/services.md",
    "docs/old/patches.md",
    "README.md",
    "feed/utils/orbyt-ab/README.md",
    "docsite/index.html",
    "openspec.lock",
)


def test_build_reads_answers_as_github_does() -> None:
    patterns = _paths("push")
    script = (
        'for path in "$@"; do if build_reads "$path"; then echo yes;'
        " else echo no; fi; done"
    )
    result = library("runs", script, *SAMPLE_PATHS)
    assert result.returncode == 0, result.stderr
    answers = dict(zip(SAMPLE_PATHS, result.stdout.split(), strict=True))
    assert answers == {
        path: "yes" if _github_reads(patterns, path) else "no" for path in SAMPLE_PATHS
    }
    assert {path for path, answer in answers.items() if answer == "no"} == {
        "openspec/specs/build/ci/spec.md",
        "openspec/config.yaml",
        "docs/ci.md",
        "docs/old/patches.md",
        "README.md",
        "feed/utils/orbyt-ab/README.md",
    }


def _repository_of(clone: Path, **env: str) -> subprocess.CompletedProcess[str]:
    """Run github_repository on ``clone``, as outside CI."""
    environment = {
        name: value for name, value in os.environ.items() if name != "GITHUB_REPOSITORY"
    }
    return library(
        "github", 'github_repository "$1"', str(clone), env={**environment, **env}
    )


def test_the_github_repository_is_the_clone_s_own(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    clone.mkdir()
    git.run(clone, "init", "-q")
    # A clone with no remote on GitHub names none.
    git.run(
        clone, "remote", "add", "codeberg", "https://codeberg.org/someone/orbyt.git"
    )
    without = _repository_of(clone)
    assert without.returncode != 0
    assert "GITHUB_REPOSITORY" in without.stderr
    # A fork's clone names the fork, by either form of URL.
    git.run(clone, "remote", "add", "origin", "https://github.com/someone/fork.git")
    assert _repository_of(clone).stdout.strip() == "someone/fork"
    git.run(clone, "remote", "set-url", "origin", "git@github.com:someone/fork")
    assert _repository_of(clone).stdout.strip() == "someone/fork"
    # CI says which.
    assert _repository_of(clone, GITHUB_REPOSITORY="ci/run").stdout.strip() == "ci/run"
