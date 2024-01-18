from dataclasses import dataclass
from datetime import datetime, time, timedelta

from construct_typed import DataclassStruct

from eq3btsmart.const import EQ3BT_OFF_TEMP, EQ3BT_ON_TEMP, OperationMode, WeekDay
from eq3btsmart.structures import (
    DeviceIdStruct,
    ScheduleEntryStruct,
    ScheduleStruct,
    StatusStruct,
)


@dataclass
class DeviceData:
    firmware_version: int
    device_serial: str

    @classmethod
    def from_struct(cls, struct: DeviceIdStruct) -> "DeviceData":
        return cls(
            firmware_version=struct.version,
            device_serial=struct.serial,
        )

    @classmethod
    def from_bytearray(cls, data: bytearray) -> "DeviceData":
        return cls.from_struct(DataclassStruct(DeviceIdStruct).parse(data))


@dataclass
class Status:
    valve: int
    target_temperature: float
    _operation_mode: OperationMode
    is_away: bool
    is_boost: bool
    is_dst: bool
    is_window_open: bool
    is_locked: bool
    is_low_battery: bool
    away_datetime: datetime | None
    window_open_temperature: float | None
    window_open_time: timedelta | None
    comfort_temperature: float | None
    eco_temperature: float | None
    offset_temperature: float | None

    @property
    def operation_mode(self) -> OperationMode:
        if self.target_temperature == EQ3BT_OFF_TEMP:
            return OperationMode.OFF

        if self.target_temperature == EQ3BT_ON_TEMP:
            return OperationMode.ON

        return self._operation_mode

    @classmethod
    def from_struct(cls, struct: StatusStruct) -> "Status":
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
    def from_bytes(cls, data: bytearray | bytes) -> "Status":
        return cls.from_struct(DataclassStruct(StatusStruct).parse(data))


@dataclass
class ScheduleEntry:
    target_temperature: float
    next_change_at: time

    @classmethod
    def from_struct(cls, struct: ScheduleEntryStruct) -> "ScheduleEntry":
        return cls(
            target_temperature=struct.target_temp,
            next_change_at=struct.next_change_at,
        )

    @classmethod
    def from_bytes(cls, data: bytearray | bytes) -> "ScheduleEntry":
        return cls.from_struct(DataclassStruct(ScheduleEntryStruct).parse(data))


@dataclass
class Schedule:
    entries: dict[WeekDay, list[ScheduleEntry]] = {}

    def add_struct(self, struct: ScheduleStruct) -> None:
        if struct.day in self.entries:
            self.entries[struct.day] = []

        self.entries[struct.day] = []

        for entry in struct.hours:
            self.entries[struct.day].append(ScheduleEntry.from_struct(entry))

    def add_bytes(self, data: bytearray | bytes) -> None:
        self.add_struct(DataclassStruct(ScheduleStruct).parse(data))
