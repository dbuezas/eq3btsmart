[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/dbuezas)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# EQ3 Bluetooth Smart Thermostat

A modernized temporary replacement for the native Home Assistant component.

[Home Assistant Forum Post](https://community.home-assistant.io/t/eq3-bt-smart-thermostat-working-with-v-2022-7/476620)

## Installation

### Option 1: [HACS](https://hacs.xyz/) Link

1. Click [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=David+Buezas+&repository=https%3A%2F%2Fgithub.com%2Fdbuezas%2Feq3btsmart&category=Integration)
2. Restart Home Assistant

### Option 2: [HACS](https://hacs.xyz/)

1. Or `HACS` > `Integrations` > `⋮` > `Custom Repositories`
2. `Repository`: paste the url of this repo
3. `Category`: Integration
4. Click `Add`
5. Close `Custom Repositories` modal
6. Click `+ EXPLORE & DOWNLOAD REPOSITORIES`
7. Search for `dbuezas_eq3btsmart`
8. Click `Download`
9. Restart _Home Assistant_

### Option 2: Manual copy

1. Copy the `dbuezas_eq3btsmart` folder inside `custom_components` of this repo to `/config/custom_components` in your Home Assistant instance
2. Restart _Home Assistant_

## Adding devices

1. Go to `Settings` > `Integrations`
2. Either wait for automatic discovery,

<img width="290" alt="image" src="https://user-images.githubusercontent.com/777196/204042747-633106fb-f63c-439a-9dea-802df341e45d.png">​

<img width="290" alt="image" src="https://user-images.githubusercontent.com/777196/204042753-6d08d4b2-d220-4d9b-9fd9-35ca57b5acc9.png">​

or click `+ ADD INTEGRATION` and search for `dbuezas_eq3btsmart`

<img width="290" alt="image" src="https://user-images.githubusercontent.com/777196/204042799-548a382f-6220-4d9f-a8e8-748ecc0de105.png">

3. Addition will succeed immediately, so give the entity some minutes to connect to the thermostat

### Pairing issues

See here https://github.com/rytilahti/python-eq3bt#pairing

### Device entities

<img width="685" alt="image" src="https://user-images.githubusercontent.com/777196/202929567-04d769f4-8f43-4032-9036-446ad447512b.png">

### Setting schedules

The internal schedules of the Auto mode can be set via a service

<img width="445" alt="image" src="https://user-images.githubusercontent.com/777196/204042126-b0e434cb-eceb-487b-bf0c-7ce178904622.png">

### Viewing schedules

There is a button to fetch the schedules from the thermostats. These are shown as attributes of that button.

<img width="385" alt="image" src="https://user-images.githubusercontent.com/777196/204042508-2d95e613-76f3-4b14-b6e4-944de487a9ed.png">

### Setting Vacation Mode / Away Mode

There is a service to set up Away mode (vacation) with an end date/time, and target temperature.

<img width="445" alt="image" src="https://user-images.githubusercontent.com/777196/222268603-a312f691-2174-43c0-a14e-0790f19db929.png">

To easily set all thermostats to away you can combine it with an input timedate helper and a script and add them to lovelace like this:

<img width="445" alt="image" src="https://user-images.githubusercontent.com/777196/222269450-fef3a62c-70f0-4184-92ac-c1dc939753be.png">


### Device options

Most notably, you can select a specific bluetooth adapter, or limit to local ones.

<img width="420" alt="image" src="https://user-images.githubusercontent.com/777196/208250665-9cead674-6ea3-4260-aa3f-a3237196934b.png">

### Differences with the original component:

- [x] It works in HA version > 2022.7
- [x] Support for BTProxy thanks to @ignisf (make sure you configure `active: true` in the BTProxy).
- [x] Supports auto discovery
- [x] Supports adding via config flow (UI)
- [x] Fixes setting operation mode
- [x] Allows to turn off by setting temp to 4.5°
- [x] Retries (10 times) when you change a thermostat attribute.
- ~~[x] Push instead of Pull. It updates on bluetooth advertisement instead of polling every x minutes (seems to generate less unsuccessful tries)~~
- [x] Connections are persistent (this may or may not reduce the battery life, but it makes the thermostats more responsive)
- [x] Fully uses asyncio (less resource intensive)
- [x] `Current Temperature` updates immediately, regardless of when the bluetooth connection is made. The component will apply the change as soon as it can connect with the device.
- [x] Service to fetch heating schedules and serial inside the thermostat
- [x] Only one concurrent request per thermostat
- [x] Service to set the heating schedules
- ~~[ ] Support for installing via yaml~~
- ~~[ ] Support pairing while adding entity~~
- [x] All features of the thermostat are exposed as entities
- [x] Bluetooth adapter, scan interval, etc are configurable.

### Previous Art

This is heavily based on https://github.com/rytilahti/python-eq3bt and https://github.com/home-assistant/core/tree/dev/homeassistant/components/eq3btsmart and it should ideally be two PRs instead.
Unfortunately, the changes go too deep and remove support for the CLI and other backends.
Therefore, here's a self contained custom component instead.
