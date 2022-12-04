"""Support for dbuezas_eQ-3 Bluetooth Smart thermostats."""

from __future__ import annotations
from datetime import timedelta
import logging
import asyncio

from .const import (
    EQ_TO_HA_HVAC,
    HA_TO_EQ_HVAC,
    Preset,
    DOMAIN,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import format_mac, CONNECTION_BLUETOOTH
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    PRECISION_HALVES,
    TEMP_CELSIUS,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.climate import HVACMode

from homeassistant.components.climate import ClimateEntity
import voluptuous as vol

from .python_eq3bt.eq3bt.eq3btsmart import (
    EQ3BT_MAX_TEMP,
    EQ3BT_OFF_TEMP,
    Mode,
    Thermostat,
)
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)
DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_MAC): cv.string})
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
DEFAULT_SCAN_INTERVAL = 1  # minutes


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_entities = [
        EQ3Climate(
            eq3, config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
    ]
    _LOGGER.debug("[%s] created climate entity", eq3.name)

    async_add_entities(
        new_entities,
        update_before_add=False,
    )


class EQ3Climate(ClimateEntity):
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

    def __init__(self, _thermostat: Thermostat, scan_interval: float):
        """Initialize the thermostat."""
        self._current_temperature = None
        # TODO: refactor the is_setting_temperature mess.
        self._is_setting_temperature = False
        self._thermostat = _thermostat
        self._thermostat.register_update_callback(self._on_updated)
        # HA forces an update after any prop is set (temp, mode, etc)
        # But each time anything is set, the thermostat responds with the most current data
        # This means after setting a prop, we can skip the next scheduled update.
        self._skip_next_update = False
        self._is_available = False
        self._scan_interval = scan_interval
        # We are the main entity of the device and should use the device name.
        # See https://developers.home-assistant.io/docs/core/entity#has_entity_name-true-mandatory-for-new-integrations
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_precision = PRECISION_HALVES
        self._attr_hvac_modes = list(HA_TO_EQ_HVAC)
        self._attr_min_temp = EQ3BT_OFF_TEMP
        self._attr_max_temp = EQ3BT_MAX_TEMP
        self._attr_preset_modes = list(Preset)
        self._attr_unique_id = format_mac(self._thermostat.mac)
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("[%s] adding", self._thermostat.name)
        asyncio.get_event_loop().create_task(self._async_update_loop())

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("[%s] removing", self._thermostat.name)
        self._cancel_timer()

    async def _async_update_loop(self):
        _LOGGER.debug(
            "[%s] update_loop starting scan = %s",
            self._thermostat.name,
            self._scan_interval,
        )
        await self.async_update()
        self._cancel_timer = async_track_time_interval(
            self.hass, self.async_update, timedelta(minutes=self._scan_interval)
        )

    @callback
    def _on_updated(self):
        self._is_available = True
        if self._current_temperature == self.target_temperature:
            self._is_setting_temperature = False
        if not self._is_setting_temperature:
            # temperature may have been updated from the thermostat
            self._current_temperature = self.target_temperature
        if self.entity_id is None:
            _LOGGER.warn(
                "[%s] Updated but the entity is not loaded", self._thermostat.name
            )
            return
        self.schedule_update_ha_state(force_refresh=False)

    @property
    def available(self) -> bool:
        """Return if thermostat is available."""
        return self._is_available

    @property
    def current_temperature(self):
        """Can not report temperature, so return target_temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._thermostat.target_temperature

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        # We can also set the HVAC mode when setting the temperature.
        # This needs to be done before changing the temperature because
        # changing the mode might change the temperature.
        if ATTR_HVAC_MODE in kwargs:
            mode = kwargs.get(ATTR_HVAC_MODE)
            assert mode != None
            # Setting the mode to off while change the tempreature doesn't make sense.
            if mode != HVACMode.OFF:
                await self.async_set_hvac_mode(mode)
            else:
                _LOGGER.warning(
                    "[%s] Can't change temperature while changing HVAC mode to off. Ignoring mode change.",
                    self._thermostat.name,
                )

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = round(temperature * 2) / 2  # increments of 0.5
        temperature = min(temperature, self.max_temp)
        temperature = max(temperature, self.min_temp)
        self._is_setting_temperature = True
        self._current_temperature = temperature
        # show current temp now
        self.async_schedule_update_ha_state(force_refresh=False)
        await self.async_set_temperature_now()

    async def async_set_temperature_now(self):
        await self._thermostat.async_set_target_temperature(self._current_temperature)
        self._is_setting_temperature = False
        self._skip_next_update = True

    @property
    def hvac_mode(self):
        """Return the current operation mode."""
        if self._thermostat.mode == None:
            return None

        return EQ_TO_HA_HVAC[self._thermostat.mode]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            self._current_temperature = EQ3BT_OFF_TEMP
            self._is_setting_temperature = True
        else:  # auto or manual/heat
            self._current_temperature = self.target_temperature
            self._is_setting_temperature = False
        self.async_schedule_update_ha_state(force_refresh=False)

        await self._thermostat.async_set_mode(HA_TO_EQ_HVAC[hvac_mode])
        self._skip_next_update = True

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        if self._thermostat.window_open:
            return "Window"
        if self._thermostat.boost:
            return Preset.BOOST
        if self._thermostat.low_battery:
            return "Low Battery"
        if self._thermostat.away:
            return Preset.AWAY
        if self._thermostat.locked:
            return Preset.LOCKED
        if self._thermostat.mode == Mode.On:
            return Preset.OPEN
        return Preset.NONE

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        match preset_mode:
            case Preset.BOOST:
                await self._thermostat.async_set_boost(True)
            case Preset.AWAY:
                await self._thermostat.async_set_away(True)
            case Preset.LOCKED:
                await self._thermostat.async_set_locked(True)
            case Preset.ECO:
                await self._thermostat.async_activate_eco()
            case Preset.COMFORT:
                await self._thermostat.async_activate_comfort()
            case Preset.OPEN:
                await self._thermostat.async_set_mode(Mode.On)
            case Preset.NONE:
                if self._thermostat.locked:
                    await self._thermostat.async_set_locked(False)
                if self._thermostat.boost:
                    await self._thermostat.async_set_boost(False)
                if self._thermostat.away:
                    await self._thermostat.async_set_away(False)
                if self._thermostat.mode == Mode.On:
                    await self._thermostat.async_activate_comfort()

        # by now, the target temperature should have been (maybe set) and fetched
        self._current_temperature = self.target_temperature
        self._is_setting_temperature = False
        self._skip_next_update = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            name=self._thermostat.name,
            manufacturer="eQ-3 AG",
            model="CC-RT-BLE-EQ",
            identifiers={(DOMAIN, self._thermostat.mac)},
            sw_version=self._thermostat.firmware_version,
            connections={(CONNECTION_BLUETOOTH, self._thermostat.mac)},
        )

    async def async_update(self, now=None):
        """Update the data from the thermostat."""
        if self._skip_next_update:
            self._skip_next_update = False
            _LOGGER.debug("[%s] skipped update", self._thermostat.name)
        else:
            try:
                await self._thermostat.async_update()
                if self._is_setting_temperature:
                    await self.async_set_temperature_now()
            except Exception as ex:
                # otherwise, if this happens during the first update, the entity will be dropped and never update
                self._is_available = False
                _LOGGER.error(
                    "[%s] Error updating, will retry later: %s",
                    self._thermostat.name,
                    ex,
                )
