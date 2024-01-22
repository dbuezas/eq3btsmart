from eq3btsmart.models import Schedule


def test_schedule():
    received = bytes(
        [
            0x21,
            0x06,
            0x26,
            0x1B,
            0x22,
            0x39,
            0x27,
            0x90,
            0x2C,
            0x81,
            0x22,
            0x90,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    )
    schedule = Schedule.from_bytes(received)

    received = bytes(
        [
            0x21,
            0x06,
            0x26,
            0x1B,
            0x22,
            0x39,
            0x27,
            0x90,
            0x2C,
            0x81,
            0x22,
            0x90,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    )
    schedule2 = Schedule.from_bytes(received)

    schedule.merge(schedule2)
