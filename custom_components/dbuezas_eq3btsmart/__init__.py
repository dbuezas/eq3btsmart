"""Support for EQ3 devices."""
from __future__ import annotations

import logging
from .python_eq3bt.eq3bt.eq3btsmart import Thermostat

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import config_flow
from .python_eq3bt import eq3bt as eq3  # pylint: disable=import-error
from .const import (
    CONF_ADAPTER,
    DEFAULT_ADAPTER,
    CONF_STAY_CONNECTED,
    DEFAULT_STAY_CONNECTED,
    DOMAIN,
)

PLATFORMS = [
    Platform.CLIMATE,
    Platform.BUTTON,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

_LOGGER = logging.getLogger(__name__)

# based on https://github.com/home-assistant/example-custom-config/tree/master/custom_components/detailed_hello_world_push


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.

    thermostat = Thermostat(
        mac=entry.data["mac"],
        name=entry.data["name"],
        adapter=entry.options.get(CONF_ADAPTER, DEFAULT_ADAPTER),
        stay_connected=entry.options.get(CONF_STAY_CONNECTED, DEFAULT_STAY_CONNECTED),
        hass=hass,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = thermostat

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        thermostat = hass.data[DOMAIN].pop(entry.entry_id)
        thermostat.shutdown()
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener. Called when integration options are changed"""
    await hass.config_entries.async_reload(entry.entry_id)
