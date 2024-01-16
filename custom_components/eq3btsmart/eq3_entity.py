from custom_components.eq3btsmart.models import Eq3Config
from eq3btsmart.thermostat import Thermostat


class Eq3Entity:
    """Base class for all eQ-3 entities."""

    def __init__(self, eq3_config: Eq3Config, thermostat: Thermostat):
        self._eq3_config = eq3_config
        self._thermostat = thermostat
