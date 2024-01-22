from datetime import timedelta
from logging import Logger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class Eq3Coordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        name: str,
        update_interval: timedelta | None,
    ):
        super().__init__(hass, logger, name=name, update_interval=update_interval)
