"""Platform for eQ-3 sensor entities."""

import asyncio
import logging
from datetime import datetime

from eq3btsmart import Thermostat
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_ICON_VALVE,
    ENTITY_NAME_AWAY_END,
    ENTITY_NAME_FIRMWARE_VERSION,
    ENTITY_NAME_MAC,
    ENTITY_NAME_RSSI,
    ENTITY_NAME_SERIAL_NUMBER,
    ENTITY_NAME_VALVE,
)
from .eq3_entity import Eq3Entity
from .models import Eq3Config, Eq3ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Called when an entry is setup."""

    eq3_config_entry: Eq3ConfigEntry = hass.data[DOMAIN][config_entry.entry_id]
    thermostat = eq3_config_entry.thermostat
    eq3_config = eq3_config_entry.eq3_config

    new_devices = [
        ValveSensor(eq3_config, thermostat),
        AwayEndSensor(eq3_config, thermostat),
        SerialNumberSensor(eq3_config, thermostat),
        FirmwareVersionSensor(eq3_config, thermostat),
    ]

    if eq3_config.debug_mode:
        new_devices += [
            RssiSensor(eq3_config, thermostat),
            MacSensor(eq3_config, thermostat),
        ]

    async_add_entities(new_devices)


class Base(Eq3Entity, SensorEntity):
    """Base class for all eQ-3 sensors."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._attr_has_entity_name = True

    @property
    def unique_id(self) -> str | None:
        if self.name is None or isinstance(self.name, UndefinedType):
            return None

        return format_mac(self._eq3_config.mac_address) + "_" + self.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._eq3_config.mac_address)},
        )


class ValveSensor(Base):
    """Sensor for the valve state."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_VALVE
        self._attr_icon = ENTITY_ICON_VALVE
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def state(self) -> int | None:
        return self._thermostat.status.valve


class AwayEndSensor(Base):
    """Sensor for the away end time."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_AWAY_END
        self._attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> datetime | None:
        if self._thermostat.status.away_until is None:
            return None

        return self._thermostat.status.away_until.value


class RssiSensor(Base):
    """Sensor for the RSSI value."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_RSSI
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> int | None:
        return self._thermostat._device._rssi


class SerialNumberSensor(Base):
    """Sensor for the serial number."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_SERIAL_NUMBER
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str | None:
        return self._thermostat.device_data.device_serial


class FirmwareVersionSensor(Base):
    """Sensor for the firmware version."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_FIRMWARE_VERSION
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self) -> None:
        asyncio.get_event_loop().create_task(self.fetch_serial())

    async def fetch_serial(self) -> None:
        try:
            await self._thermostat.async_get_id()
        except Exception as e:
            _LOGGER.error(
                f"[{self._eq3_config.name}] Error fetching serial number: {e}"
            )
            return

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, self._eq3_config.mac_address)},
        )
        if device:
            device_registry.async_update_device(
                device_id=device.id,
                sw_version=str(self._thermostat.device_data.firmware_version),
            )

        _LOGGER.debug(
            f"[{self._eq3_config.name}] firmware: {self._thermostat.device_data.firmware_version} serial: {self._thermostat.device_data.device_serial}",
        )

    @property
    def state(self) -> str | None:
        return str(self._thermostat.device_data.firmware_version)


class MacSensor(Base):
    """Sensor for the MAC address."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._attr_name = ENTITY_NAME_MAC
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def state(self) -> str | None:
        return self._eq3_config.mac_address
