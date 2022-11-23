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
from homeassistant.components.number import NumberEntity, NumberMode
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
    ]
    async_add_entities(new_devices)


class Base(NumberEntity):
    def __init__(self, _thermostat: Thermostat):
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._thermostat = _thermostat
        self._attr_has_entity_name = True
        self._attr_device_class = "temperature"
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
        self._attr_native_min_value = EQ3BT_MIN_TEMP
        self._attr_native_max_value = EQ3BT_MAX_TEMP

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
        self._attr_native_min_value = EQ3BT_MIN_TEMP
        self._attr_native_max_value = EQ3BT_MAX_TEMP

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
