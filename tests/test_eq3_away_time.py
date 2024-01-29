from datetime import datetime, timedelta

import pytest

from eq3btsmart.adapter.eq3_away_time import Eq3AwayTime


def test_encode_valid_datetime():
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45)
    encoded = Eq3AwayTime._encode(dt)
    expected_bytes = bytes([15, 22, 22, 6])
    assert encoded == expected_bytes


def test_encode_valid_datetime_with_minute():
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=25)
    encoded = Eq3AwayTime._encode(dt)
    expected_bytes = bytes([15, 22, 21, 6])
    assert encoded == expected_bytes


def test_decode_valid_bytes():
    encoded_bytes = bytes([15, 22, 21, 6])
    decoded = Eq3AwayTime._decode(encoded_bytes)
    expected_datetime = datetime(year=2022, month=6, day=15, hour=10, minute=30)
    assert decoded == expected_datetime


def test_round_trip_consistency():
    dt = datetime(year=2022, month=6, day=15, hour=10, minute=45)
    encoded = Eq3AwayTime._encode(dt)
    decoded = Eq3AwayTime._decode(encoded)
    dt_adjusted = dt + timedelta(minutes=15)
    dt_adjusted -= timedelta(minutes=dt_adjusted.minute % 30)
    assert decoded == dt_adjusted


def test_decode_special_case():
    encoded_bytes = bytes([0x00, 0x00, 0x00, 0x00])
    decoded = Eq3AwayTime._decode(encoded_bytes)
    expected_datetime = datetime(year=2000, month=1, day=1, hour=0, minute=0)
    assert decoded == expected_datetime


def test_encode_invalid_year():
    dt = datetime(year=2100, month=6, day=15, hour=10, minute=45)
    with pytest.raises(ValueError):
        Eq3AwayTime._encode(dt)
