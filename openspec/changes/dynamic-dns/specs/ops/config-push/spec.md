# Spec Delta

## MODIFIED Requirements

### Requirement: Secrets stored encrypted
Secrets in the private config repository (PPPoE credentials, honk's subscriptions, nodes and native API token, WireGuard private keys, the Tailscale auth key, SMB user credentials, the Cloudflare API token) SHALL be committed in encrypted form. Plaintext SHALL appear only temporarily, in memory or in a temporary directory on the workstation performing the push, and on the device. On the device, the files a push writes for a secret outside the uci configuration (its upload, honk's configuration, Tailscale's auth key) SHALL be readable by root alone, and no secret SHALL appear on a command line; the push's temporary files SHALL be gone once the push ends, however it ends.

#### Scenario: Scan the private repository
- **WHEN** the full history of the private config repository is checked with a secret scanner
- **THEN** no plaintext secrets are found

#### Scenario: Secrets on the device
- **WHEN** a push with a honk configuration, a Tailscale login, SMB users and a dynamic DNS service has ended, successfully or not
- **THEN** the push's temporary files were readable by root alone while they were there and are gone, honk's files and Tailscale's auth key are readable by root alone, no process was started with the Tailscale auth key, an SMB user's password or the Cloudflare API token among its arguments, and each SMB user logs in with the password pushed
