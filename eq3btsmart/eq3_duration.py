from datetime import timedelta


class Eq3Duration(int):
    """Adapter to encode and decode duration data."""

    def __new__(cls, duration: timedelta):
        if duration.seconds < 0 or duration.seconds > 3600.0:
            raise ValueError(
                "Window open time must be between 0 and 60 minutes "
                "in intervals of 5 minutes."
            )

        return super().__new__(cls, int(duration.seconds / 300.0))

    @property
    def friendly_value(self) -> timedelta:
        return timedelta(minutes=self * 5.0)

    @classmethod
    def from_device(cls, value: int):
        return cls(timedelta(minutes=float(value * 5.0)))
