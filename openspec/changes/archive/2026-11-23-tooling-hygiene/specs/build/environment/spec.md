# Spec Delta

## ADDED Requirements

### Requirement: No machine of one maintainer's
The scripts and documents SHALL name no user, home directory, volume or repository of one machine: the repository a script talks to SHALL come from the clone's own remote or from CI's environment, and paths on the host SHALL come from the build's configuration. A script that cannot tell which repository it serves SHALL fail and say so.

#### Scenario: A fork's clone
- **WHEN** the release drill's base is fetched in a fork's clone
- **THEN** it downloads the fork's releases, not the original repository's
