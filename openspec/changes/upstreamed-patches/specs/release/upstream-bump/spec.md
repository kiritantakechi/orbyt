# Spec Delta

## MODIFIED Requirements

### Requirement: Fail clearly when patches do not apply
If patches fail to apply after a bump, the PR's CI SHALL fail and name the conflicting patch file in the result. When the failing patch applies in reverse, because upstream has made its change, the result SHALL say so, so that the patch is dropped rather than refreshed.

#### Scenario: BBRv3 patch conflict
- **WHEN** a BBRv3 patch fails to apply after a bump
- **THEN** the PR check fails, and the failure message names the conflicting patch file

#### Scenario: Upstream made a patch's change
- **WHEN** a patch fails to apply after a bump because upstream made the same change
- **THEN** the PR check fails, and the failure message names the patch and says that upstream has its change
