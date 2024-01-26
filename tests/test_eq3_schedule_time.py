from datetime import time

from eq3btsmart.adapter.eq3_schedule_time import Eq3ScheduleTime


def test_encode_valid_time():
    t = time(hour=13, minute=30)
    encoded = Eq3ScheduleTime._encode(t)
    assert encoded == 81


def test_decode_valid_int():
    encoded_int = 81
    decoded = Eq3ScheduleTime._decode(encoded_int)
    assert decoded == time(hour=13, minute=30)


def test_round_trip_consistency():
    t = time(hour=13, minute=30)
    encoded = Eq3ScheduleTime._encode(t)
    decoded = Eq3ScheduleTime._decode(encoded)
    assert decoded == t


def test_encode_edge_case():
    t = time(hour=23, minute=59)
    encoded = Eq3ScheduleTime._encode(t)
    assert encoded == 143


def test_decode_edge_case():
    encoded_int = 143
    decoded = Eq3ScheduleTime._decode(encoded_int)
    assert decoded == time(hour=23, minute=50)
