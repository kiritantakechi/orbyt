"""The fixtures of every system test, composed from the harness's layers (module-boundaries D6).

Each layer of ``orbyt_tests`` provides the fixtures of its domain as a
pytest plugin, from the build under test as data up to the router
online; this file composes them and defines none of its own. A suite's
own fixtures live in its directory's conftest.
"""

pytest_plugins = [
    "orbyt_tests.model.fixtures",
    "orbyt_tests.sandbox.fixtures",
    "orbyt_tests.device.fixtures",
    "orbyt_tests.services.fixtures",
]
