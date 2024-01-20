"""Platform for eQ-3 button entities."""

import datetime
import logging
from typing import Any

from custom_components.eq3btsmart.eq3_entity import Eq3Entity
from custom_components.eq3btsmart.models import Eq3Config, Eq3ConfigEntry
from eq3btsmart import Thermostat
from eq3btsmart.const import WeekDay
from eq3btsmart.models import Schedule, ScheduleDay, ScheduleHour
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry, UndefinedType
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_NAME_FETCH,
    ENTITY_NAME_FETCH_SCHEDULE,
    SERVICE_SET_SCHEDULE,
)
from .schemas import SCHEMA_SCHEDULE_SET

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

    entities_to_add: list[Entity] = [FetchScheduleButton(eq3_config, thermostat)]
    if eq3_config.debug_mode:
        entities_to_add += [
            FetchButton(eq3_config, thermostat),
        ]

    async_add_entities(entities_to_add)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_SCHEDULE,
        SCHEMA_SCHEDULE_SET,
        SERVICE_SET_SCHEDULE,
    )


class Base(Eq3Entity, ButtonEntity):
    """Base class for all eQ-3 buttons."""

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


class FetchScheduleButton(Base):
    """Button to fetch the schedule from the thermostat."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._thermostat.register_update_callback(self.schedule_update_ha_state)
        self._attr_name = ENTITY_NAME_FETCH_SCHEDULE

    async def async_press(self) -> None:
        await self._thermostat.async_get_schedule()

        _LOGGER.debug(
            f"[{self._eq3_config.name}] schedule: {self._thermostat.schedule}",
        )

    async def set_schedule(self, **kwargs) -> None:
        """Called when the set_schedule service is invoked."""

        _LOGGER.debug(f"[{self._eq3_config.name}] set_schedule: {kwargs}")

        schedule = Schedule()
        for day in kwargs["days"]:
            week_day = WeekDay[day.upper()]
            schedule_hours: list[ScheduleHour] = []
            schedule_day = ScheduleDay(week_day=week_day, schedule_hours=schedule_hours)

            times = [
                kwargs.get(f"next_change_at_{i}", datetime.time(0, 0)) for i in range(6)
            ]
            # times[times.index(datetime.time(0, 0))] = HOUR_24_PLACEHOLDER
            temps = [kwargs.get(f"target_temp_{i}", 0) for i in range(7)]

            for i in range(0, 6):
                schedule_hour = ScheduleHour(
                    target_temperature=temps[i],
                    next_change_at=times[i],
                )
                schedule_hours.append(schedule_hour)

            schedule.schedule_days.append(schedule_day)

        await self._thermostat.async_set_schedule(schedule=schedule)

    @property
    def extra_state_attributes(self):
        schedule = {}
        for day in self._thermostat.schedule.schedule_days:
            day_nice: dict[str, Any] = {"day": day}
            for i, schedule_hour in enumerate(day.schedule_hours):
                day_nice[
                    f"target_temp_{i}"
                ] = schedule_hour.target_temperature.friendly_value
                # if schedule_hour.next_change_at == HOUR_24_PLACEHOLDER:
                #     break
                day_nice[
                    f"next_change_at_{i}"
                ] = schedule_hour.next_change_at.friendly_value.isoformat()
            schedule[day] = day_nice

        return schedule


class FetchButton(Base):
    """Button to fetch the current state from the thermostat."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        super().__init__(eq3_config, thermostat)

        self._attr_name = ENTITY_NAME_FETCH
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        await self._thermostat.async_get_info()
