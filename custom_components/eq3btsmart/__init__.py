"""Support for EQ3 devices."""

from typing import Any

from eq3btsmart import Thermostat
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADAPTER,
    CONF_CURRENT_TEMP_SELECTOR,
    CONF_DEBUG_MODE,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_STAY_CONNECTED,
    CONF_TARGET_TEMP_SELECTOR,
    DEFAULT_ADAPTER,
    DEFAULT_CURRENT_TEMP_SELECTOR,
    DEFAULT_DEBUG_MODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STAY_CONNECTED,
    DEFAULT_TARGET_TEMP_SELECTOR,
    DOMAIN,
    Adapter,
)
from .models import Eq3Config, Eq3ConfigEntry

PLATFORMS = [
    Platform.CLIMATE,
    Platform.BUTTON,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Called when an entry is setup."""

    mac_address: str = entry.data[CONF_MAC]
    name: str = entry.data[CONF_NAME]
    adapter: Adapter = entry.options.get(CONF_ADAPTER, DEFAULT_ADAPTER)
    stay_connected: bool = entry.options.get(
        CONF_STAY_CONNECTED, DEFAULT_STAY_CONNECTED
    )
    current_temp_selector = entry.options.get(
        CONF_CURRENT_TEMP_SELECTOR, DEFAULT_CURRENT_TEMP_SELECTOR
    )
    target_temp_selector = entry.options.get(
        CONF_TARGET_TEMP_SELECTOR, DEFAULT_TARGET_TEMP_SELECTOR
    )
    external_temp_sensor = entry.options.get(CONF_EXTERNAL_TEMP_SENSOR)
    debug_mode = entry.options.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    eq3_config = Eq3Config(
        mac_address=mac_address,
        name=name,
        adapter=adapter,
        stay_connected=stay_connected,
        current_temp_selector=current_temp_selector,
        target_temp_selector=target_temp_selector,
        external_temp_sensor=external_temp_sensor,
        debug_mode=debug_mode,
        scan_interval=scan_interval,
    )

    thermostat = Thermostat(
        mac=mac_address,
        name=name,
        adapter=adapter,
        stay_connected=stay_connected,
        hass=hass,
    )

    eq3_config_entry = Eq3ConfigEntry(eq3_config=eq3_config, thermostat=thermostat)

    domain_data: dict[str, Any] = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = eq3_config_entry

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Called when an entry is unloaded."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        eq3_config_entry: Eq3ConfigEntry = hass.data[DOMAIN].pop(entry.entry_id)
        eq3_config_entry.thermostat.shutdown()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when an entry is updated."""

    await hass.config_entries.async_reload(entry.entry_id)
