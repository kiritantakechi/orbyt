# Spec Delta

## ADDED Requirements

### Requirement: The sync waits for its datapath
When the transparent proxy is enabled, the sync SHALL send its first request only once the proxy holds the container bridge, so that no request leaves before the datapath that routes it. A request that fails in transit SHALL be retried a bounded number of times, and the sync SHALL report a release it could not download as failed, without activating anything.

#### Scenario: The sync starts before the proxy
- **WHEN** the data disk is mounted while the transparent proxy has not yet attached to the container bridge
- **THEN** the sync sends no request until the proxy holds the bridge, and then downloads the release through the proxy
