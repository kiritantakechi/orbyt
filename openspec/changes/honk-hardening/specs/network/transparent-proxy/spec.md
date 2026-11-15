## MODIFIED Requirements

### Requirement: Web UI through the native API in token mode
honk's web UI SHALL be served only through honk's native API, and only in static-token mode. The native API SHALL be off unless the configuration enables it, MUST answer only from the LAN zone, and MUST NOT accept configuration writes. The firmware SHALL keep password login, anonymous loopback access and configuration writes off whatever the configuration on the router says, however it got there.

#### Scenario: Native API enabled with a token
- **WHEN** a configuration that enables the native API with a token is applied
- **THEN** the web UI opens from a LAN client with that token, and an API request from the LAN without the token is refused

#### Scenario: Native API from outside the LAN
- **WHEN** the native API is enabled and a request to it comes from the WAN or from the container bridge
- **THEN** it gets no response, while the same requests reach other destinations

#### Scenario: Password login in the configuration
- **WHEN** a configuration written on the router enables the native API with a token, password login, anonymous loopback access and configuration writes
- **THEN** honk runs with the token alone: a LAN request without it is refused, and the API reports its configuration as not writable
