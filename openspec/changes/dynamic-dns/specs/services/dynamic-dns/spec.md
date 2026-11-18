# Spec Delta

## Purpose
Defines how the router keeps its WAN addresses in DNS at Cloudflare: the records it updates and when, the secrecy of the API token it updates them with, a changed configuration taking effect, and the service in the web interface.

## ADDED Requirements

### Requirement: The WAN's addresses in DNS
For each enabled dynamic DNS service, the router SHALL keep the service's record at Cloudflare on the WAN's current address: an A record on the WAN's IPv4 address, an AAAA record on its global IPv6 address.

#### Scenario: Records after dialing in
- **WHEN** the router dials in with an IPv4 and an IPv6 service enabled
- **THEN** the A record holds the WAN's IPv4 address and the AAAA record its global IPv6 address

### Requirement: Updates when the address changes
The router SHALL update a service's record when the WAN interface comes up and when its address changes, without waiting for the service's check interval. It SHALL read the address the record holds from Cloudflare's API rather than from DNS, and SHALL NOT write a record that already holds the current address.

#### Scenario: A new address after a redial
- **WHEN** the session ends and the router dials in anew with another IPv4 address
- **THEN** the A record holds the new address within a minute of the WAN coming up

#### Scenario: A record already current
- **WHEN** the service starts again while its record holds the WAN's address
- **THEN** the router reads the record and writes nothing

### Requirement: The API token kept secret
The image SHALL carry no Cloudflare API token. On the router the token SHALL be readable by root alone, and it MUST NOT appear in any process's arguments, in the system log or in the service's own log, at any of the service's log levels.

#### Scenario: Readable by root alone
- **WHEN** a service with its token has been configured
- **THEN** the file holding the token is root's and readable by root alone

#### Scenario: No process's arguments
- **WHEN** an update is under way, its request to Cloudflare not yet answered
- **THEN** no process on the router has the token among its arguments, and the request carries it

#### Scenario: Not in the logs
- **WHEN** a service has updated its record with its log at the most detailed level
- **THEN** neither the system log nor the service's log holds the token

### Requirement: A changed configuration takes effect
A change to a dynamic DNS service's configuration, saved and applied as LuCI and the configuration push apply it (a reload, not a restart), SHALL take effect: the services SHALL run on the new configuration.

#### Scenario: A new token
- **WHEN** a service's token is changed and the configuration reloaded
- **THEN** the service's next requests carry the new token

### Requirement: Dynamic DNS in the web interface
The web interface SHALL offer the dynamic DNS services under Services, with each configured service's state.

#### Scenario: The services' state
- **WHEN** the page's backend is asked for the services' state
- **THEN** it lists each configured service, the enabled one with the address its record holds
