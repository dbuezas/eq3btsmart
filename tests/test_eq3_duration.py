from datetime import timedelta

import pytest

from eq3btsmart.adapter.eq3_duration import Eq3Duration


def test_encode_valid_timedelta():
    td = timedelta(minutes=25)
    encoded = Eq3Duration._encode(td)
    assert encoded == 5


def test_decode_valid_int():
    encoded_int = 5
    decoded = Eq3Duration._decode(encoded_int)
    assert decoded == timedelta(minutes=25)


def test_round_trip_consistency():
    td = timedelta(minutes=25)
    encoded = Eq3Duration._encode(td)
    decoded = Eq3Duration._decode(encoded)
    assert decoded == td


def test_encode_invalid_timedelta_negative():
    td = timedelta(minutes=-5)
    with pytest.raises(ValueError):
        Eq3Duration._encode(td)


def test_encode_invalid_timedelta_exceed():
    td = timedelta(minutes=65)
    with pytest.raises(ValueError):
        Eq3Duration._encode(td)
