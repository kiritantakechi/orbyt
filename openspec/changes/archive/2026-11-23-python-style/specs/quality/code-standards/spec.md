# Spec Delta

## ADDED Requirements

### Requirement: Python on the free-threaded interpreter
The tests' Python SHALL run on free-threaded CPython 3.15, managed by uv, with its tools (ruff, ty, pytest) pinned to exact versions. Once the tests' environment has imported its dependencies, the GIL SHALL still be disabled: a dependency that turns it back on fails the tests.

#### Scenario: A dependency turns the GIL back on
- **WHEN** the tests' Python imports every dependency the tests use
- **THEN** the interpreter is a free-threaded 3.15 build and reports the GIL disabled
