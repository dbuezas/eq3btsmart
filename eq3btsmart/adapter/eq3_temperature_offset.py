from eq3btsmart.adapter.base_adapter import BaseAdapter
from eq3btsmart.const import EQ3BT_MAX_OFFSET, EQ3BT_MIN_OFFSET
from eq3btsmart.exceptions import TemperatureException


class Eq3TemperatureOffset(BaseAdapter[float, int]):
    """Adapter to encode and decode temperature offset data."""

    @classmethod
    def _encode(cls, value: float) -> int:
        if value < EQ3BT_MIN_OFFSET or value > EQ3BT_MAX_OFFSET:
            raise TemperatureException(
                f"Temperature {value} out of range [{EQ3BT_MIN_OFFSET}, {EQ3BT_MAX_OFFSET}]"
            )

        return int((value + 3.5) / 0.5)

    @classmethod
    def _decode(cls, value: int) -> float:
        return float(value * 0.5 - 3.5)
