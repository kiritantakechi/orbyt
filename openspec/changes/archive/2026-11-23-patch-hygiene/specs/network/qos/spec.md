# Spec Delta

## ADDED Requirements

### Requirement: Configured whenever the daemon comes up
qosify's daemon SHALL be given the configuration each time it comes up, without waiting for a configuration change: when the system boots, when qosify is started, and when it is started again after it exits. Until the daemon is up, no boot script waits for it. A query of the service's state SHALL leave the daemon's configuration alone.

#### Scenario: A boot with no configuration change
- **WHEN** the router boots with its configuration and nothing changes it after the boot
- **THEN** pppoe-wan is shaped by cake at the configured upload bandwidth once the daemon is up

#### Scenario: The daemon exits and comes back
- **WHEN** qosify's daemon is killed and the system starts it again
- **THEN** pppoe-wan is shaped by cake at the configured upload bandwidth again, within the recovery time

#### Scenario: A status query
- **WHEN** the service's state is queried, by its init script's `running` action and by rpcd's list of the services
- **THEN** the daemon is not sent its configuration
