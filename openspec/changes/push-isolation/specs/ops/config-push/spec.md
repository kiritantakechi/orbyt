# Spec Delta

## MODIFIED Requirements

### Requirement: Validate before pushing
The push tool SHALL validate all configuration to be pushed, including the honk configuration, with honk's own check as honk would load it, and the UCI configuration syntax, before it modifies the device. Validation itself MUST NOT change the device, whether the configuration passes or not: it MUST leave no uncommitted UCI change behind. When validation fails, the device MUST NOT be changed in any way.

#### Scenario: Syntax error in the proxy config
- **WHEN** a honk configuration with a syntax error is pushed
- **THEN** the push aborts before modifying the device, and the device's existing configuration and services remain unchanged

#### Scenario: Configuration the proxy would refuse
- **WHEN** a honk configuration that parses but that honk refuses to load, such as one routing to a group that does not exist, is pushed
- **THEN** the push aborts before modifying the device and reports honk's reason

#### Scenario: Proxy files in dae's layout
- **WHEN** the private config repository still keeps the proxy's files in `dae/`, from before honk replaced dae
- **THEN** the push aborts before modifying the device and names the move to `honk/`

#### Scenario: A configuration that validates
- **WHEN** a configuration with UCI changes, its secrets among them, validates, and the push finds every service unchanged
- **THEN** the device holds no uncommitted UCI change, and none of the pushed secrets is in a file of the device's UCI change directory

## ADDED Requirements

### Requirement: A push commits only its own changes
A push SHALL commit only the UCI packages its batches change, and of them only its own changes. When the device holds uncommitted changes to such a package, as LuCI holds them until they are saved, the push MUST refuse before it modifies the device, and name the package. Uncommitted changes to any other package SHALL stay as they are, uncommitted. However the push ends, it MUST leave no change of its own uncommitted.

#### Scenario: Uncommitted change to a pushed package
- **WHEN** the device holds an uncommitted change to a UCI package the push's batches change, and a push is made
- **THEN** the push aborts before modifying the device, names the package, and the change is still uncommitted

#### Scenario: Uncommitted change to another package
- **WHEN** the device holds an uncommitted change to a UCI package no batch changes, and a push applies a changed batch
- **THEN** that change is still uncommitted and its package's committed configuration is as before, and no change of the push is left uncommitted
