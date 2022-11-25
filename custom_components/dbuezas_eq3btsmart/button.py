from datetime import time

from .python_eq3bt.eq3bt.structures import (
    HOUR_24_PLACEHOLDER,
)
from .const import DOMAIN
import logging

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from .python_eq3bt.eq3bt.eq3btsmart import EQ3BT_MAX_TEMP, EQ3BT_MIN_TEMP, Thermostat
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def no_time_gaps(value):
    """Validate and transform a time."""

    keys = [
        "target_temp_0",
        "next_change_at_0",
        "target_temp_1",
        "next_change_at_1",
        "target_temp_2",
        "next_change_at_2",
        "target_temp_3",
        "next_change_at_3",
        "target_temp_4",
        "next_change_at_4",
        "target_temp_5",
        "next_change_at_5",
        "target_temp_6",
    ]

    last_none = None
    last_defined = None
    for key in keys:
        if value.get(key) == None:
            last_none = key
        if value.get(key) != None:
            last_defined = key
            if last_none != None:
                raise Exception(f"Missing {last_none} but {key} passed")
    if last_defined == None:
        raise Exception(f"Missing temperature")
    if last_defined.startswith("next_change_at"):
        raise Exception(f"Missing temperature after {last_defined}")
    return value


WEEK_DAYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
EQ3_TEMPERATURE = vol.Range(min=EQ3BT_MIN_TEMP, max=EQ3BT_MAX_TEMP)

SCHEDULE_SCHEMA = {
    vol.Required("days"): vol.All(cv.ensure_list, [vol.In(WEEK_DAYS)]),
    vol.Required("target_temp_0"): EQ3_TEMPERATURE,
    vol.Required("next_change_at_0"): cv.time,
    vol.Required("target_temp_1"): EQ3_TEMPERATURE,
    vol.Optional("next_change_at_1"): cv.time,
    vol.Optional("target_temp_2"): EQ3_TEMPERATURE,
    vol.Optional("next_change_at_2"): cv.time,
    vol.Optional("target_temp_3"): EQ3_TEMPERATURE,
    vol.Optional("next_change_at_3"): cv.time,
    vol.Optional("target_temp_4"): EQ3_TEMPERATURE,
    vol.Optional("next_change_at_4"): cv.time,
    vol.Optional("target_temp_5"): EQ3_TEMPERATURE,
    vol.Optional("next_change_at_5"): cv.time,
    vol.Optional("target_temp_6"): EQ3_TEMPERATURE,
}

SET_SCHEDULE_SCHEMA = vol.All(
    cv.make_entity_service_schema(SCHEDULE_SCHEMA),
    no_time_gaps,
)


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
        "set_schedule",
        SET_SCHEDULE_SCHEMA,
        "set_schedule",
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


def time_str(t: time) -> str:
    return "24:00:00" if t == HOUR_24_PLACEHOLDER else t.isoformat()


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

    async def set_schedule(self, **kwargs) -> None:
        _LOGGER.debug("[%s] set_schedule (day %s)", self._thermostat.name, kwargs)
        for day in kwargs["days"]:
            hours = []
            patched_end = False
            for i in range(0, 6):
                next_change_at = kwargs.get(f"next_change_at_{i}")
                if next_change_at is None:
                    if patched_end:
                        next_change_at = time(0, 0)
                    else:
                        patched_end = True
                        next_change_at = HOUR_24_PLACEHOLDER
                hours.append(
                    {
                        "target_temp": kwargs.get(f"target_temp_{i}", 0),
                        "next_change_at": next_change_at,
                    }
                )
            await self._thermostat.async_set_schedule(day=day, hours=hours)

    @property
    def extra_state_attributes(self):
        schedule = {}
        for day in self._thermostat.schedule:
            day_raw = self._thermostat.schedule[day]
            day_nice = {}
            for i, entry in enumerate(day_raw.hours):
                day_nice[f"target_temp_{i}"] = entry.target_temp
                day_nice[f"next_change_at_{i}"] = time_str(entry.next_change_at)
                if entry.next_change_at == HOUR_24_PLACEHOLDER:
                    break
            schedule[day] = day_nice

        return schedule


class ForceQueryButton(Base):
    def __init__(self, _thermostat: Thermostat):
        super().__init__(_thermostat)
        self._attr_name = "Force Query"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        await self._thermostat.async_update()
