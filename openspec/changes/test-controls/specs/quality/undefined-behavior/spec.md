# Spec Delta

## MODIFIED Requirements

### Requirement: Undefined behavior traps under UBSan
A build of the `ubsan` profile SHALL instrument every target package with UBSan in trap mode, except the toolchain's libraries and the kernel. A trap while the system tests run SHALL fail a test and name the process that trapped: the test during which it trapped, or, for a trap in a fixture outside every test, the last test that used the fixture. A trap SHALL be reported whatever happens to the router after it: a reboot, a power cut or a return to the emulator's snapshot.

#### Scenario: Trap during a system test
- **WHEN** a process of a `ubsan` build traps on undefined behavior while a system test runs
- **THEN** that test fails, and names the process

#### Scenario: A trap before a reboot
- **WHEN** a process of a `ubsan` build traps during a system test, and the test then reboots the router
- **THEN** that test fails, and names the process
