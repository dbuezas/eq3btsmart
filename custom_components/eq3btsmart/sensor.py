import asyncio
import logging
from datetime import datetime

from eq3btsmart import Thermostat
from homeassistant.components.homekit import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
        ValveSensor(eq3),
        AwayEndSensor(eq3),
        SerialNumberSensor(eq3),
        FirmwareVersionSensor(eq3),
    ]
    async_add_entities(new_devices)
    if debug_mode:
        new_devices = [
            RssiSensor(eq3),
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
    def unique_id(self) -> str | None:
        if self.name is None or isinstance(self.name, UndefinedType):
            return None

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
        self._attr_icon = "mdi:pipe-valve"
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def state(self) -> int | None:
        return self._thermostat.valve_state


class AwayEndSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Away until"
        self._attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> datetime | None:
        if self._thermostat.away_end is None:
            return None

        return self._thermostat.away_end


class RssiSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Rssi"
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> int | None:
        return self._thermostat._conn.rssi


class SerialNumberSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Serial"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str | None:
        return self._thermostat.device_serial


class FirmwareVersionSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Firmware Version"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self) -> None:
        asyncio.get_event_loop().create_task(self.fetch_serial())

    async def fetch_serial(self) -> None:
        try:
            await self._thermostat.async_query_id()
        except Exception as e:
            _LOGGER.error(
                f"[{self._thermostat.name}] Error fetching serial number: {e}"
            )
            return

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
    def state(self) -> str | None:
        return self._thermostat.firmware_version


class MacSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "MAC"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str | None:
        return self._thermostat.mac


class RetriesSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Retries"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> int:
        return self._thermostat._conn.retries


class PathSensor(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Path"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str | None:
        if self._thermostat._conn._conn is None:
            return None

        if not hasattr(self._thermostat._conn._conn._backend, "_device_path"):
            return None

        return self._thermostat._conn._conn._backend._device_path
