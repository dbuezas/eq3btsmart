from dataclasses import dataclass
from typing import Self

from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.models.base_model import BaseModel
from eq3btsmart.structures import PresetsStruct


@dataclass
class Presets(BaseModel[PresetsStruct]):
    window_open_temperature: Eq3Temperature
    window_open_time: Eq3Duration
    comfort_temperature: Eq3Temperature
    eco_temperature: Eq3Temperature
    offset_temperature: Eq3TemperatureOffset

    @classmethod
    def from_struct(cls, struct: PresetsStruct) -> Self:
        return cls(
            window_open_temperature=struct.window_open_temp,
            window_open_time=struct.window_open_time,
            comfort_temperature=struct.comfort_temp,
            eco_temperature=struct.eco_temp,
            offset_temperature=struct.offset,
        )

    @classmethod
    def struct_type(cls) -> type[PresetsStruct]:
        return PresetsStruct
