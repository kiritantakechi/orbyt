# Proposal

## Why

Eight tests can pass while what they check is broken, found by a review of the project on 2026-11-17. Each asserts an absence, a refusal or a balance without showing that the thing it watches took part:

- **T1** (firmware/base-system, excluded components): `ls /proc/lrng_type /proc/sys/kernel/random/lrng_type` fails when either path is missing, so the test passes with one of LRNG's interfaces present.
- **T2** (firmware/boot-rollback, stored boot command ignored): the helper `setenv` joins names and values unquoted, so `bootcmd="echo orbyt-hijacked"` writes `bootcmd=echo` and a variable named `orbyt-hijacked`, and `orbyt_boot` is never written: the test of a stored boot logic being ignored stores none.
- **T4** (network/nat, spoofed inbound): the half sent through the PPP session asserts that no packet reached the LAN, with nothing to show that one reached the router; the Ethernet half counts its frames at the WAN port, this one does not.
- **T5** (network/qos, two hosts share the upload): the rates of the two uploads are compared with each other alone; two uploads limited by anything else, the emulator's speed or nothing at all, are as fair.
- **T6** (firmware/kernel, a kmod of another kernel refused): `apk add` of a virtual package depending on a foreign vermagic fails, without a control that the same command with the running kernel's vermagic succeeds; any other failure of apk passes the test.
- **T8** (the `internet_zone` fixture of the network and services suites): after `dnsmasq reload` it waits until something listens on the router's port 53, which the old instance still does: the wait ends at once, and the queries that follow can meet the restart.
- **T9** (the `ubsan` profile's trap reports): traps are read from `dmesg` over SSH, and a read that fails reports none; after a reboot in a test the kernel log starts anew, and the traps before it are lost, though the requirement says every trap fails a test.
- **T10** (services/containers, ruleset): the container's `nc` to a LAN host must fail, without a control that the same `nc` from the container connects where it may.

## What Changes

- **Every negative check gets its control**, in the same test and with the same tools: a probe that shows the watched path exists (T1), the stored variables read back before the reboot (T2), the packets counted at the PPP device (T4), the rates' sum at the shaped rate, which the emulator carries several times over (T5), the same `apk add` succeeding with the running kernel's vermagic (T6), and the container's `nc` reaching a server on the internet (T10).
- **`setenv` quotes what it writes**, so that a value with a space is one value (T2).
- **The fixture waits for what it set up**: an answer from the router's DNS for a name the rebind exception lets through (T8).
- **Traps are read from the console's record too**, which keeps the kernel's reports across reboots and failed SSH sessions (T9): the kernel log reaches the console at the image's console level. `dmesg` stays the first source, whole for the current boot.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `quality/undefined-behavior`: "Undefined behavior traps under UBSan" gains the scenario of a trap before the router reboots during a test, which then fails that test as any other.

## Impact

- `tests/orbyt_tests/device/ab.py` (`setenv`), `tests/orbyt_tests/device/ubsan.py` (`Traps` reads the console), `tests/orbyt_tests/device/fixtures.py`, `tests/orbyt_tests/services/fixtures.py` (`internet_zone`).
- `tests/firmware/test_base_system.py`, `test_boot_rollback.py`, `test_kernel.py`; `tests/network/test_nat.py`, `test_qos.py`; `tests/services/test_containers.py`; the unit tests of the trap parser, if the console's lines need them.
- No change to the image, the build or CI's workflows.
