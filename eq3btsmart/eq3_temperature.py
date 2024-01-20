from eq3btsmart.const import (
    EQ3BT_OFF_TEMP,
    EQ3BT_ON_TEMP,
)
from eq3btsmart.exceptions import TemperatureException


class Eq3Temperature(int):
    """Adapter to encode and decode temperature data."""

    def __new__(cls, value: float):
        if value < EQ3BT_OFF_TEMP or value > EQ3BT_ON_TEMP:
            raise TemperatureException(
                f"Temperature {value} out of range [{EQ3BT_OFF_TEMP}, {EQ3BT_ON_TEMP}]"
            )

        return super().__new__(cls, int(value * 2))

    @property
    def friendly_value(self) -> float:
        return self / 2

    @classmethod
    def from_device(cls, value: int):
        return cls(value / 2)

    # @property
    # def is_on_temperature(self) -> bool:
    #     return self == EQ3BT_ON_TEMP

    # @property
    # def is_off_temperature(self) -> bool:
    #     return self == EQ3BT_OFF_TEMP

    # @property
    # def command(self) -> Command:
    #     if self.is_off_temperature or self.is_on_temperature:
    #         return Command.MODE_SET

    #     return Command.TEMPERATURE_SET

    # @property
    # def manual_data_int(self) -> int:
    #     value = self.device_temperature

    #     if self.is_off_temperature or self.is_on_temperature:
    #         value |= ModeFlags.MANUAL

    #     return value

    # @property
    # def away_data_int(self) -> int:
    #     value = self.device_temperature | ModeFlags.AWAY

    #     return value

    # @property
    # def manual_data_bytes(self) -> bytes:
    #     return struct.pack("B", self.manual_data_int)

    # @property
    # def away_data_bytes(self) -> bytes:
    #     return struct.pack("B", self.away_data_int)
