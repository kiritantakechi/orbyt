# Spec Delta

## MODIFIED Requirements

### Requirement: Symmetric naming
- Operations that have an inverse SHALL come in pairs with symmetric names, for example mount/unmount, pack/unpack, up/down.
- just recipe names SHALL match the corresponding script names.
- Scripts that act on a specific object SHALL be named "object-verb"; pipeline stage scripts are named with a single verb.
- Environment variables SHALL all use the `ORBYT_` prefix.

#### Scenario: Unpaired operation
- **WHEN** the repository has a command that mounts the build directory
- **THEN** a matching unmount command also exists, and the two are named symmetrically
