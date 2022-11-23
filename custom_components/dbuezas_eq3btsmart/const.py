"""Constants for EQ3 Bluetooth Smart Radiator Valves."""
from .python_eq3bt.eq3bt.eq3btsmart import Mode
from homeassistant.components.climate import HVACMode
from enum import Enum

DOMAIN = "dbuezas_eq3btsmart"
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_NONE,
)

EQ_TO_HA_HVAC = {
    Mode.Unknown: HVACMode.HEAT,
    Mode.Off: HVACMode.OFF,
    Mode.On: HVACMode.HEAT,
    Mode.Auto: HVACMode.AUTO,
    Mode.Manual: HVACMode.HEAT,
}

HA_TO_EQ_HVAC = {
    HVACMode.OFF: Mode.Off,
    HVACMode.AUTO: Mode.Auto,
    HVACMode.HEAT: Mode.Manual,
}


class Preset(str, Enum):
    NONE = PRESET_NONE
    ECO = PRESET_ECO
    COMFORT = PRESET_COMFORT
    BOOST = PRESET_BOOST
    AWAY = PRESET_AWAY
    LOCKED = "Locked"
    OPEN = "Open"
