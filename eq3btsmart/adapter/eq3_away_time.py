from datetime import datetime, timedelta

from eq3btsmart.adapter.base_adapter import BaseAdapter


class Eq3AwayTime(BaseAdapter[datetime, bytes]):
    """Adapter to encode and decode away time data."""

    @classmethod
    def _encode(cls, value: datetime) -> bytes:
        value += timedelta(minutes=15)
        value -= timedelta(minutes=value.minute % 30)

        if value.year < 2000 or value.year > 2099:
            raise ValueError("Invalid year, possible [2000, 2099]")

        year = value.year - 2000
        hour = value.hour * 2
        if value.minute != 0:
            hour |= 0x01

        return bytes([value.day, year, hour, value.month])

    @classmethod
    def _decode(cls, value: bytes) -> datetime:
        if value == bytes([0x00, 0x00, 0x00, 0x00]):
            return datetime(year=2000, month=1, day=1, hour=0, minute=0)

        (day, year, hour_min, month) = value

        year += 2000

        min = 0
        if hour_min & 0x01:
            min = 30
        hour = int(hour_min / 2)

        return datetime(year=year, month=month, day=day, hour=hour, minute=min)
