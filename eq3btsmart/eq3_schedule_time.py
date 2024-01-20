from datetime import time
from typing import Self


class Eq3ScheduleTime(int):
    """Adapter to encode and decode schedule time data."""

    def __new__(cls, value: time):
        return super().__new__(cls, int((value.hour * 60 + value.minute) / 10))

    @property
    def friendly_value(self) -> time:
        hour, minute = divmod(self * 10, 60)
        return time(hour=hour, minute=minute)

    @classmethod
    def from_device(cls, value: int) -> Self:
        hour, minute = divmod(value * 10, 60)
        return cls(time(hour=hour, minute=minute))
