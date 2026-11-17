# Spec Delta

## MODIFIED Requirements

### Requirement: Candidates and stable releases
Builds from bump PRs SHALL be published as prereleases (candidates); builds made after merging into the main branch SHALL be published as stable releases. A Release SHALL be published only from a commit that is current for its branch when publishing starts: the commit the branch holds, or one the branch has moved past by commits that change only files the build workflow does not run for, such as documentation. Its tag SHALL point at the commit that was built. A run of a commit its branch has moved past by a change to a file the build workflow runs for, a re-run among them, MUST NOT publish.

#### Scenario: PR build
- **WHEN** the build of a bump PR finishes signing
- **THEN** it appears as a prerelease and does not become the latest stable release

#### Scenario: Post-merge build
- **WHEN** the main-branch build after the PR is merged finishes signing
- **THEN** it is published as a stable release and becomes the latest stable release

#### Scenario: A run its branch has moved past
- **WHEN** a run's publishing starts after its branch has moved to a newer commit that changes a file the build workflow runs for
- **THEN** publishing fails, naming both commits, and no Release is created

#### Scenario: A branch moved by documentation only
- **WHEN** a run's publishing starts after its branch has moved to newer commits that change only files the build workflow does not run for
- **THEN** the Release is published, and its tag points at the commit that was built

#### Scenario: Tag of a Release
- **WHEN** a Release is published
- **THEN** its tag points at the commit that was built
