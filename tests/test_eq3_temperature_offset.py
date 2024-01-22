from eq3btsmart.eq3_temperature_offset import Eq3TemperatureOffset


def test_offset_index():
    value_original = 1.5
    value = Eq3TemperatureOffset(value_original)

    assert value == 10
