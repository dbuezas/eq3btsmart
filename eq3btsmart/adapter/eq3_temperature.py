from eq3btsmart.adapter.base_adapter import BaseAdapter
from eq3btsmart.const import (
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
)
from eq3btsmart.exceptions import TemperatureException


class Eq3Temperature(BaseAdapter[float, int]):
    """Adapter to encode and decode temperature data."""

    @classmethod
    def _encode(cls, value: float) -> int:
        if value < EQ3BT_OFF_TEMP or value > EQ3BT_ON_TEMP:
            raise TemperatureException(
                f"Temperature {value} out of range [{EQ3BT_OFF_TEMP}, {EQ3BT_ON_TEMP}]"
            )

        return int(value * 2)

    @classmethod
    def _decode(cls, value: int) -> float:
        return float(value / 2)
