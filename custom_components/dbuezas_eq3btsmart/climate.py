"""Support for dbuezas_eQ-3 Bluetooth Smart thermostats."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Callable

import voluptuous as vol
from eq3btsmart import Thermostat
from eq3btsmart.const import EQ3BT_MAX_TEMP, EQ3BT_OFF_TEMP, Mode
from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    PRESET_NONE,
    ClimateEntityFeature,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityPlatformState
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from dbuezas_eq3btsmart.const import (
    CONF_CURRENT_TEMP_SELECTOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_TARGET_TEMP_SELECTOR,
    DEFAULT_CURRENT_TEMP_SELECTOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_TEMP_SELECTOR,
    DOMAIN,
    EQ_TO_HA_HVAC,
    HA_TO_EQ_HVAC,
    CurrentTemperatureSelector,
    Preset,
    TargetTemperatureSelector,
)

_LOGGER = logging.getLogger(__name__)
DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_MAC): cv.string})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_entities = [
        EQ3Climate(
            thermostat=eq3,
            scan_interval=config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            ),
            conf_current_temp_selector=config_entry.options.get(
                CONF_CURRENT_TEMP_SELECTOR, DEFAULT_CURRENT_TEMP_SELECTOR
            ),
            conf_target_temp_selector=config_entry.options.get(
                CONF_TARGET_TEMP_SELECTOR, DEFAULT_TARGET_TEMP_SELECTOR
            ),
            conf_external_temp_sensor=config_entry.options.get(
                CONF_EXTERNAL_TEMP_SENSOR, ""
            ),
        )
    ]
    _LOGGER.debug("[%s] created climate entity", eq3.name)

    async_add_entities(
        new_entities,
        update_before_add=False,
    )


class EQ3Climate(ClimateEntity):
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        thermostat: Thermostat,
        scan_interval: float,
        conf_current_temp_selector: CurrentTemperatureSelector,
        conf_target_temp_selector: TargetTemperatureSelector,
        conf_external_temp_sensor: str,
    ):
        """Initialize the thermostat."""
        self._thermostat = thermostat
        self._thermostat.register_update_callback(self._on_updated)
        self._scan_interval = scan_interval
        self._conf_current_temp_selector = conf_current_temp_selector
        self._conf_target_temp_selector = conf_target_temp_selector
        self._conf_external_temp_sensor = conf_external_temp_sensor
        self._target_temperature_to_set: float | None = None
        self._is_setting_temperature = False
        self._is_available = False
        self._cancel_timer: Callable[[], None] | None = None
        # This is the main entity of the device and should use the device name.
        # See https://developers.home-assistant.io/docs/core/entity#has_entity_name-true-mandatory-for-new-integrations
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = PRECISION_TENTHS
        self._attr_hvac_modes = list(HA_TO_EQ_HVAC)
        self._attr_min_temp = EQ3BT_OFF_TEMP
        self._attr_max_temp = EQ3BT_MAX_TEMP
        self._attr_preset_modes = list(Preset)
        self._attr_unique_id = format_mac(self._thermostat.mac)
        self._attr_should_poll = False

        _LOGGER.debug(
            "[%s] created climate entity %s, %s, %s",
            self.name,
            conf_external_temp_sensor,
        )

    async def async_added_to_hass(self) -> None:
        asyncio.get_event_loop().create_task(self._async_scan_loop())

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_timer:
            self._cancel_timer()

    async def _async_scan_loop(self, now=None) -> None:
        await self.async_scan()
        if self._platform_state != EntityPlatformState.REMOVED:
            delay = timedelta(minutes=self._scan_interval)
            self._cancel_timer = async_call_later(
                self.hass, delay, self._async_scan_loop
            )

    @callback
    def _on_updated(self):
        self._is_available = True
        if self._target_temperature_to_set == self._thermostat.target_temperature:
            self._is_setting_temperature = False
        if not self._is_setting_temperature:
            # temperature may have been updated from the thermostat
            self._target_temperature_to_set = self._thermostat.target_temperature
        if self.entity_id is None:
            _LOGGER.warn(
                "[%s] Updated but the entity is not loaded", self._thermostat.name
            )
            return
        self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        """Return if thermostat is available."""
        return self._is_available

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        if self._thermostat.mode == Mode.Off:
            return HVACAction.OFF
        if self._thermostat.valve_state == 0:
            return HVACAction.IDLE
        return HVACAction.HEATING

    @property
    def current_temperature(self) -> float | None:
        """Can not report temperature, so return target_temperature."""
        if self._conf_current_temp_selector == CurrentTemperatureSelector.NOTHING:
            return None
        if self._conf_current_temp_selector == CurrentTemperatureSelector.VALVE:
            if self._thermostat.valve_state is None:
                return None
            valve: int = self._thermostat.valve_state
            return (1 - valve / 100) * 2 + self._thermostat.target_temperature - 2
        if self._conf_current_temp_selector == CurrentTemperatureSelector.UI:
            return self._target_temperature_to_set
        if self._conf_current_temp_selector == CurrentTemperatureSelector.DEVICE:
            return self._thermostat.target_temperature
        if self._conf_current_temp_selector == CurrentTemperatureSelector.ENTITY:
            state = self.hass.states.get(self._conf_external_temp_sensor)
            if state is not None:
                try:
                    return float(state.state)
                except ValueError:
                    pass
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        match self._conf_target_temp_selector:
            case TargetTemperatureSelector.TARGET:
                return self._target_temperature_to_set
            case TargetTemperatureSelector.LAST_REPORTED:
                return self._thermostat.target_temperature

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        # We can also set the HVAC mode when setting the temperature.
        # This needs to be done before changing the temperature because
        # changing the mode might change the temperature.
        if ATTR_HVAC_MODE in kwargs:
            mode = kwargs.get(ATTR_HVAC_MODE)
            if mode is None:
                return
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

        previous_temperature = self._target_temperature_to_set
        self._is_setting_temperature = True
        self._target_temperature_to_set = temperature
        # show current temp now
        self.async_schedule_update_ha_state()

        try:
            await self.async_set_temperature_now()
        except Exception as ex:
            _LOGGER.error(f"[{self._thermostat.name}] Failed setting temperature: {ex}")
            self._target_temperature_to_set = previous_temperature
            self.async_schedule_update_ha_state()

    async def async_set_temperature_now(self) -> None:
        await self._thermostat.async_set_target_temperature(
            self._target_temperature_to_set
        )
        self._is_setting_temperature = False

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current operation mode."""
        if self._thermostat.mode is None:
            return None

        return EQ_TO_HA_HVAC[self._thermostat.mode]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            self._target_temperature_to_set = EQ3BT_OFF_TEMP
            self._is_setting_temperature = True
        else:  # auto or manual/heat
            self._target_temperature_to_set = self._thermostat.target_temperature
            self._is_setting_temperature = False
        self.async_schedule_update_ha_state()

        await self._thermostat.async_set_mode(HA_TO_EQ_HVAC[hvac_mode])

    @property
    def preset_mode(self) -> str | None:
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
        if self._thermostat.target_temperature == self._thermostat.eco_temperature:
            return Preset.ECO
        if self._thermostat.target_temperature == self._thermostat.comfort_temperature:
            return Preset.COMFORT
        if self._thermostat.mode == Mode.On:
            return Preset.OPEN
        return PRESET_NONE

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        match preset_mode:
            case Preset.BOOST:
                await self._thermostat.async_set_boost(True)
            case Preset.AWAY:
                await self._thermostat.async_set_away(True)
            case Preset.ECO:
                if self._thermostat.boost:
                    await self._thermostat.async_set_boost(False)
                if self._thermostat.away:
                    await self._thermostat.async_set_away(False)

                await self._thermostat.async_activate_eco()
            case Preset.COMFORT:
                if self._thermostat.boost:
                    await self._thermostat.async_set_boost(False)
                if self._thermostat.away:
                    await self._thermostat.async_set_away(False)

                await self._thermostat.async_activate_comfort()
            case Preset.OPEN:
                if self._thermostat.boost:
                    await self._thermostat.async_set_boost(False)
                if self._thermostat.away:
                    await self._thermostat.async_set_away(False)

                await self._thermostat.async_set_mode(Mode.On)

        # by now, the target temperature should have been (maybe set) and fetched
        self._target_temperature_to_set = self._thermostat.target_temperature
        self._is_setting_temperature = False

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

    async def async_scan(self) -> None:
        """Update the data from the thermostat."""
        try:
            await self._thermostat.async_update()
            if self._is_setting_temperature:
                await self.async_set_temperature_now()
        except Exception as ex:
            self._is_available = False
            self.schedule_update_ha_state()
            _LOGGER.error(
                "[%s] Error updating: %s",
                self._thermostat.name,
                ex,
            )
