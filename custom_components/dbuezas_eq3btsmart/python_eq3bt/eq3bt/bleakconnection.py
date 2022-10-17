"""
Bleak connection backend.
This creates a new event loop that is used to integrate bleak's
asyncio functions to synchronous architecture of python-eq3bt.
"""
import asyncio
import logging
import asyncio

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from homeassistant.components.esphome.bluetooth.characteristic import (
    BleakGATTCharacteristic,
)

from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth

from . import BackendException

REQUEST_TIMEOUT = 10
RETRIES = 10

# bleak backends are very loud on debug, this reduces the log spam when using --debug
# logging.getLogger("bleak.backends").setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)


class BleakConnection:
    """Representation of a BTLE Connection."""

    def __init__(
        self, mac: str, name: str, hass: HomeAssistant, notification_handle, callback
    ):
        """Initialize the connection."""
        self._mac = mac
        self._name = name
        self._hass = hass
        self._callback = callback
        self._notification_handle = notification_handle
        self._notifyevent = asyncio.Event()
        self.ble_device = None

    @property
    def rssi(self):
        if not self.ble_device:
            return None
        return self.ble_device.rssi

    async def async_get_connection(self):
        if not self.ble_device:
            self.ble_device = bluetooth.async_ble_device_from_address(
                self._hass, self._mac, connectable=True
            )
        if self.ble_device:
            conn = BleakClient(self.ble_device)
        else:
            _LOGGER.debug(
                "[%s]NO ble_device",
                self._name,
            )
            conn = BleakClient(self._mac)
        if not conn.is_connected:
            await conn.connect(timeout=30)
        if not conn.is_connected:
            raise BackendException("Can't connect")
        return conn

    def set_ble_device(self, ble_device: BLEDevice):
        self.ble_device = ble_device

    async def on_notification(self, handle: BleakGATTCharacteristic, data: bytearray):
        """Handle Callback from a Bluetooth (GATT) request."""
        # The notification handles are off-by-one compared to gattlib and bluepy
        # service_handle = handle.handle + 1
        if handle.handle == self._notification_handle:
            self._notifyevent.set()
            self._callback(data)
        else:
            _LOGGER.error(
                "[%s] wrong charasteristic: %s",
                self._name,
                handle.handle,
            )

    async def async_make_request(self, handle: int, value):
        """Write a GATT Command without callback - not utf-8."""
        i = 0
        while True:
            i += 1
            try:
                conn = await self.async_get_connection()
                self._notifyevent.clear()
                await conn.start_notify(self._notification_handle, self.on_notification)
                await conn.write_gatt_char(handle, value)
                await asyncio.wait_for(self._notifyevent.wait(), REQUEST_TIMEOUT)
                await conn.stop_notify(self._notification_handle)
                # await conn.disconnect()
                break

            except Exception as ex:
                _LOGGER.debug(
                    "[%s][%s/%s] BLE Request error: %s", self._name, i, RETRIES, ex
                )
                if i == RETRIES:
                    raise ex
                await asyncio.sleep(5)
