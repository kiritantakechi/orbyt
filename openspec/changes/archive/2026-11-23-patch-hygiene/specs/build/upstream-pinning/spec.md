# Spec Delta

## ADDED Requirements

### Requirement: One fault per patch, each written up alike
Each patch SHALL change one thing: a fix for one fault, or one feature. Two patches MUST NOT change the same lines in turn, so that each can be taken, refreshed or dropped on its own, as upstream would take it. Every patch that is not upstream's own SHALL have a write-up in docs/patches.md with the same sections, in the same order: the problem, why it matters here, what the patch does, and its verification log.

#### Scenario: A write-up without a section
- **WHEN** a patch's write-up lacks one of the sections, or has them in another order
- **THEN** the checks fail and name the patch and the section
