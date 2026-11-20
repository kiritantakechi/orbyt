"""The build's and the release's outputs as data (module-boundaries D7).

The tests run on real files.

The fixtures are files a build and a release wrote: the R4S's dev
build's manifest and warnings report, the record of the toolchain it was
built with, the emulator directory emu-prepare made from it, and a
release assembled from it.
"""

from typing import TYPE_CHECKING

from orbyt_tests.model.boards import load
from orbyt_tests.model.data import read_json, write_json
from orbyt_tests.model.outputs import (
    EmulationSource,
    Manifest,
    Release,
    ToolchainRecord,
)
from orbyt_tests.model.repository import TESTS_DIR
from orbyt_tests.model.undefined_behavior import Diagnostic

if TYPE_CHECKING:
    from pathlib import Path

FIXTURES = TESTS_DIR / "fixtures"


def test_a_build_s_manifest_reads_as_one() -> None:
    manifest = read_json(FIXTURES / "manifest.json", Manifest)
    assert (manifest.board, manifest.profile, manifest.build) == ("r4s", "dev", "r4s")
    # The flags are the compiler's words, in the order it reads them.
    assert manifest.cflags[:2] == ("-Os", "-pipe")
    assert manifest.kernel_cflags[-1] == "-O2"
    assert any(path.endswith("-factory.img.gz") for path in manifest.files)


def test_a_manifest_writes_back_as_the_build_wrote_it(tmp_path: Path) -> None:
    manifest = read_json(FIXTURES / "manifest.json", Manifest)
    write_json(tmp_path / "manifest.json", manifest)
    assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == (
        FIXTURES / "manifest.json"
    ).read_text(encoding="utf-8")


def test_an_emulation_source_reads_as_one() -> None:
    source = read_json(FIXTURES / "source.json", EmulationSource)
    assert source.image.is_relative_to(source.build)
    assert source.firmware.is_relative_to(source.build)


def test_a_toolchain_record_reads_as_one() -> None:
    record = read_json(FIXTURES / "orbyt-toolchain.json", ToolchainRecord)
    assert "-mcpu=generic" in record.cflags
    assert record.rust_std is not None


def test_a_release_reads_as_one() -> None:
    release = read_json(FIXTURES / "release.json", Release)
    assert release.boards == ("r4s",)
    assert f"{load('r4s').device}-manifest.json" in release.assets


def test_a_warnings_report_reads_as_a_list() -> None:
    warnings = read_json(FIXTURES / "warnings.json", list[Diagnostic])
    assert warnings
    assert all(warning.package and warning.line > 0 for warning in warnings)
