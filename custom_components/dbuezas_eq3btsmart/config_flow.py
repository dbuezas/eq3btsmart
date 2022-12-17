import datetime
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ADAPTER,
    CONF_CURRENT_TEMP_SELECTOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_STAY_CONNECTED,
    CONF_DEBUG_MODE,
    Adapter,
    CurrentTemperatureSelector,
    DEFAULT_ADAPTER,
    DEFAULT_CURRENT_TEMP_SELECTOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STAY_CONNECTED,
    DOMAIN,
)
import logging

_LOGGER = logging.getLogger(__name__)


class EQ3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EQ3 One"""

    VERSION = 1

    def __init__(self):
        """Initialize the EQ3One flow."""
        self.discovery_info = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        _LOGGER.debug("async_step_user: %s", user_input)

        errors = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_MAC): str,
                    }
                ),
                errors=errors,
            )

        await self.async_set_unique_id(format_mac(user_input[CONF_MAC]))
        self._abort_if_unique_id_configured(updates=user_input)
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Handle bluetooth discovery."""

        _LOGGER.debug(
            "Discovered eQ3 thermostat using bluetooth: %s, %s",
            discovery_info,
            discovery_info.device.name,
        )
        self.discovery_info = discovery_info
        name = self.discovery_info.device.name or self.discovery_info.name
        self.context.update(
            {
                "title_placeholders": {
                    CONF_NAME: name,
                    CONF_MAC: discovery_info.address,
                    "rssi": discovery_info.device.rssi,
                }
            }
        )
        return await self.async_step_init()

    async def async_step_init(self, user_input=None):
        """Handle a flow start."""
        if self.discovery_info is None:
            # mainly to shut up the type checker
            return self.async_abort(reason="not_supported")
        self._async_abort_entries_match({CONF_MAC: self.discovery_info.address})
        if user_input is None:
            name = self.discovery_info.device.name or self.discovery_info.name
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME, default=name): str,  # type: ignore
                    }
                ),
                description_placeholders={
                    CONF_NAME: name,
                    CONF_MAC: self.discovery_info.address,
                    "rssi": str(self.discovery_info.device.rssi),
                },
            )
        await self.async_set_unique_id(format_mac(self.discovery_info.address))
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={"name": user_input["name"], "mac": self.discovery_info.address},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            )
                        },
                    ): cv.positive_float,
                    vol.Required(
                        CONF_CURRENT_TEMP_SELECTOR,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_CURRENT_TEMP_SELECTOR,
                                DEFAULT_CURRENT_TEMP_SELECTOR,
                            )
                        },
                    ): selector(
                        {
                            "select": {
                                "options": [
                                    {
                                        "label": "nothing",
                                        "value": CurrentTemperatureSelector.NOTHING,
                                    },
                                    {
                                        "label": "target temperature to be set (fast)",
                                        "value": CurrentTemperatureSelector.UI,
                                    },
                                    {
                                        "label": "target temperature in device",
                                        "value": CurrentTemperatureSelector.DEVICE,
                                    },
                                    {
                                        "label": "valve based calculation",
                                        "value": CurrentTemperatureSelector.VALVE,
                                    },
                                    {
                                        "label": "external entity",
                                        "value": CurrentTemperatureSelector.ENTITY,
                                    },
                                ],
                            }
                        }
                    ),
                    vol.Optional(
                        CONF_EXTERNAL_TEMP_SENSOR,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_EXTERNAL_TEMP_SENSOR, ""
                            )
                        },
                    ): selector(
                        {"entity": {"domain": "sensor", "device_class": "temperature"}}
                    ),
                    vol.Required(
                        CONF_ADAPTER,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_ADAPTER, DEFAULT_ADAPTER
                            )
                        },
                    ): selector(
                        {
                            "select": {
                                "options": [
                                    {"label": "Automatic", "value": Adapter.AUTO},
                                    {
                                        "label": "Local adapters only",
                                        "value": Adapter.LOCAL,
                                    },
                                    {
                                        "label": "/org/bluez/hci0",
                                        "value": "/org/bluez/hci0",
                                    },
                                    {
                                        "label": "/org/bluez/hci1",
                                        "value": "/org/bluez/hci1",
                                    },
                                    {
                                        "label": "/org/bluez/hci2",
                                        "value": "/org/bluez/hci2",
                                    },
                                    {
                                        "label": "/org/bluez/hci3",
                                        "value": "/org/bluez/hci3",
                                    },
                                ],
                                "custom_value": True,
                            }
                        }
                    ),
                    vol.Required(
                        CONF_STAY_CONNECTED,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_STAY_CONNECTED, DEFAULT_STAY_CONNECTED
                            )
                        },
                    ): cv.boolean,
                    vol.Required(
                        CONF_DEBUG_MODE,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_DEBUG_MODE, False
                            )
                        },
                    ): cv.boolean,
                }
            ),
        )
