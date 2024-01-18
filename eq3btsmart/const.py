"""Constants for the eq3btsmart library."""

from enum import Enum, IntEnum, IntFlag

PROP_ID_QUERY = 0
PROP_ID_RETURN = 1
PROP_INFO_QUERY = 3
PROP_INFO_RETURN = 2
PROP_COMFORT_ECO_CONFIG = 0x11
PROP_OFFSET = 0x13
PROP_WINDOW_OPEN_CONFIG = 0x14
PROP_SCHEDULE_SET = 0x10
PROP_SCHEDULE_QUERY = 0x20
PROP_SCHEDULE_RETURN = 0x21

PROP_MODE_WRITE = 0x40
PROP_TEMPERATURE_WRITE = 0x41
PROP_COMFORT = 0x43
PROP_ECO = 0x44
PROP_BOOST = 0x45
PROP_LOCK = 0x80

NAME_TO_DAY = {"sat": 0, "sun": 1, "mon": 2, "tue": 3, "wed": 4, "thu": 5, "fri": 6}
NAME_TO_CMD = {"write": PROP_SCHEDULE_SET, "response": PROP_SCHEDULE_RETURN}
HOUR_24_PLACEHOLDER = 1234

EQ3BT_AWAY_TEMP = 12.0
EQ3BT_MIN_TEMP = 5.0
EQ3BT_MAX_TEMP = 29.5
EQ3BT_OFF_TEMP = 4.5
EQ3BT_ON_TEMP = 30.0
EQ3BT_MIN_OFFSET = -3.5
EQ3BT_MAX_OFFSET = 3.5

# Handles in linux and BTProxy are off by 1. Using UUIDs instead for consistency
PROP_WRITE_UUID = "3fa4585a-ce4a-3bad-db4b-b8df8179ea09"
PROP_NTFY_UUID = "d0e8434d-cd29-0996-af41-6c90f4e0eb2a"

REQUEST_TIMEOUT = 5
RETRY_BACK_OFF_FACTOR = 0.25
RETRIES = 14

DEFAULT_AWAY_HOURS = 30 * 24
DEFAULT_AWAY_TEMP = 12


class ScheduleCommand(IntEnum):
    """Schedule commands."""

    WRITE = PROP_SCHEDULE_SET
    RESPONSE = PROP_SCHEDULE_RETURN


class WeekDay(IntEnum):
    """Weekdays."""

    SATURDAY = 0
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 3
    WEDNESDAY = 4
    THURSDAY = 5
    FRIDAY = 6


class OperationMode(IntEnum):
    """Operation modes."""

    UNKNOWN = 0
    AUTO = 1
    MANUAL = 2
    ON = 3
    OFF = 4


class DeviceModeFlags(IntFlag):
    """Device modes."""

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
