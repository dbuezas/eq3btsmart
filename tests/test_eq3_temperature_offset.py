import pytest

from eq3btsmart.adapter.eq3_temperature_offset import Eq3TemperatureOffset
from eq3btsmart.const import EQ3BT_MAX_OFFSET, EQ3BT_MIN_OFFSET
from eq3btsmart.exceptions import TemperatureException


def test_encode_valid_temperature_offset():
    offset = 1.0
    encoded = Eq3TemperatureOffset._encode(offset)
    assert encoded == 9


def test_decode_valid_int():
    encoded_int = 9
    decoded = Eq3TemperatureOffset._decode(encoded_int)
    assert decoded == 1.0


def test_round_trip_consistency():
    offset = 1.0
    encoded = Eq3TemperatureOffset._encode(offset)
    decoded = Eq3TemperatureOffset._decode(encoded)
    assert decoded == offset


def test_encode_temperature_offset_out_of_range_low():
    offset = EQ3BT_MIN_OFFSET - 0.1
    with pytest.raises(TemperatureException):
        Eq3TemperatureOffset._encode(offset)


def test_encode_temperature_offset_out_of_range_high():
    offset = EQ3BT_MAX_OFFSET + 0.1
    with pytest.raises(TemperatureException):
        Eq3TemperatureOffset._encode(offset)
