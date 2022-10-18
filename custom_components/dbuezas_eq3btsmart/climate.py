"""Support for dbuezas_eQ-3 Bluetooth Smart thermostats."""

from __future__ import annotations
from .python_eq3bt import eq3bt as eq3  # pylint: disable=import-error
from .const import PRESET_CLOSED, PRESET_NO_HOLD, PRESET_OPEN, PRESET_PERMANENT_HOLD
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers import entity_platform, service
from homeassistant.helpers import config_validation as cv
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_DEVICES,
    CONF_MAC,
    PRECISION_HALVES,
    TEMP_CELSIUS,
)
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
import voluptuous as vol

from datetime import date, datetime, time, timedelta
from .python_eq3bt.eq3bt.eq3btsmart import (
    Thermostat,
    EQ3BT_MIN_TEMP,
    EQ3BT_MAX_TEMP,
    EQ3BT_OFF_TEMP,
)
from homeassistant.config_entries import ConfigEntry

from bleak.backends.device import BLEDevice

SCAN_INTERVAL = timedelta(minutes=15)
# PARALLEL_UPDATES = 0

import asyncio
import json
import logging
import time as the_time


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, time):
        return {"hour": obj.hour, "minute": obj.minute}
    # raise TypeError ("Type %s not serializable" % type(obj))
    return None


_LOGGER = logging.getLogger(__name__)

STATE_BOOST = "boost"

ATTR_STATE_WINDOW_OPEN = "window_open"
ATTR_STATE_VALVE = "valve"
ATTR_STATE_LOCKED = "is_locked"
ATTR_STATE_LOW_BAT = "low_battery"
ATTR_STATE_AWAY_END = "away_end"

EQ_TO_HA_HVAC = {
    eq3.Mode.Open: HVAC_MODE_HEAT,
    eq3.Mode.Closed: HVAC_MODE_OFF,
    eq3.Mode.Auto: HVAC_MODE_AUTO,
    eq3.Mode.Manual: HVAC_MODE_HEAT,
    eq3.Mode.Boost: HVAC_MODE_AUTO,
    eq3.Mode.Away: HVAC_MODE_HEAT,
}

HA_TO_EQ_HVAC = {
    HVAC_MODE_HEAT: eq3.Mode.Manual,
    HVAC_MODE_OFF: eq3.Mode.Closed,
    HVAC_MODE_AUTO: eq3.Mode.Auto,
}

EQ_TO_HA_PRESET = {
    eq3.Mode.Boost: PRESET_BOOST,
    eq3.Mode.Away: PRESET_AWAY,
    eq3.Mode.Manual: PRESET_PERMANENT_HOLD,
    eq3.Mode.Auto: PRESET_NO_HOLD,
    eq3.Mode.Open: PRESET_OPEN,
    eq3.Mode.Closed: PRESET_CLOSED,
}

HA_TO_EQ_PRESET = {
    PRESET_BOOST: eq3.Mode.Boost,
    PRESET_AWAY: eq3.Mode.Away,
    PRESET_PERMANENT_HOLD: eq3.Mode.Manual,
    PRESET_NO_HOLD: eq3.Mode.Auto,
    PRESET_OPEN: eq3.Mode.Open,
    PRESET_CLOSED: eq3.Mode.Closed,
}


DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_MAC): cv.string})

# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
#     {vol.Required(CONF_DEVICES): vol.Schema({cv.string: DEVICE_SCHEMA})}
# )

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

# this is the setup through config.yaml.
# def setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the eQ-3 BLE thermostats."""
#     devices = []
#     for name, device_cfg in config[CONF_DEVICES].items():
#         mac = device_cfg[CONF_MAC]
#         devices.append(EQ3BTSmartThermostat(mac, name))
#     add_entities(devices, True)

# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed entry in HA."""
    eq3 = EQ3BTSmartThermostat(entry.data["mac"], entry.data["name"], hass)
    devices = []
    devices.append(eq3)
    async_add_entities(
        devices, update_before_add=False
    )  # True means update right after init

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "fetch_serial",
        {},
        EQ3BTSmartThermostat.fetch_serial.__name__,
    )

    platform.async_register_entity_service(
        "fetch_schedule",
        {
            vol.Optional("day"): vol.All(vol.Coerce(int), vol.Clamp(min=0, max=6)),
        },
        EQ3BTSmartThermostat.fetch_schedule.__name__,
    )
    platform.async_register_entity_service(
        "set_schedule",
        {},
        EQ3BTSmartThermostat.set_schedule.__name__,
    )

    @callback
    def _async_discovered_device(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Subscribe to bluetooth changes."""
        eq3.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_device,
            {"address": entry.data["mac"], "connectable": True},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )


def get_full_class_name(obj):
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + "." + obj.__class__.__name__


class EQ3BTSmartThermostat(ClimateEntity):
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

    def __init__(self, _mac: str, _name: str, _hass: HomeAssistant):
        """Initialize the thermostat."""
        # We want to avoid name clash with this module.
        self.hass = _hass
        self._name = _name
        self._mac = _mac
        self._ui_target_temperature = None
        self._is_setting_temperature = False
        self._thermostat = eq3.Thermostat(_mac, _name, _hass)
        self._skip_next_update = False
        self._loop = asyncio.new_event_loop()

    def set_ble_device(self, ble_device: BLEDevice):
        self._thermostat.set_ble_device(ble_device)
        self.schedule_update_ha_state(force_refresh=True)

    # def should_poll(self):
    #     return False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def available(self) -> bool:
        """Return if thermostat is available."""
        return self._thermostat.mode >= 0

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement that is used."""
        return TEMP_CELSIUS

    @property
    def precision(self):
        """Return eq3bt's precision 0.5."""
        return PRECISION_HALVES

    @property
    def current_temperature(self):
        """Can not report temperature, so return target_temperature."""
        return self._ui_target_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._thermostat.target_temperature

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = round(temperature * 2) / 2  # increments of 0.5
        temperature = min(temperature, self.max_temp)
        temperature = max(temperature, self.min_temp)
        self._is_setting_temperature = True
        self._ui_target_temperature = temperature
        self.async_schedule_update_ha_state(
            force_refresh=False
        )  # show current temp now
        await self.async_set_temperature_now()

    async def async_set_temperature_now(self):
        await self._thermostat.async_set_target_temperature(self._ui_target_temperature)
        self._is_setting_temperature = False
        self._skip_next_update = True

    @property
    def hvac_mode(self):
        """Return the current operation mode."""
        if self._thermostat.mode < 0:
            return HVAC_MODE_OFF
        return EQ_TO_HA_HVAC[self._thermostat.mode]

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return list(HA_TO_EQ_HVAC)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        # if self.preset_mode:
        #     return
        await self._thermostat.async_set_mode(HA_TO_EQ_HVAC[hvac_mode])
        self._skip_next_update = True

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return EQ3BT_OFF_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return EQ3BT_MAX_TEMP

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        schedule = {}

        def stringifyTime(timeObj):
            if isinstance(timeObj, time):
                return str(timeObj.hour) + ":" + str(timeObj.minute)
            return None

        for day in self._thermostat.schedule:
            obj = self._thermostat.schedule[day]

            def mapFunc(hourObj):
                return {
                    "target_temp": hourObj.target_temp,
                    "next_change_at": stringifyTime(hourObj.next_change_at),
                }

            schedule[day] = {
                "base_temp": obj.base_temp,
                "next_change_at": stringifyTime(obj.next_change_at),
                "hours": list(map(mapFunc, obj.hours)),
            }
        dev_specific = {
            ATTR_STATE_AWAY_END: self._thermostat.away_end,
            ATTR_STATE_LOCKED: self._thermostat.locked,
            ATTR_STATE_LOW_BAT: self._thermostat.low_battery,
            ATTR_STATE_VALVE: self._thermostat.valve_state,
            ATTR_STATE_WINDOW_OPEN: self._thermostat.window_open,
            "rssi": self._thermostat.rssi,
            "firmware_version": self._thermostat.firmware_version,
            "device_serial": self._thermostat.device_serial,
            "schedule": schedule,
            "schedule2": json.loads(
                json.dumps(self._thermostat.schedule, default=json_serial)
            ),
        }

        return dev_specific

    async def fetch_serial(self):
        await self._thermostat.async_query_id()
        self.async_schedule_update_ha_state(force_refresh=True)
        _LOGGER.debug("[%s] serial: %s", self._name, self._thermostat.device_serial)

    async def fetch_schedule(self):
        _LOGGER.debug("[%s] fetch_schedule", self._name)
        for x in range(0, 7):
            await self._thermostat.async_query_schedule(x)
        self.async_schedule_update_ha_state(force_refresh=True)
        _LOGGER.debug(
            "[%s] schedule (day %s): %s", self._name, self._thermostat.schedule
        )

    def set_schedule(self, day: int = 0):
        _LOGGER.debug("[%s] set_schedule (day %s)", self._name, day)

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        return EQ_TO_HA_PRESET.get(self._thermostat.mode)

    @property
    def preset_modes(self):
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        return list(HA_TO_EQ_PRESET)

    @property
    def unique_id(self) -> str:
        """Return the MAC address of the thermostat."""
        return format_mac(self._mac)

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        if preset_mode == PRESET_NONE:
            await self.async_set_hvac_mode(HVAC_MODE_HEAT)
        await self._thermostat.async_set_mode(HA_TO_EQ_PRESET[preset_mode])
        self._skip_next_update = True

    async def _async_thermostat_update(self):
        await self._thermostat.async_update()

    async def async_update(self):
        """Update the data from the thermostat."""
        if self._skip_next_update:
            self._skip_next_update = False
        else:
            await self._async_thermostat_update()
        if self._is_setting_temperature:
            await self.async_set_temperature_now()
        else:
            self._ui_target_temperature = self._thermostat.target_temperature
