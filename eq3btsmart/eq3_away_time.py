from datetime import datetime, timedelta
from typing import Self


class Eq3AwayTime(bytes):
    """Adapter to encode and decode away time data."""

    def __new__(cls, value: datetime):
        value += timedelta(minutes=15)
        value -= timedelta(minutes=value.minute % 30)

        if value.year < 2000 or value.year > 2099:
            raise Exception("Invalid year, possible [2000, 2099]")

        year = value.year - 2000
        hour = value.hour * 2
        if value.minute != 0:
            hour |= 0x01

        return super().__new__(cls, bytes([value.day, year, hour, value.month]))

    @property
    def friendly_value(self) -> datetime:
        (day, year, hour_min, month) = self
        year += 2000

        min = 0
        if hour_min & 0x01:
            min = 30
        hour = int(hour_min / 2)

        return datetime(year=year, month=month, day=day, hour=hour, minute=min)

    @classmethod
    def from_device(cls, value: bytes) -> Self:
        (day, year, hour_min, month) = value
        year += 2000

        min = 0
        if hour_min & 0x01:
            min = 30
        hour = int(hour_min / 2)

        return cls(datetime(year=year, month=month, day=day, hour=hour, minute=min))
