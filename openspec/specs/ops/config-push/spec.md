# ops/config-push Specification

## Purpose
Defines how runtime configuration and secrets are stored, and how they are pushed to the device and applied: secrets are kept encrypted in a private repository, configuration is validated before a push, a failure rolls back, and configuration persists across A/B upgrades.

## Requirements

### Requirement: Secrets stored encrypted
Secrets in the private config repository (PPPoE credentials, honk's subscriptions, nodes and native API token, WireGuard private keys, the Tailscale auth key, SMB user credentials) SHALL be committed in encrypted form. Plaintext SHALL appear only temporarily, in memory or in a temporary directory on the workstation performing the push, and on the device. On the device, the files a push writes for a secret outside the uci configuration (its upload, honk's configuration, Tailscale's auth key) SHALL be readable by root alone, and no secret SHALL appear on a command line; the push's temporary files SHALL be gone once the push ends, however it ends.

#### Scenario: Scan the private repository
- **WHEN** the full history of the private config repository is checked with a secret scanner
- **THEN** no plaintext secrets are found

#### Scenario: Secrets on the device
- **WHEN** a push with a honk configuration, a Tailscale login and SMB users has ended, successfully or not
- **THEN** the push's temporary files were readable by root alone while they were there and are gone, honk's files and Tailscale's auth key are readable by root alone, no process was started with the Tailscale auth key or an SMB user's password among its arguments, and each SMB user logs in with the password pushed

### Requirement: Validate before pushing
The push tool SHALL validate all configuration to be pushed, including the honk configuration, with honk's own check as honk would load it, and the UCI configuration syntax, before it modifies the device. When validation fails, the device MUST NOT be changed in any way.

#### Scenario: Syntax error in the proxy config
- **WHEN** a honk configuration with a syntax error is pushed
- **THEN** the push aborts before modifying the device, and the device's existing configuration and services remain unchanged

#### Scenario: Configuration the proxy would refuse
- **WHEN** a honk configuration that parses but that honk refuses to load, such as one routing to a group that does not exist, is pushed
- **THEN** the push aborts before modifying the device and reports honk's reason

#### Scenario: Proxy files in dae's layout
- **WHEN** the private config repository still keeps the proxy's files in `dae/`, from before honk replaced dae
- **THEN** the push aborts before modifying the device and names the move to `honk/`

### Requirement: Repeatable push results
Pushing the same configuration repeatedly SHALL produce the same result, and MUST NOT restart services whose configuration has not changed.

#### Scenario: Repeated push
- **WHEN** the same configuration is pushed twice in a row
- **THEN** the second push restarts no services

### Requirement: Roll back on service failure
After the configuration is written, if a service's files cannot all be written or the service fails to reload, the push tool SHALL restore that service's pre-push configuration, reload it again, and then report the failure. The restored configuration SHALL include every file the push changed for that service, its login state and its start-at-boot switch among them, and a service the switch had off SHALL be stopped again. Every service the push reloads SHALL be checked for having come back, and staying back, including that no service that ran before the push stopped.

#### Scenario: Service reload fails
- **WHEN** the new configuration passes validation but the corresponding service fails to reload
- **THEN** the service is restored to its pre-push configuration and runs normally, and the push tool exits nonzero and states the reason

#### Scenario: Tailscale login fails
- **WHEN** Tailscale is logged in, and a push with a Tailscale login that the control server refuses is made
- **THEN** Tailscale is logged in again as before the push, and the push tool exits nonzero and states the reason

#### Scenario: A service that stops with its new configuration
- **WHEN** a push changes a configuration other than the network's, honk's or Tailscale's, and a service that ran before the push no longer runs once the configuration is applied, however long the system takes to apply it
- **THEN** that configuration is restored, the service runs again, and the push tool exits nonzero and states the reason

#### Scenario: honk off before a failed push
- **WHEN** honk is off, neither running nor starting at boot, and a push with a honk configuration after which honk does not come back is made
- **THEN** honk's previous configuration is back, honk is off again, and the push tool exits nonzero and states the reason

### Requirement: Configuration persists across A/B upgrades
Configuration and secrets pushed to the device SHALL be included in the configuration backup taken during an upgrade, and SHALL still be present after the slot switch.

#### Scenario: Upgrade to the other slot
- **WHEN** a config-preserving upgrade is performed after a configuration push
- **THEN** the PPPoE, honk, WireGuard, Tailscale, and SMB configuration is all still present in the new slot

### Requirement: Proxy user config cannot set the firmware's settings
The push tool MUST reject honk user configuration that contains `lan_interface`, `wan_interface` or `data_dir`, because the firmware sets them: the interfaces honk binds, and the directory of honk's state, which follows the data disk.

#### Scenario: User config sets lan_interface
- **WHEN** a honk configuration whose user config sets `lan_interface` is pushed
- **THEN** the push fails during validation and reports that this field is managed by the firmware

#### Scenario: User config sets data_dir
- **WHEN** a honk configuration whose user config sets `data_dir` is pushed
- **THEN** the push fails during validation and reports that this field is managed by the firmware

### Requirement: SSH key authentication only
Pushes SHALL connect to the device with SSH key authentication and MUST NOT use password authentication.

#### Scenario: No SSH key configured
- **WHEN** a push is attempted while the push public key is not deployed on the device
- **THEN** the push aborts on the authentication failure and does not fall back to password login

### Requirement: The proxy's native API only with a token
The push tool MUST reject a honk configuration that enables the native API in any mode other than static-token mode, or that allows configuration writes through it, in every spelling honk takes a setting in, and one that sets a blank token.

#### Scenario: Native API with password login
- **WHEN** a honk configuration that enables the native API with password login is pushed, its value spelled in any way honk reads as true
- **THEN** the push fails during validation and reports that the native API needs a token

#### Scenario: Native API with configuration writes
- **WHEN** a honk configuration that enables the native API with a token and configuration writes is pushed, its value spelled in any way honk reads as true
- **THEN** the push fails during validation and reports that configuration writes stay off

#### Scenario: Native API with a blank token
- **WHEN** a honk configuration whose native API token is blank, even after another file's token, is pushed
- **THEN** the push fails during validation and reports the blank token
