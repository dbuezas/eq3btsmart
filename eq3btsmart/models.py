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
    firmware_version: int
    device_serial: str

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
    valve: int
    target_temperature: Eq3Temperature
    _operation_mode: OperationMode
    is_away: bool
    is_boost: bool
    is_dst: bool
    is_window_open: bool
    is_locked: bool
    is_low_battery: bool
    away_datetime: Eq3AwayTime | None
    window_open_temperature: Eq3Temperature | None
    window_open_time: Eq3Duration | None
    comfort_temperature: Eq3Temperature | None
    eco_temperature: Eq3Temperature | None
    offset_temperature: Eq3TemperatureOffset | None

    @property
    def operation_mode(self) -> OperationMode:
        if self.target_temperature == EQ3BT_OFF_TEMP:
            return OperationMode.OFF

        if self.target_temperature == EQ3BT_ON_TEMP:
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
            away_datetime=struct.away,
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
    days: list[ScheduleDay] = field(default_factory=list)

    def merge(self, other_schedule: Self) -> None:
        for schedule_day in other_schedule.days:
            self.days[
                schedule_day.week_day
            ].schedule_hours = schedule_day.schedule_hours

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls(days=[ScheduleDay.from_bytes(data)])
