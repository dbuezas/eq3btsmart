import logging

from eq3btsmart import Thermostat
from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from dbuezas_eq3btsmart.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = [
        LockedSwitch(eq3),
    ]
    async_add_entities(new_devices)


class Base(LockEntity):
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


class LockedSwitch(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Locked"

    async def async_lock(self, **kwargs) -> None:
        await self._thermostat.async_set_locked(True)

    async def async_unlock(self, **kwargs) -> None:
        await self._thermostat.async_set_locked(False)

    @property
    def is_locked(self) -> bool | None:
        return self._thermostat.locked
