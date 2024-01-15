import logging
from typing import Any

import voluptuous as vol
from eq3btsmart import Thermostat
from eq3btsmart.const import EQ3BT_MAX_TEMP, EQ3BT_OFF_TEMP
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from dbuezas_eq3btsmart.const import CONF_DEBUG_MODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SET_AWAY_UNTIL_SCHEMA = {
    vol.Required("away_until"): cv.datetime,
    vol.Required("temperature"): vol.Range(min=EQ3BT_OFF_TEMP, max=EQ3BT_MAX_TEMP),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    eq3 = hass.data[DOMAIN][config_entry.entry_id]
    debug_mode = config_entry.options.get(CONF_DEBUG_MODE, False)

    new_devices = [
        AwaySwitch(eq3),
        BoostSwitch(eq3),
    ]
    async_add_entities(new_devices)
    if debug_mode:
        new_devices = [ConnectionSwitch(eq3)]
        async_add_entities(new_devices)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "set_away_until",
        cv.make_entity_service_schema(SET_AWAY_UNTIL_SCHEMA),
        "set_away_until",
    )


class Base(SwitchEntity):
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


class AwaySwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Away"
        self._attr_icon = "mdi:lock"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_away(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_away(False)

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.away

    async def set_away_until(self, away_until, temperature: float) -> None:
        await self._thermostat.async_set_away_until(away_until, temperature)


class BoostSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Boost"
        self._attr_icon = "mdi:speedometer"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_boost(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_boost(False)

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.boost


class ConnectionSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Connection"
        self._attr_icon = "mdi:bluetooth"
        self._attr_assumed_state = True
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._thermostat._conn.async_make_request("ONLY CONNECT")

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._thermostat._conn._conn:
            await self._thermostat._conn._conn.disconnect()

    @property
    def is_on(self) -> bool | None:
        if self._thermostat._conn._conn is None:
            return None
        return self._thermostat._conn._conn.is_connected
