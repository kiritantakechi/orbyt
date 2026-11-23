# testing/harness Specification

## Purpose
Turn spec scenarios into repeatable checks with one automated system test suite that runs against the emulator, so that no verification step needs a real board.

## Requirements

### Requirement: One test per spec scenario
Every spec scenario that can be tested at the system level SHALL have exactly one corresponding test, whose marker names the capability, requirement, and scenario it covers. The test framework SHALL be able to generate a coverage report that lists the scenarios without a test.

#### Scenario: Generate coverage report
- **WHEN** a coverage report is generated for all current specs
- **THEN** the report lists the test for each scenario, and every scenario that has no test and is not marked "verified elsewhere" is listed separately

#### Scenario: Marker names a missing scenario
- **WHEN** a test is marked with a scenario that does not exist in the specs
- **THEN** the coverage check fails and names that test

### Requirement: Python toolchain locked by uv
The test suite's Python environment SHALL be fully defined by `pyproject.toml` and `uv.lock`, including the Python interpreter version. Formatting and static checks use ruff and type checking uses ty, and both MUST pass.

#### Scenario: Lock file out of sync
- **WHEN** a dependency in `pyproject.toml` is changed but `uv.lock` is not updated
- **THEN** syncing the environment in locked mode fails

#### Scenario: Type error
- **WHEN** a test file contains a type error
- **THEN** the type check fails and points to the location of the error

### Requirement: Emulator run on every build
CI SHALL run the emulator tests for every firmware build. Any failing test MUST fail the whole pipeline, and results SHALL be published in JUnit format.

#### Scenario: Test failure
- **WHEN** the image from a build makes a test fail
- **THEN** the CI test stage fails, and the JUnit report shows that test and the failure reason

### Requirement: Fixtures by layer
Each layer of the test harness SHALL provide the fixtures of its own domain. The suite's root configuration SHALL compose the layers' fixtures and define none of its own. A fixture that only one suite of tests uses SHALL live in that suite's directory. A test that returns the router to its snapshot after it SHALL NOT run in a module whose fixtures keep the router, after that module's first test that uses them: such a test fails at its setup and says so, instead of taking their state from the module's later tests.

#### Scenario: Fixture defined in the root configuration
- **WHEN** the suite's root configuration defines a fixture
- **THEN** the harness's structure check fails and names the fixture

#### Scenario: A test that would reset a module's router
- **WHEN** a test that resets the router after it starts while a module's fixtures keep the router
- **THEN** the test fails at its setup, naming the module, before it changes anything

### Requirement: One schema per data file
The tests SHALL read every data file of the repository and of the build's and the release's outputs through one schema for that file, which rejects unknown fields and values of the wrong type: the board descriptions, the registers of scenarios verified elsewhere and of reviewed warnings, the build's manifest and reports, the toolchain's record, and a release's metadata and manifests.

#### Scenario: Malformed data file
- **WHEN** an entry of a data file the tests read has an unknown field or a value of the wrong type
- **THEN** reading the file fails and names the file, the entry and the field

### Requirement: Waiting for a condition
The harness's polling helper SHALL call a probe until the probe answers with content, and return that answer. An empty answer SHALL count as no answer yet, whatever its type: `None`, `False`, zero, an empty string and an empty collection alike. When the time limit passes without an answer with content, the helper SHALL fail and name what it waited for.

#### Scenario: A probe answers empty first
- **WHEN** a probe answers with an empty string, then with an empty list, then with a value
- **THEN** the wait goes on through the empty answers, and returns the value

#### Scenario: No answer within the time limit
- **WHEN** a probe answers only with empty values until the time limit passes
- **THEN** the wait fails, and its error names what it waited for

### Requirement: Failures name the router's state
A test failure that involves the router SHALL show what the harness can still see of the router and its networks. A wait for a reboot that does not come SHALL show the command that was to reboot the router, the command's output and the console since it ran. A failing test with the router online SHALL show the LAN clients' addresses and routes, the router's WAN state with its log, and the emulated ISP's sessions with its log. When the router does not answer, the report SHALL say so after a few seconds instead of waiting out a connection for each of its parts. Gathering this SHALL NOT change the test's outcome.

#### Scenario: A reboot that does not come
- **WHEN** a command detached on the router ends without rebooting it, and the harness waits for the reboot
- **THEN** the wait fails at its time limit, and the failure shows the command, its output and the console since it ran

#### Scenario: A failing test with the router online
- **WHEN** a test that uses the router online fails
- **THEN** its report has a section with the LAN clients' addresses and routes, the router's WAN state and log, and the ISP's sessions and log

#### Scenario: A failing test with the router unreachable
- **WHEN** a test that uses the router online fails while the router takes no new connection
- **THEN** its report says that the router did not answer, still shows the LAN clients' and the ISP's state, and is ready within 20 s

### Requirement: Commands on the router end with their time limit
A command the harness runs on the router SHALL fail when its time limit passes, as a timeout that names the command, and SHALL leave no process of its own running on the router after that. A login session on the router that does not end within its time limit SHALL be ended and fail likewise, showing what the session printed.

#### Scenario: A command that overruns its time limit
- **WHEN** a command on the router starts a process that holds a lock, and runs past its time limit
- **THEN** the command fails as a timeout that names it, and the lock is free again

#### Scenario: A login session that does not end
- **WHEN** a login session on the router runs past its time limit
- **THEN** it fails as a timeout, with what the session printed

### Requirement: What a test sets up, it takes down
A fixture or test that changes the emulated machine or the networks around it for itself SHALL undo the change when it ends, whether it passes or fails, and also when it fails while still setting the change up.

#### Scenario: A setup that fails halfway
- **WHEN** a fixture fails while it brings up the WireGuard peer's tunnel
- **THEN** the peer's network namespace holds no tunnel afterwards, and the next fixture can bring one up

#### Scenario: A test that fails while writes are slowed
- **WHEN** a test that slows down the boot disk's writes fails before it cuts the power
- **THEN** the boot disk's writes are no longer limited afterwards

### Requirement: A failed command shows its output
When a command the harness runs fails, on the runner, in a namespace or on the router, the failure SHALL carry the command's output, standard output and standard error alike. A test that expects a command to fail SHALL name the failure it expects by that output, not by the bare fact of a non-zero exit.

#### Scenario: A command expected to fail fails otherwise
- **WHEN** a test expects a probe to be refused, and the probe fails for another reason, such as a timeout
- **THEN** the test fails, and its report shows the probe's output

### Requirement: Each wait has one form
Every wait in the harness and the tests SHALL go through the polling helper, with its time limit and the description of what it waits for; a wait SHALL be able to name what to report when its time limit passes, and the helper SHALL attach it to the failure. No wait SHALL be a fixed sleep standing in for a condition the test can observe.

#### Scenario: A wait that names its diagnostics
- **WHEN** a wait whose caller named what to report runs out of time
- **THEN** the failure says what was awaited and carries the reported state

### Requirement: The sandbox's daemons ready before use
A daemon the sandbox starts SHALL be ready, by a probe of the service it offers, before the sandbox hands it to a test; a daemon that exits while it starts SHALL fail the setup at once, with its output.

#### Scenario: A daemon slow to bind
- **WHEN** a daemon of the sandbox takes longer than usual to listen on its port
- **THEN** the sandbox waits for it to listen before the first test uses it

#### Scenario: A daemon that exits while it starts
- **WHEN** a daemon of a namespace the sandbox adds exits before it is ready
- **THEN** the setup fails at once, naming the daemon and its exit status, and leaves neither the namespace nor its links behind

### Requirement: Tests independent of their order
Each test SHALL leave what its module shares, the router's state, its disks, its containers and the network, as it found it, so that any test passes when it runs alone or in another order. Nothing a test needs SHALL depend on a test that ran before it.

#### Scenario: A test run alone
- **WHEN** any single test of a module is selected and run on its own
- **THEN** it passes as it does in the module's full run

### Requirement: Tests that need the build tree
A test that reads the build tree, rather than the build's outputs, SHALL be marked as such, and SHALL run where the tree is: on the build host, and in CI's firmware job once the board is built. The suites that run without the tree SHALL deselect those tests by their mark; no test SHALL skip itself for want of the tree.

#### Scenario: The system suite on CI
- **WHEN** CI's system suite runs the build tests against a board's downloaded outputs
- **THEN** the tests that need the tree are deselected, not skipped, and the firmware job has run them against the tree
