# Spec Delta

## MODIFIED Requirements

### Requirement: Hangs and panics become reboots
The hardware watchdog SHALL start before the kernel begins running and stay active until userspace takes over: the bootloader SHALL start it with a 60-second timeout, and the kernel SHALL keep a running watchdog fed for at most 90 seconds until userspace opens it. Once userspace feeds the watchdog, a hang that stops the feeding SHALL reset the device. After a kernel panic, the device SHALL reboot automatically within 10 seconds. A trial boot that the health check has not decided by its deadline, a configured time counted from the kernel's start on a clock that setting the time of day does not move, SHALL reboot, whatever the boot is still waiting for: no boot script, however long it runs, may hold the deadline off. Every such reboot during a trial boot SHALL count toward rollback.

#### Scenario: Kernel panic
- **WHEN** a kernel panic occurs while the system is running
- **THEN** the device reboots within 10 seconds, and `bootcount` is incremented if it was in the trial boot state

#### Scenario: Userspace stops feeding the watchdog
- **WHEN** the process that feeds the watchdog stops feeding it during a trial boot
- **THEN** the device resets after the watchdog times out, and `bootcount` is incremented

#### Scenario: Watchdog armed before the kernel
- **WHEN** the configuration of the shipped bootloader and kernel is inspected
- **THEN** the bootloader starts the DesignWare watchdog with a 60-second timeout, the kernel has the DesignWare driver built in and keeps a watchdog that is already running fed, and the kernel command line limits that to 90 seconds (`watchdog.open_timeout=90`)

#### Scenario: A boot script hangs during a trial boot
- **WHEN** a boot script that runs before the health check never returns, on every boot of a trial slot
- **THEN** each of those boots reboots at the trial deadline, saying so on the console, and after three of them the bootloader switches back to the original slot

### Requirement: The system writes the environment where the bootloader reads it
The bootloader SHALL pass the size and the offset of each copy of its environment to Linux on the kernel command line. The system SHALL read and write the environment at those places only, in the layout their number implies, and SHALL be able to do so on every boot before its first boot script starts, whether or not an upgrade kept the configuration. A system started by a bootloader that names no places MUST NOT write the environment, and an upgrade MUST refuse to start before it writes anything.

#### Scenario: The environment where the bootloader names it
- **WHEN** the system boots and its access to the environment is configured
- **THEN** it reads and writes the copies at the sizes and offsets on the kernel command line, and nowhere else

#### Scenario: A bootloader that names no environment
- **WHEN** the bootloader that started the system named no places for its environment, and an upgrade is started
- **THEN** the upgrade refuses before writing a slot, and says why

#### Scenario: The environment at the first boot script
- **WHEN** a slot boots for the first time after an upgrade that kept no configuration
- **THEN** its first boot script reads the environment, and finds the slot on trial
