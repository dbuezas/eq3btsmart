from dataclasses import dataclass, field
from typing import Self

from construct_typed import DataclassStruct

from eq3btsmart.const import EQ3BT_OFF_TEMP, EQ3BT_ON_TEMP, OperationMode, WeekDay
from eq3btsmart.eq3_away_time import Eq3AwayTime
from eq3btsmart.eq3_duration import Eq3Duration
from eq3btsmart.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.eq3_temperature import Eq3Temperature
from eq3btsmart.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.structures import (
    DeviceIdStruct,
    ScheduleDayStruct,
    StatusStruct,
)


@dataclass
class DeviceData:
    firmware_version: int | None = None
    device_serial: str | None = None

    @classmethod
    def from_device(cls, struct: DeviceIdStruct) -> Self:
        return cls(
            firmware_version=struct.version,
            device_serial=struct.serial,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls.from_device(DataclassStruct(DeviceIdStruct).parse(data))


@dataclass
class Status:
    valve: int | None = None
    target_temperature: Eq3Temperature | None = None
    _operation_mode: OperationMode | None = None
    is_away: bool | None = None
    is_boost: bool | None = None
    is_dst: bool | None = None
    is_window_open: bool | None = None
    is_locked: bool | None = None
    is_low_battery: bool | None = None
    away_until: Eq3AwayTime | None = None
    window_open_temperature: Eq3Temperature | None = None
    window_open_time: Eq3Duration | None = None
    comfort_temperature: Eq3Temperature | None = None
    eco_temperature: Eq3Temperature | None = None
    offset_temperature: Eq3TemperatureOffset | None = None

    @property
    def operation_mode(self) -> OperationMode | None:
        if self.target_temperature is None:
            return self._operation_mode

        if self.target_temperature.friendly_value == EQ3BT_OFF_TEMP:
            return OperationMode.OFF

        if self.target_temperature.friendly_value == EQ3BT_ON_TEMP:
            return OperationMode.ON

        return self._operation_mode

    @classmethod
    def from_device(cls, struct: StatusStruct) -> Self:
        return cls(
            valve=struct.valve,
            target_temperature=struct.target_temp,
            _operation_mode=OperationMode.MANUAL
            if struct.mode & struct.mode.MANUAL
            else OperationMode.AUTO,
            is_away=bool(struct.mode & struct.mode.AWAY),
            is_boost=bool(struct.mode & struct.mode.BOOST),
            is_dst=bool(struct.mode & struct.mode.DST),
            is_window_open=bool(struct.mode & struct.mode.WINDOW),
            is_locked=bool(struct.mode & struct.mode.LOCKED),
            is_low_battery=bool(struct.mode & struct.mode.LOW_BATTERY),
            away_until=struct.away,
            window_open_temperature=struct.presets.window_open_temp
            if struct.presets
            else None,
            window_open_time=struct.presets.window_open_time
            if struct.presets
            else None,
            comfort_temperature=struct.presets.comfort_temp if struct.presets else None,
            eco_temperature=struct.presets.eco_temp if struct.presets else None,
            offset_temperature=struct.presets.offset if struct.presets else None,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls.from_device(DataclassStruct(StatusStruct).parse(data))


@dataclass
class ScheduleHour:
    target_temperature: Eq3Temperature
    next_change_at: Eq3ScheduleTime


@dataclass
class ScheduleDay:
    week_day: WeekDay
    schedule_hours: list[ScheduleHour] = field(default_factory=list)

    @classmethod
    def from_device(cls, struct: ScheduleDayStruct) -> Self:
        return cls(
            week_day=struct.day,
            schedule_hours=[
                ScheduleHour(
                    target_temperature=hour.target_temp,
                    next_change_at=hour.next_change_at,
                )
                for hour in struct.hours
            ],
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls.from_device(DataclassStruct(ScheduleDayStruct).parse(data))


@dataclass
class Schedule:
    schedule_days: list[ScheduleDay] = field(default_factory=list)

    def merge(self, other_schedule: Self) -> None:
        for other_schedule_day in other_schedule.schedule_days:
            schedule_day = next(
                (
                    schedule_day
                    for schedule_day in self.schedule_days
                    if schedule_day.week_day == other_schedule_day.week_day
                ),
                None,
            )

            if not schedule_day:
                self.schedule_days.append(other_schedule_day)
                continue

            schedule_day.schedule_hours = other_schedule_day.schedule_hours

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls(schedule_days=[ScheduleDay.from_bytes(data)])
