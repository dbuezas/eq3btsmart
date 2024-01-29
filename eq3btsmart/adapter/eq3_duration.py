from datetime import timedelta

from eq3btsmart.adapter.base_adapter import BaseAdapter


class Eq3Duration(BaseAdapter[timedelta, int]):
    """Adapter to encode and decode duration data."""

    @classmethod
    def _encode(cls, value: timedelta) -> int:
        if value.seconds < 0 or value.seconds > 3600.0:
            raise ValueError(
                "Window open time must be between 0 and 60 minutes "
                "in intervals of 5 minutes."
            )

        return int(value.seconds / 300.0)

    @classmethod
    def _decode(cls, value: int) -> timedelta:
        return timedelta(minutes=float(value * 5.0))
