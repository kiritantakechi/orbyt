# Spec Delta

## ADDED Requirements

### Requirement: The formatters see what the checks see
`just fmt` SHALL format exactly the files whose format `just check` checks, chosen by one definition both use, so that every format failure the check reports is one the formatter fixes.

#### Scenario: A preinit hook badly indented
- **WHEN** a shell hook of the image that its name does not mark as shell (a preinit hook) is indented against shfmt's style
- **THEN** `just check` fails on it, and `just fmt` fixes it
