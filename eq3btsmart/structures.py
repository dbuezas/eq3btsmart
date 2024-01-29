"""Structures for the eQ-3 Bluetooth Smart Thermostat."""
from dataclasses import dataclass
from typing import Self

from construct import (
    Bytes,
    Const,
    Flag,
    GreedyBytes,
    GreedyRange,
    Int8ub,
    Optional,
)
from construct_typed import DataclassMixin, DataclassStruct, TEnum, TFlagsEnum, csfield

from eq3btsmart.adapter.eq3_away_time import Eq3AwayTime
from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.adapter.eq3_serial import Eq3Serial
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.adapter.eq3_time import Eq3Time
from eq3btsmart.const import (
    Command,
    StatusFlags,
    WeekDay,
)


class Eq3Struct(DataclassMixin):
    """Structure for eQ-3 data."""

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Convert the data to a structure."""

        return DataclassStruct(cls).parse(data)

    def to_bytes(self) -> bytes:
        """Convert the structure to bytes."""

        return DataclassStruct(self.__class__).build(self)


@dataclass
class PresetsStruct(Eq3Struct):
    """Structure for presets data."""

    window_open_temp: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    window_open_time: Eq3Duration = csfield(Eq3Duration.adapter()(Int8ub))
    comfort_temp: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    eco_temp: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    offset: Eq3TemperatureOffset = csfield(Eq3TemperatureOffset.adapter()(Int8ub))


@dataclass
class StatusStruct(Eq3Struct):
    """Structure for status data."""

    cmd: int = csfield(Const(Command.INFO_RETURN, Int8ub))
    const_1: int = csfield(Const(0x01, Int8ub))
    mode: StatusFlags = csfield(TFlagsEnum(Int8ub, StatusFlags))
    valve: int = csfield(Int8ub)
    const_2: int = csfield(Const(0x04, Int8ub))
    target_temp: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    away: Eq3AwayTime | None = csfield(Optional(Eq3AwayTime.adapter()(Bytes(4))))
    presets: PresetsStruct | None = csfield(Optional(DataclassStruct(PresetsStruct)))


@dataclass
class ScheduleHourStruct(Eq3Struct):
    """Structure for schedule entry data."""

    target_temp: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    next_change_at: Eq3ScheduleTime = csfield(Eq3ScheduleTime.adapter()(Int8ub))


@dataclass
class ScheduleDayStruct(Eq3Struct):
    """Structure for schedule data."""

    cmd: int = csfield(Const(Command.SCHEDULE_RETURN, Int8ub))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))
    hours: list[ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(ScheduleHourStruct))
    )


@dataclass
class DeviceDataStruct(Eq3Struct):
    """Structure for device data."""

    cmd: int = csfield(Const(Command.ID_RETURN, Int8ub))
    version: int = csfield(Int8ub)
    unknown_1: int = csfield(Int8ub)
    unknown_2: int = csfield(Int8ub)
    serial: Eq3Serial = csfield(Eq3Serial.adapter()(Bytes(10)))
    unknown_3: int = csfield(Int8ub)


@dataclass
class Eq3Command(Eq3Struct):
    """Structure for eQ-3 command."""

    cmd: int = csfield(Int8ub)
    data: bytes = csfield(GreedyBytes)


@dataclass
class IdGetCommand(Eq3Struct):
    """Structure for ID get command."""

    cmd: int = csfield(Const(Command.ID_GET, Int8ub))


@dataclass
class InfoGetCommand(Eq3Struct):
    """Structure for info get command."""

    cmd: int = csfield(Const(Command.INFO_GET, Int8ub))
    time: Eq3Time = csfield(Eq3Time.adapter()(Bytes(6)))


@dataclass
class ComfortEcoConfigureCommand(Eq3Struct):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(Command.COMFORT_ECO_CONFIGURE, Int8ub))
    comfort_temperature: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    eco_temperature: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))


@dataclass
class OffsetConfigureCommand(Eq3Struct):
    """Structure for offset configure command."""

    cmd: int = csfield(Const(Command.OFFSET_CONFIGURE, Int8ub))
    offset: Eq3TemperatureOffset = csfield(Eq3TemperatureOffset.adapter()(Int8ub))


@dataclass
class WindowOpenConfigureCommand(Eq3Struct):
    """Structure for window open configure command."""

    cmd: int = csfield(Const(Command.WINDOW_OPEN_CONFIGURE, Int8ub))
    window_open_temperature: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))
    window_open_time: Eq3Duration = csfield(Eq3Duration.adapter()(Int8ub))


@dataclass
class ScheduleGetCommand(Eq3Struct):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(Command.SCHEDULE_GET, Int8ub))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))


@dataclass
class ModeSetCommand(Eq3Struct):
    """Structure for mode set command."""

    cmd: int = csfield(Const(Command.MODE_SET, Int8ub))
    mode: int = csfield(Int8ub)


@dataclass
class AwaySetCommand(ModeSetCommand):
    """Structure for away set command."""

    away_until: Eq3AwayTime = csfield(Eq3AwayTime.adapter()(Bytes(4)))


@dataclass
class TemperatureSetCommand(Eq3Struct):
    """Structure for temperature set command."""

    cmd: int = csfield(Const(Command.TEMPERATURE_SET, Int8ub))
    temperature: Eq3Temperature = csfield(Eq3Temperature.adapter()(Int8ub))


@dataclass
class ScheduleSetCommand(Eq3Struct):
    """Structure for schedule set command."""

    cmd: int = csfield(Const(Command.SCHEDULE_SET, Int8ub))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))
    hours: list[ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(ScheduleHourStruct))
    )


@dataclass
class ComfortSetCommand(Eq3Struct):
    """Structure for comfort set command."""

    cmd: int = csfield(Const(Command.COMFORT_SET, Int8ub))


@dataclass
class EcoSetCommand(Eq3Struct):
    """Structure for eco set command."""

    cmd: int = csfield(Const(Command.ECO_SET, Int8ub))


@dataclass
class BoostSetCommand(Eq3Struct):
    """Structure for boost set command."""

    cmd: int = csfield(Const(Command.BOOST_SET, Int8ub))
    enable: bool = csfield(Flag)


@dataclass
class LockSetCommand(Eq3Struct):
    """Structure for lock set command."""

    cmd: int = csfield(Const(Command.LOCK_SET, Int8ub))
    enable: bool = csfield(Flag)
