"""Structures for the eQ-3 Bluetooth Smart Thermostat."""
from dataclasses import dataclass

from construct import (
    Adapter,
    Bytes,
    Const,
    Flag,
    GreedyBytes,
    GreedyRange,
    Int8ub,
    Optional,
)
from construct_typed import DataclassMixin, DataclassStruct, TEnum, TFlagsEnum, csfield

from eq3btsmart.const import (
    Command,
    StatusFlags,
    WeekDay,
)
from eq3btsmart.eq3_away_time import Eq3AwayTime
from eq3btsmart.eq3_duration import Eq3Duration
from eq3btsmart.eq3_schedule_time import Eq3ScheduleTime
from eq3btsmart.eq3_temperature import Eq3Temperature
from eq3btsmart.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.eq3_time import Eq3Time


class Eq3TimeAdapter(Adapter):
    """Adapter to encode and decode time data."""

    def _decode(self, obj: bytes, ctx, path) -> Eq3Time:
        return Eq3Time.from_device(obj)

    def _encode(self, obj: Eq3Time, ctx, path) -> bytes:
        return obj


class Eq3ScheduleTimeAdapter(Adapter):
    """Adapter to encode and decode schedule time data."""

    def _decode(self, obj: int, ctx, path) -> Eq3ScheduleTime:
        return Eq3ScheduleTime.from_device(obj)

    def _encode(self, obj: Eq3ScheduleTime, ctx, path) -> int:
        return obj


class Eq3TemperatureAdapter(Adapter):
    """Adapter to encode and decode temperature data."""

    def _decode(self, obj: int, ctx, path) -> Eq3Temperature:
        return Eq3Temperature.from_device(obj)

    def _encode(self, obj: Eq3Temperature, ctx, path) -> int:
        return obj


class Eq3TemperatureOffsetAdapter(Adapter):
    """Adapter to encode and decode temperature offset data."""

    def _decode(self, obj: int, ctx, path) -> Eq3TemperatureOffset:
        return Eq3TemperatureOffset.from_device(obj)

    def _encode(self, obj: Eq3TemperatureOffset, ctx, path) -> int:
        return obj


class Eq3DurationAdapter(Adapter):
    """Adapter to encode and decode duration data."""

    def _decode(self, obj: int, ctx, path) -> Eq3Duration:
        return Eq3Duration.from_device(obj)

    def _encode(self, obj: Eq3Duration, ctx, path) -> int:
        return obj


class Eq3AwayTimeAdapter(Adapter):
    """Adapter to encode and decode away time data."""

    def _decode(self, obj: bytes, ctx, path) -> Eq3AwayTime | None:
        return Eq3AwayTime.from_device(obj)

    def _encode(self, obj: Eq3AwayTime, ctx, path) -> bytes:
        return obj


class DeviceSerialAdapter(Adapter):
    """Adapter to decode the device serial number."""

    def _decode(self, obj, context, path):
        return bytearray(n - 0x30 for n in obj).decode()


@dataclass
class PresetsStruct(DataclassMixin):
    """Structure for presets data."""

    window_open_temp: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    window_open_time: Eq3Duration = csfield(Eq3DurationAdapter(Int8ub))
    comfort_temp: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    eco_temp: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    offset: Eq3TemperatureOffset = csfield(Eq3TemperatureOffsetAdapter(Int8ub))


@dataclass
class StatusStruct(DataclassMixin):
    """Structure for status data."""

    cmd: int = csfield(Const(Command.INFO_RETURN, Int8ub))
    const_1: int = csfield(Const(0x01, Int8ub))
    mode: StatusFlags = csfield(TFlagsEnum(Int8ub, StatusFlags))
    valve: int = csfield(Int8ub)
    const_2: int = csfield(Const(0x04, Int8ub))
    target_temp: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    away: Eq3AwayTime | None = csfield(Eq3AwayTimeAdapter(Bytes(4)))
    presets: PresetsStruct | None = csfield(Optional(DataclassStruct(PresetsStruct)))


@dataclass
class ScheduleHourStruct(DataclassMixin):
    """Structure for schedule entry data."""

    target_temp: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    next_change_at: Eq3ScheduleTime = csfield(Eq3ScheduleTimeAdapter(Int8ub))


@dataclass
class ScheduleDayStruct(DataclassMixin):
    """Structure for schedule data."""

    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))
    hours: list[ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(ScheduleHourStruct))
    )


@dataclass
class DeviceIdStruct(DataclassMixin):
    """Structure for device data."""

    cmd: int = csfield(Const(Command.ID_RETURN, Int8ub))
    version: int = csfield(Int8ub)
    unknown_1: int = csfield(Int8ub)
    unknown_2: int = csfield(Int8ub)
    serial: str = csfield(DeviceSerialAdapter(Bytes(10)))
    unknown_3: int = csfield(Int8ub)


@dataclass
class Eq3Command(DataclassMixin):
    """Structure for eQ-3 commands."""

    cmd: int = csfield(Int8ub)
    payload: bytes | None = csfield(Optional(GreedyBytes))

    def to_bytes(self) -> bytes:
        """Convert the command to bytes."""

        return DataclassStruct(self.__class__).build(self)


@dataclass
class IdGetCommand(Eq3Command):
    """Structure for ID get command."""

    cmd: int = csfield(Const(Command.ID_GET, Int8ub))


@dataclass
class InfoGetCommand(Eq3Command):
    """Structure for info get command."""

    cmd: int = csfield(Const(Command.INFO_GET, Int8ub))
    time: Eq3Time = csfield(Eq3TimeAdapter(Bytes(6)))


@dataclass
class ComfortEcoConfigureCommand(Eq3Command):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(Command.COMFORT_ECO_CONFIGURE, Int8ub))
    comfort_temperature: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    eco_temperature: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))


@dataclass
class OffsetConfigureCommand(Eq3Command):
    """Structure for offset configure command."""

    cmd: int = csfield(Const(Command.OFFSET_CONFIGURE, Int8ub))
    offset: Eq3TemperatureOffset = csfield(Eq3TemperatureOffsetAdapter(Int8ub))


@dataclass
class WindowOpenConfigureCommand(Eq3Command):
    """Structure for window open configure command."""

    cmd: int = csfield(Const(Command.WINDOW_OPEN_CONFIGURE, Int8ub))
    window_open_temperature: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))
    window_open_time: Eq3Duration = csfield(Eq3DurationAdapter(Int8ub))


@dataclass
class ScheduleGetCommand(Eq3Command):
    """Structure for schedule get command."""

    cmd: int = csfield(Const(Command.SCHEDULE_GET, Int8ub))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))


@dataclass
class ModeSetCommand(Eq3Command):
    """Structure for mode set command."""

    cmd: int = csfield(Const(Command.MODE_SET, Int8ub))
    mode: int = csfield(Int8ub)
    away_data: Eq3AwayTime | None = csfield(Optional(Eq3AwayTimeAdapter(Bytes(4))))


@dataclass
class TemperatureSetCommand(Eq3Command):
    """Structure for temperature set command."""

    cmd: int = csfield(Const(Command.TEMPERATURE_SET, Int8ub))
    temperature: Eq3Temperature = csfield(Eq3TemperatureAdapter(Int8ub))


@dataclass
class ScheduleSetCommand(Eq3Command):
    """Structure for schedule set command."""

    cmd: int = csfield(Const(Command.SCHEDULE_SET, Int8ub))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))
    hours: list[ScheduleHourStruct] = csfield(
        GreedyRange(DataclassStruct(ScheduleHourStruct))
    )


@dataclass
class ComfortSetCommand(Eq3Command):
    """Structure for comfort set command."""

    cmd: int = csfield(Const(Command.COMFORT_SET, Int8ub))


@dataclass
class EcoSetCommand(Eq3Command):
    """Structure for eco set command."""

    cmd: int = csfield(Const(Command.ECO_SET, Int8ub))


@dataclass
class BoostSetCommand(Eq3Command):
    """Structure for boost set command."""

    cmd: int = csfield(Const(Command.BOOST_SET, Int8ub))
    enable: bool = csfield(Flag)


@dataclass
class LockSetCommand(Eq3Command):
    """Structure for lock set command."""

    cmd: int = csfield(Const(Command.LOCK_SET, Int8ub))
    enable: bool = csfield(Flag)
