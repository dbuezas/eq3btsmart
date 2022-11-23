"""
Config flow for the EQ3 One Custom Component
Author: herikw
https://github.com/herikw/home-assistant-custom-components
"""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.helpers.device_registry import format_mac
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .climate import EQ3BTSmartThermostat
from .const import DOMAIN
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
        # thermostat = EQ3BTSmartThermostat(
        #     user_input[CONF_MAC], user_input[CONF_NAME], self.hass
        # )
        # # TODO is this the correct way to execute synchronous calls in a config flow?
        # await self.hass.async_add_executor_job(thermostat._thermostat_update)

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
