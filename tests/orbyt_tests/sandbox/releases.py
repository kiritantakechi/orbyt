"""The releases the stand-in for GitHub's Releases API serves.

A repository's releases are directories under ``<root>/<owner>/<repo>``,
each an assembled release (release-publish.sh) that ``publish`` put
there, with the time it did in ``.published``. A release with a ``.cut``
file sends only that many bytes of each asset, then drops the
connection: a sync interrupted halfway. The API (``releases_api``)
records every download in the release's ``.downloads``, which
``downloads`` reads. The tests change the store; the API only reads it.
"""

import os
import shutil
import time
from typing import TYPE_CHECKING

from orbyt_tests.model.data import read_json, write_json
from orbyt_tests.model.outputs import RELEASE_FILE, Release

if TYPE_CHECKING:
    from pathlib import Path

DOWNLOADS = ".downloads"
PUBLISHED = ".published"
CUT = ".cut"


def publish(
    root: Path,
    repository: str,
    release: Path,
    *,
    tag: str | None = None,
    prerelease: bool | None = None,
) -> str:
    """Publish an assembled release in ``repository``; return its tag.

    ``repository`` is owner/repo, and the release becomes its newest.
    ``tag`` and ``prerelease`` publish it as another release: one
    assembled build stands for several. Its files are linked, not copied
    (none changes).
    """
    info = read_json(release / RELEASE_FILE, Release)
    info = info.model_copy(
        update={
            "tag": tag or info.tag,
            "prerelease": info.prerelease if prerelease is None else prerelease,
        }
    )
    target = root / repository / info.tag
    shutil.copytree(release, target, copy_function=os.link)
    write_json(target / RELEASE_FILE, info)
    (target / PUBLISHED).write_text(str(time.time()))
    return info.tag


def rename(root: Path, repository: str, tag: str, name: str) -> None:
    """Have the API name release ``tag`` ``name``.

    Its directory, and its assets' URLs, stay.
    ``name`` may be no file name at all, as a misbehaving service would
    answer.
    """
    target = root / repository / tag
    info = read_json(target / RELEASE_FILE, Release)
    write_json(target / RELEASE_FILE, info.model_copy(update={"tag": name}))


def cut(root: Path, repository: str, tag: str, size: int | None) -> None:
    """Cut downloads of ``tag`` after ``size`` bytes.

    With None, they run whole again.
    """
    marker = root / repository / tag / CUT
    if size is None:
        marker.unlink(missing_ok=True)
    else:
        marker.write_text(str(size))


def downloads(root: Path, repository: str, tag: str) -> list[str]:
    """Return the assets of ``tag`` downloaded so far, in order.

    Each appears as often as it was downloaded.
    """
    record = root / repository / tag / DOWNLOADS
    return record.read_text().splitlines() if record.is_file() else []
