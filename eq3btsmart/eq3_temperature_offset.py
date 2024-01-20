from typing import Self

from eq3btsmart.const import EQ3BT_MAX_OFFSET, EQ3BT_MIN_OFFSET
from eq3btsmart.exceptions import TemperatureException


class Eq3TemperatureOffset(int):
    """Adapter to encode and decode temperature offset data."""

    def __new__(cls, value: float):
        if value < EQ3BT_MIN_OFFSET or value > EQ3BT_MAX_OFFSET:
            raise TemperatureException(
                f"Temperature {value} out of range [{EQ3BT_MIN_OFFSET}, {EQ3BT_MAX_OFFSET}]"
            )

        return super().__new__(cls, int((value + 3.5) / 0.5))

    @property
    def friendly_value(self) -> float:
        return self * 0.5 - 3.5

    @classmethod
    def from_device(cls, value: int) -> Self:
        return cls(value * 0.5 - 3.5)
