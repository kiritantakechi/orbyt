"""A stand-in for gh, the GitHub CLI, with a repository as data.

It answers the gh calls of scripts/cache-room.sh,
scripts/cache-prune.sh and scripts/release-publish.sh (build-integrity
D5, D6; release-integrity D6; release-freshness D2) as GitHub's API
would for the repository a JSON file describes: its caches, which it
deletes as they are deleted, so that a test reads which are left; its
branches and their heads; how two commits compare. A release it is
asked to create it records instead, its arguments in gh.args beside the
file. ``orbyt_tests.model.github`` installs it as gh, which runs it
with the repository's file, then gh's arguments.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def _answer(args: list[str], value: object) -> None:
    """Print ``value`` as gh prints an answer, through --jq if given."""
    jq = _option(args, "--jq")
    if jq is None:
        print(json.dumps(value))  # noqa: T201 (gh's answer)
    else:
        subprocess.run(["jq", "-r", jq], input=json.dumps(value), text=True, check=True)


def _caches(github: dict[str, Any], ref: str | None) -> list[dict[str, Any]]:
    """Return the caches of ``ref``, or all, newest first."""
    found = [cache for cache in github["caches"] if ref is None or cache["ref"] == ref]
    return sorted(found, key=lambda cache: cache["id"], reverse=True)


def _api(github: dict[str, Any], args: list[str]) -> None:
    """Answer a call of gh api."""
    path = next(arg for arg in args[1:] if not arg.startswith("--"))
    base = f"repos/{github['repository']}"
    if path == base:
        _answer(args, {"default_branch": "main"})
    elif path == f"{base}/actions/cache/usage":
        size = sum(cache["size"] for cache in github["caches"])
        _answer(args, {"active_caches_size_in_bytes": size})
    elif path == f"{base}/branches":
        _answer(args, [{"name": name} for name in github["branches"]])
    elif path.startswith(f"{base}/git/ref/heads/"):
        name = path.removeprefix(f"{base}/git/ref/heads/")
        _answer(args, {"object": {"sha": github["heads"].get(name, github["head"])}})
    elif path.startswith(f"{base}/compare/main..."):
        _answer(args, {"status": github["compare"][path.split("...", 1)[1]]})
    elif path.startswith(f"{base}/compare/") and path in github["changes"]:
        _answer(args, github["changes"][path])
    elif path.startswith(f"{base}/pulls/"):
        _answer(args, {"state": github["pulls"][path.rsplit("/", 1)[1]]})
    else:
        sys.exit(f"no answer for {path}")


def main(described: Path, args: list[str]) -> None:
    """Answer gh ``args`` for the repository ``described`` describes.

    What the call changes goes back to the file.
    """
    github = json.loads(described.read_text())
    match args[:2]:
        case ["cache", "list"]:
            _answer(args, _caches(github, _option(args, "--ref")))
        case ["cache", "delete"] if "--all" in args:
            gone = {cache["id"] for cache in _caches(github, _option(args, "--ref"))}
            github["caches"] = [
                cache for cache in github["caches"] if cache["id"] not in gone
            ]
        case ["cache", "delete"]:
            github["caches"] = [
                cache for cache in github["caches"] if str(cache["id"]) != args[2]
            ]
        case ["api", *_]:
            _api(github, args)
        case ["release", "create"]:
            text = "".join(f"{arg}\n" for arg in args)
            described.with_name("gh.args").write_text(text)
        case _:
            sys.exit(f"unexpected gh {args}")
    described.write_text(json.dumps(github))


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
