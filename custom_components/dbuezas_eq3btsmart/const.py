"""Constants for EQ3 Bluetooth Smart Radiator Valves."""
from .python_eq3bt.eq3bt.eq3btsmart import Mode
from homeassistant.components.climate import HVACMode
from .python_eq3bt import eq3bt as eq3  # pylint: disable=import-error

from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_BOOST,
)

PRESET_PERMANENT_HOLD = "Manual"
PRESET_NO_HOLD = "Auto"
PRESET_OPEN = "Open"
PRESET_CLOSED = "Closed"
DOMAIN = "dbuezas_eq3btsmart"


EQ_TO_HA_HVAC = {
    Mode.Open: HVACMode.HEAT,
    Mode.Closed: HVACMode.OFF,
    Mode.Auto: HVACMode.AUTO,
    Mode.Manual: HVACMode.HEAT,
    Mode.Boost: HVACMode.AUTO,
    Mode.Away: HVACMode.HEAT,
}

HA_TO_EQ_HVAC = {
    HVACMode.HEAT: Mode.Manual,
    HVACMode.OFF: Mode.Closed,
    HVACMode.AUTO: Mode.Auto,
}

EQ_TO_HA_PRESET = {
    Mode.Boost: PRESET_BOOST,
    Mode.Away: PRESET_AWAY,
    Mode.Manual: PRESET_PERMANENT_HOLD,
    Mode.Auto: PRESET_NO_HOLD,
    Mode.Open: PRESET_OPEN,
    Mode.Closed: PRESET_CLOSED,
}

HA_TO_EQ_PRESET = {
    PRESET_OPEN: Mode.Open,
    PRESET_CLOSED: Mode.Closed,
    PRESET_NO_HOLD: Mode.Auto,
    PRESET_PERMANENT_HOLD: Mode.Manual,
    PRESET_BOOST: Mode.Boost,
    PRESET_AWAY: Mode.Away,
}
