from .const import DOMAIN
import asyncio
import json
import logging

from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import Thermostat
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = [
        ValveSensor(eq3),
        AwayEndSensor(eq3),
        RssiSensor(eq3),
        SerialNumberSensor(eq3),
        FirmwareVersionSensor(eq3),
        MacSensor(eq3),
        RetriesSensor(eq3),
        PathSensor(eq3),
    ]
    async_add_entities(new_devices)


class Base(SensorEntity):
    def __init__(self, _thermostat: Thermostat):
        self._thermostat = _thermostat
        self._attr_has_entity_name = True

    @property
    def unique_id(self) -> str:
        assert self.name
        return format_mac(self._thermostat.mac) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )


class ValveSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Valve"
        self._attr_native_unit_of_measurement = "%"

    @property
    def state(self):
        return self._thermostat.valve_state


class AwayEndSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Away until"
        self._attr_device_class = "date"

    @property
    def native_value(self):
        return self._thermostat.away_end if self._thermostat.away else None


class RssiSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Rssi"
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._thermostat._conn.rssi


class SerialNumberSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Serial"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._thermostat.device_serial


class FirmwareVersionSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Firmware Version"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self) -> None:
        asyncio.get_event_loop().create_task(self.fetch_serial())

    async def fetch_serial(self):
        await self._thermostat.async_query_id()
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, self._thermostat.mac)},
        )
        if device:
            device_registry.async_update_device(
                device_id=device.id, sw_version=self._thermostat.firmware_version
            )

        _LOGGER.debug(
            "[%s] firmware: %s serial: %s",
            self._thermostat.name,
            self._thermostat.firmware_version,
            self._thermostat.device_serial,
        )

    @property
    def state(self):
        return self._thermostat.firmware_version


class MacSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "MAC"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._thermostat.mac


class RetriesSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Retries"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        return self._thermostat._conn.retries


class PathSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Path"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self):
        if self._thermostat._conn._conn == None:
            return None
        return self._thermostat._conn._conn._backend._device_path
