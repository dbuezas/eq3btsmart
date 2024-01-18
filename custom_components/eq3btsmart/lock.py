"""Platform for eQ-3 lock entities."""


from custom_components.eq3btsmart.eq3_entity import Eq3Entity
from custom_components.eq3btsmart.models import Eq3Config, Eq3ConfigEntry
from eq3btsmart import Thermostat
from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENTITY_NAME_LOCKED


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
        LockedSwitch(eq3_config, thermostat),
    ]
    async_add_entities(entities_to_add)


class Base(Eq3Entity, LockEntity):
    """Base class for all eQ-3 lock entities."""

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


class LockedSwitch(Base):
    """Lock to prevent manual changes to the thermostat."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_LOCKED

    async def async_lock(self, **kwargs) -> None:
        await self._thermostat.async_set_locked(True)

    async def async_unlock(self, **kwargs) -> None:
        await self._thermostat.async_set_locked(False)

    @property
    def is_locked(self) -> bool | None:
        return self._thermostat.locked
