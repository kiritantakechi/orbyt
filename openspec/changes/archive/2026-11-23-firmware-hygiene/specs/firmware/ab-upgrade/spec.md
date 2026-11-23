# Spec Delta

## ADDED Requirements

### Requirement: The platform hands the upgrade to the A/B slots
The platform's upgrade steps (checking an image, writing it, carrying the configuration over) SHALL be handed to the A/B upgrade by name. Which definition of a step runs MUST NOT depend on the order in which the upgrade's files are read, and the upgrade's checks, the device metadata check among them, MUST hold whatever the files are named.

#### Scenario: The A/B upgrade's file read first
- **WHEN** the A/B upgrade's file is renamed so that it is read before every other upgrade file, and an upgrade runs with a valid upgrade image and then with an image for another device
- **THEN** the valid image is accepted and written to the inactive slot only, and the image for another device is rejected before anything is written
