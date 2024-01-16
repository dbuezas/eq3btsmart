import json
import logging

from eq3btsmart import Thermostat
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEBUG_MODE, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]
    debug_mode = config_entry.options.get(CONF_DEBUG_MODE, False)
    new_devices = [
        BatterySensor(eq3),
        WindowOpenSensor(eq3),
        DSTSensor(eq3),
    ]
    async_add_entities(new_devices)
    if debug_mode:
        new_devices = [
            BusySensor(eq3),
            ConnectedSensor(eq3),
        ]
        async_add_entities(new_devices)


class Base(BinarySensorEntity):
    def __init__(self, _thermostat: Thermostat):
        self._thermostat = _thermostat
        self._attr_has_entity_name = True

    @property
    def unique_id(self) -> str | None:
        if self.name is None or isinstance(self.name, UndefinedType):
            return None

        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )


class BusySensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = "Busy"

    @property
    def is_on(self) -> bool:
        return self._thermostat._conn._lock.locked()


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    # raise TypeError ("Type %s not serializable" % type(obj))
    return None


class ConnectedSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_name = "Connected"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the device specific state attributes."""
        if (device := self._thermostat._conn._ble_device) is None:
            return None
        if (details := device.details) is None:
            return None
        if "props" not in details:
            return None

        return json.loads(json.dumps(details["props"], default=json_serial))

    @property
    def is_on(self) -> bool:
        if self._thermostat._conn._conn is None:
            return False
        return self._thermostat._conn._conn.is_connected


class BatterySensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Battery"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self._thermostat.low_battery


class WindowOpenSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Window Open"
        self._attr_device_class = BinarySensorDeviceClass.WINDOW

    @property
    def is_on(self):
        return self._thermostat.window_open


class DSTSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "dSt"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self._thermostat.dst
