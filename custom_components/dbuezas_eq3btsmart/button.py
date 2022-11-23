from .const import DOMAIN
import logging

from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import Thermostat
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers import entity_platform
from datetime import time
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    eq3 = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = [
        FetchScheduleButton(eq3),
        ForceQueryButton(eq3),
    ]
    async_add_entities(new_devices)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "fetch_schedule",
        {},
        FetchScheduleButton.fetch_schedule.__name__,
    )
    platform.async_register_entity_service(
        "set_schedule",
        {},
        FetchScheduleButton.set_schedule.__name__,
    )


class Base(ButtonEntity):
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

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


class FetchScheduleButton(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        _thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = "Fetch Schedule"

    async def async_press(self) -> None:
        await self.fetch_schedule()

    async def fetch_schedule(self):
        for x in range(0, 7):
            await self._thermostat.async_query_schedule(x)
        _LOGGER.debug(
            "[%s] schedule (day %s): %s",
            self._thermostat.name,
            self._thermostat.schedule,
        )

    def set_schedule(self, day: int = 0):
        _LOGGER.debug("[%s] set_schedule (day %s)", self._thermostat.name, day)

    @property
    def extra_state_attributes(self):
        schedule = {}

        def stringifyTime(timeObj):
            if isinstance(timeObj, time):
                return str(timeObj.hour) + ":" + str(timeObj.minute)
            return None

        for day in self._thermostat.schedule:
            obj = self._thermostat.schedule[day]

            def mapFunc(hourObj):
                return {
                    "target_temp": hourObj.target_temp,
                    "next_change_at": stringifyTime(hourObj.next_change_at),
                }

            schedule[day] = {
                "base_temp": obj.base_temp,
                "next_change_at": stringifyTime(obj.next_change_at),
                "hours": list(map(mapFunc, obj.hours)),
            }
        dev_specific = {
            "schedule": schedule,
        }

        return dev_specific


class ForceQueryButton(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Force Query"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        await self._thermostat.async_update()
