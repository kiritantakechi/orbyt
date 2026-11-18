"""The app Pod of the services tests (r4s-services D4, D10).

The Pod stands in for qBittorrent.

Its declaration lies on the data disk, as an administrator would write
one: a Kubernetes Pod of the test app image whose uhttpd serves a
directory of the data disk, and an options file that gives it a fixed
address for a port forward. orbyt-containers starts it once the data
disk is mounted.
"""

import shlex
from typing import TYPE_CHECKING

from orbyt_tests.device.storage import MOUNT
from orbyt_tests.model.poll import until

if TYPE_CHECKING:
    from orbyt_tests.device.router import Router

POD = "web"
CONTAINER = f"{POD}-httpd"
ADDRESS = "10.88.0.10"
# The router's address on podman's network, where the network's resolver
# (aardvark-dns) answers.
GATEWAY = "10.88.0.1"
PODS = f"{MOUNT}/containers/pods"
WWW = f"{MOUNT}/containers/www"
START_TIMEOUT = 180


def declaration(image: str, name: str = POD) -> str:
    """Return the Pod's declaration, as podman kube play reads it.

    ``name`` names another Pod than the default.
    """
    return f"""\
apiVersion: v1
kind: Pod
metadata:
  name: {name}
spec:
  containers:
    - name: httpd
      image: {image}
      command: [uhttpd, -f, -p, "0.0.0.0:80", -h, /www]
      volumeMounts:
        - name: www
          mountPath: /www
  volumes:
    - name: www
      hostPath:
        path: {WWW}
        type: DirectoryOrCreate
"""


def declare(router: Router, image: str) -> None:
    """Write the Pod's declaration and its page to the data disk.

    The Pod is started afterwards.
    """
    router.run(
        f"mkdir -p {PODS} {WWW} && echo {POD} >{WWW}/index.html"
        f" && printf %s {shlex.quote(declaration(image))} >{PODS}/{POD}.yaml"
        f" && echo --ip={ADDRESS} >{PODS}/{POD}.options"
        " && /etc/init.d/orbyt-containers restart"
    )


def running(router: Router) -> str | None:
    """Return the app container's ID while it runs."""
    state = router.run(
        f"podman container inspect --format '{{{{.State.Running}}}} {{{{.Id}}}}'"
        f" {CONTAINER}"
        " 2>/dev/null || true"
    ).split()
    return state[1] if state[:1] == ["true"] else None


def started(router: Router) -> str:
    """Return when the app container last started, as podman records it.

    The result is "" while the container is gone.
    """
    return router.run(
        f"podman container inspect --format '{{{{.State.StartedAt}}}}' {CONTAINER}"
        " 2>/dev/null || true"
    )


def wait_running(router: Router) -> str:
    """Wait until the app container runs; return its ID.

    Fail with orbyt-containers' log if it does not.
    """
    try:
        return until(
            lambda: running(router), timeout=START_TIMEOUT, what=f"{CONTAINER} running"
        )
    except TimeoutError as error:
        error.add_note(router.run("logread -e orbyt-containers | tail -n 20"))
        raise
