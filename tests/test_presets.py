from datetime import timedelta

from eq3btsmart.adapter.eq3_duration import Eq3Duration
from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.models.presets import Presets
from eq3btsmart.structures import PresetsStruct


def test_presets_from_struct():
    preset_struct = PresetsStruct(
        window_open_temp=Eq3Temperature(4.5),
        window_open_time=Eq3Duration(timedelta(seconds=5)),
        comfort_temp=Eq3Temperature(24),
        eco_temp=Eq3Temperature(16),
        offset=Eq3TemperatureOffset(0),
    )

    presets = Presets.from_struct(preset_struct)

    assert presets.window_open_temperature.value == 4.5
    assert presets.window_open_time.value == timedelta(seconds=5)
    assert presets.comfort_temperature.value == 24
    assert presets.eco_temperature.value == 16
    assert presets.offset_temperature.value == 0


def test_presets_struct_type():
    assert Presets.struct_type() == PresetsStruct
