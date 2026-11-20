# Spec Delta

## ADDED Requirements

### Requirement: The workflows run recipes
Every step of the workflows SHALL run a `just` recipe or a pinned action; what a step decides (which boards may be signed, whether the drill check passes, the pull request a bump opens) SHALL live in a script that the tests can run outside CI. What runs the build workflow, and each cache key, SHALL be written once, where the workflow and the scripts read it.

#### Scenario: The drill check's decision
- **WHEN** the tests run the drill check's script with each combination of the system tests', the signing's and the drills' results
- **THEN** it passes exactly when the system tests passed and every drill passed or signing did not run

### Requirement: The emulator built once per run
The tests' emulator, which no public binary cache holds, SHALL be built at most once per run, in its host stage, and not at all when the repository's cache already holds the build of the same inputs. Every job that tests in the emulator SHALL take that build instead of building it again.

#### Scenario: A run's test jobs
- **WHEN** a run's system-test and drill jobs start
- **THEN** each gets the emulator the host stage built or restored, and none compiles it
