# Spec Delta

## ADDED Requirements

### Requirement: The image's name
The image SHALL present itself as Orbyt: Orbyt as its distribution name in its release files and in LuCI, a login banner with Orbyt's name, and the hostname `orbyt` on a fresh configuration. LuCI SHALL credit LuCI and OpenWrt as the base the system runs on.

#### Scenario: A fresh install's name
- **WHEN** a freshly installed router is asked its hostname, its release and its login banner
- **THEN** its hostname is `orbyt`, `/etc/os-release` and `/etc/openwrt_release` name Orbyt as the distribution, and the banner shows Orbyt
