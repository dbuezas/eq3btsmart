from datetime import datetime


class Eq3Time(bytes):
    """Adapter to encode and decode time data."""

    def __new__(cls, value: datetime):
        return super().__new__(
            cls,
            bytes(
                [
                    value.year % 100,
                    value.month,
                    value.day,
                    value.hour,
                    value.minute,
                    value.second,
                ]
            ),
        )

    @property
    def friendly_value(self) -> datetime:
        (year, month, day, hour, minute, second) = self
        year += 2000

        return datetime(
            year=year, month=month, day=day, hour=hour, minute=minute, second=second
        )

    @classmethod
    def from_device(cls, value: bytes):
        (year, month, day, hour, minute, second) = value
        year += 2000

        return cls(
            datetime(
                year=year, month=month, day=day, hour=hour, minute=minute, second=second
            )
        )
