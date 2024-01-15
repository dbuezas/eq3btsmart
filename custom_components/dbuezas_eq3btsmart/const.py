"""Constants for EQ3 Bluetooth Smart Radiator Valves."""
from enum import Enum

from eq3btsmart.const import Mode
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
)

DOMAIN = "dbuezas_eq3btsmart"

EQ_TO_HA_HVAC: dict[Mode, HVACMode] = {
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
    ECO = PRESET_ECO
    COMFORT = PRESET_COMFORT
    BOOST = PRESET_BOOST
    AWAY = PRESET_AWAY
    OPEN = "Open"


CONF_ADAPTER = "conf_adapter"
CONF_CURRENT_TEMP_SELECTOR = "conf_current_temp_selector"
CONF_TARGET_TEMP_SELECTOR = "conf_target_temp_selector"
CONF_EXTERNAL_TEMP_SENSOR = "conf_external_temp_sensor"
CONF_STAY_CONNECTED = "conf_stay_connected"
CONF_DEBUG_MODE = "conf_debug_mode"

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


class TargetTemperatureSelector(str, Enum):
    TARGET = "TARGET"
    LAST_REPORTED = "LAST_REPORTED"


DEFAULT_ADAPTER = Adapter.AUTO
DEFAULT_CURRENT_TEMP_SELECTOR = CurrentTemperatureSelector.UI
DEFAULT_TARGET_TEMP_SELECTOR = TargetTemperatureSelector.TARGET
DEFAULT_STAY_CONNECTED = True
