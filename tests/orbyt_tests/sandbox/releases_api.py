"""A stand-in for GitHub's Releases API on the emulated internet.

It answers what orbyt-sync asks, over HTTPS with the test CA's
certificate: a repository's newest stable release
(``/repos/<owner>/<repo>/releases/latest``), its releases newest first
(``/repos/<owner>/<repo>/releases``), and each asset at its
``browser_download_url``
(``/<owner>/<repo>/releases/download/<tag>/<asset>``, as on GitHub),
from the store of ``orbyt_tests.sandbox.releases``. It runs as a daemon
of the sandbox's inet namespace (``python -m``).
"""

import argparse
import functools
import json
import ssl
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from orbyt_tests.model.data import read_json
from orbyt_tests.model.outputs import RELEASE_FILE, Release
from orbyt_tests.sandbox.releases import CUT, DOWNLOADS, PUBLISHED

if TYPE_CHECKING:
    import socket
    import socketserver

PORT = 443
CHUNK = 1 << 16
# Each request is a thread of its own: two downloads that end at once
# append to a record one after the other.
_RECORDING = threading.Lock()


def _releases(directory: Path, base: str) -> list[dict[str, Any]]:
    """Return a repository's releases in API form, newest first."""
    found = []
    for release in directory.iterdir() if directory.is_dir() else ():
        if not (release / PUBLISHED).is_file():
            continue
        info = read_json(release / RELEASE_FILE, Release)
        found.append(
            {
                "tag_name": info.tag,
                "name": info.tag,
                "prerelease": info.prerelease,
                "draft": False,
                "body": info.notes,
                "published": float((release / PUBLISHED).read_text()),
                "assets": [
                    {
                        "name": asset,
                        "size": (release / asset).stat().st_size,
                        "browser_download_url": (
                            f"{base}/download/{release.name}/{asset}"
                        ),
                    }
                    for asset in info.assets
                    if asset != RELEASE_FILE
                ],
            }
        )
    return sorted(found, key=lambda release: -release["published"])


class _Handler(BaseHTTPRequestHandler):
    def __init__(
        self,
        request: socket.socket,
        client_address: tuple[str, int],
        server: socketserver.BaseServer,
        *,
        root: Path,
        base: str,
    ) -> None:
        """Answer ``request`` from the store under ``root``.

        The store's URLs start with ``base``.
        """
        self.root = root
        self.base = base
        super().__init__(request, client_address, server)

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output free of access logs."""

    def _json(self, value: object) -> None:
        body = json.dumps(value).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _listed(self, owner: str, name: str) -> list[dict[str, Any]]:
        return _releases(
            self.root / owner / name, f"{self.base}/{owner}/{name}/releases"
        )

    def do_GET(self) -> None:
        """Answer the API's requests and the downloads."""
        path = self.path.split("?", 1)[0].strip("/").split("/")
        match path:
            case ["repos", owner, name, "releases"]:
                self._json(self._listed(owner, name))
            case ["repos", owner, name, "releases", "latest"]:
                stable = [r for r in self._listed(owner, name) if not r["prerelease"]]
                if stable:
                    self._json(stable[0])
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            case [owner, name, "releases", "download", tag, asset] if (
                self.root / owner / name / tag / asset
            ).is_file():
                release = self.root / owner / name / tag
                self._download(release / asset, release / CUT)
            case _:
                self.send_error(HTTPStatus.NOT_FOUND)

    def _download(self, file: Path, cut_file: Path) -> None:
        with _RECORDING, (file.parent / DOWNLOADS).open("a") as record:
            record.write(f"{file.name}\n")
        size = file.stat().st_size
        limit = int(cut_file.read_text()) if cut_file.is_file() else size
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with file.open("rb") as source:
            remaining = min(size, limit)
            while remaining:
                chunk = source.read(min(CHUNK, remaining))
                self.wfile.write(chunk)
                remaining -= len(chunk)
        if limit < size:
            self.close_connection = True
            self.connection.close()


def serve(root: Path, address: str, name: str, certificate: Path, key: Path) -> None:
    """Serve the releases under ``root`` on ``address`` as https://``name``."""
    root.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(_Handler, root=root, base=f"https://{name}")
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certificate, key)
    with ThreadingHTTPServer((address, PORT), handler) as server:
        # Each handshake runs in its request's thread, on the first read
        # (OpenSSL negotiates there), not in accept: a client that
        # connects ahead and sends nothing yet, as a proxy's connection
        # pool does, would otherwise hold up every client behind it.
        server.socket = context.wrap_socket(
            server.socket, server_side=True, do_handshake_on_connect=False
        )
        server.serve_forever()


def main() -> None:
    """Command line: serve the releases of a directory."""
    parser = argparse.ArgumentParser(
        prog="releases", description=__doc__.splitlines()[0]
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--address", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    args = parser.parse_args()
    serve(args.root, args.address, args.name, args.certificate, args.key)


if __name__ == "__main__":
    main()
