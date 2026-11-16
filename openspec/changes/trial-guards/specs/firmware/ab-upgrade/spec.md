# Spec Delta

## MODIFIED Requirements

### Requirement: Write only the inactive slot
An upgrade SHALL write only the inactive slot's boot and root partitions. An upgrade MUST NOT modify the active slot, the U-Boot area, or the partition table. While the running slot is in the trial boot state, the inactive slot is the one a rollback returns to: an upgrade MUST then refuse before it writes anything, and say that the running slot is on trial.

#### Scenario: Upgrade from slot A
- **WHEN** an upgrade runs while the system is running on slot A
- **THEN** only the contents of boot-B and root-B change, and the checksums of boot-A, root-A, and the boot area match those from before the upgrade

#### Scenario: Power loss mid-upgrade
- **WHEN** power is lost while the inactive slot is being written
- **THEN** after power is restored, the device still boots normally from the original slot

#### Scenario: Upgrade during a trial boot
- **WHEN** an upgrade is started while the running slot is in the trial boot state
- **THEN** the upgrade refuses, saying that the running slot is on trial, and neither slot nor the U-Boot environment changes
