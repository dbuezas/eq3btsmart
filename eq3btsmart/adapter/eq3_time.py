from datetime import datetime

from eq3btsmart.adapter.base_adapter import BaseAdapter


class Eq3Time(BaseAdapter[datetime, bytes]):
    """Adapter to encode and decode time data."""

    @classmethod
    def _encode(cls, value: datetime) -> bytes:
        return bytes(
            [
                value.year % 100,
                value.month,
                value.day,
                value.hour,
                value.minute,
                value.second,
            ]
        )

    @classmethod
    def _decode(cls, value: bytes) -> datetime:
        (year, month, day, hour, minute, second) = value
        year += 2000

        return datetime(
            year=year, month=month, day=day, hour=hour, minute=minute, second=second
        )
