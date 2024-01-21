"""Constants for EQ3 Bluetooth Smart Radiator Valves."""
from enum import Enum

from eq3btsmart.const import Adapter, OperationMode
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
)

DOMAIN = "eq3btsmart"

MANUFACTURER = "eQ-3 AG"
DEVICE_MODEL = "CC-RT-BLE-EQ"

GET_DEVICE_TIMEOUT = 5  # seconds


EQ_TO_HA_HVAC: dict[OperationMode, HVACMode] = {
    OperationMode.OFF: HVACMode.OFF,
    OperationMode.ON: HVACMode.HEAT,
    OperationMode.AUTO: HVACMode.AUTO,
    OperationMode.MANUAL: HVACMode.HEAT,
}

HA_TO_EQ_HVAC = {
    HVACMode.OFF: OperationMode.OFF,
    HVACMode.AUTO: OperationMode.AUTO,
    HVACMode.HEAT: OperationMode.MANUAL,
}


class Preset(str, Enum):
    ECO = PRESET_ECO
    COMFORT = PRESET_COMFORT
    BOOST = PRESET_BOOST
    AWAY = PRESET_AWAY
    OPEN = "Open"
    LOW_BATTERY = "Low Battery"
    WINDOW_OPEN = "Window"


CONF_ADAPTER = "conf_adapter"
CONF_CURRENT_TEMP_SELECTOR = "conf_current_temp_selector"
CONF_TARGET_TEMP_SELECTOR = "conf_target_temp_selector"
CONF_EXTERNAL_TEMP_SENSOR = "conf_external_temp_sensor"
CONF_STAY_CONNECTED = "conf_stay_connected"
CONF_DEBUG_MODE = "conf_debug_mode"
CONF_RSSI = "rssi"

ENTITY_NAME_BUSY = "Busy"
ENTITY_NAME_CONNECTED = "Connected"
ENTITY_NAME_BATTERY = "Battery"
ENTITY_NAME_WINDOW_OPEN = "Window Open"
ENTITY_NAME_DST = "dSt"
ENTITY_NAME_FETCH_SCHEDULE = "Fetch Schedule"
ENTITY_NAME_FETCH = "Fetch"
ENTITY_NAME_LOCKED = "Locked"
ENTITY_NAME_COMFORT = "Comfort"
ENTITY_NAME_ECO = "Eco"
ENTITY_NAME_OFFSET = "Offset"
ENTITY_NAME_WINDOW_OPEN_TEMPERATURE = "Window Open"
ENTITY_NAME_WINDOW_OPEN_TIMEOUT = "Window Open Timeout"
ENTITY_NAME_AWAY_HOURS = "Away Hours"
ENTITY_NAME_AWAY_TEMPERATURE = "Away"
ENTITY_NAME_VALVE = "Valve"
ENTITY_NAME_AWAY_END = "Away until"
ENTITY_NAME_RSSI = "Rssi"
ENTITY_NAME_SERIAL_NUMBER = "Serial"
ENTITY_NAME_FIRMWARE_VERSION = "Firmware Version"
ENTITY_NAME_MAC = "MAC"
ENTITY_NAME_RETRIES = "Retries"
ENTITY_NAME_PATH = "Path"
ENTITY_NAME_AWAY_SWITCH = "Away"
ENTITY_NAME_BOOST_SWITCH = "Boost"
ENTITY_NAME_CONNECTION = "Connection"

ENTITY_ICON_VALVE = "mdi:pipe-valve"
ENTITY_ICON_AWAY_SWITCH = "mdi:lock"
ENTITY_ICON_BOOST_SWITCH = "mdi:speedometer"
ENTITY_ICON_CONNECTION = "mdi:bluetooth"

SERVICE_SET_AWAY_UNTIL = "set_away_until"
SERVICE_SET_SCHEDULE = "set_schedule"


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
DEFAULT_DEBUG_MODE = False
DEFAULT_SCAN_INTERVAL = 10  # seconds
