import json
import logging

from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import Thermostat
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.binary_sensor import BinarySensorEntity
from datetime import time
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = [
        BatterySensor(eq3),
        WindowOpenSensor(eq3),
        ConnectedSensor(eq3),
        BussySensor(eq3),
    ]
    async_add_entities(new_devices)


class BaseStateSensor(BinarySensorEntity):
    def __init__(self, _thermostat: Thermostat):
        self._thermostat = _thermostat
        _thermostat.register_update_callback(self.schedule_update_ha_state)

    @property
    def unique_id(self) -> str:
        """Return the MAC address of the thermostat."""
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )


class BaseConnectionSensor(BinarySensorEntity):
    def __init__(self, _thermostat: Thermostat):
        self._thermostat = _thermostat
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return the MAC address of the thermostat."""
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )


class BussySensor(BaseConnectionSensor):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Busy"

    @property
    def is_on(self):
        return self._thermostat._conn._lock.locked()


class ConnectedSensor(BaseConnectionSensor):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Connected"
        self._attr_device_class = "connectivity"

    @property
    def is_on(self):
        if self._thermostat._conn._conn is None:
            return False
        return self._thermostat._conn._conn.is_connected


class BatterySensor(BaseStateSensor):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Battery"
        self._attr_device_class = "battery"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self._thermostat.low_battery


class WindowOpenSensor(BaseStateSensor):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Window Open"
        self._attr_device_class = "window"

    @property
    def state(self):
        return self._thermostat.window_open
