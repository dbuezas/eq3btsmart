from datetime import timedelta
from .const import DOMAIN
import logging

from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import (
    EQ3BT_MAX_OFFSET,
    EQ3BT_MAX_TEMP,
    EQ3BT_MIN_OFFSET,
    EQ3BT_MIN_TEMP,
    Thermostat,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = [
        ComfortTemperature(eq3),
        EcoTemperature(eq3),
        OffsetTemperature(eq3),
        WindowOpenTemperature(eq3),
        WindowOpenTimeout(eq3),
        AwayForHours(eq3),
        AwayTemperature(eq3),
    ]
    async_add_entities(new_devices)


class Base(NumberEntity):
    def __init__(self, _thermostat: Thermostat):
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._thermostat = _thermostat
        self._attr_has_entity_name = True
        self._attr_device_class = "temperature"
        self._attr_native_unit_of_measurement = "°C"
        self._attr_native_min_value = EQ3BT_MIN_TEMP
        self._attr_native_max_value = EQ3BT_MAX_TEMP

        self._attr_native_step = 0.5
        self._attr_mode = NumberMode.BOX

    @property
    def unique_id(self) -> str:
        assert self.name
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )


class ComfortTemperature(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Comfort"

    @property
    def native_value(self):
        return self._thermostat.comfort_temperature

    async def async_set_native_value(self, value: float) -> None:
        await self._thermostat.async_update()  # to ensure the other temp is up to date
        other = self._thermostat.eco_temperature
        await self._thermostat.async_temperature_presets(comfort=value, eco=other)


class EcoTemperature(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Eco"

    @property
    def native_value(self):
        return self._thermostat.eco_temperature

    async def async_set_native_value(self, value: float) -> None:
        await self._thermostat.async_update()  # to ensure the other temp is up to date
        other = self._thermostat.comfort_temperature
        await self._thermostat.async_temperature_presets(comfort=other, eco=value)


class OffsetTemperature(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Offset"
        self._attr_native_min_value = EQ3BT_MIN_OFFSET
        self._attr_native_max_value = EQ3BT_MAX_OFFSET

    @property
    def native_value(self):
        return self._thermostat.temperature_offset

    async def async_set_native_value(self, value: float) -> None:
        await self._thermostat.async_set_temperature_offset(value)


class WindowOpenTemperature(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Window Open"

    @property
    def native_value(self):
        return self._thermostat.window_open_temperature

    async def async_set_native_value(self, value: float) -> None:
        await self._thermostat.async_update()  # to ensure the other value is up to date
        await self._thermostat.async_window_open_config(
            temperature=value, duration=self._thermostat.window_open_time
        )


class WindowOpenTimeout(NumberEntity):
    def __init__(self, _thermostat: Thermostat):
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._thermostat = _thermostat
        self._attr_has_entity_name = True
        self._attr_mode = NumberMode.BOX
        self._attr_name = "Window Open Timeout"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 60
        self._attr_native_step = 5
        self._attr_native_unit_of_measurement = "minutes"

    @property
    def unique_id(self) -> str:
        assert self.name
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )

    @property
    def native_value(self):
        if self._thermostat.window_open_time is None:
            return None
        return self._thermostat.window_open_time.total_seconds() / 60

    async def async_set_native_value(self, value: float) -> None:
        await self._thermostat.async_update()  # to ensure the other value is up to date
        await self._thermostat.async_window_open_config(
            temperature=self._thermostat.window_open_temperature,
            duration=timedelta(minutes=value),
        )


class AwayForHours(RestoreNumber):
    def __init__(self, _thermostat: Thermostat):
        self._thermostat = _thermostat
        self._attr_has_entity_name = True
        self._attr_mode = NumberMode.BOX
        self._attr_name = "Away Hours"
        self._attr_native_min_value = 0.5
        self._attr_native_max_value = 1000000
        self._attr_native_step = 0.5
        self._attr_native_unit_of_measurement = "hours"

    @property
    def unique_id(self) -> str:
        assert self.name
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""

        data = await self.async_get_last_number_data()
        if data and data.native_value != None:
            self._thermostat.default_away_hours = data.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._thermostat.default_away_hours = value

    @property
    def native_value(self) -> float | None:
        return self._thermostat.default_away_hours


class AwayTemperature(Base, RestoreNumber):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Away"

    @property
    def unique_id(self) -> str:
        assert self.name
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        data = await self.async_get_last_number_data()
        if data and data.native_value != None:
            self._thermostat.default_away_temp = data.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._thermostat.default_away_temp = value

    @property
    def native_value(self) -> float | None:
        return self._thermostat.default_away_temp
