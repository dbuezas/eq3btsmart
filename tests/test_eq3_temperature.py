import pytest

from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import EQ3BT_OFF_TEMP, EQ3BT_ON_TEMP
from eq3btsmart.exceptions import TemperatureException


def test_encode_valid_temperature():
    temperature = 22.0
    encoded = Eq3Temperature._encode(temperature)
    assert encoded == 44


def test_decode_valid_int():
    encoded_int = 44
    decoded = Eq3Temperature._decode(encoded_int)
    assert decoded == 22.0


def test_round_trip_consistency():
    temperature = 22.0
    encoded = Eq3Temperature._encode(temperature)
    decoded = Eq3Temperature._decode(encoded)
    assert decoded == temperature


def test_encode_temperature_out_of_range_low():
    temperature = EQ3BT_OFF_TEMP - 0.1
    with pytest.raises(TemperatureException):
        Eq3Temperature._encode(temperature)


def test_encode_temperature_out_of_range_high():
    temperature = EQ3BT_ON_TEMP + 0.1
    with pytest.raises(TemperatureException):
        Eq3Temperature._encode(temperature)
