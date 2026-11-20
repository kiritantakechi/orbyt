# Spec Delta

## REMOVED Requirements

### Requirement: Validate before pushing
**Reason**: Its scenario "Proxy files in dae's layout" goes (tooling-hygiene D8): the private repository keeps honk's files in `honk/`, and the push no longer refuses `dae/` by name. A modified requirement keeps every scenario it had, so the requirement is replaced whole.
**Migration**: "Validate before changing the device", below, is the requirement as it was, without that scenario.

## ADDED Requirements

### Requirement: Validate before changing the device
The push tool SHALL validate all configuration to be pushed, including the honk configuration, with honk's own check as honk would load it, and the UCI configuration syntax, before it modifies the device. Validation itself MUST NOT change the device, whether the configuration passes or not: it MUST leave no uncommitted UCI change behind. When validation fails, the device MUST NOT be changed in any way.

#### Scenario: Syntax error in the proxy config
- **WHEN** a honk configuration with a syntax error is pushed
- **THEN** the push aborts before modifying the device, and the device's existing configuration and services remain unchanged

#### Scenario: Configuration the proxy would refuse
- **WHEN** a honk configuration that parses but that honk refuses to load, such as one routing to a group that does not exist, is pushed
- **THEN** the push aborts before modifying the device and reports honk's reason

#### Scenario: A configuration that validates
- **WHEN** a configuration with UCI changes, its secrets among them, validates, and the push finds every service unchanged
- **THEN** the device holds no uncommitted UCI change, and none of the pushed secrets is in a file of the device's UCI change directory
