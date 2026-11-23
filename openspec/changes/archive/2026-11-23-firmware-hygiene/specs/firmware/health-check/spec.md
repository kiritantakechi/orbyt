# Spec Delta

## ADDED Requirements

### Requirement: The trial watchdog starts first
The trial boot's deadline SHALL be armed by the image's first boot script, before any other boot script can run. The health check MUST NOT rely on the order in which the other boot scripts start: each of its checks waits for its own condition, within its time limit.

#### Scenario: The image's boot scripts
- **WHEN** the boot scripts the image enables are listed in the order the system starts them
- **THEN** the trial watchdog's script is the first of them

#### Scenario: A service that starts after the health check
- **WHEN** a service whose check is registered starts after the health check has begun
- **THEN** the check passes once the service is up, within the check's time limit, and the trial is confirmed
