from dataclasses import dataclass

from eq3btsmart.const import Adapter


@dataclass
class ThermostatConfig:
    mac_address: str
    name: str
    adapter: Adapter
    stay_connected: bool
