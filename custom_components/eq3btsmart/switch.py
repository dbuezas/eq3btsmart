"""Platform for eQ-3 switch entities."""

from datetime import datetime
from typing import Any

from custom_components.eq3btsmart.eq3_entity import Eq3Entity
from eq3btsmart import Thermostat
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_ICON_AWAY_SWITCH,
    ENTITY_ICON_BOOST_SWITCH,
    ENTITY_ICON_CONNECTION,
    ENTITY_NAME_AWAY_SWITCH,
    ENTITY_NAME_BOOST_SWITCH,
    ENTITY_NAME_CONNECTION,
)
from .models import Eq3Config, Eq3ConfigEntry
from .schemas import SCHEMA_SET_AWAY_UNTIL


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Called when an entry is setup."""

    eq3_config_entry: Eq3ConfigEntry = hass.data[DOMAIN][config_entry.entry_id]
    thermostat = eq3_config_entry.thermostat
    eq3_config = eq3_config_entry.eq3_config

    entities_to_add = [
        AwaySwitch(eq3_config, thermostat),
        BoostSwitch(eq3_config, thermostat),
    ]

    if eq3_config.debug_mode:
        entities_to_add += [ConnectionSwitch(eq3_config, thermostat)]

    async_add_entities(entities_to_add)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_away_until",
        cv.make_entity_service_schema(SCHEMA_SET_AWAY_UNTIL),
        "set_away_until",
    )


class Base(Eq3Entity, SwitchEntity):
    """Base class for all eQ-3 switches."""

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


class AwaySwitch(Base):
    """Switch to set the thermostat to away mode."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_AWAY_SWITCH
        self._attr_icon = ENTITY_ICON_AWAY_SWITCH

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_away(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_away(False)

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.away

    async def set_away_until(self, away_until: datetime, temperature: float) -> None:
        await self._thermostat.async_set_away_until(away_until, temperature)


class BoostSwitch(Base):
    """Switch to set the thermostat to boost mode."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_BOOST_SWITCH
        self._attr_icon = ENTITY_ICON_BOOST_SWITCH

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_boost(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._thermostat.async_set_boost(False)

    @property
    def is_on(self) -> bool | None:
        return self._thermostat.boost


class ConnectionSwitch(Base):
    """Switch to connect/disconnect the thermostat."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat._conn.register_connection_callback(
            self.schedule_update_ha_state
        )
        self._attr_name = ENTITY_NAME_CONNECTION
        self._attr_icon = ENTITY_ICON_CONNECTION
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
