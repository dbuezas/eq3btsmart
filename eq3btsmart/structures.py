"""Structures for the eQ-3 Bluetooth Smart Thermostat."""
from datetime import datetime, time, timedelta

from attr import dataclass
from construct import (
    Adapter,
    Bytes,
    Const,
    GreedyRange,
    IfThenElse,
    Int8ub,
    Optional,
)
from construct_typed import DataclassMixin, DataclassStruct, TEnum, TFlagsEnum, csfield

from eq3btsmart.const import (
    HOUR_24_PLACEHOLDER,
    PROP_ID_RETURN,
    PROP_INFO_RETURN,
    DeviceModeFlags,
    ScheduleCommand,
    WeekDay,
)


class TimeAdapter(Adapter):
    """Adapter to encode and decode schedule times."""

    def _decode(self, obj, ctx, path):
        h, m = divmod(obj * 10, 60)
        if h == 24:  # HACK, can we do better?
            return HOUR_24_PLACEHOLDER
        return time(hour=h, minute=m)

    def _encode(self, obj, ctx, path):
        # TODO: encode h == 24 hack
        if obj == HOUR_24_PLACEHOLDER:
            return int(24 * 60 / 10)
        encoded = int((obj.hour * 60 + obj.minute) / 10)
        return encoded


class TempAdapter(Adapter):
    """Adapter to encode and decode temperature."""

    def _decode(self, obj, ctx, path):
        return float(obj / 2.0)

    def _encode(self, obj, ctx, path):
        return int(obj * 2.0)


class WindowOpenTimeAdapter(Adapter):
    """Adapter to encode and decode window open times (5 min increments)."""

    def _decode(self, obj, context, path):
        return timedelta(minutes=float(obj * 5.0))

    def _encode(self, obj, context, path):
        if isinstance(obj, timedelta):
            obj = obj.seconds
        if 0 <= obj <= 3600.0:
            return int(obj / 300.0)
        raise ValueError(
            "Window open time must be between 0 and 60 minutes "
            "in intervals of 5 minutes."
        )


class TempOffsetAdapter(Adapter):
    """Adapter to encode and decode the temperature offset."""

    def _decode(self, obj, context, path):
        return float((obj - 7) / 2.0)

    def _encode(self, obj, context, path):
        if -3.5 <= obj <= 3.5:
            return int(obj * 2.0) + 7
        raise ValueError(
            "Temperature offset must be between -3.5 and 3.5 (in " "intervals of 0.5)."
        )


class AwayDataAdapter(Adapter):
    """Adapter to encode and decode away data."""

    def _decode(self, obj, ctx, path):
        (day, year, hour_min, month) = obj
        year += 2000

        min = 0
        if hour_min & 0x01:
            min = 30
        hour = int(hour_min / 2)

        return datetime(year=year, month=month, day=day, hour=hour, minute=min)

    def _encode(self, obj, ctx, path):
        if obj.year < 2000 or obj.year > 2099:
            raise Exception("Invalid year, possible [2000,2099]")
        year = obj.year - 2000
        hour = obj.hour * 2
        if obj.minute:  # we encode all minute values to h:30
            hour |= 0x01
        return (obj.day, year, hour, obj.month)


class DeviceSerialAdapter(Adapter):
    """Adapter to decode the device serial number."""

    def _decode(self, obj, context, path):
        return bytearray(n - 0x30 for n in obj).decode()


@dataclass
class PresetsStruct(DataclassMixin):
    """Structure for presets data."""

    window_open_temp: float = csfield(TempAdapter(Int8ub))
    window_open_time: timedelta = csfield(WindowOpenTimeAdapter(Int8ub))
    comfort_temp: float = csfield(TempAdapter(Int8ub))
    eco_temp: float = csfield(TempAdapter(Int8ub))
    offset: float = csfield(TempOffsetAdapter(Int8ub))


@dataclass
class StatusStruct(DataclassMixin):
    """Structure for status data."""

    cmd: int = csfield(Const(PROP_INFO_RETURN, Int8ub))
    const_1: int = csfield(Const(0x01, Int8ub))
    mode: DeviceModeFlags = csfield(TFlagsEnum(Int8ub, DeviceModeFlags))
    valve: int = csfield(Int8ub)
    const_2: int = csfield(Const(0x04, Int8ub))
    target_temp: float = csfield(TempAdapter(Int8ub))
    away: datetime | None = csfield(
        IfThenElse(
            lambda ctx: ctx.mode & DeviceModeFlags.AWAY,
            AwayDataAdapter(Bytes(4)),
            Optional(Bytes(4)),
        )
    )
    presets: PresetsStruct | None = csfield(Optional(DataclassStruct(PresetsStruct)))


@dataclass
class ScheduleEntryStruct(DataclassMixin):
    """Structure for schedule entry data."""

    target_temp: float = csfield(TempAdapter(Int8ub))
    next_change_at: time = csfield(TimeAdapter(Int8ub))


@dataclass
class ScheduleStruct(DataclassMixin):
    """Structure for schedule data."""

    cmd: ScheduleCommand = csfield(TEnum(Int8ub, ScheduleCommand))
    day: WeekDay = csfield(TEnum(Int8ub, WeekDay))
    hours: list[ScheduleEntryStruct] = csfield(
        GreedyRange(DataclassStruct(ScheduleEntryStruct))
    )


@dataclass
class DeviceIdStruct(DataclassMixin):
    """Structure for device data."""

    cmd: int = csfield(Const(PROP_ID_RETURN, Int8ub))
    version: int = csfield(Int8ub)
    unknown_1: int = csfield(Int8ub)
    unknown_2: int = csfield(Int8ub)
    serial: str = csfield(DeviceSerialAdapter(Bytes(10)))
    unknown_3: int = csfield(Int8ub)
