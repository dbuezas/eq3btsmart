from dataclasses import dataclass
from typing import Self

from eq3btsmart.adapter.eq3_away_time import Eq3AwayTime
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import EQ3BT_OFF_TEMP, EQ3BT_ON_TEMP, OperationMode
from eq3btsmart.models import BaseModel, Presets
from eq3btsmart.structures import StatusStruct


@dataclass
class Status(BaseModel[StatusStruct]):
    valve: int
    target_temperature: Eq3Temperature
    _operation_mode: OperationMode
    is_away: bool
    is_boost: bool
    is_dst: bool
    is_window_open: bool
    is_locked: bool
    is_low_battery: bool
    away_until: Eq3AwayTime | None = None
    presets: Presets | None = None

    @property
    def operation_mode(self) -> OperationMode:
        if self.target_temperature.value == EQ3BT_OFF_TEMP:
            return OperationMode.OFF

        if self.target_temperature.value == EQ3BT_ON_TEMP:
            return OperationMode.ON

        return self._operation_mode

    @classmethod
    def from_struct(cls, struct: StatusStruct) -> Self:
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
            presets=Presets.from_struct(struct.presets) if struct.presets else None,
        )

    @classmethod
    def struct_type(cls) -> type[StatusStruct]:
        return StatusStruct
