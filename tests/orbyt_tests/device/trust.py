"""The router's trust in the session's own CA and release keys.

The sandbox's CA (``orbyt_tests.sandbox.pki``) certifies the emulated
internet's servers, and the session's release keys
(``orbyt_tests.model.keys``) sign its build. The router trusts both for
the session only: the CA beside the system's certificates, and the keys
in place of the image's own trust anchors.
"""

from typing import TYPE_CHECKING

from orbyt_tests.model.keys import APK_KEYS, FIRMWARE_KEYS

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router
    from orbyt_tests.model.keys import Keys
    from orbyt_tests.sandbox.pki import Pki

# Where the router trusts the CA, and its Go programs (podman,
# tailscale) find it.
CA_ON_ROUTER = "/etc/ssl/certs/orbyt-test-ca.crt"


def trust_ca(router: Router, pki: Pki) -> None:
    """Have ``router`` trust the sandbox's test CA, of ``pki``."""
    router.put(pki.ca, CA_ON_ROUTER)


def trust_keys(router: Router, keys: Keys) -> None:
    """Make ``keys`` the router's only trust anchors.

    They replace the image's own.
    """
    router.run(
        f"rm -f /{APK_KEYS}/* /{FIRMWARE_KEYS}/*"
        f" && mkdir -p /{APK_KEYS} /{FIRMWARE_KEYS}"
    )
    for anchors in (APK_KEYS, FIRMWARE_KEYS):
        for key in (keys.keyring / anchors).iterdir():
            router.put(key, f"/{anchors}/{key.name}")
