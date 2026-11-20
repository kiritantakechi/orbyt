# Spec Delta

## ADDED Requirements

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
