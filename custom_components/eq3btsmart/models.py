from dataclasses import dataclass

from eq3btsmart.thermostat import Thermostat

from .const import (
    Adapter,
    CurrentTemperatureSelector,
    TargetTemperatureSelector,
)


@dataclass
class Eq3Config:
    mac_address: str
    name: str
    adapter: Adapter
    stay_connected: bool
    current_temp_selector: CurrentTemperatureSelector
    target_temp_selector: TargetTemperatureSelector
    external_temp_sensor: str
    debug_mode: bool
    scan_interval: int


@dataclass
class Eq3ConfigEntry:
    eq3_config: Eq3Config
    thermostat: Thermostat
