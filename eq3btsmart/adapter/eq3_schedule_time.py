from datetime import time

from eq3btsmart.adapter.base_adapter import BaseAdapter


class Eq3ScheduleTime(BaseAdapter[time, int]):
    """Adapter to encode and decode schedule time data."""

    @classmethod
    def _encode(cls, value: time) -> int:
        return int((value.hour * 60 + value.minute) / 10)

    @classmethod
    def _decode(cls, value: int) -> time:
        hour, minute = divmod(value * 10, 60)
        return time(hour=hour, minute=minute)
