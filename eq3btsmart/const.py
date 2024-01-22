"""Constants for the eq3btsmart library."""

from enum import Enum, IntEnum

from construct_typed import EnumBase, FlagsEnumBase

EQ3BT_AWAY_TEMP = 12.0
EQ3BT_MIN_TEMP = 5.0
EQ3BT_MAX_TEMP = 29.5
EQ3BT_OFF_TEMP = 4.5
EQ3BT_ON_TEMP = 30.0
EQ3BT_MIN_OFFSET = -3.5
EQ3BT_MAX_OFFSET = 3.5

WRITE_CHARACTERISTIC_UUID = "3fa4585a-ce4a-3bad-db4b-b8df8179ea09"
NOTIFY_CHARACTERISTIC_UUID = "d0e8434d-cd29-0996-af41-6c90f4e0eb2a"

REQUEST_TIMEOUT = 10
RETRY_BACK_OFF_FACTOR = 0.25
RETRIES = 14
MONITOR_INTERVAL = 10

DEFAULT_AWAY_HOURS = 30 * 24
DEFAULT_AWAY_TEMP = 12


class Command(IntEnum):
    ID_GET = 0x00
    ID_RETURN = 0x01
    INFO_RETURN = 0x02
    INFO_GET = 0x03
    SCHEDULE_SET = 0x10
    COMFORT_ECO_CONFIGURE = 0x11
    OFFSET_CONFIGURE = 0x13
    WINDOW_OPEN_CONFIGURE = 0x14
    SCHEDULE_GET = 0x20
    SCHEDULE_RETURN = 0x21
    MODE_SET = 0x40
    TEMPERATURE_SET = 0x41
    COMFORT_SET = 0x43
    ECO_SET = 0x44
    BOOST_SET = 0x45
    LOCK_SET = 0x80


class WeekDay(EnumBase):
    """Weekdays."""

    SATURDAY = 0
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 3
    WEDNESDAY = 4
    THURSDAY = 5
    FRIDAY = 6

    @classmethod
    def from_index(cls, index: int) -> "WeekDay":
        """Return weekday from index."""

        adjusted_index = index + 2 if index < 5 else index - 5
        return cls(adjusted_index)


class OperationMode(EnumBase):
    """Operation modes."""

    AUTO = 0x00
    MANUAL = 0x40
    OFF = 0x49
    ON = 0x7B
    AWAY = 0x80


class StatusFlags(FlagsEnumBase):
    """Status flags."""

    AUTO = 0x00  # always True, doesnt affect building
    MANUAL = 0x01
    AWAY = 0x02
    BOOST = 0x04
    DST = 0x08
    WINDOW = 0x10
    LOCKED = 0x20
    UNKNOWN = 0x40
    LOW_BATTERY = 0x80


class Adapter(str, Enum):
    AUTO = "AUTO"
    LOCAL = "LOCAL"


class Eq3Preset(Enum):
    """Preset modes."""

    COMFORT = 0
    ECO = 1
