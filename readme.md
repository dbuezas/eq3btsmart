[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# EQ3 Bluetooth smart

This is a modernized replacement for the native Home Assistant component.

### Installation

1. HACS > Integrations > ⋮ > Custom Repositories
2. Repository: paste the url of this repo
3. Category: Integration
4. Click "Add"
5. Close "Custom Repositories" modal
6. Click "+ EXPLORE & DOWNLOAD REPOSITORIES"
7. Search for eq3btsmart
8. Click Download
9. Restart Home Assistant
10. Go to Settings > Integrations
11. Either wait for autodiscovery, or click "+ ADD INTEGRATION" and search for "dbuezas_eq3btsmart"
12. Addition will succeed immediately, give it some minutes to connect to the thermostat

### Differences with the original component:

- [x] It works in HA version > 2022.7
- [x] Supports ESP32 Bluetooth proxies
- [x] Supports auto discovery
- [x] Supports adding via config flow (UI)
- [x] Fixes setting operation mode
- [x] Allows to turn off by setting temp to 4.5°
- [x] Retries (10 times) when you change a thermostat attribute.
- [x] Push instead of Pull. It updates on bluetooth advertisement instead of polling every x minutes (seems to generate less unsuccessful tries)
- [x] Connections are persistent (this may or may not reduce the battery life, but it makes the thermostats more responsive)
- [x] Fully uses asyncio (less resource intensive)
- [x] `Current Temperature` updates immediately, regardless of when the bluetooth connection is made. The component will apply the change as soon as it can connect with the device.
- [x] Service to fetch heating schedules and serial inside the thermostat
- [ ] Service to set the heating schedules (Work in progress)

### Pairing issues

see https://github.com/rytilahti/python-eq3bt/issues/41

### Credits

This is a derivate from https://github.com/rytilahti/python-eq3bt, and it should actually be PR instead.
Unfortunately, I had to change it too much and had to remove support for the CLI and other backends. Also, the update requires a PR to Home Assistant to work.
So I decided to upload this here so others can make use of their thermostats quickly.
