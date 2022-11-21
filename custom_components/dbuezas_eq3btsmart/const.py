"""Constants for EQ3 Bluetooth Smart Radiator Valves."""
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
    eq3.Mode.Open: HVACMode.HEAT,
    eq3.Mode.Closed: HVACMode.OFF,
    eq3.Mode.Auto: HVACMode.AUTO,
    eq3.Mode.Manual: HVACMode.HEAT,
    eq3.Mode.Boost: HVACMode.AUTO,
    eq3.Mode.Away: HVACMode.HEAT,
}

HA_TO_EQ_HVAC = {
    HVACMode.HEAT: eq3.Mode.Manual,
    HVACMode.OFF: eq3.Mode.Closed,
    HVACMode.AUTO: eq3.Mode.Auto,
}

EQ_TO_HA_PRESET = {
    eq3.Mode.Boost: PRESET_BOOST,
    eq3.Mode.Away: PRESET_AWAY,
    eq3.Mode.Manual: PRESET_PERMANENT_HOLD,
    eq3.Mode.Auto: PRESET_NO_HOLD,
    eq3.Mode.Open: PRESET_OPEN,
    eq3.Mode.Closed: PRESET_CLOSED,
}

HA_TO_EQ_PRESET = {
    PRESET_OPEN: eq3.Mode.Open,
    PRESET_CLOSED: eq3.Mode.Closed,
    PRESET_NO_HOLD: eq3.Mode.Auto,
    PRESET_PERMANENT_HOLD: eq3.Mode.Manual,
    PRESET_BOOST: eq3.Mode.Boost,
    PRESET_AWAY: eq3.Mode.Away,
}
