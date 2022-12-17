from .const import CONF_DEBUG_MODE, DOMAIN
import logging

from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import Mode, Thermostat
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    eq3 = hass.data[DOMAIN][config_entry.entry_id]
    debug_mode = config_entry.options.get(CONF_DEBUG_MODE, False)

    new_devices = [
        LockedSwitch(eq3),
        AwaySwitch(eq3),
        BoostSwitch(eq3),
    ]
    async_add_entities(new_devices)
    if debug_mode:
        new_devices = [ConnectionSwitch(eq3)]
        async_add_entities(new_devices)


class Base(SwitchEntity):
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


class LockedSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Locked"
        self._attr_icon = "mdi:lock"

    async def async_turn_on(self):
        await self._thermostat.async_set_locked(True)

    async def async_turn_off(self):
        await self._thermostat.async_set_locked(False)

    @property
    def is_on(self):
        return self._thermostat.locked


class AwaySwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Away"
        self._attr_icon = "mdi:lock"

    async def async_turn_on(self):
        await self._thermostat.async_set_away(True)

    async def async_turn_off(self):
        await self._thermostat.async_set_away(False)

    @property
    def is_on(self):
        return self._thermostat.away


class BoostSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Boost"
        self._attr_icon = "mdi:speedometer"

    async def async_turn_on(self):
        await self._thermostat.async_set_boost(True)

    async def async_turn_off(self):
        await self._thermostat.async_set_boost(False)

    @property
    def is_on(self):
        return self._thermostat.boost


class ConnectionSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat._conn.register_connection_callback(self.schedule_update_ha_state)
        self._attr_name = "Connection"
        self._attr_icon = "mdi:bluetooth"
        self._attr_assumed_state = True
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_turn_on(self):
        await self._thermostat._conn.async_make_request("ONLY CONNECT")

    async def async_turn_off(self):
        if self._thermostat._conn._conn:
            await self._thermostat._conn._conn.disconnect()

    @property
    def is_on(self):
        if self._thermostat._conn._conn is None:
            return None
        return self._thermostat._conn._conn.is_connected
