"""Support for dbuezas_eQ-3 Bluetooth Smart thermostats."""

from __future__ import annotations
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_MAC,
    PRECISION_HALVES,
    TEMP_CELSIUS,
)
from homeassistant.components.climate.const import (
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.climate import HVACMode

from homeassistant.components.climate import ClimateEntity
import voluptuous as vol

from datetime import datetime, timedelta
from .python_eq3bt.eq3bt.eq3btsmart import (
    EQ3BT_MAX_TEMP,
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
    Mode,
    Thermostat,
)
from homeassistant.config_entries import ConfigEntry


SCAN_INTERVAL = timedelta(minutes=5)
# PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_MAC): cv.string})

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_entities = [EQ3BTSmartThermostat(eq3, hass)]

    async_add_entities(
        new_entities,
        update_before_add=False,
    )


class EQ3BTSmartThermostat(ClimateEntity):
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

    def __init__(self, _thermostat: Thermostat, _hass: HomeAssistant):
        """Initialize the thermostat."""
        self.hass = _hass
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

        # We are the main entity of the device and should use the device name.
        # See https://developers.home-assistant.io/docs/core/entity#has_entity_name-true-mandatory-for-new-integrations
        self._attr_has_entity_name = True
        self._attr_name = None

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug("[%s] adding", self._thermostat.name)
        asyncio.get_event_loop().create_task(self.async_update())

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug("[%s] removing", self._thermostat.name)

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
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def available(self) -> bool:
        """Return if thermostat is available."""
        return self._is_available

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
        return self._current_temperature

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

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return list(HA_TO_EQ_HVAC)

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
    def min_temp(self):
        """Return the minimum temperature."""
        return EQ3BT_OFF_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return EQ3BT_MAX_TEMP

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        if self._thermostat.boost:
            return Preset.BOOST
        if self._thermostat.away:
            return Preset.AWAY
        if self._thermostat.locked:
            return Preset.LOCKED
        if self._thermostat.target_temperature == self._thermostat.eco_temperature:
            return Preset.ECO
        if self._thermostat.target_temperature == self._thermostat.comfort_temperature:
            return Preset.COMFORT
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
    def preset_modes(self):
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        return list(Preset)

    @property
    def unique_id(self) -> str:
        """Return the MAC address of the thermostat."""
        return format_mac(self._thermostat.mac)

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

    async def async_update(self):
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
