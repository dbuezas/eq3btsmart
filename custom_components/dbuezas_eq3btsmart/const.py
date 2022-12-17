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


CONF_ADAPTER = "conf_adapter"
CONF_CURRENT_TEMP_SELECTOR = "conf_current_temp_selector"
CONF_EXTERNAL_TEMP_SENSOR = "conf_external_temp_sensor"
CONF_STAY_CONNECTED = "conf_stay_connected"

DEFAULT_SCAN_INTERVAL = 1  # minutes


class Adapter(str, Enum):
    AUTO = "AUTO"
    LOCAL = "LOCAL"


class CurrentTemperatureSelector(str, Enum):
    NOTHING = "NOTHING"
    UI = "UI"
    DEVICE = "DEVICE"
    VALVE = "VALVE"
    ENTITY = "ENTITY"


DEFAULT_ADAPTER = Adapter.AUTO
DEFAULT_CURRENT_TEMP_SELECTOR = CurrentTemperatureSelector.UI
DEFAULT_STAY_CONNECTED = True
